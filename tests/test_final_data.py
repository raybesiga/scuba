import copy
import tempfile
import unittest
from pathlib import Path

from scuba.artifacts import file_hash, write_json
from scuba.contract import GeneratorConfig
from scuba.final_data import checked_final_plan, digest, load_final_partitions, prepare_final_plan
from scuba.models.data import load_development_bundle
from scuba.models.runner import run_comparators
from scuba.pipeline import prepare_bundle


class FinalDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.input, cls.local = cls.root / "input", cls.root / "local"
        prepare_bundle(cls.input, GeneratorConfig(customers=180))
        cls.expected = file_hash(cls.input / "manifest.json")
        run_comparators(cls.input, cls.local, cls.expected)
        cls.plan = prepare_final_plan(
            cls.input,
            cls.local,
            file_hash(cls.local / "manifest.json"),
            cls.root / "frozen",
            cls.expected,
        )
        cls.plan_path = cls.root / "frozen/plan.json"
        cls.plan_hash = digest(cls.plan)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_final_partitions_match_frozen_memberships_and_original_training(self):
        plan = checked_final_plan(self.input, self.plan_path, self.plan_hash)
        development, _, _ = load_development_bundle(self.input, self.expected)
        temporal, audit = load_final_partitions(self.input, plan, "temporal")
        self.assertEqual(temporal["train"], development["train"])
        self.assertEqual(temporal["validation"], development["validation"])
        self.assertTrue(temporal["test"])
        self.assertEqual(set(audit["customer_overlap_counts"].values()), {0})
        random, audit = load_final_partitions(self.input, plan, "random_reference")
        self.assertTrue(any(audit["customer_overlap_counts"].values()))
        self.assertEqual(
            sum(len(r) for r in random.values()),
            sum(1 for _ in (self.input / "snapshots.csv").open()) - 1,
        )

    def test_plan_or_recipe_changes_stop_before_loading_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            bad = copy.deepcopy(self.plan)
            bad["threshold"] = 0.2
            write_json(path, {"plan": bad, "sha256": self.plan_hash})
            with self.assertRaisesRegex(ValueError, "final plan changed"):
                checked_final_plan(self.input, path, self.plan_hash)
            bad = copy.deepcopy(self.plan)
            bad["models"]["xgboost"]["estimator"]["max_depth"] = 9
            write_json(path, {"plan": bad, "sha256": digest(bad)})
            with self.assertRaisesRegex(ValueError, "recipe changed"):
                checked_final_plan(self.input, path, digest(bad))
