import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scuba.artifacts import file_hash, write_json
from scuba.contract import GeneratorConfig
from scuba.final_data import digest, load_final_partitions, prepare_final_plan
from scuba.final_runner import run_final
from scuba.final_worker import run_worker
from scuba.models.runner import run_comparators
from scuba.pipeline import prepare_bundle


class FinalEvaluationTests(unittest.TestCase):
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

    def test_worker_keeps_test_labels_out_of_fit_and_reproduces_validation(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("socket.socket.connect", side_effect=AssertionError("offline")),
        ):
            spec = {
                "input": str(self.input),
                "plan": str(self.plan_path),
                "plan_sha256": self.plan_hash,
                "regime": "temporal",
                "model": "constant_prior",
            }
            result = run_worker(spec, Path(directory) / "worker")
            train_rate = self.plan["models"]["constant_prior"]["estimator"]["strategy"]
            self.assertEqual(train_rate, "prior")
            self.assertEqual(
                result["predictions"]["validation"]["sha256"],
                self.plan["validation_prediction_hashes"]["constant_prior"],
            )
            self.assertEqual(result["status"], "complete")
            # Fit labels must match the original training set; outcome changes in
            # test cannot alter this validation prediction hash or training prior.
            partitions, _ = load_final_partitions(self.input, self.plan, "temporal")
            partitions["test"] = [
                {**r, "dormant_30d": 1 - r["dormant_30d"]} for r in partitions["test"]
            ]
            with patch("scuba.final_worker.load_final_partitions", return_value=(partitions, {})):
                changed = run_worker(spec, Path(directory) / "changed")
            self.assertEqual(
                changed["predictions"]["validation"], result["predictions"]["validation"]
            )

    def test_fresh_process_runner_repeats_deterministically(self):
        # A reduced fixture plan exercises real child processes without timing
        # the full benchmark in unit tests; production plans always specify 3.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = copy.deepcopy(self.plan)
            plan["repetitions"], plan["bootstrap_replicates"] = 1, 10
            path = root / "plan.json"
            write_json(path, {"plan": plan, "sha256": digest(plan)})
            result = run_final(self.input, path, digest(plan), "temporal", root / "run")
            self.assertEqual(result["status"], "complete")
            self.assertTrue(result["test_scored"])
            self.assertEqual(result["api_requests"], 0)
            for name, model in result["models"].items():
                self.assertEqual(
                    model["repetitions"][0]["predictions"]["validation"]["sha256"],
                    self.plan["validation_prediction_hashes"][name],
                )
            evaluation = json.loads((root / "run/evaluation.json").read_text())
            self.assertEqual(evaluation["regime"], "temporal")
            self.assertEqual(set(evaluation["evaluations"]), {"test", "validation"})
