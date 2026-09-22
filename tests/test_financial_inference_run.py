"""Exercise full-data uploads, saved output and failure handling with invented rows."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import pandas as pd
from test_financial_stress import source_bundle
from test_tabpfn_rest import FakeService, response_fixture

from scuba.financial_inference import prepare_inference
from scuba.financial_inference_run import run, verify_output
from scuba.financial_stress import digest, prepare, write_json
from scuba.integrations.tabpfn_response_archive import ARCHIVE_NAME
from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest, validate_prediction


class FullInferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = source_bundle(self.root)
        self.prepared = self.root / "prepared"
        prepare(self.bundle, self.prepared)
        self.plan = prepare_inference(self.bundle, self.prepared, self.root / "plan")
        self.approved = self.root / "plan/plan.json"
        self.output = self.root / "output"
        reference = self.root / "docs/reference"
        reference.mkdir(parents=True)
        write_json(
            reference / "financial-stress-final-evaluation-v1.json",
            {
                "status": "verified_final",
                "prepared_manifest_sha256": digest(self.prepared / "manifest.json"),
            },
        )
        self.patch_root = patch("scuba.financial_inference_run.ROOT", self.root)
        self.patch_root.start()
        self.addCleanup(self.patch_root.stop)
        # The shared fake returns its original validation fixture; real plan stays test-only.
        fake_plan = copy.deepcopy(self.plan)
        fake_plan["cohorts"]["validation"] = fake_plan["cohorts"]["test"]
        self.service = FakeService(fake_plan)
        self.calls = 0

    def client(self, token):
        self.calls += 1
        return TabPFNRest(token, transport=httpx.MockTransport(self.service))

    def execute(self, **options):
        with patch("socket.socket.connect", side_effect=AssertionError("offline only")):
            return run(
                self.bundle,
                self.prepared,
                self.approved,
                self.output,
                client_factory=self.client,
                token_loader=lambda: "fictional-token",
                **options,
            )

    def test_full_fit_preserves_original_test_order_and_exact_probabilities(self):
        result = self.execute(allow_upload=True, max_tokens=20000)
        self.assertEqual(result["status"], "complete")
        self.assertFalse(result["quality_metrics_available"])
        self.assertNotIn("metrics", result)
        rows = pd.read_csv(self.output / "predictions.csv")
        source = pd.read_csv(self.bundle / "files/Test.csv")
        self.assertEqual(rows.ID.tolist(), source.ID.tolist())
        self.assertTrue((rows.probability_stress_30d == 0.25).all())
        uploads = [r for r in self.service.requests if r.method == "PUT"]
        self.assertEqual(len(uploads), 3)
        for request in uploads:
            self.assertNotIn(b"ID", request.content.split(b"\n")[0].split(b","))
        self.assertEqual(uploads[0].content.count(b"\n"), 201)
        self.assertEqual(uploads[2].content.count(b"\n"), 41)
        self.assertEqual(sum(r.url.path.endswith("/predict") for r in self.service.requests), 1)
        self.assertEqual(verify_output(self.output)["rows"], 40)
        archive = self.output / ARCHIVE_NAME
        self.assertEqual(result["complete_response_archive"]["sha256"], digest(archive))
        original = archive.read_bytes()
        archive.write_text("{}")
        with self.assertRaisesRegex(ValueError, "archive checksum"):
            verify_output(self.output)
        archive.write_bytes(original)
        rows = rows.iloc[::-1]
        rows.to_csv(self.output / "predictions.csv", index=False)
        manifest = json.loads((self.output / "manifest.json").read_text())
        manifest["predictions_sha256"] = digest(self.output / "predictions.csv")
        write_json(self.output / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "rows or probabilities"):
            verify_output(self.output)

    def test_approval_and_changed_plan_fail_before_credentials_or_output(self):
        with self.assertRaises(IntegrationError):
            self.execute()
        saved = json.loads(self.approved.read_text())
        saved["plan"]["configuration"]["n_estimators"] = 1
        write_json(self.approved, saved)
        with self.assertRaises(IntegrationError):
            self.execute(allow_upload=True, max_tokens=20000)
        self.assertEqual(self.calls, 0)
        self.assertFalse(self.output.exists())

    def test_prediction_failure_is_retained_and_never_retried(self):
        self.service.timeout_path = "/tabpfn/predict"
        result = self.execute(allow_upload=True, max_tokens=20000)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(sum(r.url.path.endswith("/predict") for r in self.service.requests), 1)
        self.assertFalse((self.output / "predictions.csv").exists())
        self.assertNotIn("fictional-token", (self.output / "manifest.json").read_text())
        with self.assertRaises(FileExistsError):
            self.execute(allow_upload=True, max_tokens=20000)
        self.assertEqual(self.calls, 1)

    def test_full_response_is_on_disk_before_rejection_with_unknown_column_names(self):
        def fixture(plan):
            response = response_fixture(plan)
            response["metadata"]["test_set_num_cols"] += 2
            response["metadata"]["transformed_feature_names"] = [f"feature_{i}" for i in range(184)]
            response["unfamiliar_field"] = {"notes": ["Some useful diagnostic context"] * 20}
            return response

        def checked(plan, response):
            archived = json.loads((self.output / ARCHIVE_NAME).read_text())
            self.assertEqual(archived["body"], response)
            manifest = json.loads((self.output / "manifest.json").read_text())
            self.assertEqual(
                manifest["complete_response_archive"]["sha256"], digest(self.output / ARCHIVE_NAME)
            )
            return validate_prediction(plan, response)

        with (
            patch("test_tabpfn_rest.response_fixture", side_effect=fixture),
            patch("scuba.integrations.tabpfn_rest.validate_prediction", side_effect=checked),
        ):
            result = self.execute(allow_upload=True, max_tokens=20000)
        self.assertEqual(result["failure"]["category"], "prediction_contract")
        self.assertFalse((self.output / "predictions.csv").exists())
        self.assertEqual(sum(r.url.path.endswith("/predict") for r in self.service.requests), 1)

    def test_http_failure_body_is_archived_before_status_rejection(self):
        self.service.fail_path = "/tabpfn/predict"
        self.service.status = 422
        self.service.message = "Column diagnostic, with fictional-token echoed"
        result = self.execute(allow_upload=True, max_tokens=20000)
        self.assertEqual(result["failure"]["category"], "schema_or_data")
        archived = json.loads((self.output / ARCHIVE_NAME).read_text())
        self.assertEqual(archived["http_status"], 422)
        self.assertIn("Column diagnostic", archived["body"]["detail"])
        self.assertNotIn("fictional-token", json.dumps(archived))
        self.assertEqual(
            result["complete_response_archive"]["sha256"], digest(self.output / ARCHIVE_NAME)
        )

    def test_invalid_json_response_is_archived_before_json_rejection(self):
        original = self.service

        def handler(request):
            if request.url.path == "/tabpfn/predict":
                original.requests.append(request)
                return httpx.Response(200, text='{"metadata": incomplete fictional-token')
            return original(request)

        self.service = handler
        result = self.execute(allow_upload=True, max_tokens=20000)
        self.assertEqual(result["failure"]["category"], "invalid_json")
        archived = json.loads((self.output / ARCHIVE_NAME).read_text())
        self.assertEqual(archived["body_format"], "text")
        self.assertIn('"metadata": incomplete', archived["body"])
        self.assertNotIn("fictional-token", archived["body"])
        self.assertEqual(sum(r.url.path.endswith("/predict") for r in original.requests), 1)

    def test_archive_write_failure_stops_acceptance_without_prediction_retry(self):
        with patch(
            "scuba.integrations.tabpfn_rest.archive_response", side_effect=OSError("disk full")
        ):
            result = self.execute(allow_upload=True, max_tokens=20000)
        self.assertEqual(result["failure"]["category"], "local_io")
        self.assertTrue(result["failure"]["billing_uncertain"])
        self.assertFalse((self.output / "predictions.csv").exists())
        self.assertEqual(sum(r.url.path.endswith("/predict") for r in self.service.requests), 1)

    def test_fresh_estimate_stops_before_any_upload(self):
        result = self.execute(allow_upload=True, max_tokens=9999)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(any("upload" in r.url.path for r in self.service.requests))
