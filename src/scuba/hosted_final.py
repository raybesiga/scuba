"""Offline final-test review and an explicitly approved one-prediction execution."""

import argparse
import copy
import json
from pathlib import Path

from scuba.artifacts import file_hash, write_json, write_table
from scuba.final_data import checked_final_plan, load_final_partitions
from scuba.integrations.secrets import tabpfn_token
from scuba.integrations.tabpfn_plan import digest, plan_digest
from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest
from scuba.integrations.tabpfn_runner import continuation_context, provenance, safe_failure
from scuba.models.common import feature_frame
from scuba.models.runner import PREDICTION_SCHEMA, validation_metrics


def prepare_hosted_plan(input, final_plan, final_plan_sha256, prior_run, prior_manifest_sha256):
    frozen = checked_final_plan(Path(input), Path(final_plan), final_plan_sha256)
    original, _, previous, continuation = continuation_context(
        Path(input), Path(prior_run), prior_manifest_sha256, frozen["input_files"]["manifest.json"]
    )
    rows, _ = load_final_partitions(Path(input), frozen, "temporal")
    if (
        plan_digest([[r["customer_id"], r["prediction_date"]] for r in rows["train"]])
        != original["cohorts"]["train"]["key_sha256"]
    ):
        raise ValueError("retained fitted resource used a different training cohort")
    frame = feature_frame(rows["test"])
    payload = frame.to_csv(index=False, lineterminator="\n", na_rep="").encode()
    plan = copy.deepcopy(original)
    plan.update(
        schema="scuba.tabpfn-final-plan/v1",
        phase="final_test",
        prediction_partition="test",
        test_cohort_included=True,
        test_labels_uploaded=False,
        final_plan_sha256=final_plan_sha256,
        retained_fitted_train_set_id=continuation["fitted_train_set_id"],
        prior_manifest_sha256=prior_manifest_sha256,
        retained_resource_evidence=previous["evidence"],
    )
    plan["retained_training_payloads"] = {
        name: original["payloads"][name] for name in ("train", "labels")
    }
    plan["cohorts"] = {
        "train": original["cohorts"]["train"],
        "test": {
            "rows": len(rows["test"]),
            "customers": len({r["customer_id"] for r in rows["test"]}),
            "positives": sum(r["dormant_30d"] for r in rows["test"]),
            "key_sha256": plan_digest(
                [[r["customer_id"], r["prediction_date"]] for r in rows["test"]]
            ),
        },
    }
    plan["payloads"] = {
        "test": {
            "sha256": digest(payload),
            "size_bytes": len(payload),
            "memory_bytes": int(frame.memory_usage(deep=True).sum()),
            "rows": len(frame),
            "columns": list(frame.columns),
            "classification": "synthetic",
        }
    }
    plan["estimate_requests"][0]["test_rows"] = len(frame)
    plan["operation_limits"] = {
        "prediction_requests": 1,
        "fit_requests": 0,
        "training_uploads": 0,
        "test_feature_uploads": 1,
    }
    return plan, payload, rows["test"]


def review_hosted_test(sources, output):
    plan, _, rows = prepare_hosted_plan(**sources)
    output.mkdir(parents=True, exist_ok=False)
    write_json(
        output / "plan.json", {"plan": plan, "sha256": plan_digest(plan), "sources": sources}
    )
    write_table(
        output / "row_provenance.csv",
        [
            {
                "customer_id": r["customer_id"],
                "prediction_date": r["prediction_date"],
                "is_synthetic": "true",
            }
            for r in rows
        ],
        {"customer_id": "string", "prediction_date": "date", "is_synthetic": "boolean"},
    )
    write_json(
        output / "manifest.json",
        {
            "status": "awaiting_upload_and_budget_approval",
            "evidence": "offline_plan",
            "classification": "synthetic",
            "plan_sha256": plan_digest(plan),
            "api_requests": 0,
            "proposed_estimate_ceiling": 10000,
            "ceiling_basis": "provisional; prior v3.5 prediction estimate minimum, fresh estimate required",
            "test_labels_uploaded": False,
        },
    )
    return plan


def run_hosted_test(
    plan_path,
    expected_digest,
    output,
    *,
    allow_upload=False,
    max_tokens=None,
    client_factory=TabPFNRest,
):
    if not allow_upload or type(max_tokens) is not int or max_tokens <= 0:
        raise IntegrationError("upload_and_positive_budget_approval_required")
    approved = json.loads(plan_path.read_text())
    plan, payload, rows = prepare_hosted_plan(**approved["sources"])
    if (
        approved["sha256"] != expected_digest
        or approved["plan"] != plan
        or plan_digest(plan) != expected_digest
    ):
        raise IntegrationError("approved_plan_changed")
    if client_factory is TabPFNRest and plan["retained_resource_evidence"] != "live_attempt":
        raise IntegrationError("mock_source_cannot_be_used_live")
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "status": "running",
        "classification": "synthetic",
        "phase": "final_test",
        "test_scored": False,
        "evidence": "live_attempt" if client_factory is TabPFNRest else "offline_mock",
        "plan_sha256": expected_digest,
        **provenance(),
    }
    client = None
    write_json(output / "plan.json", approved)
    write_json(output / "manifest.json", result)
    try:
        client = client_factory(tabpfn_token(Path(".env")))

        def save_response(evidence):
            path = output / "response_evidence.json"
            write_json(path, evidence)
            result["response_evidence"] = {
                "path": path.name,
                "sha256": file_hash(path),
                "checks": evidence["checks"],
            }
            write_json(output / "manifest.json", result)

        probability, evidence = client.predict_final_test(
            plan, payload, allow_upload=True, max_tokens=max_tokens, response_sink=save_response
        )
        result["integration"] = evidence
        if client_factory is not TabPFNRest:
            evidence["fresh_preflight"]["evidence"] = "offline_mock"
        result["predictions"] = write_table(
            output / "test_predictions.csv",
            [
                {
                    "customer_id": row["customer_id"],
                    "prediction_date": row["prediction_date"],
                    "dormant_30d": row["dormant_30d"],
                    "probability_dormant": format(float(p), ".17g"),
                    "is_synthetic": "true",
                }
                for row, p in zip(rows, probability, strict=True)
            ],
            PREDICTION_SCHEMA,
        )
        result.update(
            status="complete",
            test_scored=True,
            metrics=validation_metrics([r["dormant_30d"] for r in rows], probability),
            evidence="live_verified" if client_factory is TabPFNRest else "offline_mock",
        )
        write_json(output / "manifest.json", result)
        return result
    except Exception as exc:
        failure = safe_failure(exc, client)
        result.update(status="failed", failure=failure)
        if client:
            result["integration_attempt"] = client.execution_evidence
            result["stages"] = client.stages
        write_json(output / "manifest.json", result)
        raise IntegrationError(**failure) from None
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Execute a reviewed final-test upload and one prediction."
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-upload", action="store_true")
    parser.add_argument("--max-estimated-tokens", type=int)
    args = parser.parse_args()
    try:
        result = run_hosted_test(
            args.plan,
            args.plan_sha256,
            args.output,
            allow_upload=args.allow_upload,
            max_tokens=args.max_estimated_tokens,
        )
    except (IntegrationError, ValueError, OSError):
        parser.exit(2, "Final-test run stopped; inspect the local manifest when present.\n")
    print(json.dumps({k: result[k] for k in ("status", "evidence", "metrics")}))
