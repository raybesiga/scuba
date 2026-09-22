import unittest
from copy import deepcopy

from scuba.audit import split_audit
from scuba.contract import ARCHETYPES, DEFAULT_SEED, customer_partition
from scuba.features import PREDICTION_DATES
from scuba.splits import (
    PARTITIONS,
    SCHEDULE,
    random_reference,
    snapshot_key,
    temporal_split,
    validate_temporal_split,
)


def rows_fixture():
    return [
        {
            "customer_id": f"SYN-C{index:06d}",
            "prediction_date": day.isoformat(),
            "dormant_30d": index % 2,
            "archetype": ARCHETYPES[index % 3],
            "activity_level": "medium",
            "is_synthetic": "true",
        }
        for index in range(1, 101)
        for day in PREDICTION_DATES
    ]


class SplitTests(unittest.TestCase):
    def test_main_split_uses_only_assigned_customers_and_dates(self):
        result = temporal_split(rows_fixture())
        validate_temporal_split(result)
        for partition, rows in result.items():
            self.assertTrue(rows)
            for row in rows:
                self.assertEqual(customer_partition(row["customer_id"], DEFAULT_SEED), partition)
                self.assertIn(row["prediction_date"], [d.isoformat() for d in SCHEDULE[partition]])
        audit = split_audit(result)
        self.assertTrue(all(value == 0 for value in audit["customer_overlap_counts"].values()))
        self.assertEqual(result, temporal_split(list(reversed(rows_fixture()))))

    def test_forged_customer_overlap_and_dates_fail(self):
        result = temporal_split(rows_fixture())
        overlap = deepcopy(result)
        row = dict(overlap["train"][0], prediction_date="2032-08-01")
        overlap["validation"].append(row)
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_temporal_split(overlap)
        wrong_date = deepcopy(result)
        wrong_date["test"][0]["prediction_date"] = "2032-09-01"
        with self.assertRaisesRegex(ValueError, "schedule"):
            validate_temporal_split(wrong_date)
        wrong_group = deepcopy(result)
        row = wrong_group["test"].pop(0)
        row["prediction_date"] = "2032-08-01"
        wrong_group["validation"].append(row)
        with self.assertRaisesRegex(ValueError, "incorrect group"):
            validate_temporal_split(wrong_group)

    def test_random_split_is_stratified_exhaustive_and_order_independent(self):
        rows = rows_fixture()
        result = random_reference(rows)
        self.assertEqual(result, random_reference(list(reversed(rows))))
        self.assertNotEqual(result, random_reference(rows, 3502))
        keys = [snapshot_key(r) for partition in PARTITIONS for r in result[partition]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), {snapshot_key(r) for r in rows})
        for partition, count in (("train", 300), ("validation", 100), ("test", 100)):
            self.assertEqual(len(result[partition]), count)
            self.assertEqual(sum(r["dormant_30d"] for r in result[partition]), count // 2)
        audit = split_audit(result)
        self.assertTrue(all(value > 0 for value in audit["customer_overlap_counts"].values()))

    def test_sparse_single_class_and_duplicate_rows_are_rejected(self):
        rows = rows_fixture()
        with self.assertRaisesRegex(ValueError, "five rows per class"):
            random_reference([r for r in rows if r["dormant_30d"] == 0])
        for splitter in (temporal_split, random_reference):
            with self.assertRaisesRegex(ValueError, "duplicate snapshot"):
                splitter(rows + [rows[0]])

    def test_sparse_slice_has_counts_and_no_misleading_rate(self):
        partitions = {name: [] for name in PARTITIONS}
        partitions["train"] = rows_fixture()[:1]
        audit = split_audit(partitions)
        self.assertEqual(audit["partitions"]["validation"]["rows"], 0)
        self.assertIsNone(audit["partitions"]["validation"]["dormancy_rate"])
        self.assertTrue(audit["partitions"]["train"]["sparse_support"])
