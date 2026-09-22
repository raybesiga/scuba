"""Explicit final-evaluation boundary and frozen model execution plans."""

import csv
import hashlib
import json
from pathlib import Path

from scuba.artifacts import file_hash, write_json
from scuba.audit import split_audit
from scuba.features import PREDICTION_DATES
from scuba.models.data import load_development_bundle
from scuba.models.runner import FACTORIES, json_settings
from scuba.splits import membership_rows, random_reference, temporal_split, validate_rows

ROOT = Path(__file__).resolve().parents[2]
PROTOCOLS = ("docs/M4_SPEC.md", "docs/M4_FINAL_PROTOCOL.md")


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def model_sources():
    paths = list((ROOT / "src/scuba/models").glob("*.py"))
    paths += [ROOT / f"src/scuba/{name}.py" for name in ("features", "splits", "contract")]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(paths)}


def prepare_final_plan(input_dir, local_run, local_hash, output, expected_manifest_hash=None):
    # This established loader excludes test feature/outcome parsing.
    _, source, consumed = load_development_bundle(input_dir, expected_manifest_hash)
    if file_hash(local_run / "manifest.json") != local_hash:
        raise ValueError("M2 manifest changed")
    local = json.loads((local_run / "manifest.json").read_text())
    models = {factory().name: json_settings(factory().settings()) for factory in FACTORIES}
    if (
        local.get("status") != "complete"
        or local.get("phase") != "M2_validation_only"
        or local.get("test_scored") is not False
        or local.get("input_files") != consumed
        or set(local.get("models", {})) != set(models)
        or any(
            local["models"][name].get("status") != "complete"
            or local["models"][name]["settings"] != settings
            for name, settings in models.items()
        )
    ):
        raise ValueError("model recipe differs from the frozen M2 run")
    random_path = input_dir / "random_reference_membership.csv"
    if file_hash(random_path) != source["files"][random_path.name]["sha256"]:
        raise ValueError("random membership hash mismatch")
    plan = {
        "schema": "scuba.final-plan/v1",
        "classification": "synthetic",
        "input_files": {**consumed, random_path.name: file_hash(random_path)},
        "input_parameters": source["parameters"],
        "m2_manifest_sha256": local_hash,
        "models": models,
        "model_source_sha256": model_sources(),
        "validation_prediction_hashes": {
            name: local["models"][name]["predictions"]["sha256"] for name in models
        },
        "dependency_lock_sha256": file_hash(ROOT / "uv.lock"),
        "protocol_sha256": {name: file_hash(ROOT / name) for name in PROTOCOLS},
        "regimes": ["temporal", "random_reference"],
        "repetitions": 3,
        "calibration": None,
        "threshold": 0.5,
        "budgets": [0.05, 0.10],
        "bootstrap_replicates": 1000,
        "bootstrap_seed": 4401,
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "plan.json", {"plan": plan, "sha256": digest(plan)})
    return plan


def checked_final_plan(input_dir, path, expected_digest):
    envelope = json.loads(path.read_text())
    plan = envelope["plan"]
    if envelope["sha256"] != expected_digest or digest(plan) != expected_digest:
        raise ValueError("final plan changed")
    if (
        plan["model_source_sha256"] != model_sources()
        or plan["dependency_lock_sha256"] != file_hash(ROOT / "uv.lock")
        or plan["protocol_sha256"] != {name: file_hash(ROOT / name) for name in PROTOCOLS}
        or plan["models"]
        != {factory().name: json_settings(factory().settings()) for factory in FACTORIES}
    ):
        raise ValueError("frozen execution recipe changed")
    for name, expected in plan["input_files"].items():
        if file_hash(input_dir / name) != expected:
            raise ValueError("frozen input changed")
    return plan


def load_final_partitions(input_dir, plan, regime):
    if regime not in ("temporal", "random_reference"):
        raise ValueError("unknown final regime")
    with (input_dir / "snapshots.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row["dormant_30d"] = int(row["dormant_30d"])
        if row["prediction_date"] not in {d.isoformat() for d in PREDICTION_DATES}:
            raise ValueError("snapshot outside frozen schedule")
    validate_rows(rows)
    split_seed = plan["input_parameters"]["split_seed"]
    partitions = (
        temporal_split(rows, split_seed)
        if regime == "temporal"
        else random_reference(rows, split_seed)
    )
    name = "temporal_membership.csv" if regime == "temporal" else "random_reference_membership.csv"
    with (input_dir / name).open(newline="") as stream:
        actual = list(csv.DictReader(stream))
    if actual != membership_rows(partitions):
        raise ValueError("reconstructed membership differs from frozen membership")
    for values in partitions.values():
        if {r["dormant_30d"] for r in values} != {0, 1}:
            raise ValueError("final evaluation requires both labels in each complete partition")
    return partitions, split_audit(partitions)
