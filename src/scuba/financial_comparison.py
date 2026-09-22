"""Frozen local comparisons and TabPFN payload planning for Financial Stress."""

import argparse
import hashlib
import importlib.metadata
import json
import time
import warnings
from dataclasses import asdict
from pathlib import Path

from catboost import CatBoostClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits
from xgboost import XGBClassifier

from scuba.evaluation import point_metrics
from scuba.financial_stress import (
    SEED,
    TARGET,
    digest,
    load_validation_rows,
    make_pipeline,
    new_output,
    runtime,
    write_json,
)
from scuba.integrations.tabpfn_plan import TabPFNConfig, plan_digest

COMPARISON_VERSION = "financial-stress-comparison/v1"
TREE_SETTINGS = {
    "xgboost": dict(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=1.0,
        objective="binary:logistic",
        tree_method="hist",
        device="cpu",
        n_jobs=1,
        random_state=SEED,
        eval_metric="logloss",
    ),
    "catboost": dict(
        iterations=300,
        depth=4,
        learning_rate=0.05,
        loss_function="Logloss",
        task_type="CPU",
        thread_count=1,
        random_seed=SEED,
        allow_writing_files=False,
        verbose=False,
    ),
}


def provenance():
    return {
        **runtime(),
        "comparison_source_sha256": digest(__file__),
        "dependency_lock_sha256": digest(Path(__file__).resolve().parents[2] / "uv.lock"),
        "tree_packages": {name: importlib.metadata.version(name) for name in TREE_SETTINGS},
        "integration_source_sha256": {
            path.name: digest(path)
            for path in sorted(Path(__file__).with_name("integrations").glob("*.py"))
        },
    }


def cat_frame(frame, features, categories):
    result = frame[features].copy()
    for name in categories:
        result[name] = result[name].fillna("__SCUBA_MISSING__").astype(str)
    return result


def compare(prepared, output, *, exclude_features=()):
    manifest, train, validation = load_validation_rows(prepared)
    return compare_rows(
        manifest,
        train,
        validation,
        output,
        digest(Path(prepared) / "manifest.json"),
        exclude_features=exclude_features,
    )


def compare_rows(
    manifest,
    train,
    validation,
    output,
    prepared_hash,
    *,
    exclude_features=(),
    partition="validation",
):
    """Shared fixed recipes; callers verify and freeze the selected evaluation rows."""
    if partition not in ("validation", "final"):
        raise ValueError("unsupported evaluation partition")
    if set(exclude_features) - set(manifest["features"]):
        raise ValueError("unknown excluded feature")
    features = [f for f in manifest["features"] if f not in exclude_features]
    if not features:
        raise ValueError("at least one predictor is required")
    cats = [f for f in manifest["categorical"] if f in features]
    numeric = [f for f in manifest["numeric"] if f in features]
    logistic = make_pipeline(numeric, cats)
    xgboost = make_pipeline(numeric, cats)
    xgboost.set_params(
        model=XGBClassifier(**TREE_SETTINGS["xgboost"]),
        preprocess__numeric__scale="passthrough",
    )
    catboost = CatBoostClassifier(**TREE_SETTINGS["catboost"], cat_features=cats)
    models = {"logistic_regression": logistic, "xgboost": xgboost, "catboost": catboost}
    predictions = validation[["ID", TARGET]].copy()
    predictions["constant_prior"] = float(train[TARGET].mean())
    timing = {}
    with new_output(output) as out:
        for name, model in models.items():
            fitting, scoring = train[features], validation[features]
            if name == "catboost":
                fitting = cat_frame(train, features, cats)
                scoring = cat_frame(validation, features, cats)
            with threadpool_limits(limits=1), warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                start = time.perf_counter()
                model.fit(fitting, train[TARGET])
                fit_seconds = time.perf_counter() - start
                if list(model.classes_) != [0, 1]:
                    raise ValueError("unexpected model class order")
                start = time.perf_counter()
                predictions[name] = model.predict_proba(scoring)[:, 1]
                timing[name] = {
                    "fit_seconds": fit_seconds,
                    "predict_seconds": time.perf_counter() - start,
                }
        metrics = {}
        for name in ["constant_prior", *models]:
            p = predictions[name].to_numpy()
            metrics[name] = point_metrics(validation[TARGET], p, validation.ID.tolist())
            metrics[name]["roc_auc"] = float(roc_auc_score(validation[TARGET], p))
        prediction_file = out / f"{partition}_predictions.csv"
        predictions.to_csv(prediction_file, index=False)
        report = {
            "version": COMPARISON_VERSION,
            "evaluation_partition": partition,
            "final_evaluated": partition == "final",
            "hosted_calls": 0,
            "prepared_manifest_sha256": prepared_hash,
            "feature_columns": features,
            "cohorts": {name: manifest["partitions"][name] for name in ("train", partition)},
            "input_sha256": {
                name: manifest["files"][name + ".csv"] for name in ("train", partition)
            },
            "training_subset": None,
            "excluded_features": sorted(set(exclude_features)),
            "settings": {
                "constant_prior": "training prevalence",
                "logistic_regression": {
                    "C": 1.0,
                    "solver": "lbfgs",
                    "max_iter": 2000,
                    "class_weight": None,
                    "random_state": SEED,
                },
                **TREE_SETTINGS,
                "catboost_categories": cats,
                "preprocessing": "train-only; logistic scaled/one-hot; XGBoost imputed/one-hot; CatBoost native",
            },
            "runtime": provenance(),
            "timing": timing,
            "metrics": metrics,
            "predictions_sha256": digest(prediction_file),
        }
        write_json(out / "metrics.json", report)
    return report


