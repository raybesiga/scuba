import csv
import io
import json
import math
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from scuba.artifacts import file_hash, write_json, write_table
from scuba.cli import main
from scuba.contract import GeneratorConfig, customer_partition
from scuba.features import SNAPSHOT_SCHEMA
from scuba.models.baselines import prior_model
from scuba.models.data import load_development_bundle
from scuba.models.runner import run_comparators, validation_metrics
from scuba.pipeline import prepare_bundle
from scuba.splits import MEMBERSHIP_SCHEMA, SCHEDULE


def csv_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def refresh_file(root, name):
    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["files"][name]["sha256"] = file_hash(root / name)
    manifest["files"][name]["rows"] = len(csv_rows(root / name))
    write_json(path, manifest)
    return file_hash(path)


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.directory.name)
        cls.bundle = cls.root / "input"
        prepare_bundle(cls.bundle, GeneratorConfig(customers=180))
        cls.expected = file_hash(cls.bundle / "manifest.json")

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_validation_metrics_hand_calculated(self):
        result = validation_metrics([0, 0, 0, 1], [0.25] * 4)
        self.assertEqual(result["average_precision"], 0.25)
        self.assertEqual(result["brier_score"], 0.1875)
        self.assertAlmostEqual(result["log_loss"], -(3 * math.log(0.75) + math.log(0.25)) / 4)
        for labels, probabilities in (([0, 0], [0.2, 0.3]), ([0, 1], [1.2, 0.5]), ([0, 1], [0.5])):
            with self.assertRaises(ValueError):
                validation_metrics(labels, probabilities)

    def test_frozen_hash_and_consumed_file_tampering_rejected(self):
        with self.assertRaisesRegex(ValueError, "frozen M1 hash"):
            load_development_bundle(self.bundle)
        for filename in ("snapshots.csv", "temporal_membership.csv", "sources/manifest.json"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "input"
                shutil.copytree(self.bundle, root)
                with (root / filename).open("a") as handle:
                    handle.write("\n")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    load_development_bundle(root, self.expected)

    def test_membership_missing_or_wrong_group_rejected_even_with_updated_hash(self):
        for mutation in ("missing", "wrong_group"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "input"
                shutil.copytree(self.bundle, root)
                rows = csv_rows(root / "temporal_membership.csv")
                if mutation == "missing":
                    rows.pop()
                else:
                    rows[0]["partition"] = "test"
                write_table(root / "temporal_membership.csv", rows, MEMBERSHIP_SCHEMA)
                expected = refresh_file(root, "temporal_membership.csv")
                with self.assertRaises(ValueError):
                    load_development_bundle(root, expected)

    def test_all_models_offline_same_rows_and_exact_replay_without_test_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            poisoned = root / "poisoned"
            shutil.copytree(self.bundle, poisoned)
            rows = csv_rows(poisoned / "snapshots.csv")
            poisoned_count = 0
            for row in rows:
                if (
                    customer_partition(row["customer_id"]) == "test"
                    and row["prediction_date"] == SCHEDULE["test"][0].isoformat()
                ):
                    row["dormant_30d"] = "TEST LABEL MUST NOT BE PARSED"
                    row["recency_days"] = "TEST FEATURE MUST NOT BE PARSED"
                    poisoned_count += 1
            self.assertGreater(poisoned_count, 0)
            write_table(poisoned / "snapshots.csv", rows, SNAPSHOT_SCHEMA)
            expected = refresh_file(poisoned, "snapshots.csv")
            with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
                original = run_comparators(self.bundle, root / "a", self.expected)
                replay = run_comparators(poisoned, root / "b", expected)
            self.assertEqual(original["status"], "complete")
            self.assertFalse(original["test_scored"])
            self.assertEqual(set(original["cohorts"]), {"train", "validation"})
            reference_keys = None
            for name, result in original["models"].items():
                self.assertEqual(result["metrics"], replay["models"][name]["metrics"])
                a, b = root / "a" / name, root / "b" / name
                self.assertEqual(
                    (a / "validation_predictions.csv").read_bytes(),
                    (b / "validation_predictions.csv").read_bytes(),
                )
                self.assertEqual(
                    result["predictions"]["sha256"], file_hash(a / "validation_predictions.csv")
                )
                predictions = csv_rows(a / "validation_predictions.csv")
                keys = [(r["customer_id"], r["prediction_date"]) for r in predictions]
                if reference_keys is None:
                    reference_keys = keys
                self.assertEqual(keys, reference_keys)
                self.assertTrue(all(r["is_synthetic"] == "true" for r in predictions))
                self.assertTrue(
                    all(customer_partition(r["customer_id"]) == "validation" for r in predictions)
                )
                self.assertEqual(result["positive_class"], 1)
            self.assertEqual(original["cohorts"], replay["cohorts"])
            prior = csv_rows(root / "a" / "constant_prior" / "validation_predictions.csv")
            prevalence = (
                original["cohorts"]["train"]["positives"] / original["cohorts"]["train"]["rows"]
            )
            self.assertTrue(all(float(row["probability_dormant"]) == prevalence for row in prior))
            with self.assertRaises(FileExistsError):
                run_comparators(self.bundle, root / "a", self.expected)

    def test_failure_is_recorded_and_completed_results_preserved(self):
        def broken_factory():
            raise RuntimeError("deliberate model failure")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            with patch("scuba.models.runner.FACTORIES", (prior_model, broken_factory)):
                with self.assertRaisesRegex(RuntimeError, "deliberate model failure"):
                    run_comparators(self.bundle, output, self.expected)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["models"]["constant_prior"]["status"], "complete")
            self.assertTrue((output / "constant_prior" / "validation_predictions.csv").exists())

    def test_cli_rejects_unfrozen_input(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(
                    [
                        "benchmark",
                        "--input",
                        str(self.bundle),
                        "--output",
                        str(Path(directory) / "run"),
                    ]
                )
            self.assertEqual(raised.exception.code, 2)
