import copy
import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scuba.artifacts import file_hash
from scuba.contract import GeneratorConfig
from scuba.features import FEATURE_COLUMNS
from scuba.integrations.tabpfn_plan import (
    TabPFNConfig,
    check_limits,
    checked_estimate,
    plan_digest,
    prepare_plan,
)
from scuba.pipeline import prepare_bundle


def limits_fixture():
    limits = {
        "train_set_max_rows": 1000000,
        "train_set_max_cells": 20000000,
        "test_set_max_rows": 1000000,
        "test_set_max_cells": 20000000,
        "max_cols": 20000,
        "max_classes": 160,
        "predict_row_pairs_budget": 250000000000,
    }
    return {
        "model_limits": {"v3.5": limits, "v3.5-fast": limits.copy()},
        "dataset_max_size_bytes": 1000000000,
    }


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / "input"
        prepare_bundle(cls.root, GeneratorConfig(customers=180))
        cls.expected = file_hash(cls.root / "manifest.json")
        cls.plan, cls.payloads, cls.rows = prepare_plan(cls.root, TabPFNConfig(), cls.expected)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_offline_replay_allowlist_and_labels(self):
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            plan, payloads, rows = prepare_plan(self.root, TabPFNConfig(), self.expected)
        self.assertEqual(plan_digest(plan), plan_digest(self.plan))
        self.assertEqual(payloads, self.payloads)
        self.assertFalse(plan["test_cohort_included"])
        for name in ("train", "validation"):
            table = list(csv.DictReader(io.StringIO(payloads[name].decode())))
            self.assertEqual(tuple(table[0]), FEATURE_COLUMNS)
            self.assertEqual(len(table), len(rows[name]))
            self.assertTrue(all(row["is_synthetic"] == "true" for row in rows[name]))
        labels = list(csv.DictReader(io.StringIO(payloads["labels"].decode())))
        self.assertEqual(
            [int(r["dormant_30d"]) for r in labels], [r["dormant_30d"] for r in rows["train"]]
        )

    def test_every_model_limit_and_missing_fields_fail_closed(self):
        self.assertEqual(check_limits(self.plan, limits_fixture())["model_version"], "v3.5")
        for key in limits_fixture()["model_limits"]["v3.5"]:
            limits = limits_fixture()
            limits["model_limits"]["v3.5"][key] = 0
            with self.subTest(limit=key), self.assertRaises(ValueError):
                check_limits(self.plan, limits)
        limits = limits_fixture()
        limits["dataset_max_size_bytes"] = 1
        with self.assertRaises(ValueError):
            check_limits(self.plan, limits)
        with self.assertRaises(ValueError):
            check_limits(self.plan, {})

    def test_variant_identity_and_thinking_estimates(self):
        fast, _, _ = prepare_plan(self.root, TabPFNConfig("fast"), self.expected)
        self.assertEqual(fast["fit_parameters"]["tabpfn_config"]["model_path"], "v3.5-fast_default")
        thinking, _, _ = prepare_plan(self.root, TabPFNConfig("thinking"), self.expected)
        self.assertEqual(
            [r["operation"] for r in thinking["estimate_requests"]],
            ["thinking_fit", "thinking_predict"],
        )
        self.assertEqual(thinking["estimate_requests"][0]["test_rows"], 0)
        self.assertEqual(thinking["fit_parameters"]["thinking_effort_metric"], "log_loss")
        with self.assertRaises(ValueError):
            TabPFNConfig("base")
        with self.assertRaises(ValueError):
            TabPFNConfig(n_estimators=0)

    def test_estimates_must_match_settings(self):
        request = self.plan["estimate_requests"][0]
        response = {
            "estimated_cost": 10000,
            "pricing_version": "fictional-test-rate",
            "inputs": request.copy(),
        }
        self.assertEqual(checked_estimate(request, response)["estimated_tokens"], 10000)
        bad = copy.deepcopy(response)
        bad["inputs"]["n_estimators"] = 1
        with self.assertRaises(ValueError):
            checked_estimate(request, bad)
        with self.assertRaises(ValueError):
            checked_estimate(request, {**response, "inputs": []})
        for value in (0, -1, True, None):
            bad = {**response, "estimated_cost": value}
            with self.assertRaises(ValueError):
                checked_estimate(request, bad)