def hosted_plan(prepared):
    manifest, train, validation = load_validation_rows(prepared)
    config = TabPFNConfig(variant="plus", n_estimators=8, seed=SEED)
    frames = {
        "train": train[manifest["features"]],
        "validation": validation[manifest["features"]],
        "labels": train[[TARGET]],
    }
    payloads = {
        name: frame.to_csv(index=False, lineterminator="\n", na_rep="").encode()
        for name, frame in frames.items()
    }
    plan = {
        "schema": "scuba.financial-stress-tabpfn-plan/v1",
        "classification": "external_challenge_data_origin_unverified",
        "upload_description": "SCUBA Financial Stress challenge snapshots; real/synthetic origin unverified.",
        "phase": "validation_only",
        "prediction_partition": "validation",
        "prepared_manifest_sha256": digest(Path(prepared) / "manifest.json"),
        "input_files": {name: manifest["files"][name + ".csv"] for name in ("train", "validation")},
        "configuration": asdict(config),
        "fit_parameters": config.fit_parameters(),
        "feature_columns": manifest["features"],
        "class_order": [0, 1],
        "cohorts": {
            name: {
                "rows": len(frame),
                "positives": int(frame[TARGET].sum()),
                "key_sha256": plan_digest(frame.ID.tolist()),
            }
            for name, frame in (("train", train), ("validation", validation))
        },
        "payloads": {
            name: {
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
                "memory_bytes": int(frames[name].memory_usage(deep=True).sum()),
                "rows": len(frames[name]),
                "columns": list(frames[name].columns),
            }
            for name, data in payloads.items()
        },
        "estimate_requests": [
            {
                "train_rows": len(train),
                "test_rows": len(validation),
                "raw_columns": len(manifest["features"]),
                "model_version": config.version,
                "n_estimators": config.n_estimators,
                "operation": "predict",
            }
        ],
        "test_cohort_included": False,
        "validation_labels_uploaded": False,
        "identifiers_uploaded": False,
        "training_subset": None,
    }
    return plan, payloads


def preflight(prepared, output, *, online=False, client_factory=None, token_loader=None):
    # Imports and credential access are isolated from the offline path.
    from scuba.integrations.secrets import tabpfn_token
    from scuba.integrations.tabpfn_rest import TabPFNRest
    from scuba.integrations.tabpfn_runner import safe_failure

    with new_output(output) as out:
        plan, _ = hosted_plan(prepared)
        write_json(out / "plan.json", {"plan": plan, "sha256": plan_digest(plan)})
        report = {
            "plan_sha256": plan_digest(plan),
            "rows_uploaded": 0,
            "status": "awaiting_metadata_preflight",
            "runtime": provenance(),
        }
        if online:
            client = None
            try:
                client = (client_factory or TabPFNRest)((token_loader or tabpfn_token)())
                report["preflight"] = client.preflight(plan)
                if client_factory is not None:
                    report["preflight"]["evidence"] = "offline_mock"
                report["status"] = "awaiting_upload_and_budget_approval"
            except Exception as exc:
                report["status"] = "failed"
                report["failure"] = safe_failure(exc, client)
            finally:
                if client:
                    report["stages"] = client.stages
                    client.close()
        write_json(out / "preflight.json", report)
    return report


