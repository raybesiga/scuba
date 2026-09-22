"""Frozen Financial Stress final evaluation; hosted execution is explicitly gated."""

import argparse
import copy
import hashlib
import json
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

from scuba.evaluation import point_metrics
from scuba.financial_comparison import compare_rows, provenance
from scuba.financial_dashboard import cohort_audit, pinned, read
from scuba.financial_stress import TARGET, digest, load_validation_rows, new_output, write_json
from scuba.integrations.tabpfn_plan import plan_digest
from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest
from scuba.integrations.tabpfn_runner import safe_failure

ROOT = Path(__file__).resolve().parents[2]


def source_hashes():
    return {
        name: digest(ROOT / name)
        for name in (
            "src/scuba/financial_final.py",
            "src/scuba/financial_comparison.py",
            "src/scuba/financial_stress.py",
            "uv.lock",
            "docs/F4_SPEC.md",
        )
    }


def freeze(prepared, output, references=ROOT / "docs/reference"):
    """Freeze hashes/settings without opening final.csv."""
    prepared = Path(prepared)
    pm, _, _ = load_validation_rows(prepared)
    pinned(prepared / "manifest.json", references / "financial-stress-preparation-v1.json")
    local = read(references / "financial-stress-comparison-v1.json")
    hosted = read(references / "financial-stress-hosted-validation-v1.json")
    original = read(references / "financial-stress-hosted-plan-v1.json")
    expected = digest(prepared / "manifest.json")
    if any(m["prepared_manifest_sha256"] != expected for m in (local, hosted)):
        raise ValueError("development evidence uses different prepared data")
    if hosted["status"] != "complete" or hosted["evidence"] != "live_verified":
        raise ValueError("verified hosted validation required")
    if (
        original["sha256"] != plan_digest(original["plan"])
        or original["sha256"] != hosted["plan_sha256"]
    ):
        raise ValueError("hosted plan mismatch")
    if (
        local["feature_columns"] != pm["features"]
        or original["plan"]["feature_columns"] != pm["features"]
    ):
        raise ValueError("feature order mismatch")
    frozen = {
        "schema": "scuba.financial-stress-final/v1",
        "primary_metric": "log_loss",
        "prepared_manifest_sha256": expected,
        "partition_files": pm["files"],
        "local_settings": local["settings"],
        "original_hosted_plan": original["plan"],
        "hosted_validation_manifest_sha256": digest(
            references / "financial-stress-hosted-validation-v1.json"
        ),
        "retained_fitted_train_set_id": hosted["integration"]["fitted_train_set_id"],
        "checkpoint_identity": hosted["integration"]["checkpoint_identity"],
        "source_sha256": source_hashes(),
        "evaluation_partition": "final",
        "training_partition": "train",
        "feature_exclusions": [],
        "review_budgets": [0.05, 0.1],
        "threshold": 0.5,
        "calibration": "unchanged raw probabilities",
        "final_scored": False,
    }
    with new_output(output) as out:
        write_json(out / "protocol.json", {"protocol": frozen, "sha256": plan_digest(frozen)})
    return frozen


def final_context(prepared, protocol_path):
    frozen = read(protocol_path)
    p = frozen["protocol"]
    if frozen["sha256"] != plan_digest(p) or p["source_sha256"] != source_hashes():
        raise ValueError("frozen protocol or execution source changed")
    prepared = Path(prepared)
    if digest(prepared / "manifest.json") != p["prepared_manifest_sha256"]:
        raise ValueError("prepared manifest changed")
    pm, train, validation = load_validation_rows(prepared)
    path = prepared / "final.csv"
    if digest(path) != pm["files"]["final.csv"]:
        raise ValueError("final partition checksum mismatch")
    final = pd.read_csv(path, dtype={"ID": str})
    if set(final.columns) != {"ID", TARGET, *pm["features"]}:
        raise ValueError("final schema mismatch")
    if (
        final.ID.isna().any()
        or final.ID.duplicated().any()
        or set(final.ID) & (set(train.ID) | set(validation.ID))
    ):
        raise ValueError("final snapshot IDs invalid or overlap")
    if final[TARGET].isna().any() or set(final[TARGET].unique()) != {0, 1}:
        raise ValueError("final labels invalid")
    if (
        len(final) != pm["partitions"]["final"]["rows"]
        or int(final[TARGET].sum()) != pm["partitions"]["final"]["positives"]
    ):
        raise ValueError("final cohort differs from frozen audit")
    return p, pm, train, final


def local_final(prepared, protocol, output):
    p, pm, train, final = final_context(prepared, protocol)
    report = compare_rows(
        pm, train, final, output, p["prepared_manifest_sha256"], partition="final"
    )
    if report["settings"] != p["local_settings"]:
        raise ValueError("local recipes differ from frozen validation settings")
    report["protocol_sha256"] = plan_digest(p)
    write_json(Path(output) / "metrics.json", report)
    return report


