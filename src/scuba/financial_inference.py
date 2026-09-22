"""Prepare, but never execute, a full-labelled-data Financial Stress inference run."""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from scuba.financial_stress import TARGET, digest, new_output, validate_tables, write_json
from scuba.integrations.tabpfn_plan import TabPFNConfig, plan_digest
from scuba.source_bundle import verify_bundle


def inference_context(bundle, prepared):
    bundle, prepared = Path(bundle), Path(prepared)
    verify_bundle(bundle)
    pm = json.loads((prepared / "manifest.json").read_text())
    if digest(bundle / "manifest.json") != pm["source_manifest_sha256"]:
        raise ValueError("source bundle differs from prepared experiment")
    files = bundle / "files"
    for name, expected in pm["source_files"].items():
        if digest(files / name) != expected:
            raise ValueError("source bytes changed")
    train = (
        pd.read_csv(files / "Train.csv", dtype={"ID": str}).sort_values("ID").reset_index(drop=True)
    )
    inference = pd.read_csv(files / "Test.csv", dtype={"ID": str})
    dictionary = pd.read_csv(files / "data_dictionary.csv")
    sample = pd.read_csv(files / "SampleSubmission.csv", dtype={"ID": str})
    features, _, _ = validate_tables(train, inference, dictionary, sample)
    if (
        features != pm["features"]
        or len(train) != sum(x["rows"] for x in pm["partitions"].values())
        or len(inference) != pm["inference_rows"]
    ):
        raise ValueError("full-data schema or counts changed")
    config = TabPFNConfig(variant="plus", n_estimators=8, seed=3501)
    frames = {"train": train[features], "labels": train[[TARGET]], "test": inference[features]}
    payloads, content = {}, {}
    for name, frame in frames.items():
        data = frame.to_csv(index=False, lineterminator="\n", na_rep="").encode()
        content[name] = data
        payloads[name] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
            "memory_bytes": int(frame.memory_usage(deep=True).sum()),
            "rows": len(frame),
            "columns": list(frame.columns),
        }
    plan = {
        "schema": "scuba.financial-stress-inference-plan/v1",
        "phase": "unlabelled_inference_only",
        "classification": "external_challenge_data_origin_unverified",
        "prediction_partition": "test",
        "source_partition": "challenge_unlabelled_Test.csv",
        "prepared_manifest_sha256": digest(prepared / "manifest.json"),
        "source_files": pm["source_files"],
        "configuration": asdict(config),
        "fit_parameters": config.fit_parameters(),
        "feature_columns": features,
        "class_order": [0, 1],
        "payloads": payloads,
        "cohorts": {
            "train": {"rows": len(train), "key_sha256": plan_digest(train.ID.tolist())},
            "test": {"rows": len(inference), "key_sha256": plan_digest(inference.ID.tolist())},
        },
        "estimate_requests": [
            {
                "train_rows": len(train),
                "test_rows": len(inference),
                "raw_columns": len(features),
                "model_version": config.version,
                "n_estimators": 8,
                "operation": "predict",
            }
        ],
        "training_includes_prior_holdout": True,
        "identifiers_uploaded": False,
        "test_labels_available": False,
        "quality_metrics_available": False,
        "requires_new_fit": True,
        "output_contract": {
            "columns": ["ID", "probability_stress_30d"],
            "rows": len(inference),
            "id_order": "original Test.csv",
            "probability_range": [0, 1],
            "quality_claim": "none; unlabelled inference",
        },
        "execution_status": "not_executed",
        "prerequisites": [
            "record final-holdout comparison",
            "approve separate full-data upload and estimate ceiling",
        ],
    }
    return plan, content, inference


def prepare_inference(bundle, prepared, output):
    plan, _, _ = inference_context(bundle, prepared)
    with new_output(output) as out:
        write_json(out / "plan.json", {"plan": plan, "sha256": plan_digest(plan)})
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("bundle", "prepared", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    plan = prepare_inference(**vars(parser.parse_args()))
    print(
        json.dumps(
            {
                "status": "planned_not_executed",
                "train_rows": plan["cohorts"]["train"]["rows"],
                "inference_rows": plan["cohorts"]["test"]["rows"],
            }
        )
    )