def run_hosted(
    prepared,
    approved_plan_path,
    output,
    *,
    allow_upload=False,
    max_tokens=None,
    client_factory=None,
    token_loader=None,
):
    """One explicitly approved attempt; keep failures and diagnostics without retries."""
    from scuba.integrations.secrets import tabpfn_token
    from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest
    from scuba.integrations.tabpfn_runner import safe_failure

    if not allow_upload or type(max_tokens) is not int or max_tokens <= 0:
        raise IntegrationError("upload_and_positive_budget_approval_required")
    plan, payloads = hosted_plan(prepared)
    approved = json.loads(Path(approved_plan_path).read_text())
    if approved != {"plan": plan, "sha256": plan_digest(plan)}:
        raise IntegrationError("approved_plan_changed")
    _, _, validation = load_validation_rows(prepared)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "version": COMPARISON_VERSION,
        "status": "running",
        "classification": plan["classification"],
        "model": "TabPFN-3.5-Plus",
        "plan_sha256": plan_digest(plan),
        "prepared_manifest_sha256": plan["prepared_manifest_sha256"],
        "evaluation_partition": "validation",
        "final_evaluated": False,
        "approved_estimated_tokens": max_tokens,
        "runtime": provenance(),
        "evidence": "live_attempt" if client_factory is None else "offline_mock",
    }
    write_json(output / "manifest.json", report)
    client = None
    start = time.perf_counter()
    try:
        client = (client_factory or TabPFNRest)((token_loader or tabpfn_token)())

        def save_response(evidence):
            write_json(output / "response_evidence.json", evidence)
            report["response_sha256"] = digest(output / "response_evidence.json")
            write_json(output / "manifest.json", report)

        probability, evidence = client.execute(
            plan, payloads, allow_upload=True, max_tokens=max_tokens, response_sink=save_response
        )
        metrics = point_metrics(validation[TARGET], probability, validation.ID.tolist())
        metrics["roc_auc"] = float(roc_auc_score(validation[TARGET], probability))
        predictions = validation[["ID", TARGET]].copy()
        predictions["tabpfn_3_5_plus"] = probability
        predictions.to_csv(output / "validation_predictions.csv", index=False)
        report.update(
            status="complete",
            metrics=metrics,
            integration=evidence,
            predictions_sha256=digest(output / "validation_predictions.csv"),
            evidence="live_verified" if client_factory is None else "offline_mock",
        )
    except Exception as exc:
        report.update(status="failed", failure=safe_failure(exc, client))
        if client:
            report["stages"] = client.stages
            report["integration_attempt"] = client.execution_evidence
    finally:
        if client:
            client.close()
        report["end_to_end_seconds"] = time.perf_counter() - start
        write_json(output / "manifest.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("compare", "preflight", "run-hosted"))
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--exclude-age-gender", action="store_true")
    parser.add_argument("--approved-plan", type=Path)
    parser.add_argument("--allow-upload", action="store_true")
    parser.add_argument("--max-estimated-tokens", type=int)
    args = parser.parse_args()
    if args.exclude_age_gender and args.command != "compare":
        parser.error("feature exclusion is local comparison only")
    if args.command != "run-hosted" and (
        args.allow_upload or args.approved_plan or args.max_estimated_tokens
    ):
        parser.error("upload approval arguments are only valid for run-hosted")
    if args.command == "run-hosted":
        if not args.approved_plan or not args.allow_upload or not args.max_estimated_tokens:
            parser.error("run-hosted requires an approved plan, upload flag and token ceiling")
        result = run_hosted(
            args.prepared,
            args.approved_plan,
            args.output,
            allow_upload=args.allow_upload,
            max_tokens=args.max_estimated_tokens,
        )
        print(json.dumps({"status": result["status"]}))
        if result["status"] != "complete":
            raise SystemExit(1)
        return
    if args.command == "compare":
        if args.online:
            parser.error("compare is offline")
        result = compare(
            args.prepared,
            args.output,
            exclude_features=("age", "gender") if args.exclude_age_gender else (),
        )
        print(json.dumps({name: m["log_loss"] for name, m in result["metrics"].items()}))
    else:
        result = preflight(args.prepared, args.output, online=args.online)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "estimated_tokens": result.get("preflight", {}).get("estimated_total_tokens"),
                }
            )
        )
        if result["status"] == "failed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
