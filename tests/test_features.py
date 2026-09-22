import unittest
from copy import deepcopy
from datetime import date

from scuba.contract import ARCHETYPES, CHANNELS, PRODUCTS, REGIONS, GeneratorConfig
from scuba.features import FEATURE_COLUMNS, SNAPSHOT_SCHEMA, build_snapshots, model_inputs

ORIGIN = date(2032, 4, 1)


def customer():
    return {
        "customer_id": "SYN-C000001",
        "archetype": ARCHETYPES[0],
        "channel": CHANNELS[0],
        "region": REGIONS[0],
        "is_synthetic": "true",
    }


def event(identifier, day, value=100, product=0, status="success"):
    return {
        "event_id": f"SYN-E{identifier}",
        "customer_id": "SYN-C000001",
        "event_date": day,
        "amount_minor": value,
        "product": PRODUCTS[product],
        "status": status,
        "is_synthetic": "true",
    }


def fixture():
    return [
        event(1, "2032-01-31", 9999),
        event(2, "2032-02-01"),
        event(3, "2032-02-11", product=1),
        event(4, "2032-03-02", 50),
        event(5, "2032-03-31", 150, product=2),
        event(6, "2032-03-31", 999, status="failed"),
        event(7, "2032-02-20", 888, status="reversed"),
        event(8, "2032-04-01", 400),
    ]


class FeatureTests(unittest.TestCase):
    def build(self, events, config=None, dates=(ORIGIN,)):
        return build_snapshots([customer()], events, config or GeneratorConfig(customers=1), dates)

    def test_hand_calculated_features_and_window_boundaries(self):
        rows, excluded = self.build(fixture())
        self.assertEqual(excluded, [])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        expected = {
            "recency_days": 1,
            "frequency_trend": 0,
            "value_trend": 0,
            "gap_trend_days": 19,
            "product_diversity": 3,
            "merchant_adoption": 1,
            "product_concentration": 0.375,
            "active_day_trend": 0,
            "failure_reversal_rate": 2 / 6,
        }
        for name, value in expected.items():
            self.assertAlmostEqual(row[name], value, msg=name)
        self.assertEqual(set(row), set(SNAPSHOT_SCHEMA))
        self.assertEqual(row["dormant_30d"], 0)
        self.assertEqual(row["success_count_60d"], 4)
        self.assertEqual(row["activity_level"], "low")
        self.assertEqual(row["is_synthetic"], "true")

    def test_future_changes_affect_only_label_and_never_features(self):
        original, _ = self.build(fixture())
        altered = [e for e in fixture() if e["event_date"] < "2032-04-01"]
        altered += [
            event(9, "2032-04-01", 999999, status="failed"),
            event(10, "2032-04-30", 999999, status="reversed"),
            event(11, "2032-05-01", 999999, product=1),
        ]
        changed, _ = self.build(altered)
        self.assertEqual(original[0]["dormant_30d"], 0)
        self.assertEqual(changed[0]["dormant_30d"], 1)
        self.assertEqual(model_inputs(original), model_inputs(changed))
        self.assertEqual(
            {k: v for k, v in original[0].items() if k != "dormant_30d"},
            {k: v for k, v in changed[0].items() if k != "dormant_30d"},
        )
        altered += [event(12, "2032-04-30", 1)]
        rows, _ = self.build(altered)
        self.assertEqual(rows[0]["dormant_30d"], 0)

    def test_active_boundary_and_failed_reversed_only_customers(self):
        for day, status, eligible in (
            ("2032-03-02", "success", True),
            ("2032-03-01", "success", False),
            ("2032-03-31", "failed", False),
            ("2032-03-31", "reversed", False),
        ):
            with self.subTest(day=day, status=status):
                rows, excluded = self.build([event(1, day, status=status)])
                self.assertEqual(bool(rows), eligible)
                if eligible:
                    self.assertEqual(rows[0]["recency_days"], 30)
                    self.assertIsNone(rows[0]["gap_trend_days"])
                else:
                    self.assertEqual(excluded[0]["reason"], "inactive")

    def test_incomplete_history_and_censoring_are_not_dormancy(self):
        for config, expected in (
            (GeneratorConfig(customers=1, start=date(2032, 2, 2)), "incomplete_history"),
            (GeneratorConfig(customers=1, end_exclusive=date(2032, 4, 30)), "censored_outcome"),
        ):
            rows, excluded = self.build([event(1, "2032-03-31")], config)
            self.assertFalse(rows)
            self.assertEqual(excluded[0]["reason"], expected)
            self.assertNotIn("dormant_30d", excluded[0])
        exact = GeneratorConfig(customers=1, start=date(2032, 2, 1), end_exclusive=date(2032, 5, 1))
        rows, excluded = self.build([event(1, "2032-03-31")], exact)
        self.assertFalse(excluded)
        self.assertEqual(rows[0]["dormant_30d"], 1)

    def test_same_day_attempts_distinguish_frequency_and_active_days(self):
        original = fixture()
        original.append(event(9, "2032-02-01"))
        rows, _ = self.build(original)
        row = rows[0]
        self.assertEqual(row["gap_trend_days"], 24)
        self.assertEqual(row["frequency_trend"], -0.25)
        self.assertEqual(row["active_day_trend"], 0)

    def test_order_independence_and_feature_allowlist(self):
        rows, excluded = self.build(fixture())
        reversed_rows, reversed_excluded = self.build(list(reversed(fixture())))
        self.assertEqual((rows, excluded), (reversed_rows, reversed_excluded))
        rows[0]["future_success_count"] = 500
        projected = model_inputs(rows)[0]
        self.assertEqual(set(projected), set(FEATURE_COLUMNS))
        for name in (
            "dormant_30d",
            "archetype",
            "customer_id",
            "prediction_date",
            "is_synthetic",
            "success_count_60d",
            "activity_level",
            "future_success_count",
        ):
            self.assertNotIn(name, projected)

    def test_invalid_sources_and_duplicate_dates_are_rejected(self):
        for field, value in (
            ("customer_id", "SYN-Cunknown"),
            ("amount_minor", 0),
            ("amount_minor", True),
            ("status", "pending"),
            ("is_synthetic", False),
            ("is_synthetic", 1),
            ("event_date", "2033-01-01"),
            ("product", "unknown"),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                invalid = fixture()
                invalid[0][field] = value
                self.build(invalid)
        with self.assertRaisesRegex(ValueError, "duplicate event"):
            self.build(fixture() + [deepcopy(fixture()[0])])
        with self.assertRaisesRegex(ValueError, "duplicate prediction"):
            self.build(fixture(), dates=(ORIGIN, ORIGIN))
        with self.assertRaisesRegex(ValueError, "duplicate customer"):
            build_snapshots(
                [customer(), customer()], fixture(), GeneratorConfig(customers=2), (ORIGIN,)
            )

    def test_activity_slice_thresholds_and_null_gap(self):
        for count, expected in ((5, "low"), (6, "medium"), (20, "medium"), (21, "high")):
            rows, _ = self.build([event(i, "2032-03-31") for i in range(count)])
            self.assertEqual(rows[0]["activity_level"], expected)
            self.assertIsNone(rows[0]["gap_trend_days"])

    def test_old_events_outside_lookback_do_not_influence_features(self):
        rows, _ = self.build(fixture())
        changed = fixture()
        changed[0]["amount_minor"] = 1
        changed[0]["status"] = "reversed"
        self.assertEqual(rows, self.build(changed)[0])