def final_plan(prepared, protocol):
    p, pm, train, final = final_context(prepared, protocol)
    plan = copy.deepcopy(p["original_hosted_plan"])
    # Require the same training bytes as the previously fitted resource.
    for name, frame in (("train", train[pm["features"]]), ("labels", train[[TARGET]])):
        payload = frame.to_csv(index=False, lineterminator="\n", na_rep="").encode()
        if hashlib.sha256(payload).hexdigest() != plan["payloads"][name]["sha256"]:
            raise ValueError("retained model training payload mismatch")
    frame = final[pm["features"]]
    payload = frame.to_csv(index=False, lineterminator="\n", na_rep="").encode()
    plan.update(
        schema="scuba.tabpfn-final-plan/v1",
        phase="final_test",
        prediction_partition="test",
        source_partition="final",
        test_cohort_included=True,
        test_labels_uploaded=False,
        protocol_sha256=plan_digest(p),
        retained_fitted_train_set_id=p["retained_fitted_train_set_id"],
    )
    plan["cohorts"] = {
        "train": plan["cohorts"]["train"],
        "test": {"rows": len(final), "key_sha256": plan_digest(final.ID.tolist())},
    }
    plan["retained_training_payloads"] = {
        name: plan["payloads"][name] for name in ("train", "labels")
    }
    plan["payloads"] = {
        "test": {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "memory_bytes": int(frame.memory_usage(deep=True).sum()),
            "rows": len(final),
            "columns": pm["features"],
        }
    }
    plan["input_files"] = {name: pm["files"][name + ".csv"] for name in ("train", "final")}
    plan["estimate_requests"][0]["test_rows"] = len(final)
    plan["operation_limits"] = {
        "prediction_requests": 1,
        "fit_requests": 0,
        "training_uploads": 0,
        "test_feature_uploads": 1,
    }
    return plan, payload, final


def review(prepared, protocol, output, *, online=False, client_factory=None, token_loader=None):
    from scuba.integrations.secrets import tabpfn_token

    plan, _, _ = final_plan(prepared, protocol)
    with new_output(output) as out:
        write_json(out / "plan.json", {"plan": plan, "sha256": plan_digest(plan)})
        report = {
            "status": "awaiting_upload_approval",
            "rows_uploaded": 0,
            "plan_sha256": plan_digest(plan),
        }
        if online:
            client = (client_factory or TabPFNRest)((token_loader or tabpfn_token)())
            try:
                report["preflight"] = client.preflight(plan)
                if client_factory:
                    report["preflight"]["evidence"] = "offline_mock"
            finally:
                client.close()
        write_json(out / "manifest.json", report)
    return report


def run(
    prepared,
    protocol,
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
    plan, payload, rows = final_plan(prepared, protocol)
    if read(approved_plan) != {"plan": plan, "sha256": plan_digest(plan)}:
        raise IntegrationError("approved_plan_changed")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "status": "running",
        "evaluation_partition": "final",
        "final_evaluated": False,
        "classification": plan["classification"],
        "plan_sha256": plan_digest(plan),
        "protocol_sha256": plan["protocol_sha256"],
        "approved_estimated_tokens": max_tokens,
        "runtime": provenance(),
        "evidence": "live_attempt" if client_factory is None else "offline_mock",
    }
    write_json(output / "manifest.json", result)
    client = None
    start = time.perf_counter()
    try:
        client = (client_factory or TabPFNRest)((token_loader or tabpfn_token)())

        def save_response(evidence):
            write_json(output / "response_evidence.json", evidence)
            result["response_sha256"] = digest(output / "response_evidence.json")
            write_json(output / "manifest.json", result)

        probability, evidence = client.predict_final_test(
            plan, payload, allow_upload=True, max_tokens=max_tokens, response_sink=save_response
        )
        metrics = point_metrics(rows[TARGET], probability, rows.ID.tolist())
        metrics["roc_auc"] = float(roc_auc_score(rows[TARGET], probability))
        predictions = rows[["ID", TARGET]].assign(tabpfn_3_5_plus=probability)
        predictions.to_csv(output / "final_predictions.csv", index=False)
        result.update(
            status="complete",
            final_evaluated=True,
            metrics=metrics,
            integration=evidence,
            cohort_audit=cohort_audit(rows, probability),
            predictions_sha256=digest(output / "final_predictions.csv"),
            evidence="live_verified" if client_factory is None else "offline_mock",
        )
    except Exception as exc:
        result.update(status="failed", failure=safe_failure(exc, client))
        if client:
            result["stages"] = client.stages
            result["integration_attempt"] = client.execution_evidence
    finally:
        if client:
            client.close()
        result["end_to_end_seconds"] = time.perf_counter() - start
        write_json(output / "manifest.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "local", "review", "run"))
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--approved-plan", type=Path)
    parser.add_argument("--allow-upload", action="store_true")
    parser.add_argument("--max-estimated-tokens", type=int)
    a = parser.parse_args()
    if a.command != "freeze" and not a.protocol:
        parser.error("a frozen protocol is required")
    if a.online and a.command != "review":
        parser.error("online metadata checks require review")
    if a.command != "run" and (a.approved_plan or a.allow_upload or a.max_estimated_tokens):
        parser.error("upload arguments require run")
    if a.command == "freeze":
        result = freeze(a.prepared, a.output)
    elif a.command == "local":
        result = local_final(a.prepared, a.protocol, a.output)
    elif a.command == "review":
        result = review(a.prepared, a.protocol, a.output, online=a.online)
    else:
        if not a.approved_plan:
            parser.error("approved plan required")
        result = run(
            a.prepared,
            a.protocol,
            a.approved_plan,
            a.output,
            allow_upload=a.allow_upload,
            max_tokens=a.max_estimated_tokens,
        )
    print(
        json.dumps(
            {
                "status": result.get("status", "complete"),
                "metrics": result.get("metrics"),
                "preflight": result.get("preflight"),
            }
        )
    )
    if result.get("status") == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
