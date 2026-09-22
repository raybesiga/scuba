"""Full-data planning uses invented source files and makes no service call."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_financial_stress import source_bundle

from scuba.financial_inference import prepare_inference
from scuba.financial_stress import TARGET, prepare


class InferencePlanTests(unittest.TestCase):
    def test_plan_includes_all_labels_without_claiming_inference_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = source_bundle(root)
            prepare(source, root / "prepared")
            with patch("socket.socket.connect", side_effect=AssertionError("offline only")):
                plan = prepare_inference(source, root / "prepared", root / "plan")
            self.assertEqual(plan["cohorts"]["train"]["rows"], 200)
            self.assertEqual(plan["cohorts"]["test"]["rows"], 40)
            self.assertTrue(plan["training_includes_prior_holdout"])
            self.assertFalse(plan["quality_metrics_available"])
            self.assertFalse(plan["test_labels_available"])
            self.assertEqual(plan["execution_status"], "not_executed")
            for name, payload in plan["payloads"].items():
                self.assertNotIn("ID", payload["columns"])
                self.assertEqual(
                    payload["columns"], [TARGET] if name == "labels" else ["amount", "category"]
                )
            (source / "files/Test.csv").write_text("corrupt")
            with self.assertRaises(ValueError):
                prepare_inference(source, root / "prepared", root / "bad")
            self.assertFalse((root / "bad").exists())
