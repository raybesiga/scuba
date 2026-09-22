import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scuba.artifacts import file_hash
from scuba.cli import main
from scuba.contract import GeneratorConfig
from scuba.features import FEATURE_COLUMNS
from scuba.pipeline import prepare_bundle


def read_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


class PipelineTests(unittest.TestCase):
    def test_full_bundle_replays_offline_and_hashes_match(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("socket.socket.connect", side_effect=AssertionError("network forbidden")),
        ):
            root = Path(directory)
            config = GeneratorConfig(customers=80)
            audit = prepare_bundle(root / "a", config)
            self.assertEqual(audit, prepare_bundle(root / "b", config))
            files = [p.relative_to(root / "a") for p in (root / "a").rglob("*") if p.is_file()]
            self.assertEqual(len(files), 9)
            for name in files:
                self.assertEqual(
                    (root / "a" / name).read_bytes(), (root / "b" / name).read_bytes(), name
                )
            for folder in (root / "a", root / "a" / "sources"):
                manifest = json.loads((folder / "manifest.json").read_text())
                self.assertEqual(manifest["classification"], "synthetic")
                for name, entry in manifest["files"].items():
                    self.assertEqual(entry["sha256"], file_hash(folder / name))
                    if name.endswith(".csv"):
                        rows = read_rows(folder / name)
                        self.assertEqual(len(rows), entry["rows"])
                        self.assertTrue(all(r["is_synthetic"] == "true" for r in rows))
            manifest = json.loads((root / "a" / "manifest.json").read_text())
            self.assertEqual(
                manifest["source_manifest"]["sha256"],
                file_hash(root / "a" / "sources" / "manifest.json"),
            )
            self.assertEqual(manifest["feature_columns"], list(FEATURE_COLUMNS))
            self.assertEqual(audit["candidate_rows"], config.customers * 5)
            self.assertFalse(audit["random_reference"]["deployment_valid"])
            self.assertTrue(
                all(
                    count == 0
                    for count in audit["temporal_grouped"]["customer_overlap_counts"].values()
                )
            )
            with self.assertRaises(FileExistsError):
                prepare_bundle(root / "a", config)

    def test_serialised_membership_reconciles_with_cohort_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            audit = prepare_bundle(output, GeneratorConfig(customers=80))
            snapshots = read_rows(output / "snapshots.csv")
            by_key = {(r["customer_id"], r["prediction_date"]): r for r in snapshots}
            self.assertEqual(len(by_key), len(snapshots))
            for filename, strategy in (
                ("temporal_membership.csv", "temporal_grouped"),
                ("random_reference_membership.csv", "random_reference"),
            ):
                members = read_rows(output / filename)
                for partition in ("train", "validation", "test"):
                    subset = [
                        by_key[(r["customer_id"], r["prediction_date"])]
                        for r in members
                        if r["partition"] == partition
                    ]
                    stats = audit[strategy]["partitions"][partition]
                    self.assertEqual(len(subset), stats["rows"])
                    self.assertEqual(sum(int(r["dormant_30d"]) for r in subset), stats["positives"])
                    self.assertEqual(len({r["customer_id"] for r in subset}), stats["customers"])
            excluded = read_rows(output / "exclusions.csv")
            self.assertEqual(len(excluded) + len(snapshots), audit["candidate_rows"])

    def test_cli_reports_insufficient_support_without_hiding_artifacts(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as capture:
            output = Path(directory) / "bundle"
            status = main(["prepare", "--output", str(output), "--customers", "80"])
            self.assertEqual(status, 1)
            result = json.loads(capture.getvalue())
            self.assertFalse(result["main_support_passed"])
            self.assertTrue(result["support_failures"])
            self.assertTrue((output / "audit.json").exists())
