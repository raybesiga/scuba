"""Evaluate hash-pinned saved validation runs without training or remote calls."""

import csv
import json
import platform
from importlib.metadata import version
from pathlib import Path

import numpy as np

from scuba.artifacts import file_hash, write_json
from scuba.contract import ARCHETYPES
from scuba.evaluation import (
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    EVALUATION_VERSION,
    evaluate_cohort,
)
from scuba.features import FEATURE_COLUMNS
from scuba.models.data import load_development_bundle
from scuba.models.runner import PREDICTION_SCHEMA, validation_metrics
from scuba.splits import snapshot_key

LOCAL_MODELS = ("constant_prior", "logistic_regression", "xgboost", "catboost")


def pinned_manifest(folder, expected):
    path = folder / "manifest.json"
    if not expected or file_hash(path) != expected:
        raise ValueError("prediction-run manifest hash mismatch")
    manifest = json.loads(path.read_text())
    if (
        manifest.get("status") != "complete"
        or manifest.get("classification") != "synthetic"
        or manifest.get("test_scored") is not False
    ):
        raise ValueError("only complete synthetic validation runs are accepted")
    return manifest


def read_predictions(path, reference, rows, original_metrics):
    if file_hash(path) != reference["sha256"]:
        raise ValueError("saved prediction hash mismatch")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(PREDICTION_SCHEMA):
            raise ValueError("prediction schema mismatch")
        saved = list(reader)
    if len(saved) != len(rows) or reference["rows"] != len(rows):
        raise ValueError("prediction row count mismatch")
    by_key = {}
    for row in saved:
        key = snapshot_key(row)
        if key in by_key or row["is_synthetic"] != "true" or row["dormant_30d"] not in ("0", "1"):
            raise ValueError("invalid synthetic prediction row")
        by_key[key] = row
    if set(by_key) != {snapshot_key(row) for row in rows}:
        raise ValueError("prediction keys differ from frozen validation")
    probability = []
    for row in rows:
        saved_row = by_key[snapshot_key(row)]
        if int(saved_row["dormant_30d"]) != row["dormant_30d"]:
            raise ValueError("prediction labels differ from frozen validation")
        probability.append(float(saved_row["probability_dormant"]))
    recomputed = validation_metrics([r["dormant_30d"] for r in rows], probability)
    if set(original_metrics) != set(recomputed) or any(
        not np.isclose(value, original_metrics[key], rtol=0, atol=1e-12)
        for key, value in recomputed.items()
    ):
        raise ValueError("saved metrics do not reconcile")
    return np.asarray(probability)


