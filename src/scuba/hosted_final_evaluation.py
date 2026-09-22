"""Offline final-test comparison against a pinned, verified hosted response."""

import json

import numpy as np

from scuba.artifacts import file_hash, write_json
from scuba.contract import ARCHETYPES
from scuba.evaluation import evaluate_cohort
from scuba.evaluation_runner import read_predictions
from scuba.final_data import checked_final_plan, load_final_partitions
from scuba.hosted_final import prepare_hosted_plan
from scuba.integrations.tabpfn_plan import plan_digest
from scuba.integrations.tabpfn_rest import validate_prediction
from scuba.integrations.tabpfn_revalidation import retained_value


def evaluate_hosted_final(
    hosted_run, hosted_hash, local_run, local_hash, output, *, allow_mock=False
):
    if file_hash(hosted_run / "manifest.json") != hosted_hash:
        raise ValueError("hosted manifest changed")
    hosted = json.loads((hosted_run / "manifest.json").read_text())
    accepted = ("live_verified", "offline_mock") if allow_mock else ("live_verified",)
    if (
        hosted.get("status") != "complete"
        or hosted.get("phase") != "final_test"
        or hosted.get("classification") != "synthetic"
        or hosted.get("test_scored") is not True
        or hosted.get("evidence") not in accepted
    ):
        raise ValueError("verified hosted final-test evidence required")
    envelope = json.loads((hosted_run / "plan.json").read_text())
    plan, _, rows = prepare_hosted_plan(**envelope["sources"])
    if (
        envelope["plan"] != plan
        or envelope["sha256"] != plan_digest(plan)
        or hosted["plan_sha256"] != envelope["sha256"]
        or hosted["integration"]["fresh_preflight"]["plan_sha256"] != envelope["sha256"]
        or hosted["integration"]["fitted_train_set_id"] != plan["retained_fitted_train_set_id"]
    ):
        raise ValueError("hosted plan or fitted resource changed")
    reference = hosted["response_evidence"]
    response_path = hosted_run / "response_evidence.json"
    if reference["path"] != response_path.name or file_hash(response_path) != reference["sha256"]:
        raise ValueError("captured response changed")
    saved = json.loads(response_path.read_text())
    if saved["plan_sha256"] != envelope["sha256"] or saved["prediction_partition"] != "test":
        raise ValueError("captured response cohort changed")
    metadata = {
        name: retained_value(saved["reported_metadata"][name])
        for name in (
            "task",
            "test_set_num_rows",
            "test_set_num_cols",
            "package_version",
            "billing_model_version",
            "execution_mode",
            "classes",
        )
    }
    metadata["tabpfn_config"] = {
        name: retained_value(value) for name, value in saved["reported_configuration"].items()
    }
    probability, identity = validate_prediction(
        plan, {"metadata": metadata, "prediction": saved["prediction"]}
    )
    p = read_predictions(
        hosted_run / "test_predictions.csv", hosted["predictions"], rows, hosted["metrics"]
    )
    if not np.array_equal(p, probability):
        raise ValueError("saved probabilities differ from captured response")
    if file_hash(local_run / "manifest.json") != local_hash:
        raise ValueError("local manifest changed")
    local = json.loads((local_run / "manifest.json").read_text())
    if (
        local.get("status") != "complete"
        or local.get("phase") != "M4_final"
        or local.get("classification") != "synthetic"
        or local.get("test_scored") is not True
        or local.get("regime") != "temporal"
        or local.get("plan_sha256") != plan["final_plan_sha256"]
        or set(local["models"]) != {"constant_prior", "logistic_regression", "xgboost", "catboost"}
    ):
        raise ValueError("matching local temporal final run required")
    from pathlib import Path

    sources = envelope["sources"]
    frozen = checked_final_plan(
        Path(sources["input"]), Path(sources["final_plan"]), sources["final_plan_sha256"]
    )
    if frozen["input_parameters"]["generator_seed"] != 3501:
        raise ValueError("hosted final comparison is primary seed only")
    if local["input_files"] != frozen["input_files"]:
        raise ValueError("local inputs differ from hosted inputs")
    _, audit = load_final_partitions(Path(sources["input"]), frozen, "temporal")
    probabilities = {}
    for name, model in local["models"].items():
        rep = model["repetitions"][0]
        probabilities[name] = read_predictions(
            local_run / name / "repeat-1/test_predictions.csv",
            rep["predictions"]["test"],
            rows,
            rep["metrics"]["test"],
        )
    probabilities["hosted_plus"] = p
    slices = {}
    for field, categories in (
        ("archetype", ARCHETYPES),
        ("activity_level", ("low", "medium", "high")),
    ):
        slices[field] = {}
        for category in categories:
            indices = [i for i, r in enumerate(rows) if r[field] == category]
            slices[field][category] = evaluate_cohort(
                [rows[i] for i in indices],
                {name: p[indices] for name, p in probabilities.items()},
                replicates=frozen["bootstrap_replicates"],
            )
    result = {
        "classification": "synthetic",
        "phase": "M4_hosted_final_comparison",
        "generator_seed": 3501,
        "regime": "temporal",
        "plan_sha256": plan["final_plan_sha256"],
        "split_audit": audit,
        "overall": evaluate_cohort(rows, probabilities, replicates=frozen["bootstrap_replicates"]),
        "slices": slices,
        "integration": hosted["integration"],
        "identity_reverified": identity["identity_validation"],
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "evaluation.json", result)
    write_json(
        output / "manifest.json",
        {
            "status": "complete",
            "phase": "M4_hosted_final_comparison",
            "classification": "synthetic",
            "evidence": hosted["evidence"],
            "test_scored": True,
            "api_requests": 0,
            "rows_uploaded": 0,
            "hosted_run": str(hosted_run),
            "hosted_manifest_sha256": hosted_hash,
            "local_run": str(local_run),
            "local_manifest_sha256": local_hash,
            "plan_sha256": plan["final_plan_sha256"],
            "evaluation_sha256": file_hash(output / "evaluation.json"),
        },
    )
    return result
