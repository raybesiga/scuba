"""Execute one approved full-data inference plan and verify the retained output."""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from scuba.financial_comparison import provenance
from scuba.financial_inference import inference_context
from scuba.financial_stress import digest, write_json
from scuba.integrations.tabpfn_plan import plan_digest
from scuba.integrations.tabpfn_response_archive import ARCHIVE_NAME
from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest, validate_prediction
from scuba.integrations.tabpfn_revalidation import retained_value
from scuba.integrations.tabpfn_runner import safe_failure

ROOT = Path(__file__).resolve().parents[2]


def checked_context(bundle, prepared, approved_plan):
    plan, payloads, rows = inference_context(bundle, prepared)
    if json.loads(Path(approved_plan).read_text()) != {
        "plan": plan,
        "sha256": plan_digest(plan),
    }:
        raise IntegrationError("approved_plan_changed")
    final = ROOT / "docs/reference/financial-stress-final-evaluation-v1.json"
    result = json.loads(final.read_text())
    if (
        result["status"] != "verified_final"
        or result["prepared_manifest_sha256"] != plan["prepared_manifest_sha256"]
    ):
        raise IntegrationError("recorded_final_evaluation_required")
    return plan, payloads, rows, digest(final)


def retained_probability(plan, evidence):
    if evidence["plan_sha256"] != plan_digest(plan):
        raise ValueError("response plan mismatch")
    metadata = {
        key: retained_value(value)
        for key, value in evidence["reported_metadata"].items()
        if value["present"]
    }
    metadata["tabpfn_config"] = {
        key: retained_value(value) for key, value in evidence["reported_configuration"].items()
    }
    return validate_prediction(plan, {"prediction": evidence["prediction"], "metadata": metadata})


def verify_output(output):
    """Recheck identity, all probabilities, row count/order and hashes offline."""
    output = Path(output)
    report = json.loads((output / "manifest.json").read_text())
    record = json.loads((output / "plan.json").read_text())
    plan = record["plan"]
    if record["sha256"] != plan_digest(plan) or report["plan_sha256"] != record["sha256"]:
        raise ValueError("plan checksum mismatch")
    if report["status"] != "complete" or report["quality_metrics_available"]:
        raise ValueError("completed unlabelled inference required")
    archive = report.get("complete_response_archive")
    if archive is not None and (
        archive["path"] != ARCHIVE_NAME or digest(output / ARCHIVE_NAME) != archive["sha256"]
    ):
        raise ValueError("response archive checksum mismatch")
    for name, key in (
        ("response_evidence.json", "response_sha256"),
        ("predictions.csv", "predictions_sha256"),
    ):
        if digest(output / name) != report[key]:
            raise ValueError("output checksum mismatch")
    evidence = json.loads((output / "response_evidence.json").read_text())
    probability, metadata = retained_probability(plan, evidence)
    rows = pd.read_csv(output / "predictions.csv", dtype={"ID": str}, float_precision="round_trip")
    if (
        list(rows.columns) != plan["output_contract"]["columns"]
        or len(rows) != plan["cohorts"]["test"]["rows"]
        or rows.ID.isna().any()
        or rows.ID.duplicated().any()
        or plan_digest(rows.ID.tolist()) != plan["cohorts"]["test"]["key_sha256"]
        or not np.array_equal(rows.probability_stress_30d.to_numpy(), probability)
    ):
        raise ValueError("prediction rows or probabilities mismatch")
    return {
        "status": "verified_unlabelled_inference",
        "rows": len(rows),
        "original_id_order": True,
        "response_probabilities_match": True,
        "identity": metadata["identity_validation"],
        "quality_metrics_available": False,
        "api_requests": 0,
    }


def run(
    bundle,
    prepared,
    approved_plan,
    output,
    *,
    allow_upload=False,
    max_tokens=None,
    client_factory=None,
    token_loader=None,
):
    from scuba.integrations.secrets import tabpfn_token

    if not allow_upload or type(max_tokens) is not int or max_tokens <= 0:
        raise IntegrationError("upload_and_positive_budget_approval_required")
    plan, payloads, rows, final_hash = checked_context(bundle, prepared, approved_plan)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "plan.json", {"plan": plan, "sha256": plan_digest(plan)})
    report = {
        "status": "running",
        "model": "TabPFN-3.5-Plus",
        "phase": "unlabelled_inference_only",
        "quality_metrics_available": False,
        "classification": plan["classification"],
        "plan_sha256": plan_digest(plan),
        "train_rows": plan["cohorts"]["train"]["rows"],
        "inference_rows": len(rows),
        "recorded_final_evaluation_sha256": final_hash,
        "approved_estimated_tokens": max_tokens,
        "runtime": {
            **provenance(),
            "inference_source_sha256": digest(__file__),
            "planner_source_sha256": digest(Path(__file__).with_name("financial_inference.py")),
        },
        "evidence": "live_attempt" if client_factory is None else "offline_mock",
    }
    write_json(output / "manifest.json", report)
    client = None
    start = time.perf_counter()
    try:
        client = (client_factory or TabPFNRest)((token_loader or tabpfn_token)())
        client.response_archive_dir = output

        def save_response(evidence):
            if client.prediction_response_archive is not None:
                report["complete_response_archive"] = client.prediction_response_archive
            write_json(output / "response_evidence.json", evidence)
            report["response_sha256"] = digest(output / "response_evidence.json")
            write_json(output / "manifest.json", report)

        probability, evidence = client.execute(
            plan, payloads, allow_upload=True, max_tokens=max_tokens, response_sink=save_response
        )
        retained, _ = retained_probability(
            plan, json.loads((output / "response_evidence.json").read_text())
        )
        if not np.array_equal(probability, retained):
            raise ValueError("retained response differs from prediction")
        predictions = rows[["ID"]].copy()
        predictions["probability_stress_30d"] = probability
        predictions.to_csv(output / "predictions.csv", index=False)
        report.update(
            status="complete",
            integration=evidence,
            predictions_sha256=digest(output / "predictions.csv"),
            evidence="live_verified" if client_factory is None else "offline_mock",
        )
        write_json(output / "manifest.json", report)
        report["verification"] = verify_output(output)
    except Exception as exc:
        report.update(status="failed", failure=safe_failure(exc, client))
        if client:
            report["stages"] = client.stages
            report["integration_attempt"] = client.execution_evidence
    finally:
        if client:
            if client.prediction_response_archive is not None:
                report["complete_response_archive"] = client.prediction_response_archive
            client.close()
        report["end_to_end_seconds"] = time.perf_counter() - start
        write_json(output / "manifest.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "verify"))
    for arg in ("bundle", "prepared", "approved-plan", "output"):
        parser.add_argument("--" + arg, type=Path, required=arg == "output")
    parser.add_argument("--allow-upload", action="store_true")
    parser.add_argument("--max-estimated-tokens", type=int)
    args = parser.parse_args()
    if args.command == "verify":
        result = verify_output(args.output)
    else:
        if not all((args.bundle, args.prepared, args.approved_plan)):
            parser.error("run requires bundle, prepared and approved-plan")
        result = run(
            args.bundle,
            args.prepared,
            args.approved_plan,
            args.output,
            allow_upload=args.allow_upload,
            max_tokens=args.max_estimated_tokens,
        )
    print(json.dumps({key: result[key] for key in ("status", "rows") if key in result}))
    if result["status"] == "failed":
        raise SystemExit(1)
