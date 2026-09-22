"""Validation-only local runs with frozen inputs and auditable artifacts."""

import hashlib
import json
import os
import platform
import warnings
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss

from scuba.artifacts import file_hash, write_json, write_table
from scuba.features import FEATURE_COLUMNS
from scuba.models.baselines import logistic_model, prior_model
from scuba.models.catboost import catboost_model
from scuba.models.common import MODEL_SEED, feature_frame
from scuba.models.data import load_development_bundle
from scuba.models.xgboost import xgboost_model
from scuba.splits import snapshot_key

FACTORIES = (prior_model, logistic_model, xgboost_model, catboost_model)
PREDICTION_SCHEMA = {
    "customer_id": "string",
    "prediction_date": "date:YYYY-MM-DD",
    "dormant_30d": "integer:0|1",
    "probability_dormant": "float:probability",
    "is_synthetic": "boolean",
}


def json_settings(value):
    """Estimator defaults can include NaN; preserve it explicitly in valid JSON."""
    if isinstance(value, dict):
        return {str(key): json_settings(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_settings(item) for item in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def validation_metrics(labels, probabilities):
    labels, probabilities = np.asarray(labels), np.asarray(probabilities, dtype=float)
    if (
        labels.ndim != 1
        or set(labels.tolist()) != {0, 1}
        or labels.shape != probabilities.shape
        or not np.isfinite(probabilities).all()
        or (probabilities < 0).any()
        or (probabilities > 1).any()
    ):
        raise ValueError(
            "validation metrics require aligned binary labels and finite probabilities"
        )
    return {
        "average_precision": float(average_precision_score(labels, probabilities)),
        "log_loss": float(log_loss(labels, probabilities, labels=[0, 1])),
        "brier_score": float(brier_score_loss(labels, probabilities)),
    }


def run_comparators(input_dir: Path, output: Path, expected_manifest_hash: str | None = None):
    """Run fixed candidates once. Existing outputs are never overwritten."""
    start = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "classification": "synthetic",
        "phase": "M2_validation_only",
        "status": "running",
        "models": {},
        "test_scored": False,
        "random_reference_run": False,
    }
    write_json(output / "manifest.json", manifest)
    try:
        root = Path(__file__).resolve().parents[3]
        partitions, source, consumed = load_development_bundle(input_dir, expected_manifest_hash)
        data_seconds = perf_counter() - start
        table_start = perf_counter()
        train = feature_frame(partitions["train"])
        validation = feature_frame(partitions["validation"])
        labels = {
            name: np.array([row["dormant_30d"] for row in rows])
            for name, rows in partitions.items()
        }
        table_seconds = perf_counter() - table_start
        manifest.update(
            {
                "schema": "scuba.local-model-run/v1",
                "input_files": consumed,
                "input_parameters": source["parameters"],
                "feature_columns": list(FEATURE_COLUMNS),
                "feature_version": source["feature_version"],
                "split_version": source["split_version"],
                "model_seed": MODEL_SEED,
                "candidates_per_model": 1,
                "calibration": None,
                "threshold_selection": None,
                "dependency_lock_sha256": file_hash(root / "uv.lock"),
                "source_sha256": {
                    str(path.relative_to(root / "src")): file_hash(path)
                    for path in sorted((root / "src" / "scuba").rglob("*.py"))
                },
                "dependencies": {
                    name: version(name)
                    for name in (
                        "numpy",
                        "pandas",
                        "scipy",
                        "scikit-learn",
                        "xgboost",
                        "catboost",
                        "threadpoolctl",
                    )
                },
                "runtime": {
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "logical_cpus": os.cpu_count(),
                    "model_threads": 1,
                },
                "timing_protocol": {
                    "repetitions": 1,
                    "cache_warmth": "uncontrolled",
                    "clock": "perf_counter",
                    "includes_process_startup_and_imports": False,
                },
                "latency": {
                    "input_load_verify_seconds": data_seconds,
                    "feature_table_seconds": table_seconds,
                },
                "api_usage": {
                    "estimated_tokens": 0,
                    "actual_tokens": 0,
                    "reason": "local models only",
                },
                "cohorts": {
                    name: {
                        "rows": len(rows),
                        "customers": len({r["customer_id"] for r in rows}),
                        "positives": int(labels[name].sum()),
                        "key_sha256": hashlib.sha256(
                            json.dumps(
                                [snapshot_key(r) for r in rows], separators=(",", ":")
                            ).encode()
                        ).hexdigest(),
                    }
                    for name, rows in partitions.items()
                },
            }
        )
        for factory in FACTORIES:
            model_start = perf_counter()
            model = factory()
            result = {"status": "running", "settings": json_settings(model.settings())}
            manifest["models"][model.name] = result
            write_json(output / "manifest.json", manifest)
            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                model.fit(train, labels["train"])
            probabilities, predict_times = model.predict(validation)
            metrics = validation_metrics(labels["validation"], probabilities)
            folder = output / model.name
            folder.mkdir()
            prediction_info = write_table(
                folder / "validation_predictions.csv",
                [
                    {
                        "customer_id": row["customer_id"],
                        "prediction_date": row["prediction_date"],
                        "dormant_30d": row["dormant_30d"],
                        "probability_dormant": format(float(probability), ".17g"),
                        "is_synthetic": "true",
                    }
                    for row, probability in zip(
                        partitions["validation"], probabilities, strict=True
                    )
                ],
                PREDICTION_SCHEMA,
            )
            write_json(
                folder / "validation_metrics.json",
                {"classification": "synthetic", "partition": "validation", "metrics": metrics},
            )
            if model.name == "catboost":
                result["resolved_parameters"] = json_settings(model.estimator.get_all_params())
            elif model.name == "xgboost":
                result["resolved_parameters"] = json.loads(
                    model.estimator.get_booster().save_config()
                )
            result.update(
                {
                    "status": "complete",
                    "classes": [int(c) for c in model.estimator.classes_],
                    "positive_class": 1,
                    "metrics": metrics,
                    "predictions": prediction_info,
                    "metrics_sha256": file_hash(folder / "validation_metrics.json"),
                    "latency": {
                        **model.fit_times,
                        **predict_times,
                        "model_end_to_end_seconds": perf_counter() - model_start,
                    },
                }
            )
            write_json(output / "manifest.json", manifest)
        manifest["latency"]["run_end_to_end_seconds"] = perf_counter() - start
        manifest["status"] = "complete"
        write_json(output / "manifest.json", manifest)
        return manifest
    except Exception as exc:
        manifest.update(status="failed", failure_type=type(exc).__name__, failure=str(exc))
        for result in manifest["models"].values():
            if result["status"] == "running":
                result["status"] = "failed"
        write_json(output / "manifest.json", manifest)
        raise
