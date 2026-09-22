import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

import httpx
from test_tabpfn_rest import FIT_ID, TEST_ID, FakeService, response_fixture

from scuba.artifacts import file_hash, write_json
from scuba.cli import main
from scuba.contract import GeneratorConfig
from scuba.integrations.tabpfn_plan import TabPFNConfig, plan_digest, prepare_plan
from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest
from scuba.integrations.tabpfn_runner import continue_prediction
from scuba.pipeline import prepare_bundle


class ContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.input = Path(cls.temp.name) / "input"
        prepare_bundle(cls.input, GeneratorConfig(customers=180))
        cls.expected = file_hash(cls.input / "manifest.json")
        cls.plan, _, _ = prepare_plan(cls.input, TabPFNConfig(), cls.expected)
        cls.source = {
            "status": "failed",
            "evidence": "offline_mock",
            "classification": "synthetic",
            "phase": "validation_only",
            "test_scored": False,
            "plan_sha256": plan_digest(cls.plan),
            "failure": {"category": "prediction_contract"},
            "integration_attempt": {
                "fitted_train_set_id": FIT_ID,
                "test_set_upload_id": TEST_ID,
                "fresh_preflight": {"plan_sha256": plan_digest(cls.plan)},
            },
        }

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def source_bundle(self, directory):
        prior = Path(directory) / "prior"
        prior.mkdir()
        write_json(prior / "manifest.json", self.source)
        write_json(prior / "plan.json", {"plan": self.plan, "sha256": plan_digest(self.plan)})
        return prior, file_hash(prior / "manifest.json")

    def run_continuation(self, prior, digest, output, **kwargs):
        return continue_prediction(
            self.input, prior, digest, output, expected_manifest_hash=self.expected, **kwargs
        )

    def test_offline_review_never_loads_credentials_or_connects_and_preserves_source(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("scuba.integrations.tabpfn_runner.tabpfn_token") as token,
            patch("socket.socket.connect", side_effect=AssertionError("network forbidden")),
        ):
            prior, digest = self.source_bundle(directory)
            before = {p.name: file_hash(p) for p in prior.iterdir()}
            output = Path(directory) / "review"
            result = self.run_continuation(prior, digest, output)
            token.assert_not_called()
            self.assertEqual(result["status"], "awaiting_prediction_approval")
            self.assertEqual(result["evidence"], "offline_plan")
            self.assertEqual(result["plan_sha256"], plan_digest(self.plan))
            review = json.loads((output / "continuation.json").read_text())
            self.assertEqual(review["fitted_train_set_id"], FIT_ID)
            self.assertEqual(review["test_set_upload_id"], TEST_ID)
            self.assertEqual(review["prediction_request_limit"], 1)
            self.assertEqual(review["rows_uploaded"], 0)
            self.assertEqual(review["fit_requests"], 0)
            self.assertEqual(before, {p.name: file_hash(p) for p in prior.iterdir()})
            with self.assertRaises(FileExistsError):
                self.run_continuation(prior, digest, output)

    def test_budget_required_before_loading_credentials_or_creating_output(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("scuba.integrations.tabpfn_runner.tabpfn_token") as token,
        ):
            prior, digest = self.source_bundle(directory)
            for budget in (None, 0, -1, True):
                output = Path(directory) / str(budget)
                with self.assertRaises(IntegrationError) as raised:
                    self.run_continuation(
                        prior, digest, output, allow_predict=True, max_tokens=budget
                    )
                self.assertEqual(
                    raised.exception.category, "prediction_and_positive_budget_approval_required"
                )
                self.assertFalse(output.exists())
            token.assert_not_called()

    def test_modified_source_plan_and_unsupported_sources_stop_before_credentials(self):
        for case in ("hash", "plan", "chain", "test", "phase", "id", "preflight", "mock"):
            with (
                self.subTest(case=case),
                tempfile.TemporaryDirectory() as directory,
                patch("scuba.integrations.tabpfn_runner.tabpfn_token") as token,
            ):
                prior, digest = self.source_bundle(directory)
                source = copy.deepcopy(self.source)
                expected_category = "unsupported_continuation_source"
                if case == "hash":
                    digest = "0" * 64
                    expected_category = "source_manifest_changed"
                elif case == "plan":
                    changed = copy.deepcopy(self.plan)
                    changed["payloads"]["train"]["sha256"] = "changed"
                    write_json(
                        prior / "plan.json", {"plan": changed, "sha256": plan_digest(changed)}
                    )
                    expected_category = "approved_plan_changed"
                elif case == "chain":
                    source["mode"] = "prediction_only"
                elif case == "test":
                    source["test_scored"] = True
                elif case == "phase":
                    source["phase"] = "test"
                elif case == "id":
                    source["integration_attempt"]["test_set_upload_id"] = "invalid"
                    expected_category = "invalid_resource_id"
                elif case == "preflight":
                    source["integration_attempt"]["fresh_preflight"]["plan_sha256"] = "changed"
                else:
                    expected_category = "mock_source_cannot_be_used_live"
                if case not in ("hash", "plan"):
                    write_json(prior / "manifest.json", source)
                    digest = file_hash(prior / "manifest.json")
                with self.assertRaises(IntegrationError) as raised:
                    self.run_continuation(
                        prior, digest, Path(directory) / "run", allow_predict=True, max_tokens=10000
                    )
                self.assertEqual(raised.exception.category, expected_category)
                token.assert_not_called()

    def test_mock_continuation_captures_before_validation_without_upload_or_fit(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("scuba.integrations.tabpfn_runner.tabpfn_token", return_value="fictional-token"),
        ):
            prior, digest = self.source_bundle(directory)
            output = Path(directory) / "run"
            service = FakeService(self.plan)

            def factory(token):
                return TabPFNRest(token, transport=httpx.MockTransport(service))

            from scuba.integrations.tabpfn_rest import validate_prediction

            def inspect_then_validate(plan, response):
                saved = json.loads((output / "response_evidence.json").read_text())
                manifest = json.loads((output / "manifest.json").read_text())
                self.assertEqual(saved["prediction"], response["prediction"])
                self.assertEqual(
                    manifest["response_evidence"]["sha256"],
                    file_hash(output / "response_evidence.json"),
                )
                self.assertEqual(manifest["integration_attempt"]["fitted_train_set_id"], FIT_ID)
                self.assertFalse((output / "validation_predictions.csv").exists())
                return validate_prediction(plan, response)

            with patch("scuba.integrations.tabpfn_rest.validate_prediction", inspect_then_validate):
                result = self.run_continuation(
                    prior,
                    digest,
                    output,
                    allow_predict=True,
                    max_tokens=10000,
                    client_factory=factory,
                )
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["evidence"], "offline_mock")
            self.assertFalse(result["test_scored"])
            self.assertEqual(result["rows_uploaded"], 0)
            self.assertEqual(
                [r.url.path for r in service.requests],
                ["/tabpfn/get_model_limits", "/tabpfn/estimate_cost", "/tabpfn/predict"],
            )
            self.assertEqual(file_hash(prior / "manifest.json"), digest)

    def test_rejected_identity_and_expired_resources_stop_with_evidence(self):
        for case in ("identity", "expired"):
            with (
                self.subTest(case=case),
                tempfile.TemporaryDirectory() as directory,
                patch(
                    "scuba.integrations.tabpfn_runner.tabpfn_token", return_value="fictional-token"
                ),
            ):
                prior, digest = self.source_bundle(directory)
                output = Path(directory) / "run"
                service = FakeService(self.plan)
                if case == "expired":
                    service.fail_path, service.status = "/tabpfn/predict", 404

                def handler(request):
                    response = service(request)
                    if case == "identity" and request.url.path == "/tabpfn/predict":
                        response = response_fixture(self.plan)
                        response["metadata"]["tabpfn_config"]["model_path"] = "/models/unknown.ckpt"
                        return httpx.Response(200, json=response)
                    return response

                def factory(token):
                    return TabPFNRest(token, transport=httpx.MockTransport(handler))

                with self.assertRaises(IntegrationError):
                    self.run_continuation(
                        prior,
                        digest,
                        output,
                        allow_predict=True,
                        max_tokens=10000,
                        client_factory=factory,
                    )
                manifest = json.loads((output / "manifest.json").read_text())
                self.assertEqual(manifest["status"], "failed")
                self.assertNotIn("metrics", manifest)
                self.assertFalse((output / "validation_predictions.csv").exists())
                self.assertEqual(
                    [r.url.path for r in service.requests],
                    ["/tabpfn/get_model_limits", "/tabpfn/estimate_cost", "/tabpfn/predict"],
                )
                if case == "identity":
                    evidence = json.loads((output / "response_evidence.json").read_text())
                    self.assertEqual(
                        evidence["reported_model_identity"]["value"], "/models/unknown.ckpt"
                    )
                    self.assertTrue(evidence["checks"]["probabilities"])
                    self.assertFalse(evidence["checks"]["model_path"])
                else:
                    self.assertNotIn("response_evidence", manifest)
                self.assertEqual(file_hash(prior / "manifest.json"), digest)

    def test_cli_prediction_flag_requires_budget_before_input_or_credentials(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("scuba.integrations.tabpfn_runner.tabpfn_token") as token,
            redirect_stderr(io.StringIO()) as stderr,
        ):
            with self.assertRaises(SystemExit) as raised:
                main(
                    [
                        "tabpfn-continue",
                        "--input",
                        "missing",
                        "--prior-run",
                        "missing",
                        "--source-manifest-sha256",
                        "0" * 64,
                        "--output",
                        str(Path(directory) / "run"),
                        "--allow-predict",
                    ]
                )
            self.assertEqual(raised.exception.code, 2)
            self.assertIn("prediction_and_positive_budget_approval_required", stderr.getvalue())
            token.assert_not_called()
