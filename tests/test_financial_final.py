"""Invented fixtures for sealed holdouts, retained resources and upload guards."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from test_financial_stress import source_bundle
from test_tabpfn_rest import FIT_ID, FakeService

from scuba.financial_comparison import compare, hosted_plan
from scuba.financial_final import final_context, final_plan, freeze, local_final, review, run
from scuba.financial_final_evaluation import verify
from scuba.financial_stress import TARGET, digest, prepare, write_json
from scuba.integrations.tabpfn_plan import plan_digest
from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest


class FinancialFinalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.prepared = cls.root / "prepared"
        prepare(source_bundle(cls.root), cls.prepared)
        local = compare(cls.prepared, cls.root / "local")
        plan, _ = hosted_plan(cls.prepared)
        refs = cls.root / "references"
        refs.mkdir()
        write_json(
            refs / "financial-stress-preparation-v1.json",
            json.loads((cls.prepared / "manifest.json").read_text()),
        )
        write_json(refs / "financial-stress-comparison-v1.json", local)
        write_json(
            refs / "financial-stress-hosted-plan-v1.json",
            {"plan": plan, "sha256": plan_digest(plan)},
        )
        # Only this private invented fixture represents successful prior hosted evidence.
        write_json(
            refs / "financial-stress-hosted-validation-v1.json",
            {
                "status": "complete",
                "evidence": "live_verified",
                "prepared_manifest_sha256": digest(cls.prepared / "manifest.json"),
                "plan_sha256": plan_digest(plan),
                "integration": {
                    "fitted_train_set_id": FIT_ID,
                    "checkpoint_identity": {"policy": "fixture"},
                },
            },
        )
        final = cls.prepared / "final.csv"
        saved = final.read_bytes()
        final.unlink()
        freeze(cls.prepared, cls.root / "frozen", references=refs)
        final.write_bytes(saved)
        cls.protocol = cls.root / "frozen/protocol.json"

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_freeze_does_not_read_final_and_local_evaluation_preserves_split(self):
        result = local_final(self.prepared, self.protocol, self.root / "final-local")
        self.assertTrue(result["final_evaluated"])
        self.assertEqual(result["evaluation_partition"], "final")
        self.assertEqual(result["cohorts"]["train"]["rows"], 120)
        self.assertEqual(result["cohorts"]["final"]["rows"], 40)
        self.assertEqual(set(result["input_sha256"]), {"train", "final"})
        self.assertTrue((self.root / "final-local/final_predictions.csv").exists())
        self.assertFalse((self.root / "final-local/validation_predictions.csv").exists())

    def test_final_plan_excludes_ids_labels_and_training_uploads(self):
        plan, payload, rows = final_plan(self.prepared, self.protocol)
        self.assertEqual(plan["retained_fitted_train_set_id"], FIT_ID)
        self.assertEqual(plan["payloads"]["test"]["rows"], 40)
        self.assertNotIn(b"FIXTURE-", payload)
        self.assertNotIn(TARGET.encode(), payload)
        self.assertEqual(payload.splitlines()[0], b"amount,category")
        self.assertEqual(set(plan["payloads"]), {"test"})
        self.assertEqual(plan["operation_limits"]["fit_requests"], 0)
        self.assertFalse(plan["test_labels_uploaded"])
        self.assertEqual(len(rows), 40)
        forbidden = Mock(side_effect=AssertionError("no credentials"))
        review(self.prepared, self.protocol, self.root / "offline-review", token_loader=forbidden)
        forbidden.assert_not_called()

    def test_changed_protocol_or_partition_rejected(self):
        bad = copy.deepcopy(json.loads(self.protocol.read_text()))
        bad["protocol"]["threshold"] = 0.1
        path = self.root / "bad.json"
        write_json(path, bad)
        with self.assertRaisesRegex(ValueError, "protocol"):
            final_context(self.prepared, path)
        final = self.prepared / "final.csv"
        saved = final.read_bytes()
        try:
            final.write_text("changed")
            with self.assertRaisesRegex(ValueError, "checksum"):
                final_context(self.prepared, self.protocol)
        finally:
            final.write_bytes(saved)

    def test_saved_final_evidence_replays_and_rejects_changed_probabilities(self):
        local = self.root / "verify-local"
        hosted = self.root / "verify-hosted"
        local_final(self.prepared, self.protocol, local)
        plan, _, _ = final_plan(self.prepared, self.protocol)
        approved = self.root / "verify-plan.json"
        write_json(approved, {"plan": plan, "sha256": plan_digest(plan)})
        response_plan = copy.deepcopy(plan)
        response_plan["cohorts"]["validation"] = plan["cohorts"]["test"]
        service = FakeService(response_plan)

        def factory(value):
            return TabPFNRest(value, transport=httpx.MockTransport(service))

        with patch("scuba.financial_final.cohort_audit", return_value=[]):
            result = run(
                self.prepared,
                self.protocol,
                approved,
                hosted,
                allow_upload=True,
                max_tokens=10000,
                client_factory=factory,
                token_loader=lambda: "fixture-token",
            )
        self.assertEqual(result["status"], "complete")
        with self.assertRaisesRegex(ValueError, "verified hosted"):
            verify(
                self.prepared, self.protocol, local, hosted, approved, self.root / "mock-rejected"
            )
        # Private invented success fixture exercises replay; never used as live evidence.
        result["evidence"] = "live_verified"
        write_json(hosted / "manifest.json", result)
        with patch("scuba.financial_final_evaluation.cohort_audit", return_value=[]):
            verified = verify(
                self.prepared, self.protocol, local, hosted, approved, self.root / "verified"
            )
        self.assertEqual(verified["verification"]["model_count"], 5)
        self.assertEqual(verified["verification"]["api_requests"], 0)
        (hosted / "final_predictions.csv").write_text("changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            verify(
                self.prepared,
                self.protocol,
                local,
                hosted,
                approved,
                self.root / "corrupt-rejected",
            )

    def test_one_hosted_prediction_reuses_fit_and_requires_exact_approval(self):
        plan, _, _ = final_plan(self.prepared, self.protocol)
        approved = self.root / "approved.json"
        write_json(approved, {"plan": plan, "sha256": plan_digest(plan)})
        token = Mock(return_value="fixture-token")
        response_plan = copy.deepcopy(plan)
        response_plan["cohorts"]["validation"] = plan["cohorts"]["test"]
        service = FakeService(response_plan)

        def factory(value):
            return TabPFNRest(value, transport=httpx.MockTransport(service))

        with self.assertRaises(IntegrationError):
            run(self.prepared, self.protocol, approved, self.root / "blocked", token_loader=token)
        token.assert_not_called()
        with patch("scuba.financial_final.cohort_audit", return_value=[]):
            result = run(
                self.prepared,
                self.protocol,
                approved,
                self.root / "hosted",
                allow_upload=True,
                max_tokens=10000,
                client_factory=factory,
                token_loader=token,
            )
        self.assertEqual(result["status"], "complete", result.get("failure"))
        self.assertEqual(result["evidence"], "offline_mock")
        paths = [r.url.path for r in service.requests]
        self.assertEqual(sum(p.endswith("/predict") for p in paths), 1)
        self.assertFalse(any(p.endswith("/fit") or "prepare_train_set" in p for p in paths))
        self.assertTrue((self.root / "hosted/response_evidence.json").exists())
        self.assertTrue(result["final_evaluated"])
