"""Offline Financial Stress preparation and validation baselines; no hosted calls."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import tempfile
import time
import warnings
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from scuba.evaluation import point_metrics
from scuba.source_bundle import verify_bundle

TARGET = "liquidity_stress_next_30d"
VERSION = "financial-stress/v1"
SEED = 3501


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


@contextmanager
def new_output(output):
    output = Path(output)
    if output.exists():
        raise ValueError("output must be new")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stress-", dir=output.parent) as tmp:
        staging = Path(tmp) / "result"
        staging.mkdir()
        yield staging
        staging.rename(output)


def runtime():
    return {
        "python": platform.python_version(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "scikit-learn", "threadpoolctl")
        },
        "module_sha256": digest(__file__),
        "evaluation_sha256": digest(Path(__file__).with_name("evaluation.py")),
    }


def validate_tables(train, test, dictionary, submission):
    """Reject schema/identity errors before any partition or fit is written."""
    if dictionary.column_name.duplicated().any():
        raise ValueError("duplicate dictionary columns")
    if set(dictionary.column_name) != set(train.columns):
        raise ValueError("training schema differs from dictionary")
    if set(test.columns) != set(train.columns) - {TARGET}:
        raise ValueError("inference schema differs from training predictors")
    if set(submission.columns) != {"ID", "Target"}:
        raise ValueError("unexpected submission schema")
    for frame in (train, test, submission):
        if frame.empty or frame.ID.isna().any() or frame.ID.duplicated().any():
            raise ValueError("nonempty tables require unique, non-null snapshot IDs")
    if set(train.ID) & set(test.ID):
        raise ValueError("training/inference snapshot IDs overlap")
    if set(submission.ID) != set(test.ID):
        raise ValueError("submission IDs differ from inference IDs")
    if train[TARGET].isna().any() or set(train[TARGET].unique()) != {0, 1}:
        raise ValueError("target must contain both binary labels without missing values")
    features = [name for name in train.columns if name not in ("ID", TARGET)]
    types = dictionary.set_index("column_name").data_type
    categorical = [name for name in features if types[name] in ("object", "string")]
    numeric = [name for name in features if name not in categorical]
    for frame in (train, test):
        values = frame[numeric].to_numpy(dtype=float)
        if np.isinf(values).any():
            raise ValueError("infinite numeric predictors")
        if frame[features].isna().all().any():
            raise ValueError("entirely missing predictor")
        if frame[features].duplicated().any():
            raise ValueError("duplicate predictor rows require an explicit split policy")
    left = pd.util.hash_pandas_object(train[features], index=False)
    right = pd.util.hash_pandas_object(test[features], index=False)
    if set(left) & set(right):
        raise ValueError("matching training/inference predictor rows require review")
    return features, numeric, categorical


def split_rows(train):
    ordered = train.sort_values("ID").reset_index(drop=True)
    fitting, held = train_test_split(
        ordered, test_size=0.4, random_state=SEED, stratify=ordered[TARGET]
    )
    validation, final = train_test_split(
        held, test_size=0.5, random_state=SEED, stratify=held[TARGET]
    )
    return {
        name: frame.sort_values("ID").reset_index(drop=True)
        for name, frame in (("train", fitting), ("validation", validation), ("final", final))
    }


def prepare(bundle, output):
    bundle = Path(bundle)
    verify_bundle(bundle)
    # This source package stores originals directly. Check these consumed bytes too,
    # so a changed manifest part path cannot silently select a different source file.
    source = json.loads((bundle / "manifest.json").read_text())
    for record in source["files"]:
        path = bundle / "files" / record["name"]
        if path.stat().st_size != record["bytes"] or digest(path) != record["sha256"]:
            raise ValueError("consumed source differs from pinned original")
    files = bundle / "files"
    train = pd.read_csv(files / "Train.csv", dtype={"ID": str})
    test = pd.read_csv(files / "Test.csv", dtype={"ID": str})
    dictionary = pd.read_csv(files / "data_dictionary.csv")
    submission = pd.read_csv(files / "SampleSubmission.csv", dtype={"ID": str})
    features, numeric, categorical = validate_tables(train, test, dictionary, submission)
    partitions = split_rows(train)
    with new_output(output) as out:
        members = []
        for name, frame in partitions.items():
            frame.to_csv(out / f"{name}.csv", index=False)
            members.extend({"ID": key, "partition": name} for key in frame.ID)
        pd.DataFrame(members).sort_values("ID").to_csv(out / "membership.csv", index=False)
        manifest = {
            "version": VERSION,
            "target": TARGET,
            "seed": SEED,
            "split": "stratified rows 60/20/20; dates and persistent customers unavailable",
            "source_manifest_sha256": digest(bundle / "manifest.json"),
            "source_files": {r["name"]: r["sha256"] for r in source["files"]},
            "features": features,
            "numeric": numeric,
            "categorical": categorical,
            "partitions": {
                name: {"rows": len(frame), "positives": int(frame[TARGET].sum())}
                for name, frame in partitions.items()
            },
            "files": {p.name: digest(p) for p in sorted(out.glob("*.csv"))},
            "runtime": runtime(),
            "origin": "external challenge data; real/synthetic status unverified",
            "source_train_missing_cells": int(train.isna().sum().sum()),
            "inference_rows": len(test),
        }
        write_json(out / "manifest.json", manifest)
    return manifest


def make_pipeline(numeric, categorical):
    numeric_steps = Pipeline(
        [("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
    )
    categorical_steps = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return Pipeline(
        [
            (
                "preprocess",
                ColumnTransformer(
                    [
                        ("numeric", numeric_steps, numeric),
                        ("category", categorical_steps, categorical),
                    ]
                ),
            ),
            ("model", LogisticRegression(C=1.0, max_iter=2000, solver="lbfgs", random_state=SEED)),
        ]
    )


def load_validation_rows(prepared):
    """Verify development partitions without reading reserved evaluation rows."""
    prepared = Path(prepared)
    manifest = json.loads((prepared / "manifest.json").read_text())
    if manifest["version"] != VERSION or manifest["target"] != TARGET:
        raise ValueError("unsupported prepared contract")
    features = manifest["features"]
    if set(features) & {"ID", TARGET} or len(set(features)) != len(features):
        raise ValueError("forbidden or duplicate predictor")
    if set(manifest["numeric"]) & set(manifest["categorical"]) or set(features) != set(
        manifest["numeric"] + manifest["categorical"]
    ):
        raise ValueError("invalid predictor type assignment")
    frames = {}
    # Deliberately never open final.csv or the unlabelled challenge Test.csv here.
    for name in ("train", "validation"):
        path = prepared / f"{name}.csv"
        if digest(path) != manifest["files"][path.name]:
            raise ValueError("prepared partition checksum mismatch")
        frame = pd.read_csv(path, dtype={"ID": str})
        if set(frame.columns) != {"ID", TARGET, *features}:
            raise ValueError("prepared partition schema mismatch")
        if frame.ID.isna().any() or frame.ID.duplicated().any():
            raise ValueError("invalid prepared snapshot IDs")
        if frame[TARGET].isna().any() or set(frame[TARGET].unique()) != {0, 1}:
            raise ValueError("invalid prepared target")
        frames[name] = frame
    train, validation = frames["train"], frames["validation"]
    if set(train.ID) & set(validation.ID):
        raise ValueError("prepared training/validation IDs overlap")
    return manifest, train, validation


def baseline(prepared, output):
    prepared = Path(prepared)
    manifest, train, validation = load_validation_rows(prepared)
    features = manifest["features"]
    pipeline = make_pipeline(manifest["numeric"], manifest["categorical"])
    start = time.perf_counter()
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        pipeline.fit(train[features], train[TARGET])
        fit_seconds = time.perf_counter() - start
        predict_start = time.perf_counter()
        probability = pipeline.predict_proba(validation[features])[:, 1]
        predict_seconds = time.perf_counter() - predict_start
    scores = {
        "constant_prior": np.full(len(validation), float(train[TARGET].mean())),
        "logistic_regression": probability,
    }
    results = {}
    with new_output(output) as out:
        predictions = validation[["ID", TARGET]].copy()
        for name, p in scores.items():
            predictions[name] = p
            results[name] = point_metrics(validation[TARGET], p, validation.ID.tolist())
            results[name]["roc_auc"] = float(roc_auc_score(validation[TARGET], p))
        predictions.to_csv(out / "validation_predictions.csv", index=False)
        report = {
            "version": VERSION,
            "evaluation_partition": "validation",
            "final_evaluated": False,
            "hosted_calls": 0,
            "prepared_manifest_sha256": digest(prepared / "manifest.json"),
            "runtime": runtime(),
            "settings": {
                "solver": "lbfgs",
                "C": 1.0,
                "max_iter": 2000,
                "class_weight": None,
                "threads": 1,
                "seed": SEED,
                "preprocessing": "training-only median/scale and most-frequent/one-hot",
            },
            "fit_seconds": fit_seconds,
            "predict_seconds": predict_seconds,
            "metrics": results,
            "predictions_sha256": digest(out / "validation_predictions.csv"),
        }
        write_json(out / "metrics.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--bundle", type=Path, default=Path("datasets/financial-stress"))
    prep.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("baseline")
    run.add_argument("--prepared", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.bundle, args.output)
        print(json.dumps({"partitions": result["partitions"], "features": len(result["features"])}))
    else:
        result = baseline(args.prepared, args.output)
        print(json.dumps({name: m["log_loss"] for name, m in result["metrics"].items()}))


if __name__ == "__main__":
    main()
