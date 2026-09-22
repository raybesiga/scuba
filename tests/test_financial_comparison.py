"""Invented fixtures exercise local comparisons and the hosted approval boundary."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pandas as pd
from test_financial_stress import fixture, source_bundle
from test_tabpfn_rest import FakeService

from scuba.financial_comparison import compare, hosted_plan, preflight, run_hosted
from scuba.financial_stress import TARGET, prepare
from scuba.integrations.tabpfn_plan import plan_digest
from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest


class FinancialComparisonTests(unittest.TestCase):
    def setup_fixture(self, root):
        prepared = root / "prepared"
        prepare(source_bundle(root), prepared)
        (prepared / "final.csv").write_text("sealed, deliberately invalid")
        return prepared

    def test_local_comparison_replays_aligned_predictions_without_final_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = self.setup_fixture(root)
            first = compare(prepared, root / "first")
            second = compare(prepared, root / "second")
            self.assertEqual(first["metrics"], second["metrics"])
            self.assertEqual(first["predictions_sha256"], second["predictions_sha256"])
            self.assertEqual(
                set(first["metrics"]),
                {"constant_prior", "logistic_regression", "xgboost", "catboost"},
            )
            predicted = pd.read_csv(root / "first/validation_predictions.csv")
            expected = pd.read_csv(prepared / "validation.csv")
            self.assertEqual(predicted.ID.tolist(), expected.ID.tolist())
            self.assertEqual(predicted[TARGET].tolist(), expected[TARGET].tolist())
            self.assertFalse(first["final_evaluated"])
            (prepared / "validation.csv").write_text("corrupt")
            with self.assertRaisesRegex(ValueError, "checksum"):
                compare(prepared, root / "bad")
            self.assertFalse((root / "bad").exists())

    def test_exclusion_refits_same_partitions_and_rejects_unknown_features(self):
        train, test, dictionary, submission = fixture()
        for frame in (train, test):
            frame["age"] = 30
            frame["gender"] = ["Example A", "Example B"] * (len(frame) // 2)
        dictionary = pd.concat(
            [
                dictionary,
                pd.DataFrame({"column_name": ["age", "gender"], "data_type": ["int64", "object"]}),
            ],
            ignore_index=True,
        )
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch(
                "test_financial_stress.fixture", return_value=(train, test, dictionary, submission)
            ),
        ):
            root = Path(tmp)
            prepared = self.setup_fixture(root)
            result = compare(prepared, root / "excluded", exclude_features=("age", "gender"))
            self.assertEqual(result["excluded_features"], ["age", "gender"])
            self.assertEqual(result["feature_columns"], ["amount", "category"])
            self.assertEqual(result["cohorts"]["validation"]["rows"], 40)
            self.assertFalse(result["final_evaluated"])
            self.assertEqual(result["hosted_calls"], 0)
            for excluded in [("unknown",), ("amount", "category", "age", "gender")]:
                with self.assertRaises(ValueError):
                    compare(prepared, root / "invalid", exclude_features=excluded)
            self.assertFalse((root / "invalid").exists())

    def test_offline_plan_excludes_identifiers_evaluation_labels_and_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = self.setup_fixture(root)
            forbidden = Mock(side_effect=AssertionError("no credentials or network"))
            report = preflight(
                prepared, root / "offline", client_factory=forbidden, token_loader=forbidden
            )
            forbidden.assert_not_called()
            self.assertEqual(report["status"], "awaiting_metadata_preflight")
            plan, payloads = hosted_plan(prepared)
            self.assertNotEqual(plan["classification"], "synthetic")
            for name, data in payloads.items():
                frame = pd.read_csv(io.BytesIO(data))
                self.assertNotIn("ID", frame.columns)
                self.assertNotIn(b"FIXTURE-", data)
                self.assertEqual(
                    list(frame.columns), [TARGET] if name == "labels" else plan["feature_columns"]
                )
            self.assertFalse(plan["test_cohort_included"])
            self.assertFalse(plan["validation_labels_uploaded"])
            self.assertEqual(plan["cohorts"]["validation"]["rows"], 40)

    def test_upload_gate_plan_integrity_metadata_preflight_and_external_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = self.setup_fixture(root)
            plan, _ = hosted_plan(prepared)
            approved = root / "plan.json"
            approved.write_text(json.dumps({"plan": plan, "sha256": plan_digest(plan)}))
            token = Mock(return_value="fixture-token")
            service = FakeService(plan)

            def factory(value):
                return TabPFNRest(value, transport=httpx.MockTransport(service))

            for allow, budget in [(False, 10000), (True, None), (True, 0), (True, -1)]:
                with self.assertRaises(IntegrationError):
                    run_hosted(
                        prepared,
                        approved,
                        root / "blocked",
                        allow_upload=allow,
                        max_tokens=budget,
                        client_factory=factory,
                        token_loader=token,
                    )
            token.assert_not_called()
            approved.write_text(json.dumps({"plan": plan, "sha256": "changed"}))
            with self.assertRaisesRegex(IntegrationError, "approved_plan_changed"):
                run_hosted(
                    prepared,
                    approved,
                    root / "changed",
                    allow_upload=True,
                    max_tokens=10000,
                    client_factory=factory,
                    token_loader=token,
                )
            token.assert_not_called()
            approved.write_text(json.dumps({"plan": plan, "sha256": plan_digest(plan)}))
            metadata = preflight(
                prepared,
                root / "online-mock",
                online=True,
                client_factory=factory,
                token_loader=token,
            )
            self.assertEqual(metadata["preflight"]["estimated_total_tokens"], 10000)
            self.assertEqual(len(service.requests), 2)
            self.assertTrue(
                all(
                    r.url.path.endswith(("get_model_limits", "estimate_cost"))
                    for r in service.requests
                )
            )
            service.requests.clear()
            result = run_hosted(
                prepared,
                approved,
                root / "accepted",
                allow_upload=True,
                max_tokens=10000,
                client_factory=factory,
                token_loader=token,
            )
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["evidence"], "offline_mock")
            self.assertEqual(result["metrics"]["rows"], 40)
            upload = next(
                r for r in service.requests if r.url.path.endswith("prepare_train_set_upload")
            )
            description = json.loads(upload.content)["description"]
            self.assertIn("origin unverified", description)
            self.assertNotIn("entirely synthetic", description)
            evidence = json.loads((root / "accepted/response_evidence.json").read_text())
            self.assertEqual(evidence["classification"], plan["classification"])
            self.assertEqual(sum(r.url.path.endswith("/predict") for r in service.requests), 1)
            self.assertFalse(result["final_evaluated"])

    def test_estimate_ceiling_and_failed_identity_keep_evidence_without_retry(self):
        for kind in ("budget", "identity"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                prepared = self.setup_fixture(root)
                plan, _ = hosted_plan(prepared)
                approved = root / "plan.json"
                approved.write_text(json.dumps({"plan": plan, "sha256": plan_digest(plan)}))
                service = FakeService(plan)

                def transport(request):
                    response = service(request)
                    if kind == "identity" and request.url.path.endswith("/predict"):
                        body = response.json()
                        body["metadata"]["tabpfn_config"]["model_path"] = "unknown-model"
                        return httpx.Response(200, json=body)
                    return response

                def factory(value):
                    return TabPFNRest(value, transport=httpx.MockTransport(transport))

                report = run_hosted(
                    prepared,
                    approved,
                    root / "attempt",
                    allow_upload=True,
                    max_tokens=9999 if kind == "budget" else 10000,
                    client_factory=factory,
                    token_loader=lambda: "fixture-token",
                )
                self.assertEqual(report["status"], "failed")
                self.assertNotIn("metrics", report)
                self.assertFalse((root / "attempt/validation_predictions.csv").exists())
                predictions = [r for r in service.requests if r.url.path.endswith("/predict")]
                self.assertEqual(len(predictions), 0 if kind == "budget" else 1)
                if kind == "budget":
                    self.assertEqual(len(service.requests), 2)
                else:
                    self.assertTrue((root / "attempt/response_evidence.json").exists())
                    self.assertTrue(report["failure"]["billing_uncertain"])
