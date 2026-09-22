"""Auditable grouped temporal evaluation and diagnostic random-row reference."""

import random
from datetime import date, timedelta
from itertools import combinations

from scuba.contract import DEFAULT_SEED, TEST_DATE, TRAIN_DATES, VALIDATION_DATE, customer_partition
from scuba.features import is_synthetic

SPLIT_VERSION = "1.0.0"
PARTITIONS = ("train", "validation", "test")
SCHEDULE = {"train": TRAIN_DATES, "validation": (VALIDATION_DATE,), "test": (TEST_DATE,)}
MEMBERSHIP_SCHEMA = {
    "customer_id": "string",
    "prediction_date": "date:YYYY-MM-DD",
    "partition": "enum:train|validation|test",
    "is_synthetic": "boolean",
}


def snapshot_key(row: dict) -> tuple[str, str]:
    return row["customer_id"], row["prediction_date"]


def validate_rows(rows: list[dict]) -> None:
    keys = set()
    for row in rows:
        key = snapshot_key(row)
        if key in keys:
            raise ValueError("duplicate snapshot key")
        keys.add(key)
        if not is_synthetic(row["is_synthetic"]):
            raise ValueError("snapshot must be synthetic")
        if type(row["dormant_30d"]) is not int or row["dormant_30d"] not in (0, 1):
            raise ValueError("snapshot label must be 0 or 1")
        date.fromisoformat(row["prediction_date"])


def temporal_split(rows: list[dict], seed: int = DEFAULT_SEED) -> dict[str, list[dict]]:
    validate_rows(rows)
    result = {name: [] for name in PARTITIONS}
    for row in sorted(rows, key=snapshot_key):
        partition = customer_partition(row["customer_id"], seed)
        if date.fromisoformat(row["prediction_date"]) in SCHEDULE[partition]:
            result[partition].append(row)
    validate_temporal_split(result, seed)
    return result


def validate_temporal_split(partitions: dict[str, list[dict]], seed: int = DEFAULT_SEED) -> None:
    if set(partitions) != set(PARTITIONS):
        raise ValueError("expected train, validation and test partitions")
    validate_rows([row for name in PARTITIONS for row in partitions[name]])
    groups = {name: {r["customer_id"] for r in partitions[name]} for name in PARTITIONS}
    if any(groups[left] & groups[right] for left, right in combinations(PARTITIONS, 2)):
        raise ValueError("customer overlap in temporal split")
    for name in PARTITIONS:
        for row in partitions[name]:
            if customer_partition(row["customer_id"], seed) != name:
                raise ValueError("customer assigned to incorrect group")
            if date.fromisoformat(row["prediction_date"]) not in SCHEDULE[name]:
                raise ValueError("snapshot outside partition schedule")
    for earlier, later in (("train", "validation"), ("validation", "test")):
        if partitions[earlier] and partitions[later]:
            mature = max(
                date.fromisoformat(r["prediction_date"]) + timedelta(days=30)
                for r in partitions[earlier]
            )
            first_prediction = min(
                date.fromisoformat(r["prediction_date"]) for r in partitions[later]
            )
            if mature > first_prediction:
                raise ValueError("labels are not mature before next evaluation origin")


def random_reference(rows: list[dict], seed: int = DEFAULT_SEED) -> dict[str, list[dict]]:
    """Class-wise 60/20/20 split. Explicitly not a deployment-valid evaluation."""
    validate_rows(rows)
    result = {name: [] for name in PARTITIONS}
    for label in (0, 1):
        group = sorted((r for r in rows if r["dormant_30d"] == label), key=snapshot_key)
        if len(group) < 5:
            raise ValueError("random reference requires at least five rows per class")
        random.Random(f"{seed}:{label}").shuffle(group)
        train_end, validation_count = len(group) * 60 // 100, len(group) * 20 // 100
        result["train"].extend(group[:train_end])
        result["validation"].extend(group[train_end : train_end + validation_count])
        result["test"].extend(group[train_end + validation_count :])
    return {name: sorted(result[name], key=snapshot_key) for name in PARTITIONS}


def membership_rows(partitions: dict[str, list[dict]]) -> list[dict]:
    return [
        {
            "customer_id": r["customer_id"],
            "prediction_date": r["prediction_date"],
            "partition": name,
            "is_synthetic": "true",
        }
        for name in PARTITIONS
        for r in partitions[name]
    ]
