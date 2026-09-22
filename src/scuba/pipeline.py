"""Generate and audit M1 data locally; there is no dataset import path."""

import platform
from pathlib import Path

from scuba.artifacts import file_hash, source_hashes, write_json, write_table
from scuba.audit import build_audit
from scuba.contract import DEFAULT_SEED, GeneratorConfig
from scuba.features import (
    EXCLUSION_SCHEMA,
    FEATURE_COLUMNS,
    FEATURE_VERSION,
    SNAPSHOT_SCHEMA,
    build_snapshots,
)
from scuba.simulation import generate_rows, write_sources
from scuba.splits import (
    MEMBERSHIP_SCHEMA,
    SCHEDULE,
    SPLIT_VERSION,
    membership_rows,
    random_reference,
    temporal_split,
)


def prepare_bundle(output: Path, config: GeneratorConfig, split_seed: int = DEFAULT_SEED) -> dict:
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    customers, events = generate_rows(config)
    snapshots, exclusions = build_snapshots(customers, events, config)
    temporal = temporal_split(snapshots, split_seed)
    reference = random_reference(snapshots, split_seed)
    audit = build_audit(snapshots, exclusions, temporal, reference, split_seed)
    output.mkdir(parents=True, exist_ok=False)
    write_sources(output / "sources", config, customers, events)
    files = {}
    for filename, rows, schema in (
        ("snapshots.csv", snapshots, SNAPSHOT_SCHEMA),
        ("exclusions.csv", exclusions, EXCLUSION_SCHEMA),
        ("temporal_membership.csv", membership_rows(temporal), MEMBERSHIP_SCHEMA),
        ("random_reference_membership.csv", membership_rows(reference), MEMBERSHIP_SCHEMA),
    ):
        files[filename] = write_table(output / filename, rows, schema)
    write_json(output / "audit.json", audit)
    files["audit.json"] = {"sha256": file_hash(output / "audit.json"), "schema": "scuba.audit/v1"}
    manifest = {
        "classification": "synthetic",
        "purpose": "benchmark_snapshots",
        "feature_version": FEATURE_VERSION,
        "split_version": SPLIT_VERSION,
        "source_manifest": {
            "path": "sources/manifest.json",
            "sha256": file_hash(output / "sources/manifest.json"),
        },
        "source_sha256": source_hashes(),
        "python_version": platform.python_version(),
        "feature_columns": list(FEATURE_COLUMNS),
        "csv_null_encoding": "empty field",
        "parameters": {
            "generator_seed": config.seed,
            "split_seed": split_seed,
            "customers": config.customers,
            "start_inclusive": config.start.isoformat(),
            "end_exclusive": config.end_exclusive.isoformat(),
            "timezone": "UTC",
        },
        "windows": {"features": "[t-60d,t)", "active": "[t-30d,t)", "outcome": "[t,t+30d)"},
        "temporal_schedule": {
            name: [d.isoformat() for d in dates] for name, dates in SCHEDULE.items()
        },
        "eligibility": "Complete 60-day history and 30-day outcome; success in preceding 30 days.",
        "random_reference": "Class-wise seeded row shuffle, floor 60/20/remainder; diagnostic only.",
        "files": files,
    }
    write_json(output / "manifest.json", manifest)
    return audit
