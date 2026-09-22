"""Read hash-verified synthetic M1 train/validation rows, never test model inputs."""

import csv
import json
from datetime import date
from pathlib import Path

from scuba.artifacts import file_hash
from scuba.contract import customer_partition
from scuba.features import FEATURE_COLUMNS, FEATURE_VERSION, SNAPSHOT_SCHEMA, is_synthetic
from scuba.splits import (
    MEMBERSHIP_SCHEMA,
    SCHEDULE,
    SPLIT_VERSION,
    snapshot_key,
    validate_temporal_split,
)

FROZEN_MANIFESTS = {
    3501: "6f073aacfdb3923572c14c756fa1a4de78cc7818f375f2e618da28810b469e29",
    3502: "98cbe77247191a6f49b8857da41744c076dd223d6c2876d93a2eaada94cea61b",
    3503: "a7d499a124ffcebc08c1e9a2852546eeaaac4cbe4dfc0a883c9d567f6b4c1801",
}


def load_development_bundle(root: Path, expected_manifest_hash: str | None = None):
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    actual_hash = file_hash(manifest_path)
    expected = expected_manifest_hash or FROZEN_MANIFESTS.get(
        manifest["parameters"]["generator_seed"]
    )
    if not expected or actual_hash != expected:
        raise ValueError("input manifest does not match the frozen M1 hash")
    if (
        manifest["classification"] != "synthetic"
        or manifest["purpose"] != "benchmark_snapshots"
        or manifest["feature_columns"] != list(FEATURE_COLUMNS)
        or manifest["feature_version"] != FEATURE_VERSION
        or manifest["split_version"] != SPLIT_VERSION
        or manifest["temporal_schedule"]
        != {k: [d.isoformat() for d in v] for k, v in SCHEDULE.items()}
    ):
        raise ValueError("incompatible synthetic feature/split contract")
    consumed = {"manifest.json": actual_hash}
    for name in ("snapshots.csv", "temporal_membership.csv"):
        consumed[name] = file_hash(root / name)
        if consumed[name] != manifest["files"][name]["sha256"]:
            raise ValueError(f"input hash mismatch: {name}")
    source_name = "sources/manifest.json"
    consumed[source_name] = file_hash(root / source_name)
    if (
        manifest["source_manifest"]["path"] != source_name
        or consumed[source_name] != manifest["source_manifest"]["sha256"]
    ):
        raise ValueError("source manifest hash mismatch")

    split_seed = manifest["parameters"]["split_seed"]
    membership = {}
    with (root / "temporal_membership.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(MEMBERSHIP_SCHEMA):
            raise ValueError("invalid membership columns")
        for row in reader:
            key, partition = snapshot_key(row), row["partition"]
            if key in membership or not is_synthetic(row["is_synthetic"]):
                raise ValueError("duplicate or non-synthetic membership")
            if (
                partition not in SCHEDULE
                or customer_partition(key[0], split_seed) != partition
                or date.fromisoformat(key[1]) not in SCHEDULE[partition]
            ):
                raise ValueError("membership violates customer/date assignment")
            membership[key] = partition
    if len(membership) != manifest["files"]["temporal_membership.csv"]["rows"]:
        raise ValueError("membership row count mismatch")
    partitions = {"train": [], "validation": [], "test": []}
    all_keys, expected_membership = set(), set()
    with (root / "snapshots.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(SNAPSHOT_SCHEMA):
            raise ValueError("invalid snapshot columns")
        for row in reader:
            key = snapshot_key(row)
            if key in all_keys or not is_synthetic(row["is_synthetic"]):
                raise ValueError("duplicate or non-synthetic snapshot")
            all_keys.add(key)
            assigned = customer_partition(key[0], split_seed)
            if date.fromisoformat(key[1]) in SCHEDULE[assigned]:
                expected_membership.add(key)
            partition = membership.get(key)
            if partition not in ("train", "validation"):
                continue  # Do not parse held-out features or outcomes.
            row["dormant_30d"] = int(row["dormant_30d"])
            partitions[partition].append(row)
    if len(all_keys) != manifest["files"]["snapshots.csv"]["rows"]:
        raise ValueError("snapshot row count mismatch")
    if set(membership) != expected_membership:
        raise ValueError("membership does not cover exactly the scheduled snapshots")
    validate_temporal_split(partitions, split_seed)
    for partition in ("train", "validation"):
        partitions[partition].sort(key=snapshot_key)
        if {r["dormant_30d"] for r in partitions[partition]} != {0, 1}:
            raise ValueError(f"{partition} requires both classes")
    return {name: partitions[name] for name in ("train", "validation")}, manifest, consumed
