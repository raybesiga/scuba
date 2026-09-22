import copy
import json
import tempfile
import unittest
from pathlib import Path

from scuba.artifacts import file_hash, write_json
from scuba.evaluation import evaluate_cohort
from scuba.final_report import build_report


class FinalReportTests(unittest.TestCase):
    def fixture(self, root):
        rows = [
            {"customer_id": str(i), "prediction_date": "2032-10-01", "dormant_30d": i % 2}
            for i in range(4)
        ]
        names = ("constant_prior", "logistic_regression", "xgboost", "catboost")
        temporal = evaluate_cohort(rows, {name: [0.5] * 4 for name in names}, replicates=10)
        reference = evaluate_cohort(
            rows, {name: [0.1, 0.8, 0.2, 0.9] for name in names}, replicates=10
        )
        refs = []
        times = {
            key: {"median": 1, "min": 0.9, "max": 1.1}
            for key in (
                "imports_seconds",
                "load_verify_seconds",
                "estimator_fit_seconds",
                "test_estimator_predict_seconds",
                "process_wall_seconds",
            )
        }
        audit = {
            "partitions": {
                p: {"rows": 4, "customers": 4, "positives": 2, "dormancy_rate": 0.5}
                for p in ("train", "validation", "test")
            },
            "customer_overlap_counts": {
                "train__validation": 0,
                "train__test": 0,
                "validation__test": 0,
            },
        }
        for seed in (3501, 3502, 3503):
            for regime, overall in (("temporal", temporal), ("random_reference", reference)):
                folder = root / f"{seed}-{regime}"
                folder.mkdir()
                result = {
                    "generator_seed": seed,
                    "regime": regime,
                    "plan_sha256": str(seed),
                    "split_audit": audit,
                    "evaluations": {"test": {"overall": overall, "slices": {}}},
                }
                write_json(folder / "evaluation.json", result)
                write_json(
                    folder / "manifest.json",
                    {
                        "status": "complete",
                        "phase": "M4_final",
                        "classification": "synthetic",
                        "test_scored": True,
                        "regime": regime,
                        "plan_sha256": str(seed),
                        "input_files": {"fixture": str(seed)},
                        "evaluation_sha256": file_hash(folder / "evaluation.json"),
                        "models": {name: {"timing_summary": times} for name in names},
                    },
                )
                refs.append((folder, file_hash(folder / "manifest.json")))
        validation = root / "validation"
        validation.mkdir()
        write_json(validation / "evaluation.json", {"overall": temporal})
        write_json(
            validation / "manifest.json",
            {
                "status": "complete",
                "phase": "M4_validation_only",
                "test_scored": False,
                "evaluation_sha256": file_hash(validation / "evaluation.json"),
            },
        )
        return refs, (validation, file_hash(validation / "manifest.json"))

    def test_standalone_report_preserves_signed_differences_and_evidence_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            refs, validation = self.fixture(root)
            result = build_report(refs, validation, root / "report")
            gap = result["random_minus_temporal"]["3501"]["xgboost"]
            self.assertEqual(gap["average_precision"], 0.5)
            self.assertLess(gap["log_loss"], 0)
            page = (root / "report/index.html").read_text()
            self.assertIn("validation only", page)
            self.assertIn("diagnostic only", page)
            self.assertIn("<svg", page)
            self.assertNotIn('src="http', page)
            self.assertNotIn('href="http', page)
            build_report(refs, validation, root / "replay")
            self.assertEqual(
                (root / "report/index.html").read_bytes(), (root / "replay/index.html").read_bytes()
            )

    def test_changed_or_missing_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            refs, validation = self.fixture(root)
            with self.assertRaises(ValueError):
                build_report(refs[:-1], validation, root / "missing")
            with self.assertRaises(ValueError):
                build_report(refs + [refs[0]], validation, root / "duplicate")
            path = refs[0][0] / "evaluation.json"
            result = copy.deepcopy(json.loads(path.read_text()))
            result["generator_seed"] = 9
            write_json(path, result)
            with self.assertRaisesRegex(ValueError, "evaluation changed"):
                build_report(refs, validation, root / "changed")

    def test_hosted_final_report_requires_matching_verified_primary_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            refs, validation = self.fixture(root)
            primary = json.loads((refs[0][0] / "evaluation.json").read_text())
            rows = [
                {"customer_id": str(i), "prediction_date": "2032-10-01", "dormant_30d": i % 2}
                for i in range(4)
            ]
            names = ("constant_prior", "logistic_regression", "xgboost", "catboost", "hosted_plus")
            overall = evaluate_cohort(rows, {name: [0.5] * 4 for name in names}, replicates=10)
            hosted = root / "hosted"
            hosted.mkdir()
            evaluation = {
                "generator_seed": 3501,
                "regime": "temporal",
                "plan_sha256": "3501",
                "split_audit": primary["split_audit"],
                "overall": overall,
                "slices": {},
                "integration": {
                    "stages": [{"stage": "predict", "elapsed_seconds": 1.0}],
                    "fresh_preflight": {"estimated_total_tokens": 10000},
                    "approved_estimate_budget": 10000,
                    "checkpoint_identity": {"reported_model_path": "fictional checkpoint"},
                },
            }
            write_json(hosted / "evaluation.json", evaluation)
            manifest = {
                "status": "complete",
                "phase": "M4_hosted_final_comparison",
                "classification": "synthetic",
                "evidence": "live_verified",
                "test_scored": True,
                "plan_sha256": "3501",
                "local_manifest_sha256": refs[0][1],
                "hosted_manifest_sha256": "fictional",
                "evaluation_sha256": file_hash(hosted / "evaluation.json"),
            }
            write_json(hosted / "manifest.json", manifest)
            result = build_report(
                refs,
                validation,
                root / "report",
                hosted_ref=(hosted, file_hash(hosted / "manifest.json")),
            )
            page = (root / "report/index.html").read_text()
            self.assertEqual(result["status"], "final_complete")
            self.assertIn("Primary final test · TabPFN-3.5-Plus and local models", page)
            self.assertIn("Actual charges are unavailable", page)
            self.assertNotIn("its final test result is not available", page)
            self.assertNotIn("pending a separate upload", page)
            # A sensitivity run must not masquerade as the primary local source.
            manifest["local_manifest_sha256"] = refs[2][1]
            write_json(hosted / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "matching hosted"):
                build_report(
                    refs,
                    validation,
                    root / "wrong-source",
                    hosted_ref=(hosted, file_hash(hosted / "manifest.json")),
                )
            manifest["local_manifest_sha256"] = refs[0][1]
            manifest["evidence"] = "offline_mock"
            write_json(hosted / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "matching hosted"):
                build_report(
                    refs,
                    validation,
                    root / "mock",
                    hosted_ref=(hosted, file_hash(hosted / "manifest.json")),
                )