def evaluate_saved(
    input_dir,
    local_run,
    local_hash,
    output,
    *,
    hosted_run=None,
    hosted_hash=None,
    expected_manifest_hash=None,
    replicates=BOOTSTRAP_REPLICATES,
):
    if (hosted_run is None) != (hosted_hash is None):
        raise ValueError("hosted run and its pinned manifest hash must be supplied together")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "status": "running",
        "classification": "synthetic",
        "phase": "M4_validation_only",
        "test_scored": False,
        "random_reference_run": False,
        "api_requests": 0,
        "models_fitted": 0,
    }
    try:
        partitions, source, consumed = load_development_bundle(input_dir, expected_manifest_hash)
        rows = partitions["validation"]
        local = pinned_manifest(local_run, local_hash)
        if (
            local.get("phase") != "M2_validation_only"
            or local.get("input_files") != consumed
            or local.get("feature_columns") != list(FEATURE_COLUMNS)
            or local.get("random_reference_run") is not False
            or set(local.get("models", {})) != set(LOCAL_MODELS)
        ):
            raise ValueError("incompatible local model run")
        probabilities, references = {}, {}
        for name in LOCAL_MODELS:
            model = local["models"][name]
            if (
                model.get("status") != "complete"
                or model.get("classes") != [0, 1]
                or model.get("positive_class") != 1
            ):
                raise ValueError("incomplete or incompatible local model")
            path = local_run / name / "validation_predictions.csv"
            probabilities[name] = read_predictions(
                path, model["predictions"], rows, model["metrics"]
            )
            references[name] = {
                "run_manifest_sha256": local_hash,
                "predictions_sha256": file_hash(path),
                "source_metrics": model["metrics"],
                "evidence": "local_model_run",
                "settings": model["settings"],
            }
        if hosted_run is not None:
            hosted = pinned_manifest(hosted_run, hosted_hash)
            envelope = json.loads((hosted_run / "plan.json").read_text())
            # Importing the plan helper is credential-free; no REST client is used.
            from scuba.integrations.tabpfn_plan import plan_digest

            plan = envelope["plan"]
            if (
                hosted.get("evidence") != "offline_revalidated_live_response"
                or hosted.get("phase") != "validation_only"
                or hosted.get("requested_variant") != "plus"
                or envelope["sha256"] != plan_digest(plan)
                or hosted["plan_sha256"] != envelope["sha256"]
                or plan["input_files"] != consumed
                or plan["feature_columns"] != list(FEATURE_COLUMNS)
                or plan["test_cohort_included"] is not False
                or plan["validation_labels_uploaded"] is not False
            ):
                raise ValueError("hosted response is unaccepted or uses different inputs")
            path = hosted_run / "validation_predictions.csv"
            probabilities["hosted_plus"] = read_predictions(
                path, hosted["predictions"], rows, hosted["metrics"]
            )
            references["hosted_plus"] = {
                "run_manifest_sha256": hosted_hash,
                "predictions_sha256": file_hash(path),
                "source_metrics": hosted["metrics"],
                "evidence": hosted["evidence"],
                "identity": hosted["identity_validation"],
                "label": "Hosted Plus requested; server-reported v3.5 checkpoint",
            }
        slices = {}
        for field, categories in (
            ("archetype", ARCHETYPES),
            ("activity_level", ("low", "medium", "high")),
        ):
            if not {row[field] for row in rows} <= set(categories):
                raise ValueError("unexpected evaluation category")
            slices[field] = {}
            for category in categories:
                indices = [i for i, row in enumerate(rows) if row[field] == category]
                slices[field][category] = evaluate_cohort(
                    [rows[i] for i in indices],
                    {k: p[indices] for k, p in probabilities.items()},
                    replicates=replicates,
                )
        result = {
            "schema": EVALUATION_VERSION,
            "classification": "synthetic",
            "partition": "validation",
            "generator_seed": source["parameters"]["generator_seed"],
            "bootstrap": {"replicates": replicates, "seed": BOOTSTRAP_SEED},
            "overall": evaluate_cohort(rows, probabilities, replicates=replicates),
            "slices": slices,
            "sources": references,
            "missing_hosted_evidence": None
            if hosted_run
            else "No accepted hosted prediction supplied for this seed; local models only.",
        }
        write_json(output / "evaluation.json", result)
        root = Path(__file__).resolve().parents[2]
        manifest.update(
            status="complete",
            schema=EVALUATION_VERSION,
            input_files=consumed,
            input_parameters=source["parameters"],
            prediction_sources=references,
            evaluation_sha256=file_hash(output / "evaluation.json"),
            protocol_sha256=file_hash(root / "docs/M4_SPEC.md"),
            source_sha256={
                str(p.relative_to(root)): file_hash(p)
                for p in sorted((root / "src/scuba").rglob("*.py"))
            },
            dependency_lock_sha256=file_hash(root / "uv.lock"),
            dependencies={name: version(name) for name in ("numpy", "scikit-learn")},
            python=platform.python_version(),
            bootstrap=result["bootstrap"],
        )
        write_json(output / "manifest.json", manifest)
        return result
    except Exception as exc:
        manifest.update(status="failed", failure_type=type(exc).__name__)
        write_json(output / "manifest.json", manifest)
        raise
