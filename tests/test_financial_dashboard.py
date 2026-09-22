"""Invented evidence tests for shortlist aggregates and artifact integrity."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from scuba.evaluation import point_metrics
from scuba.financial_dashboard import checked_predictions, cohort_audit, pinned, review_snapshots
from scuba.financial_stress import TARGET, digest


class FinancialDashboardTests(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame(
            {
                "ID": [f"FIXTURE-{i:02d}" for i in range(40)],
                TARGET: [int(i % 3 == 0) for i in range(40)],
                "region": ["Invented north"] * 20 + ["Invented south"] * 20,
                "segment": ["Example"] * 40,
                "earning_pattern": ["Example"] * 40,
                "gender": ["Example A", "Example B"] * 20,
                "age": [18, 30, 45, 60] * 10,
            }
        )

    def test_group_capture_reconciles_to_global_capacity_including_ties(self):
        frame = self.fixture()
        p = np.array([0.8] * 4 + [0.1] * 36)
        audit = cohort_audit(frame, p)
        for dimension in {g["dimension"] for g in audit}:
            groups = [g for g in audit if g["dimension"] == dimension]
            self.assertEqual(sum(g["rows"] for g in groups), 40)
            self.assertEqual(sum(g["positives"] for g in groups), 14)
            for q, count, captured in [("0.05", 2, 1), ("0.1", 4, 2)]:
                self.assertEqual(sum(g["budgets"][q]["selected"] for g in groups), count)
                self.assertEqual(sum(g["budgets"][q]["captured"] for g in groups), captured)
        south = next(
            g for g in audit if g["dimension"] == "region" and g["group"].endswith("south")
        )
        self.assertEqual(south["budgets"]["0.1"]["selected"], 0)

    def test_predictions_require_hash_alignment_and_recomputed_metrics(self):
        frame = self.fixture()
        p = np.linspace(0.01, 0.99, 40)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "validation_predictions.csv"
            frame[["ID", TARGET]].assign(example=p).to_csv(path, index=False)
            metric = point_metrics(frame[TARGET], p, frame.ID.tolist())
            metric["roc_auc"] = float(roc_auc_score(frame[TARGET], p))
            manifest = {"predictions_sha256": digest(path), "metrics": {"example": metric}}
            checked = checked_predictions(root, manifest, frame, ["example"])
            np.testing.assert_array_equal(checked["example"], p)
            manifest["metrics"]["example"]["log_loss"] += 0.01
            with self.assertRaisesRegex(ValueError, "metrics"):
                checked_predictions(root, manifest, frame, ["example"])
            with self.assertRaisesRegex(ValueError, "IDs or labels"):
                checked_predictions(root, manifest, frame.iloc[::-1], ["example"])
            path.write_text("corrupt")
            with self.assertRaisesRegex(ValueError, "checksum"):
                checked_predictions(root, manifest, frame, ["example"])

    def test_review_snapshots_hide_labels_and_order_months_oldest_first(self):
        frame = self.fixture()
        for m in range(1, 7):
            for family in (
                "paybill",
                "merchantpay",
                "transfer_from_bank",
                "mm_send",
                "received",
                "deposit",
                "withdraw",
            ):
                frame[f"m{m}_{family}_volume"] = m
            frame[f"m{m}_daily_avg_bal"] = m * 10.0
        p = np.array([0.2] * 39 + [0.9])
        rows = review_snapshots(frame, p)
        self.assertEqual(rows[0]["id"], "FIXTURE-39")
        self.assertEqual(rows[1]["id"], "FIXTURE-00")
        self.assertEqual(
            set(rows[0]),
            {"id", "probability", "region", "segment", "earning_pattern", "activity", "balance"},
        )
        self.assertEqual(rows[0]["activity"]["deposit"], [6, 5, 4, 3, 2, 1])
        self.assertEqual(rows[0]["balance"], [60, 50, 40, 30, 20, 10])

    def test_pinned_evidence_rejects_changed_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.json", Path(tmp) / "b.json"
            a.write_text(json.dumps({"status": "complete"}))
            b.write_bytes(a.read_bytes())
            self.assertEqual(pinned(a, b), {"status": "complete"})
            b.write_text("{}")
            with self.assertRaisesRegex(ValueError, "pinned"):
                pinned(a, b)
