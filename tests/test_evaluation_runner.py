import csv
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scuba.artifacts import file_hash, write_json, write_table
from scuba.cli import main
from scuba.contract import GeneratorConfig
from scuba.evaluation_runner import evaluate_saved
from scuba.integrations.tabpfn_plan import TabPFNConfig, plan_digest, prepare_plan
from scuba.models.data import FROZEN_MANIFESTS
from scuba.models.runner import PREDICTION_SCHEMA, run_comparators
from scuba.pipeline import prepare_bundle


class EvaluationRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.input, cls.local = cls.root / "input", cls.root / "local"
        prepare_bundle(cls.input, GeneratorConfig(customers=180))
        cls.expected = file_hash(cls.input / "manifest.json")
        cls.local_manifest = run_comparators(cls.input, cls.local, cls.expected)
        cls.local_hash = file_hash(cls.local / "manifest.json")
        cls.hosted = cls.root / "hosted-fixture"
        cls.hosted.mkdir()
        plan, _, _ = prepare_plan(cls.input, TabPFNConfig(), cls.expected)
        write_json(cls.hosted / "plan.json", {"plan": plan, "sha256": plan_digest(plan)})
        # Fictional test evidence; never a live run or a benchmark artifact.
        shutil.copyfile(
            cls.local / "xgboost/validation_predictions.csv",
            cls.hosted / "validation_predictions.csv",
        )
        write_json(
            cls.hosted / "manifest.json",
            {
                "status": "complete",
                "classification": "synthetic",
                "phase": "validation_only",
                "test_scored": False,
                "evidence": "offline_revalidated_live_response",
                "requested_variant": "plus",
                "plan_sha256": plan_digest(plan),
                "predictions": cls.local_manifest["models"]["xgboost"]["predictions"],
                "metrics": cls.local_manifest["models"]["xgboost"]["metrics"],
                "identity_validation": {"scope": "fictional test fixture"},
            },
        )
        cls.hosted_hash = file_hash(cls.hosted / "manifest.json")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_offline_end_to_end_replay_and_cli(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("socket.socket.connect", side_effect=AssertionError("network forbidden")),
            patch("scuba.models.runner.run_comparators", side_effect=AssertionError("no training")),
            patch("scuba.integrations.tabpfn_runner.tabpfn_token") as token,
        ):
            before = file_hash(self.input / "snapshots.csv")
            outputs = [Path(directory) / name for name in ("first", "replay")]
            for output in outputs:
                result = evaluate_saved(
                    self.input,
                    self.local,
                    self.local_hash,
                    output,
                    hosted_run=self.hosted,
                    hosted_hash=self.hosted_hash,
                    expected_manifest_hash=self.expected,
                    replicates=40,
                )
                self.assertEqual(
                    set(result["overall"]["models"]),
                    {"constant_prior", "logistic_regression", "xgboost", "catboost", "hosted_plus"},
                )
                self.assertEqual(
                    result["overall"]["paired_comparisons"]["hosted_plus_minus_xgboost"][
                        "ap_difference"
                    ],
                    0,
                )
                self.assertEqual(set(result["slices"]["activity_level"]), {"low", "medium", "high"})
                manifest = json.loads((output / "manifest.json").read_text())
                self.assertEqual(manifest["api_requests"], 0)
                self.assertEqual(manifest["models_fitted"], 0)
                self.assertFalse(manifest["test_scored"])
            self.assertEqual(
                (outputs[0] / "evaluation.json").read_bytes(),
                (outputs[1] / "evaluation.json").read_bytes(),
            )
            self.assertEqual(file_hash(self.input / "snapshots.csv"), before)
            self.assertEqual(file_hash(self.local / "manifest.json"), self.local_hash)
            token.assert_not_called()
            with self.assertRaises(FileExistsError):
                evaluate_saved(self.input, self.local, self.local_hash, outputs[0])
            with (
                patch.dict(FROZEN_MANIFESTS, {3501: self.expected}),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(
                    main(
                        [
                            "evaluate",
                            "--input",
                            str(self.input),
                            "--local-run",
                            str(self.local),
                            "--local-manifest-sha256",
                            self.local_hash,
                            "--output",
                            str(Path(directory) / "cli"),
                        ]
                    ),
                    0,
                )
            cli = json.loads((Path(directory) / "cli/evaluation.json").read_text())
            self.assertIsNotNone(cli["missing_hosted_evidence"])

    def test_hash_status_input_and_unverified_hosted_sources_are_rejected(self):
        for case in ("hash", "failed", "test", "input", "unverified", "wrong_hosted_seed"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                local, hosted = Path(directory) / "local", Path(directory) / "hosted"
                shutil.copytree(self.local, local)
                shutil.copytree(self.hosted, hosted)
                manifest = json.loads((local / "manifest.json").read_text())
                if case == "failed":
                    manifest["status"] = "failed"
                if case == "test":
                    manifest["test_scored"] = True
                if case == "input":
                    manifest["input_files"]["snapshots.csv"] = "changed"
                write_json(local / "manifest.json", manifest)
                remote = json.loads((hosted / "manifest.json").read_text())
                if case == "unverified":
                    remote["evidence"] = "live_attempt"
                write_json(hosted / "manifest.json", remote)
                if case == "wrong_hosted_seed":
                    envelope = json.loads((hosted / "plan.json").read_text())
                    envelope["plan"]["input_files"]["snapshots.csv"] = "changed"
                    write_json(hosted / "plan.json", envelope)
                with self.assertRaises(ValueError):
                    evaluate_saved(
                        self.input,
                        local,
                        "0" * 64 if case == "hash" else file_hash(local / "manifest.json"),
                        Path(directory) / "out",
                        hosted_run=hosted,
                        hosted_hash=file_hash(hosted / "manifest.json"),
                        expected_manifest_hash=self.expected,
                        replicates=10,
                    )

    def test_changed_duplicate_extra_keys_labels_and_metrics_are_rejected(self):
        for case in ("hash", "duplicate", "key", "label", "synthetic", "metrics"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                local = Path(directory) / "local"
                shutil.copytree(self.local, local)
                manifest = json.loads((local / "manifest.json").read_text())
                path = local / "xgboost/validation_predictions.csv"
                with path.open() as f:
                    rows = list(csv.DictReader(f))
                if case == "duplicate":
                    rows[1] = rows[0].copy()
                if case == "key":
                    rows[0]["customer_id"] = "SYN-EXTRA"
                if case == "label":
                    rows[0]["dormant_30d"] = str(1 - int(rows[0]["dormant_30d"]))
                if case == "synthetic":
                    rows[0]["is_synthetic"] = "false"
                if case == "hash":
                    rows[0]["probability_dormant"] = "0.123456"
                reference = write_table(path, rows, PREDICTION_SCHEMA)
                if case != "hash":
                    manifest["models"]["xgboost"]["predictions"] = reference
                if case == "metrics":
                    manifest["models"]["xgboost"]["metrics"]["average_precision"] = -1
                write_json(local / "manifest.json", manifest)
                with self.assertRaises(ValueError):
                    evaluate_saved(
                        self.input,
                        local,
                        file_hash(local / "manifest.json"),
                        Path(directory) / "out",
                        expected_manifest_hash=self.expected,
                        replicates=10,
                    )
