"""Deterministic local payload planning and hosted limit/cost validation."""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from scuba.features import FEATURE_COLUMNS
from scuba.models.common import MODEL_SEED, feature_frame
from scuba.models.data import load_development_bundle


@dataclass(frozen=True)
class TabPFNConfig:
    variant: str = "plus"
    n_estimators: int = 8
    seed: int = MODEL_SEED

    def __post_init__(self):
        if self.variant not in ("plus", "fast", "thinking"):
            raise ValueError("Supported routes: plus, fast, thinking; base identity is unresolved.")
        if type(self.n_estimators) is not int or not 1 <= self.n_estimators <= 8:
            raise ValueError("n_estimators must be an integer from 1 to 8")
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer")

    @property
    def version(self):
        return "v3.5-fast" if self.variant == "fast" else "v3.5"

    @property
    def model_path(self):
        return f"{self.version}_default"

    def model_parameters(self):
        return {
            "model_path": self.model_path,
            "n_estimators": self.n_estimators,
            "random_state": self.seed,
            "fit_mode": "fit_preprocessors",
        }

    def fit_parameters(self):
        result = {
            "task": "classification",
            "tabpfn_config": self.model_parameters(),
            "tabpfn_systems": ["preprocessing", "text"],
        }
        if self.variant == "thinking":
            result.update(
                tabpfn_systems=["preprocessing", "text", "thinking"],
                thinking_effort="medium",
                thinking_timeout_s=300,
                thinking_effort_metric="log_loss",
            )
        return result


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def plan_digest(plan: dict) -> str:
    return digest(json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def prepare_plan(input_dir: Path, config: TabPFNConfig, expected_manifest_hash=None):
    rows, source, consumed = load_development_bundle(input_dir, expected_manifest_hash)
    frames = {name: feature_frame(values) for name, values in rows.items()}
    frames["labels"] = pd.DataFrame({"dormant_30d": [r["dormant_30d"] for r in rows["train"]]})
    payloads = {
        name: frame.to_csv(index=False, lineterminator="\n", na_rep="").encode("utf-8")
        for name, frame in frames.items()
    }
    n_train, n_valid = len(rows["train"]), len(rows["validation"])
    dimensions = {
        "train_rows": n_train,
        "test_rows": n_valid,
        "raw_columns": len(FEATURE_COLUMNS),
        "model_version": config.version,
        "n_estimators": config.n_estimators,
    }
    estimates = [
        {
            **dimensions,
            "operation": "thinking_predict" if config.variant == "thinking" else "predict",
        }
    ]
    if config.variant == "thinking":
        estimates.insert(
            0,
            {
                **dimensions,
                "test_rows": 0,
                "operation": "thinking_fit",
                "thinking_effort": "medium",
            },
        )
    plan = {
        "schema": "scuba.tabpfn-plan/v1",
        "classification": "synthetic",
        "phase": "validation_only",
        "input_files": consumed,
        "input_parameters": source["parameters"],
        "configuration": asdict(config),
        "fit_parameters": config.fit_parameters(),
        "feature_columns": list(FEATURE_COLUMNS),
        "class_order": [0, 1],
        "class_order_basis": "sorted unique training labels, matching tabpfn-client 0.6.0",
        "cohorts": {
            name: {
                "rows": len(values),
                "customers": len({r["customer_id"] for r in values}),
                "positives": sum(r["dormant_30d"] for r in values),
                "key_sha256": plan_digest(
                    [[r["customer_id"], r["prediction_date"]] for r in values]
                ),
            }
            for name, values in rows.items()
        },
        "payloads": {
            name: {
                "sha256": digest(payload),
                "size_bytes": len(payload),
                "memory_bytes": int(frames[name].memory_usage(deep=True).sum()),
                "rows": len(frames[name]),
                "columns": list(frames[name].columns),
                "classification": "synthetic",
            }
            for name, payload in payloads.items()
        },
        "estimate_requests": estimates,
        "test_cohort_included": False,
        "validation_labels_uploaded": False,
    }
    return plan, payloads, rows


def prediction_rows(plan):
    partition = plan.get("prediction_partition", "validation")
    if partition not in ("validation", "test"):
        raise ValueError("unsupported prediction partition")
    return plan["cohorts"][partition]["rows"]


def check_limits(plan: dict, response: dict):
    version = TabPFNConfig(**plan["configuration"]).version
    try:
        limits = response["model_limits"][version]
        train, valid = plan["cohorts"]["train"]["rows"], prediction_rows(plan)
        columns = len(plan["feature_columns"])
        requirements = {
            "train_set_max_rows": train,
            "test_set_max_rows": valid,
            "train_set_max_cells": train * columns,
            "test_set_max_cells": valid * columns,
            "max_cols": columns,
            "max_classes": 2,
            "predict_row_pairs_budget": train * valid,
        }
        for name, value in requirements.items():
            if type(limits[name]) is not int or limits[name] < value:
                raise ValueError(f"Selected model limit does not fit the complete cohort: {name}")
        size_limit = response["dataset_max_size_bytes"]
        if type(size_limit) is not int or size_limit <= 0:
            raise ValueError("Invalid dataset size limit")
        for payload in plan["payloads"].values():
            if max(payload["size_bytes"], payload["memory_bytes"]) > size_limit:
                raise ValueError("Dataset exceeds the server byte-size limit")
        return {
            "model_version": version,
            "limits": {k: limits[k] for k in requirements},
            "dataset_max_size_bytes": size_limit,
        }
    except (KeyError, TypeError) as exc:
        raise ValueError("Missing or incompatible model-limit response") from exc


def checked_estimate(request: dict, response: dict):
    try:
        inputs = response["inputs"]
        if not isinstance(inputs, dict):
            raise ValueError("Invalid estimate inputs")
        if any(inputs.get(key) != value for key, value in request.items()):
            raise ValueError("Estimate settings differ from the planned request")
        cost, pricing = response["estimated_cost"], response["pricing_version"]
        if (
            type(cost) is not int
            or cost <= 0
            or not isinstance(pricing, str)
            or not pricing
            or len(pricing) > 128
        ):
            raise ValueError("Invalid token estimate")
        return {"request": request, "estimated_tokens": cost, "pricing_version": pricing}
    except (KeyError, TypeError) as exc:
        raise ValueError("Missing or incompatible token-estimate response") from exc
