import unittest
from datetime import date, timedelta

from scuba.contract import (
    TEST_DATE,
    TRAIN_DATES,
    VALIDATION_DATE,
    GeneratorConfig,
    customer_partition,
    require_complete_coverage,
    snapshot_windows,
)


class ContractTests(unittest.TestCase):
    def test_half_open_windows_have_exact_lengths(self):
        origin = date(2032, 4, 1)
        windows = snapshot_windows(origin)
        self.assertEqual(windows["features"], (date(2032, 2, 1), origin))
        self.assertEqual(windows["active"], (date(2032, 3, 2), origin))
        self.assertEqual(windows["outcome"], (origin, date(2032, 5, 1)))
        feature_days = {windows["features"][0] + timedelta(days=i) for i in range(60)}
        outcome_days = {origin + timedelta(days=i) for i in range(30)}
        self.assertFalse(feature_days & outcome_days)
        self.assertNotIn(origin, feature_days)
        self.assertIn(origin, outcome_days)

    def test_exact_coverage_edges_and_censoring(self):
        origin = date(2032, 4, 1)
        exact = GeneratorConfig(start=date(2032, 2, 1), end_exclusive=date(2032, 5, 1))
        require_complete_coverage(origin, exact)
        with self.assertRaisesRegex(ValueError, "history"):
            require_complete_coverage(origin, GeneratorConfig(start=date(2032, 2, 2)))
        with self.assertRaisesRegex(ValueError, "censored"):
            require_complete_coverage(origin, GeneratorConfig(end_exclusive=date(2032, 4, 30)))

    def test_planned_labels_mature_before_next_origin(self):
        for origin in (*TRAIN_DATES, VALIDATION_DATE, TEST_DATE):
            require_complete_coverage(origin, GeneratorConfig())
        self.assertLessEqual(snapshot_windows(max(TRAIN_DATES))["outcome"][1], VALIDATION_DATE)
        self.assertLessEqual(snapshot_windows(VALIDATION_DATE)["outcome"][1], TEST_DATE)

    def test_group_membership_is_order_independent_and_disjoint(self):
        ids = [f"SYN-C{i:06d}" for i in range(1, 601)]
        forward = {customer: customer_partition(customer) for customer in ids}
        reverse = {customer: customer_partition(customer) for customer in reversed(ids)}
        self.assertEqual(forward, reverse)
        groups = {
            name: {c for c, group in forward.items() if group == name}
            for name in ("train", "validation", "test")
        }
        self.assertTrue(all(groups.values()))
        self.assertEqual(sum(map(len, groups.values())), 600)
        self.assertFalse(groups["train"] & groups["validation"])
        self.assertFalse(groups["train"] & groups["test"])
        self.assertFalse(groups["validation"] & groups["test"])
        self.assertNotEqual(forward, {c: customer_partition(c, seed=3502) for c in ids})

    def test_invalid_configuration_is_rejected(self):
        for kwargs in (
            {"customers": 0},
            {"customers": True},
            {"seed": "3501"},
            {"end_exclusive": date(2031, 1, 1)},
            {"start": "2032-01-01"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                GeneratorConfig(**kwargs)
        with self.assertRaises(ValueError):
            customer_partition("")
