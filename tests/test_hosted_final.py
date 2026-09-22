import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from test_tabpfn_rest import FIT_ID, TEST_ID, FakeService, response_fixture

from scuba.artifacts import file_hash, write_json
from scuba.contract import GeneratorConfig
from scuba.final_data import digest as final_digest
from scuba.final_data import prepare_final_plan
from scuba.hosted_final import prepare_hosted_plan, review_hosted_test, run_hosted_test
from scuba.integrations.tabpfn_plan import TabPFNConfig, plan_digest, prepare_plan
from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest
from scuba.models.runner import run_comparators
from scuba.pipeline import prepare_bundle


class HostedFinalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = cls.root = Path(cls.temp.name)
        inp, local, prior = root / "input", root / "local", root / "prior"
        prepare_bundle(inp, GeneratorConfig(customers=180))
        expected = file_hash(inp / "manifest.json")
        run_comparators(inp, local, expected)
        frozen = prepare_final_plan(
            inp, local, file_hash(local / "manifest.json"), root / "frozen", expected
        )
        original, _, _ = prepare_plan(inp, TabPFNConfig(), expected)
        prior.mkdir()
        write_json(prior / "plan.json", {"plan": original, "sha256": plan_digest(original)})
        write_json(
            prior / "manifest.json",
            {
                "status": "failed",
                "failure": {"category": "prediction_contract"},
                "classification": "synthetic",
                "phase": "validation_only",
                "test_scored": False,
                "evidence": "offline_mock",
                "plan_sha256": plan_digest(original),
                "integration_attempt": {
                    "fitted_train_set_id": FIT_ID,
                    "test_set_upload_id": TEST_ID,
                    "fresh_preflight": {"plan_sha256": plan_digest(original)},
                },
            },
        )
        cls.sources = {
            "input": str(inp),
            "final_plan": str(root / "frozen/plan.json"),
            "final_plan_sha256": final_digest(frozen),
            "prior_run": str(prior),
            "prior_manifest_sha256": file_hash(prior / "manifest.json"),
        }
        cls.plan, cls.payload, cls.rows = prepare_hosted_plan(**cls.sources)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def service(self, *, wrong_identity=False):
        fixture_plan = copy.deepcopy(self.plan)
        fixture_plan["cohorts"]["validation"] = fixture_plan["cohorts"]["test"]
        service = FakeService(fixture_plan)

        def handler(request):
            response = service(request)
            if request.url.path == "/tabpfn/predict" and response.status_code == 200:
                body = response.json()
                body["metadata"].update(
                    billing_model_version="v3.5", execution_mode="standard", classes=[0, 1]
                )
                response = httpx.Response(200, json=body)
            if wrong_identity and request.url.path == "/tabpfn/predict":
                body = response_fixture(fixture_plan)
                body["metadata"]["tabpfn_config"]["model_path"] = "unknown.ckpt"
                return httpx.Response(200, json=body)
            return response

        return service, handler

    def test_review_is_offline_and_contains_only_test_feature_payload(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("scuba.hosted_final.tabpfn_token") as token,
            patch("socket.socket.connect", side_effect=AssertionError("offline")),
        ):
            plan = review_hosted_test(self.sources, Path(directory) / "review")
            token.assert_not_called()
            self.assertEqual(plan["phase"], "final_test")
            self.assertEqual(set(plan["payloads"]), {"test"})
            self.assertEqual(plan["retained_fitted_train_set_id"], FIT_ID)
            self.assertNotIn("dormant_30d", self.payload.decode().splitlines()[0])
            self.assertNotIn("customer_id", self.payload.decode().splitlines()[0])
            self.assertEqual(plan["estimate_requests"][0]["test_rows"], len(self.rows))

    def test_transport_uploads_only_final_features_then_predicts_once(self):
        service, handler = self.service()
        client = TabPFNRest("fictional-token", transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        captured = []
        p, _ = client.predict_final_test(
            self.plan,
            self.payload,
            allow_upload=True,
            max_tokens=10000,
            response_sink=captured.append,
        )
        self.assertEqual(len(p), len(self.rows))
        self.assertEqual(captured[0]["prediction_partition"], "test")
        self.assertEqual(
            [r.url.path for r in service.requests if r.method != "PUT"],
            [
                "/tabpfn/get_model_limits",
                "/tabpfn/estimate_cost",
                "/tabpfn/prepare_test_set_upload",
                "/tabpfn/predict",
            ],
        )
        self.assertEqual([r.content for r in service.requests if r.method == "PUT"], [self.payload])
        count = len(service.requests)
        with self.assertRaises(IntegrationError):
            client.predict_final_test(self.plan, self.payload, allow_upload=True, max_tokens=10000)
        self.assertEqual(len(service.requests), count)

    def test_budget_payload_and_resource_failures_stop_without_refit(self):
        for case in ("approval", "payload", "budget", "expired", "timeout"):
            with self.subTest(case=case):
                service, handler = self.service()
                if case == "budget":
                    service.cost = 10001
                if case == "expired":
                    service.fail_path, service.status = "/tabpfn/prepare_test_set_upload", 404
                if case == "timeout":
                    service.timeout_path = "/tabpfn/predict"
                client = TabPFNRest("fictional-token", transport=httpx.MockTransport(handler))
                with self.assertRaises(IntegrationError):
                    client.predict_final_test(
                        self.plan,
                        self.payload + b"changed" if case == "payload" else self.payload,
                        allow_upload=case != "approval",
                        max_tokens=10000,
                    )
                client.close()
                paths = [r.url.path for r in service.requests]
                self.assertNotIn("/tabpfn/fit", paths)
                self.assertNotIn("/tabpfn/prepare_train_set_upload", paths)
                self.assertEqual(paths.count("/tabpfn/predict"), 1 if case == "timeout" else 0)
                if case in ("approval", "payload"):
                    self.assertFalse(paths)

    def test_runner_preserves_failure_and_requires_approval_before_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review_hosted_test(self.sources, root / "review")
            approved = root / "review/plan.json"
            with patch("scuba.hosted_final.tabpfn_token") as token:
                with self.assertRaises(IntegrationError):
                    run_hosted_test(approved, plan_digest(self.plan), root / "missing")
                with self.assertRaises(IntegrationError):
                    run_hosted_test(
                        approved,
                        plan_digest(self.plan),
                        root / "mock-live",
                        allow_upload=True,
                        max_tokens=10000,
                    )
                token.assert_not_called()
            for wrong in (False, True):
                service, handler = self.service(wrong_identity=wrong)

                def factory(token):
                    return TabPFNRest(token, transport=httpx.MockTransport(handler))

                output = root / str(wrong)
                with patch("scuba.hosted_final.tabpfn_token", return_value="fictional-token"):
                    if wrong:
                        with self.assertRaises(IntegrationError):
                            run_hosted_test(
                                approved,
                                plan_digest(self.plan),
                                output,
                                allow_upload=True,
                                max_tokens=10000,
                                client_factory=factory,
                            )
                    else:
                        result = run_hosted_test(
                            approved,
                            plan_digest(self.plan),
                            output,
                            allow_upload=True,
                            max_tokens=10000,
                            client_factory=factory,
                        )
                        self.assertEqual(result["evidence"], "offline_mock")
                        self.assertTrue(result["test_scored"])
                saved = json.loads((output / "response_evidence.json").read_text())
                self.assertEqual(saved["prediction_partition"], "test")
                self.assertEqual((output / "test_predictions.csv").exists(), not wrong)
                self.assertFalse((output / "validation_predictions.csv").exists())

    def test_offline_final_comparison_rechecks_identity_labels_and_cohort(self):
        from scuba.artifacts import write_table
        from scuba.hosted_final_evaluation import evaluate_hosted_final
        from scuba.models.runner import PREDICTION_SCHEMA, validation_metrics

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review_hosted_test(self.sources, root / "review")
            _, handler = self.service()

            def factory(token):
                return TabPFNRest(token, transport=httpx.MockTransport(handler))

            hosted = root / "hosted"
            with patch("scuba.hosted_final.tabpfn_token", return_value="fictional-token"):
                run_hosted_test(
                    root / "review/plan.json",
                    plan_digest(self.plan),
                    hosted,
                    allow_upload=True,
                    max_tokens=10000,
                    client_factory=factory,
                )
            local = root / "local"
            local.mkdir()
            models = {}
            for name in ("catboost", "xgboost", "logistic_regression", "constant_prior"):
                folder = local / name / "repeat-1"
                folder.mkdir(parents=True)
                reference = write_table(
                    folder / "test_predictions.csv",
                    [
                        {
                            "customer_id": r["customer_id"],
                            "prediction_date": r["prediction_date"],
                            "dormant_30d": r["dormant_30d"],
                            "probability_dormant": "0.5",
                            "is_synthetic": "true",
                        }
                        for r in self.rows
                    ],
                    PREDICTION_SCHEMA,
                )
                models[name] = {
                    "repetitions": [
                        {
                            "predictions": {"test": reference},
                            "metrics": {
                                "test": validation_metrics(
                                    [r["dormant_30d"] for r in self.rows], [0.5] * len(self.rows)
                                )
                            },
                        }
                    ]
                }
            frozen = json.loads((self.root / "frozen/plan.json").read_text())["plan"]
            lm = {
                "status": "complete",
                "phase": "M4_final",
                "classification": "synthetic",
                "test_scored": True,
                "regime": "temporal",
                "models": models,
                "plan_sha256": self.plan["final_plan_sha256"],
                "input_files": frozen["input_files"],
            }
            write_json(local / "manifest.json", lm)
            hh, lh = file_hash(hosted / "manifest.json"), file_hash(local / "manifest.json")
            with patch("socket.socket.connect", side_effect=AssertionError("offline")):
                with self.assertRaisesRegex(ValueError, "verified hosted"):
                    evaluate_hosted_final(hosted, hh, local, lh, root / "reject-mock")
                a = evaluate_hosted_final(hosted, hh, local, lh, root / "result", allow_mock=True)
                b = evaluate_hosted_final(hosted, hh, local, lh, root / "replay", allow_mock=True)
                self.assertEqual(a, b)
                self.assertIn("hosted_plus_minus_xgboost", a["overall"]["paired_comparisons"])
                self.assertEqual(a["overall"]["rows"], len(self.rows))
                lm["regime"] = "random_reference"
                write_json(local / "manifest.json", lm)
                with self.assertRaisesRegex(ValueError, "temporal"):
                    evaluate_hosted_final(
                        hosted,
                        hh,
                        local,
                        file_hash(local / "manifest.json"),
                        root / "wrong",
                        allow_mock=True,
                    )
                with (hosted / "response_evidence.json").open("a") as stream:
                    stream.write(" ")
                with self.assertRaisesRegex(ValueError, "captured response changed"):
                    evaluate_hosted_final(hosted, hh, local, lh, root / "tampered", allow_mock=True)
