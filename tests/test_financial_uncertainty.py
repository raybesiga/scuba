"""Check pairing, ranking ties and reproducibility on invented rows."""

import unittest

import numpy as np
from sklearn.metrics import log_loss

from scuba.financial_uncertainty import paired_intervals


class FinancialUncertaintyTests(unittest.TestCase):
    def test_identical_models_have_exactly_zero_paired_intervals(self):
        result = paired_intervals(
            [0, 1, 1, 0], [0.2, 0.8, 0.5, 0.5], [0.2, 0.8, 0.5, 0.5], list("abcd"), repeats=50
        )
        for value in result["differences"].values():
            self.assertEqual(value, dict(estimate=0.0, lower=0.0, upper=0.0))

    def test_direction_ties_and_seed_replay(self):
        y = np.array([1, 0] * 10)
        a = np.where(y, 0.9, 0.1)
        b = np.full(20, 0.5)
        ids = [f"id{i:02}" for i in range(20)]
        result = paired_intervals(y, a, b, ids, repeats=100)
        self.assertEqual(result, paired_intervals(y, a, b, ids, repeats=100))
        self.assertAlmostEqual(
            result["differences"]["log_loss"]["estimate"], log_loss(y, a) - log_loss(y, b)
        )
        self.assertLess(result["differences"]["log_loss"]["upper"], 0)
        self.assertEqual(result["differences"]["capture_0.1"]["estimate"], 1)
        reverse = paired_intervals(y, b, a, ids, repeats=100)
        for key, value in result["differences"].items():
            other = reverse["differences"][key]
            self.assertAlmostEqual(value["lower"], -other["upper"])
            self.assertAlmostEqual(value["upper"], -other["lower"])

    def test_invalid_probabilities_and_duplicate_ids_rejected(self):
        for p, ids in (([float("nan"), 0.2], ["a", "b"]), ([0.1, 0.2], ["a", "a"])):
            with self.assertRaises(ValueError):
                paired_intervals([0, 1], p, [0.3, 0.7], ids, repeats=10)
