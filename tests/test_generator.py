import csv
import json
import random
import tempfile
import unittest
from datetime import date
from hashlib import sha256
from pathlib import Path

from scuba.contract import CUSTOMER_SCHEMA, EVENT_SCHEMA, PRODUCTS, STATUSES, GeneratorConfig
from scuba.generator import generate_rows, write_bundle


class GeneratorTests(unittest.TestCase):
    def test_replay_is_byte_identical_and_global_rng_is_untouched(self):
        state = random.getstate()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = GeneratorConfig(customers=8)
            write_bundle(root / "a", config)
            write_bundle(root / "b", config)
            for name in ("customers.csv", "events.csv", "manifest.json"):
                self.assertEqual((root / "a" / name).read_bytes(), (root / "b" / name).read_bytes())
        self.assertEqual(random.getstate(), state)

    def test_different_seed_changes_rows(self):
        self.assertNotEqual(
            generate_rows(GeneratorConfig(customers=8, seed=3501)),
            generate_rows(GeneratorConfig(customers=8, seed=3502)),
        )

    def test_rows_follow_schema_identity_coverage_and_synthetic_boundary(self):
        config = GeneratorConfig(customers=12)
        customers, events = generate_rows(config)
        ids = {c["customer_id"] for c in customers}
        self.assertEqual(len(ids), config.customers)
        self.assertGreater(len(events), 0)
        self.assertEqual(len({e["event_id"] for e in events}), len(events))
        for customer in customers:
            self.assertEqual(set(customer), set(CUSTOMER_SCHEMA))
            self.assertEqual(customer["is_synthetic"], "true")
            self.assertTrue(customer["customer_id"].startswith("SYN-C"))
        for event in events:
            self.assertEqual(set(event), set(EVENT_SCHEMA))
            self.assertEqual(event["is_synthetic"], "true")
            self.assertIn(event["customer_id"], ids)
            self.assertIn(event["product"], PRODUCTS)
            self.assertIn(event["status"], STATUSES)
            self.assertIs(type(event["amount_minor"]), int)
            self.assertGreater(event["amount_minor"], 0)
            self.assertGreaterEqual(date.fromisoformat(event["event_date"]), config.start)
            self.assertLess(date.fromisoformat(event["event_date"]), config.end_exclusive)

    def test_manifest_matches_written_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            manifest = write_bundle(output, GeneratorConfig(customers=8))
            self.assertEqual(manifest, json.loads((output / "manifest.json").read_text()))
            self.assertEqual(manifest["classification"], "synthetic")
            self.assertEqual(manifest["purpose"], "smoke_fixture")
            self.assertEqual(manifest["seed"], manifest["parameters"]["seed"])
            self.assertEqual(manifest["coverage"]["start_inclusive"], "2032-01-01")
            self.assertEqual(manifest["coverage"]["end_exclusive"], "2032-11-01")
            for name, info in manifest["files"].items():
                contents = (output / name).read_bytes()
                self.assertEqual(sha256(contents).hexdigest(), info["sha256"])
                self.assertNotIn(b"\r", contents)
                with (output / name).open(newline="") as stream:
                    reader = csv.DictReader(stream)
                    rows = list(reader)
                    self.assertEqual(set(reader.fieldnames), set(info["schema"]))
                self.assertEqual(len(rows), info["rows"])
                self.assertTrue(all(row["is_synthetic"] == "true" for row in rows))
            source = Path(__file__).resolve().parents[1] / "src" / "scuba"
            for name, digest in manifest["source_sha256"].items():
                self.assertEqual(sha256((source / name).read_bytes()).hexdigest(), digest)

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            write_bundle(output, GeneratorConfig(customers=2))
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(FileExistsError):
                write_bundle(output, GeneratorConfig(seed=9, customers=2))
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_empty_event_table_still_has_schema_and_null_range(self):
        # Seed 0 produces no attempt for one customer on this one-day fixture.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            manifest = write_bundle(
                output,
                GeneratorConfig(
                    seed=0, customers=1, start=date(2032, 1, 1), end_exclusive=date(2032, 1, 2)
                ),
            )
            self.assertEqual(manifest["files"]["events.csv"]["rows"], 0)
            self.assertEqual(manifest["observed_event_range"], {"min": None, "max": None})
            self.assertEqual(len((output / "events.csv").read_text().splitlines()), 1)
