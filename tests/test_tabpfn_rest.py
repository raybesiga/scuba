import copy
import json
import tempfile
import time
import unittest
from itertools import count
from pathlib import Path
from unittest.mock import patch

import httpx
import numpy as np
from test_tabpfn_plan import limits_fixture

from scuba.artifacts import file_hash
from scuba.contract import GeneratorConfig
from scuba.integrations.tabpfn_plan import TabPFNConfig, prepare_plan
from scuba.integrations.tabpfn_rest import (
    IntegrationError,
    TabPFNRest,
    prediction_diagnostics,
    validate_prediction,
)
from scuba.pipeline import prepare_bundle

TRAIN_ID = "00000000-0000-4000-8000-000000000001"
FIT_ID = "00000000-0000-4000-8000-000000000002"
TEST_ID = "00000000-0000-4000-8000-000000000003"


def signed_info(name):
    return {
        "signed_urls": [
            f"https://storage.googleapis.com/scuba-fictional/{name}?signature=fictional"
        ],
        "expires_at": time.time() + 3600,
        "required_headers": {
            "Content-Type": "text/csv",
            "Host": "storage.googleapis.com",
            "X-Goog-Content-Length-Range": "0,5368709120",
        },
    }


def response_fixture(plan):
    return {
        "prediction": [[0.75, 0.25]] * plan["cohorts"]["validation"]["rows"],
        "metadata": {
            "test_set_num_rows": plan["cohorts"]["validation"]["rows"],
            "test_set_num_cols": len(plan["feature_columns"]),
            "task": "classification",
            "package_version": "9.0.0",
            "tabpfn_config": TabPFNConfig(**plan["configuration"]).model_parameters(),
        },
    }


class FakeService:
    def __init__(self, plan):
        self.plan, self.requests = plan, []
        self.fail_path, self.status, self.message = None, 401, "fictional-sensitive-response"
        self.timeout_path = None
        self.duplicate = False
        self.cost = 10000

    def __call__(self, request):
        self.requests.append(request)
        path = request.url.path
        if path == self.timeout_path:
            raise httpx.ReadTimeout("fictional-token and signed URL must not leak", request=request)
        if path == self.fail_path:
            return httpx.Response(self.status, json={"detail": self.message})
        if request.method == "PUT":
            return httpx.Response(200)
        if path.endswith("get_model_limits"):
            return httpx.Response(200, json=limits_fixture())
        if path.endswith("estimate_cost"):
            return httpx.Response(
                200,
                json={
                    "estimated_cost": self.cost,
                    "pricing_version": "fixture-rate",
                    "inputs": json.loads(request.content),
                },
            )
        if path.endswith("prepare_train_set_upload"):
            if self.duplicate:
                return httpx.Response(409, json={"train_set_upload_id": TRAIN_ID})
            return httpx.Response(
                200,
                json={
                    "train_set_upload_id": TRAIN_ID,
                    "x_train_info": signed_info("train"),
                    "y_train_info": signed_info("labels"),
                },
            )
        if path.endswith("/fit"):
            return httpx.Response(
                200, content=" \n\t" + json.dumps({"fitted_train_set_id": FIT_ID})
            )
        if path.endswith("prepare_test_set_upload"):
            if self.duplicate:
                return httpx.Response(409, json={"test_set_upload_id": TEST_ID})
            return httpx.Response(
                200, json={"test_set_upload_id": TEST_ID, "x_test_info": signed_info("validation")}
            )
        if path.endswith("/predict"):
            return httpx.Response(200, json=response_fixture(self.plan))
        raise AssertionError(f"Unexpected mock route: {path}")


class RestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name) / "input"
        prepare_bundle(root, GeneratorConfig(customers=180))
        cls.plan, cls.payloads, _ = prepare_plan(
            root, TabPFNConfig(), file_hash(root / "manifest.json")
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def client(self, service):
        client = TabPFNRest("fictional-token", transport=httpx.MockTransport(service))
        self.addCleanup(client.close)
        return client

    def test_no_upload_without_explicit_approval_and_budget(self):
        for options in ({}, {"allow_upload": True}, {"allow_upload": True, "max_tokens": 0}):
            service = FakeService(self.plan)
            with self.assertRaises(IntegrationError):
                self.client(service).execute(self.plan, self.payloads, **options)
            self.assertEqual(service.requests, [])

    def test_metadata_only_preflight_and_budget_check(self):
        service = FakeService(self.plan)
        client = self.client(service)
        result = client.preflight(self.plan)
        self.assertEqual(result["estimated_total_tokens"], 10000)
        self.assertEqual(result["rows_uploaded"], 0)
        self.assertEqual(
            [r.url.path for r in service.requests],
            ["/tabpfn/get_model_limits", "/tabpfn/estimate_cost"],
        )
        self.assertEqual(json.loads(service.requests[1].content), self.plan["estimate_requests"][0])
        with self.assertRaises(IntegrationError) as raised:
            client.execute(self.plan, self.payloads, allow_upload=True, max_tokens=9999)
        self.assertEqual(raised.exception.category, "approved_estimate_budget_exceeded")
        self.assertFalse(any("upload" in r.url.path for r in service.requests))

    def test_slower_signed_upload_has_bounded_transfer_time_without_retries(self):
        service = FakeService(self.plan)

        def slow_upload(request):
            timeouts = request.extensions["timeout"]
            if request.method == "PUT":
                if timeouts["write"] < 60 or timeouts["read"] < 60:
                    raise httpx.WriteTimeout("fictional slow transfer", request=request)
                self.assertLessEqual(timeouts["write"], 180)
                self.assertLessEqual(timeouts["read"], 180)
            else:
                self.assertEqual(timeouts["read"], 30)
            self.assertEqual(timeouts["connect"], 10)
            return service(request)

        probability, _ = self.client(slow_upload).execute(
            self.plan, self.payloads, allow_upload=True, max_tokens=10000
        )
        self.assertEqual(len(probability), self.plan["cohorts"]["validation"]["rows"])
        self.assertEqual(sum(r.method == "PUT" for r in service.requests), 3)
        self.assertEqual(sum(r.url.path.endswith("/predict") for r in service.requests), 1)

    def test_full_flow_offline_and_auth_header_separation(self):
        service = FakeService(self.plan)
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            probability, evidence = self.client(service).execute(
                self.plan, self.payloads, allow_upload=True, max_tokens=10000
            )
        np.testing.assert_array_equal(probability, [0.25] * len(probability))
        uploads = [r for r in service.requests if r.method == "PUT"]
        self.assertEqual(len(uploads), 3)
        self.assertEqual(
            [r.content for r in uploads],
            [self.payloads[k] for k in ("train", "labels", "validation")],
        )
        self.assertTrue(all("Authorization" not in r.headers for r in uploads))
        self.assertTrue(all(r.headers["Host"] == "storage.googleapis.com" for r in uploads))
        self.assertTrue(
            all(
                r.headers["Authorization"] == "Bearer fictional-token"
                for r in service.requests
                if r.url.host == "api.priorlabs.ai"
            )
        )
        self.assertNotIn("fictional-token", json.dumps(evidence))
        self.assertNotIn("signature=", json.dumps(evidence))
        self.assertIsNone(evidence["actual_tokens"])
        predict = json.loads(service.requests[-1].content)
        self.assertEqual(predict["task_config"]["predict_params"]["output_type"], "probas")
        self.assertEqual(predict["task_config"]["tabpfn_config"]["model_path"], "v3.5_default")

    def test_duplicate_uploads_reuse_ids(self):
        service = FakeService(self.plan)
        service.duplicate = True
        self.client(service).execute(self.plan, self.payloads, allow_upload=True, max_tokens=10000)
        self.assertFalse(any(r.method == "PUT" for r in service.requests))

    def test_errors_are_sanitised_and_never_retried(self):
        for status, message, category in (
            (401, "secret", "authentication"),
            (403, "secret", "access_denied"),
            (422, "secret", "schema_or_data"),
            (429, "daily quota secret", "quota_exhausted"),
            (429, "request rate secret", "rate_limit"),
            (500, "secret", "http_failure"),
        ):
            service = FakeService(self.plan)
            service.fail_path, service.status, service.message = "/tabpfn/predict", status, message
            with (
                self.subTest(status=status, category=category),
                self.assertRaises(IntegrationError) as raised,
            ):
                self.client(service).execute(
                    self.plan, self.payloads, allow_upload=True, max_tokens=10000
                )
            self.assertEqual(raised.exception.category, category)
            self.assertTrue(raised.exception.billing_uncertain)
            self.assertNotIn("secret", str(raised.exception))
            self.assertEqual(sum(r.url.path == "/tabpfn/predict" for r in service.requests), 1)
        service = FakeService(self.plan)
        service.timeout_path = "/tabpfn/predict"
        with self.assertRaises(IntegrationError) as raised:
            self.client(service).execute(
                self.plan, self.payloads, allow_upload=True, max_tokens=10000
            )
        self.assertEqual(raised.exception.category, "timeout")
        self.assertNotIn("fictional-token", str(raised.exception))

    def test_total_deadline_catches_keepalive_streams(self):
        service = FakeService(self.plan)
        client = self.client(service)
        with patch("scuba.integrations.tabpfn_rest.time.perf_counter", side_effect=count(0, 2)):
            with self.assertRaises(IntegrationError) as raised:
                client._api("POST", "/tabpfn/predict", billable=True, timeout=1)
        self.assertEqual(raised.exception.category, "timeout")
        self.assertTrue(raised.exception.billing_uncertain)
        self.assertEqual(len(service.requests), 1)

    def test_payload_tampering_and_unsafe_upload_rejected(self):
        service = FakeService(self.plan)
        with self.assertRaises(IntegrationError):
            self.client(service).execute(
                self.plan,
                {**self.payloads, "train": b"changed"},
                allow_upload=True,
                max_tokens=10000,
            )
        self.assertEqual(service.requests, [])
        for change in (
            {"signed_urls": ["http://storage.googleapis.com/file"]},
            {"signed_urls": ["https://unapproved.invalid/file"]},
            {"expires_at": 0},
            {"required_headers": {"Authorization": "must-not-forward"}},
            {"required_headers": {"Host": "unapproved.invalid"}},
            {"required_headers": {"Host": "storage.googleapis.com:444"}},
            {"required_headers": {"Host": "storage.googleapis.com", "host": "elsewhere.invalid"}},
        ):
            with self.assertRaises(IntegrationError):
                self.client(service)._upload(
                    {**signed_info("test"), **change}, b"fictional", "upload"
                )
        self.assertEqual(service.requests, [])

    def test_bad_prediction_shape_values_or_identity_rejected(self):
        fixture = response_fixture(self.plan)
        for mutate in (
            lambda r: r.update(prediction=[[0.75, 0.25]]),
            lambda r: r["prediction"].__setitem__(0, [0.8, 0.8]),
            lambda r: r["prediction"].__setitem__(0, [float("nan"), 0.2]),
            lambda r: r["metadata"]["tabpfn_config"].update(model_path="auto"),
            lambda r: r["metadata"]["tabpfn_config"].update(n_estimators=1),
            lambda r: r["metadata"].update(test_set_num_rows=1),
        ):
            bad = copy.deepcopy(fixture)
            mutate(bad)
            with self.assertRaises(IntegrationError):
                validate_prediction(self.plan, bad)

    def test_unverified_evidence_excludes_arbitrary_remote_values(self):
        response = response_fixture(self.plan)
        response["metadata"]["tabpfn_config"]["model_path"] = "fictional-secret-url"
        response["metadata"]["package_version"] = "fictional-sensitive-body"
        response["detail"] = "fictional-token"
        evidence = prediction_diagnostics(self.plan, response)
        self.assertFalse(evidence["checks"]["model_path"])
        self.assertFalse(evidence["checks"]["package_version"])
        self.assertTrue(evidence["checks"]["probabilities"])
        self.assertEqual(evidence["prediction"], response["prediction"])
        self.assertNotIn("fictional-token", json.dumps(evidence))
        self.assertNotIn("fictional-secret-url", json.dumps(evidence))
        for identifier in ("v3.5_default", "tabpfn-v3.5-classifier-fictional.ckpt"):
            response["metadata"]["tabpfn_config"]["model_path"] = identifier
            observed = prediction_diagnostics(self.plan, response)["reported_model_identity"]
            self.assertEqual(observed["type"], "str")
            self.assertEqual(observed["value"], identifier)
        for identifier in ("password=hidden", None):
            response["metadata"]["tabpfn_config"]["model_path"] = identifier
            observed = prediction_diagnostics(self.plan, response)["reported_model_identity"]
            self.assertIsNone(observed["value"])
        for value in (None, {"token": "fictional-secret"}, [[float("nan"), 1]], [[0.8, 0.8]]):
            response["prediction"] = value
            evidence = prediction_diagnostics(self.plan, response)
            self.assertIsNone(evidence["prediction"])
            self.assertFalse(evidence["checks"]["probabilities"])
            json.dumps(evidence, allow_nan=False)

    def test_captured_checkpoint_does_not_relax_identity_acceptance(self):
        for identifier in (
            "tabpfn-v3.5-classifier-example.ckpt",
            "v3.5-fast_default",
            "v3_default",
            None,
            ["v3.5_default"],
            {"model": "v3.5_default"},
        ):
            response = response_fixture(self.plan)
            response["metadata"]["tabpfn_config"]["model_path"] = identifier
            observed = prediction_diagnostics(self.plan, response)
            self.assertFalse(observed["checks"]["model_path"])
            self.assertEqual(observed["reported_model_identity"]["type"], type(identifier).__name__)
            with self.assertRaises(IntegrationError):
                validate_prediction(self.plan, response)
        response = response_fixture(self.plan)
        del response["metadata"]["tabpfn_config"]["model_path"]
        observed = prediction_diagnostics(self.plan, response)
        self.assertEqual(observed["reported_model_identity"]["status"], "missing")
        with self.assertRaises(IntegrationError):
            validate_prediction(self.plan, response)

    def test_diagnostics_retain_unfamiliar_path_and_reported_settings(self):
        response = response_fixture(self.plan)
        response["metadata"]["tabpfn_config"]["model_path"] = "/opt/models/revision-42.bin"
        response["metadata"]["billing_model_version"] = "v3.5"
        evidence = prediction_diagnostics(self.plan, response)
        self.assertEqual(
            evidence["reported_model_identity"]["value"], "/opt/models/revision-42.bin"
        )
        self.assertEqual(evidence["reported_metadata"]["package_version"]["value"], "9.0.0")
        self.assertEqual(evidence["reported_metadata"]["billing_model_version"]["value"], "v3.5")
        self.assertEqual(evidence["reported_configuration"]["n_estimators"]["value"], 8)
        self.assertEqual(evidence["requested_configuration"]["model_path"], "v3.5_default")
        self.assertFalse(evidence["checks"]["model_path"])

    def test_response_inventory_distinguishes_discarded_fields_from_absent_fields(self):
        response = response_fixture(self.plan)
        response["metadata"]["feature_names"] = ["fictional-private-feature"]
        response["timings"] = {"opaque": "fictional-private-value"}
        response["metadata"]["test_set_num_cols"] += 2
        evidence = prediction_diagnostics(self.plan, response)
        inventory = evidence["response_field_inventory"]
        self.assertIn(
            {"name": "feature_names", "type": "list", "length": 1},
            inventory["metadata"]["fields"],
        )
        self.assertIn(
            {"name": "timings", "type": "dict", "length": 1},
            inventory["top_level"]["fields"],
        )
        self.assertFalse(evidence["raw_response_preserved"])
        self.assertNotIn("fictional-private", json.dumps(evidence))
        self.assertFalse(evidence["checks"]["columns"])
        with self.assertRaises(IntegrationError):
            validate_prediction(self.plan, response)

    def test_echoed_api_credential_is_redacted_before_evidence_sink(self):
        service = FakeService(self.plan)
        captured = []

        def handler(request):
            if request.url.path == "/tabpfn/predict":
                service.requests.append(request)
                response = response_fixture(self.plan)
                response["metadata"]["package_version"] = "1.2.3-opaque123456789"
                return httpx.Response(200, json=response)
            return service(request)

        client = TabPFNRest("opaque123456789", transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        with self.assertRaises(IntegrationError):
            client.execute(
                self.plan,
                self.payloads,
                allow_upload=True,
                max_tokens=10000,
                response_sink=captured.append,
            )
        self.assertEqual(len(captured), 1)
        self.assertNotIn("opaque123456789", json.dumps(captured))
        self.assertEqual(
            captured[0]["reported_metadata"]["package_version"]["reason"], "known_credential"
        )
        self.assertEqual(sum(r.url.path == "/tabpfn/predict" for r in service.requests), 1)

    def test_existing_resources_only_estimate_and_predict_once(self):
        service = FakeService(self.plan)
        client = self.client(service)
        captured = []
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            probability, result = client.predict_existing(
                self.plan,
                FIT_ID,
                TEST_ID,
                allow_predict=True,
                max_tokens=10000,
                response_sink=captured.append,
            )
        self.assertEqual(len(probability), self.plan["cohorts"]["validation"]["rows"])
        self.assertEqual(len(captured), 1)
        self.assertEqual(
            [r.url.path for r in service.requests],
            ["/tabpfn/get_model_limits", "/tabpfn/estimate_cost", "/tabpfn/predict"],
        )
        request = json.loads(service.requests[-1].content)
        self.assertEqual(request["fitted_train_set_id"], FIT_ID)
        self.assertEqual(request["test_set_upload_id"], TEST_ID)
        self.assertEqual(result["approved_estimate_budget"], 10000)
        with self.assertRaises(IntegrationError):
            client.predict_existing(
                self.plan, FIT_ID, TEST_ID, allow_predict=True, max_tokens=10000
            )
        self.assertEqual(len(service.requests), 3)

    def test_existing_resource_guard_budget_and_failures_never_refit_or_retry(self):
        for options in ({}, {"allow_predict": True}, {"allow_predict": True, "max_tokens": 0}):
            service = FakeService(self.plan)
            with self.assertRaises(IntegrationError):
                self.client(service).predict_existing(self.plan, FIT_ID, TEST_ID, **options)
            self.assertEqual(service.requests, [])
        for status in (404, 429, 500, "timeout", "budget"):
            with self.subTest(status=status):
                service = FakeService(self.plan)
                if status == "timeout":
                    service.timeout_path = "/tabpfn/predict"
                elif status == "budget":
                    service.cost = 10001
                else:
                    service.fail_path, service.status = "/tabpfn/predict", status
                client = self.client(service)
                with self.assertRaises(IntegrationError):
                    client.predict_existing(
                        self.plan, FIT_ID, TEST_ID, allow_predict=True, max_tokens=10000
                    )
                paths = [r.url.path for r in service.requests]
                self.assertEqual(paths.count("/tabpfn/predict"), 0 if status == "budget" else 1)
                self.assertTrue(
                    all(
                        p
                        in ("/tabpfn/get_model_limits", "/tabpfn/estimate_cost", "/tabpfn/predict")
                        for p in paths
                    )
                )
                if status != "budget":
                    with self.assertRaises(IntegrationError):
                        client.predict_existing(
                            self.plan, FIT_ID, TEST_ID, allow_predict=True, max_tokens=10000
                        )
                    self.assertEqual(len(service.requests), len(paths))

    def test_existing_resource_contract_failure_preserves_response_and_stops(self):
        service = FakeService(self.plan)
        captured = []

        def handler(request):
            if request.url.path == "/tabpfn/predict":
                service.requests.append(request)
                response = response_fixture(self.plan)
                response["metadata"]["tabpfn_config"]["model_path"] = "/models/unknown.ckpt"
                return httpx.Response(200, json=response)
            return service(request)

        client = self.client(handler)
        with self.assertRaises(IntegrationError):
            client.predict_existing(
                self.plan,
                FIT_ID,
                TEST_ID,
                allow_predict=True,
                max_tokens=10000,
                response_sink=captured.append,
            )
        self.assertEqual(captured[0]["reported_model_identity"]["value"], "/models/unknown.ckpt")
        self.assertFalse(captured[0]["checks"]["model_path"])
        self.assertEqual(sum(r.url.path == "/tabpfn/predict" for r in service.requests), 1)
