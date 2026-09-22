import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

import httpx
from test_tabpfn_rest import FakeService, response_fixture

from scuba.artifacts import file_hash, write_json
from scuba.cli import main
from scuba.contract import GeneratorConfig
from scuba.integrations.tabpfn_plan import TabPFNConfig, prepare_plan
from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest
from scuba.integrations.tabpfn_runner import preflight_bundle, run_approved
from scuba.pipeline import prepare_bundle


class TabPFNRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / "input"
        prepare_bundle(cls.root, GeneratorConfig(customers=180))
        cls.expected = file_hash(cls.root / "manifest.json")
        cls.plan, _, _ = prepare_plan(cls.root, TabPFNConfig(), cls.expected)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_offline_plan_never_loads_token_or_network(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch(
                "scuba.integrations.tabpfn_runner.tabpfn_token",
                side_effect=AssertionError("must not load token"),
            ),
            patch("socket.socket.connect", side_effect=AssertionError("network forbidden")),
        ):
            output = Path(directory) / "plan"
            result = preflight_bundle(
                self.root, output, TabPFNConfig(), expected_manifest_hash=self.expected
            )
            self.assertEqual(result["evidence"], "offline_plan")
            self.assertEqual(result["rows_uploaded"], 0)
            self.assertEqual(
                result["row_provenance"]["rows"],
                sum(self.plan["cohorts"][key]["rows"] for key in ("train", "validation")),
            )
            self.assertEqual(json.loads((output / "plan.json").read_text())["plan"], self.plan)
            with self.assertRaises(FileExistsError):
                preflight_bundle(
                    self.root, output, TabPFNConfig(), expected_manifest_hash=self.expected
                )

    def test_changed_plan_stops_before_token_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preflight_bundle(
                self.root, root / "plan", TabPFNConfig(), expected_manifest_hash=self.expected
            )
            path = root / "plan/plan.json"
            bad = json.loads(path.read_text())
            bad["plan"]["payloads"]["train"]["sha256"] = "changed"
            write_json(path, bad)
            with patch(
                "scuba.integrations.tabpfn_runner.tabpfn_token",
                side_effect=AssertionError("must not load token"),
            ):
                with self.assertRaises(IntegrationError) as raised:
                    run_approved(
                        self.root,
                        path,
                        root / "run",
                        allow_upload=True,
                        max_tokens=10000,
                        expected_manifest_hash=self.expected,
                    )
            self.assertEqual(raised.exception.category, "approved_plan_changed")
            self.assertEqual(
                json.loads((root / "run/manifest.json").read_text())["status"], "failed"
            )

    def test_mock_run_is_labelled_mock_and_failures_are_saved(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"TABPFN_TOKEN": "fictional-token"}),
        ):
            root = Path(directory)
            preflight_bundle(
                self.root, root / "plan", TabPFNConfig(), expected_manifest_hash=self.expected
            )
            service = FakeService(self.plan)

            def factory(token):
                return TabPFNRest(token, transport=httpx.MockTransport(service))

            result = run_approved(
                self.root,
                root / "plan/plan.json",
                root / "run",
                allow_upload=True,
                max_tokens=10000,
                expected_manifest_hash=self.expected,
                client_factory=factory,
            )
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["evidence"], "offline_mock")
            self.assertFalse(result["test_scored"])
            self.assertEqual(
                result["predictions"]["sha256"], file_hash(root / "run/validation_predictions.csv")
            )
            service.timeout_path = "/tabpfn/predict"
            with self.assertRaises(IntegrationError):
                run_approved(
                    self.root,
                    root / "plan/plan.json",
                    root / "failed",
                    allow_upload=True,
                    max_tokens=10000,
                    expected_manifest_hash=self.expected,
                    client_factory=factory,
                )
            evidence = (root / "failed/manifest.json").read_text()
            failure = json.loads(evidence)
            self.assertTrue(failure["failure"]["billing_uncertain"])
            self.assertNotIn("fictional-token", evidence)
            self.assertNotIn("signature=", evidence)
            self.assertFalse((root / "failed/validation_predictions.csv").exists())

    def test_fast_and_thinking_run_with_their_exact_plans(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"TABPFN_TOKEN": "fictional-token"}),
        ):
            root = Path(directory)
            for variant in ("fast", "thinking"):
                config = TabPFNConfig(variant)
                plan, _, _ = prepare_plan(self.root, config, self.expected)
                preflight_bundle(
                    self.root, root / variant, config, expected_manifest_hash=self.expected
                )
                service = FakeService(plan)

                def factory(token):
                    return TabPFNRest(token, transport=httpx.MockTransport(service))

                result = run_approved(
                    self.root,
                    root / variant / "plan.json",
                    root / (variant + "-run"),
                    allow_upload=True,
                    max_tokens=20000,
                    expected_manifest_hash=self.expected,
                    client_factory=factory,
                )
                self.assertEqual(result["requested_variant"], variant)
                self.assertEqual(result["evidence"], "offline_mock")
                fit_request = next(
                    json.loads(r.content) for r in service.requests if r.url.path == "/tabpfn/fit"
                )
                self.assertEqual(fit_request["tabpfn_config"]["model_path"], config.model_path)
                operations = [
                    json.loads(r.content)["operation"]
                    for r in service.requests
                    if r.url.path.endswith("estimate_cost")
                ]
                self.assertEqual(
                    operations,
                    ["thinking_fit", "thinking_predict"] if variant == "thinking" else ["predict"],
                )
                if variant == "thinking":
                    self.assertEqual(fit_request["thinking_effort"], "medium")
                    self.assertEqual(fit_request["thinking_timeout_s"], 300)
                    self.assertEqual(fit_request["thinking_effort_metric"], "log_loss")

    def test_contract_failure_retains_quarantined_evidence_without_scoring_or_retry(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"TABPFN_TOKEN": "fictional-token"}),
        ):
            root = Path(directory)
            preflight_bundle(
                self.root, root / "plan", TabPFNConfig(), expected_manifest_hash=self.expected
            )
            service = FakeService(self.plan)

            def handler(request):
                if request.url.path == "/tabpfn/predict":
                    service.requests.append(request)
                    response = response_fixture(self.plan)
                    response["metadata"]["tabpfn_config"]["n_estimators"] = 1
                    response["detail"] = "fictional-token"
                    return httpx.Response(200, json=response)
                return service(request)

            with self.assertRaises(IntegrationError):
                run_approved(
                    self.root,
                    root / "plan/plan.json",
                    root / "failed",
                    allow_upload=True,
                    max_tokens=10000,
                    expected_manifest_hash=self.expected,
                    client_factory=lambda token: TabPFNRest(
                        token, transport=httpx.MockTransport(handler)
                    ),
                )
            result = json.loads((root / "failed/manifest.json").read_text())
            evidence_path = root / "failed/response_evidence.json"
            evidence = json.loads(evidence_path.read_text())
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["failure"]["billing_uncertain"])
            self.assertFalse(evidence["checks"]["n_estimators"])
            self.assertTrue(evidence["checks"]["probabilities"])
            self.assertEqual(result["unverified_response"]["sha256"], file_hash(evidence_path))
            self.assertEqual(result["integration_attempt"]["approved_estimate_budget"], 10000)
            self.assertNotIn("metrics", result)
            self.assertFalse((root / "failed/validation_predictions.csv").exists())
            self.assertNotIn("fictional-token", evidence_path.read_text())
            self.assertEqual(sum(r.url.path == "/tabpfn/predict" for r in service.requests), 1)

    def test_cli_upload_guard_and_missing_token_evidence(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stderr(io.StringIO()):
            root = Path(directory)
            with self.assertRaises(SystemExit) as raised:
                main(
                    [
                        "tabpfn-run",
                        "--input",
                        str(self.root),
                        "--plan",
                        str(root / "missing.json"),
                        "--output",
                        str(root / "run"),
                        "--max-estimated-tokens",
                        "10000",
                    ]
                )
            self.assertEqual(raised.exception.code, 2)
            self.assertFalse((root / "run").exists())
            with patch.dict(os.environ, {}, clear=True), self.assertRaises(IntegrationError):
                preflight_bundle(
                    self.root,
                    root / "online",
                    TabPFNConfig(),
                    online=True,
                    env_file=root / "absent.env",
                    expected_manifest_hash=self.expected,
                )
            evidence = json.loads((root / "online/manifest.json").read_text())
            self.assertEqual(evidence["failure"]["category"], "missing_token")
            self.assertEqual(evidence["rows_uploaded"], 0)

    def test_response_evidence_is_on_disk_before_validator_runs(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"TABPFN_TOKEN": "fictional-token"}),
        ):
            root = Path(directory)
            preflight_bundle(
                self.root, root / "plan", TabPFNConfig(), expected_manifest_hash=self.expected
            )
            service = FakeService(self.plan)

            def inspect_then_fail(plan, response):
                path = root / "run/response_evidence.json"
                evidence = json.loads(path.read_text())
                manifest = json.loads((root / "run/manifest.json").read_text())
                self.assertEqual(manifest["response_evidence"]["sha256"], file_hash(path))
                self.assertEqual(evidence["requested_configuration"]["model_path"], "v3.5_default")
                self.assertEqual(evidence["reported_metadata"]["package_version"]["value"], "9.0.0")
                self.assertNotIn("metrics", manifest)
                raise IntegrationError("prediction_contract", billing_uncertain=True)

            with patch("scuba.integrations.tabpfn_rest.validate_prediction", inspect_then_fail):
                with self.assertRaises(IntegrationError) as raised:
                    run_approved(
                        self.root,
                        root / "plan/plan.json",
                        root / "run",
                        allow_upload=True,
                        max_tokens=10000,
                        expected_manifest_hash=self.expected,
                        client_factory=lambda token: TabPFNRest(
                            token, transport=httpx.MockTransport(service)
                        ),
                    )
            self.assertEqual(raised.exception.category, "prediction_contract")
            self.assertFalse((root / "run/validation_predictions.csv").exists())
            self.assertEqual(sum(r.url.path == "/tabpfn/predict" for r in service.requests), 1)
