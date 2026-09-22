import unittest

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss

from scuba.evaluation import cluster_draws, evaluate_cohort, percentile_interval, point_metrics


class EvaluationTests(unittest.TestCase):
    def test_hand_calculated_scores_bins_threshold_and_top_budget(self):
        # Two tied scores share an AP threshold; key a wins the one-row top budget.
        y, p = [1, 0, 1, 0], [0.8, 0.8, 0.4, 0.0]
        keys = [(c, "2032-08-01") for c in ("b", "a", "c", "d")]
        result = point_metrics(y, p, keys)
        self.assertAlmostEqual(result["average_precision"], 7 / 12)
        self.assertAlmostEqual(result["brier_score"], 0.26)
        self.assertAlmostEqual(result["ece_10_bins"], 0.30)
        self.assertEqual(result["threshold_0.5"], {"tp": 1, "fp": 1, "tn": 1, "fn": 1})
        self.assertEqual(result["top_budgets"]["0.05"]["selected"], 1)
        self.assertEqual(result["top_budgets"]["0.05"]["tp"], 0)
        self.assertEqual(result["reliability"][8]["rows"], 2)
        self.assertIsNone(result["reliability"][1]["mean_probability"])
        perfect = point_metrics([0, 1], [0, 1], [("a", "d"), ("b", "d")])
        self.assertEqual(perfect["reliability"][9]["rows"], 1)
        self.assertEqual(perfect["ece_10_bins"], 0)
        self.assertEqual(perfect["top_budgets"]["0.1"]["lift"], 2)

    def test_point_metrics_match_sklearn_on_ties_and_extreme_scores(self):
        rng = np.random.default_rng(4401)
        for _ in range(20):
            labels = rng.integers(0, 2, size=40)
            probability = rng.integers(0, 11, size=40) / 10
            result = point_metrics(labels, probability, [(str(i), "d") for i in range(40)])
            self.assertAlmostEqual(
                result["average_precision"], average_precision_score(labels, probability)
            )
            self.assertAlmostEqual(result["log_loss"], log_loss(labels, probability))
            self.assertAlmostEqual(result["brier_score"], brier_score_loss(labels, probability))

    def test_empty_single_class_and_invalid_inputs(self):
        for labels in ([], [0, 0], [1, 1]):
            result = point_metrics(
                labels, [0.5] * len(labels), [(str(i), "d") for i in range(len(labels))]
            )
            self.assertIsNone(result["average_precision"])
            self.assertTrue(result["sparse"])
            if not sum(labels):
                self.assertIsNone(result["top_budgets"]["0.1"]["capture"])
        for y, p, keys in (
            ([0, 1], [0.5], [("a", "d"), ("b", "d")]),
            ([0, 2], [0.5, 0.5], [("a", "d"), ("b", "d")]),
            ([0, 1], [0.5, float("nan")], [("a", "d"), ("b", "d")]),
            ([0, 1], [-0.1, 1.1], [("a", "d"), ("b", "d")]),
            ([0, 1], [0.5, 0.5], [("a", "d"), ("a", "d")]),
        ):
            with self.assertRaises(ValueError):
                point_metrics(y, p, keys)

    def test_bootstrap_keeps_complete_customer_clusters(self):
        customers = ["a", "a", "b", "c", "c", "c"]
        for draw in cluster_draws(customers, 30, 4):
            counts = np.bincount(draw, minlength=len(customers))
            self.assertEqual(counts[0], counts[1])
            self.assertEqual(counts[3], counts[4])
            self.assertEqual(counts[4], counts[5])
            self.assertEqual(counts[0] + counts[2] + counts[3], 3)

    def test_paired_identical_models_have_zero_difference_and_replay_ignores_order(self):
        rows = [
            {"customer_id": str(i), "prediction_date": "d", "dormant_30d": i % 2} for i in range(40)
        ]
        probabilities = {"xgboost": np.linspace(0, 1, 40), "hosted_plus": np.linspace(0, 1, 40)}
        result = evaluate_cohort(rows, probabilities, replicates=100)
        pair = result["paired_comparisons"]["hosted_plus_minus_xgboost"]
        self.assertEqual(pair["ap_difference"], 0)
        self.assertEqual(pair["interval"]["lower"], 0)
        self.assertEqual(pair["interval"]["upper"], 0)
        replay = evaluate_cohort(
            rows[::-1], {k: v[::-1] for k, v in probabilities.items()}, replicates=100
        )
        self.assertEqual(result, replay)

    def test_unavailable_bootstrap_is_explicit(self):
        rows = [{"customer_id": str(i), "prediction_date": "d", "dormant_30d": 0} for i in range(2)]
        result = evaluate_cohort(rows, {"xgboost": [0.5, 0.5]}, replicates=100)
        interval = result["models"]["xgboost"]["ap_interval"]
        self.assertEqual(interval["unavailable_reason"], "single_class")
        self.assertEqual(interval["attempted_draws"], 0)
        interval = percentile_interval([0.5] * 79, 100)
        self.assertEqual(interval["unavailable_reason"], "insufficient_valid_draws")
        self.assertEqual(interval["invalid_single_class_draws"], 21)
