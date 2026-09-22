"""CLI workflows that distinguish offline plans, metadata checks and approved runs."""

import json
import platform
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

from scuba.artifacts import file_hash, write_json, write_table
from scuba.integrations.secrets import MissingToken, tabpfn_token
from scuba.integrations.tabpfn_plan import TabPFNConfig, plan_digest, prepare_plan
from scuba.integrations.tabpfn_rest import IntegrationError, TabPFNRest, resource_id
from scuba.models.runner import PREDICTION_SCHEMA, validation_metrics

PROVENANCE_SCHEMA = {
    "partition": "string",
    "row_index": "integer",
    "customer_id": "string",
    "prediction_date": "date:YYYY-MM-DD",
    "is_synthetic": "boolean",
}


def provenance():
    root = Path(__file__).resolve().parents[3]
    return {
        "dependency_lock_sha256": file_hash(root / "uv.lock"),
        "source_sha256": {
            str(path.relative_to(root / "src")): file_hash(path)
            for path in sorted((root / "src/scuba").rglob("*.py"))
        },
        "dependencies": {
            name: version(name)
            for name in ("httpx", "python-dotenv", "numpy", "pandas", "scikit-learn")
        },
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


def save_plan(output, plan, rows):
    write_json(output / "plan.json", {"plan": plan, "sha256": plan_digest(plan)})
    # Model matrices omit metadata; retain a local synthetic marker for every row.
    row_map = [
        {
            "partition": name,
            "row_index": index,
            "customer_id": row["customer_id"],
            "prediction_date": row["prediction_date"],
            "is_synthetic": "true",
        }
        for name, values in rows.items()
        for index, row in enumerate(values)
    ]
    return write_table(output / "row_provenance.csv", row_map, PROVENANCE_SCHEMA)


def safe_failure(exc, client):
    if isinstance(exc, IntegrationError):
        result = exc.evidence()
    else:
        category = (
            "missing_token"
            if isinstance(exc, MissingToken)
            else "local_io"
            if isinstance(exc, OSError)
            else "invalid_input_or_plan"
            if isinstance(exc, (ValueError, KeyError, TypeError))
            else "internal_error"
        )
        result = {"category": category, "status_code": None, "billing_uncertain": False}
    result["billing_uncertain"] |= bool(client and client.billing_uncertain)
    return result


def preflight_bundle(
    input_dir,
    output,
    config,
    *,
    online=False,
    env_file=Path(".env"),
    expected_manifest_hash=None,
    client_factory=TabPFNRest,
):
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "classification": "synthetic",
        "status": "running",
        "evidence": "offline_plan",
        "rows_uploaded": 0,
    }
    client = None
    try:
        plan, _, rows = prepare_plan(input_dir, config, expected_manifest_hash)
        result.update(
            plan_sha256=plan_digest(plan),
            row_provenance=save_plan(output, plan, rows),
            **provenance(),
        )
        if online:
            client = client_factory(tabpfn_token(env_file))
            result["metadata_preflight"] = client.preflight(plan)
            result["evidence"] = (
                "live_metadata_only" if client_factory is TabPFNRest else "offline_mock"
            )
            result["metadata_preflight"]["evidence"] = result["evidence"]
            result["stages"] = client.stages.copy()
            result["status"] = "awaiting_upload_and_budget_approval"
        else:
            result["status"] = "awaiting_online_limits_and_estimate"
        write_json(output / "manifest.json", result)
        return result
    except Exception as exc:
        failure = safe_failure(exc, client)
        result.update(status="failed", failure=failure)
        write_json(output / "manifest.json", result)
        raise IntegrationError(**failure) from None
    finally:
        if client:
            client.close()


def run_approved(
    input_dir,
    plan_path,
    output,
    *,
    allow_upload=False,
    max_tokens=None,
    env_file=Path(".env"),
    expected_manifest_hash=None,
    client_factory=TabPFNRest,
):
    # An approval flag and budget are required before even loading credentials.
    if not allow_upload or type(max_tokens) is not int or max_tokens <= 0:
        raise IntegrationError("upload_and_positive_budget_approval_required")
    start = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "classification": "synthetic",
        "status": "running",
        "phase": "validation_only",
        "test_scored": False,
        "evidence": "live_attempt" if client_factory is TabPFNRest else "offline_mock",
    }
    client = None
    write_json(output / "manifest.json", result)
    try:
        approved = json.loads(plan_path.read_text())
        config = TabPFNConfig(**approved["plan"]["configuration"])
        plan, payloads, rows = prepare_plan(input_dir, config, expected_manifest_hash)
        if approved["plan"] != plan or approved["sha256"] != plan_digest(plan):
            raise IntegrationError("approved_plan_changed")
        result.update(
            plan_sha256=plan_digest(plan),
            requested_variant=config.variant,
            row_provenance=save_plan(output, plan, rows),
            **provenance(),
        )
        write_json(output / "manifest.json", result)
        client = client_factory(tabpfn_token(env_file))

        def save_response(evidence):
            # Persist diagnostic fields before acceptance or metric computation.
            path = output / "response_evidence.json"
            write_json(path, evidence)
            result["response_evidence"] = {
                "path": path.name,
                "sha256": file_hash(path),
                "checks": evidence["checks"],
            }
            write_json(output / "manifest.json", result)

        probability, evidence = client.execute(
            plan,
            payloads,
            allow_upload=allow_upload,
            max_tokens=max_tokens,
            response_sink=save_response,
        )
        result.update(integration=evidence)
        if client_factory is not TabPFNRest:
            evidence["fresh_preflight"]["evidence"] = "offline_mock"
        save_validation_result(output, result, rows, probability)
        result.update(
            status="complete",
            evidence="live_verified" if client_factory is TabPFNRest else "offline_mock",
            end_to_end_seconds=perf_counter() - start,
        )
        write_json(output / "manifest.json", result)
        return result
    except Exception as exc:
        failure = safe_failure(exc, client)
        result.update(status="failed", failure=failure)
        if client:
            result["stages"] = client.stages.copy()
            if client.execution_evidence is not None:
                result["integration_attempt"] = client.execution_evidence
            if "response_evidence" in result:
                result["unverified_response"] = result["response_evidence"]
        write_json(output / "manifest.json", result)
        raise IntegrationError(**failure) from None
    finally:
        if client:
            client.close()


def save_validation_result(output, result, rows, probability):
    predictions = [
        {
            "customer_id": row["customer_id"],
            "prediction_date": row["prediction_date"],
            "dormant_30d": row["dormant_30d"],
            "probability_dormant": format(float(p), ".17g"),
            "is_synthetic": "true",
        }
        for row, p in zip(rows["validation"], probability, strict=True)
    ]
    result["predictions"] = write_table(
        output / "validation_predictions.csv", predictions, PREDICTION_SCHEMA
    )
    result["metrics"] = validation_metrics(
        [r["dormant_30d"] for r in rows["validation"]], probability
    )


def continuation_context(input_dir, prior_run, source_hash, expected_manifest_hash=None):
    """Pin the historical resource IDs to its plan and current frozen input hashes."""
    path = prior_run / "manifest.json"
    if not isinstance(source_hash, str) or file_hash(path) != source_hash:
        raise IntegrationError("source_manifest_changed")
    previous = json.loads(path.read_text())
    approved = json.loads((prior_run / "plan.json").read_text())
    config = TabPFNConfig(**approved["plan"]["configuration"])
    plan, _, rows = prepare_plan(input_dir, config, expected_manifest_hash)
    if approved != {"plan": plan, "sha256": plan_digest(plan)}:
        raise IntegrationError("approved_plan_changed")
    attempt = previous.get("integration_attempt", {})
    if (
        config.variant != "plus"
        or previous.get("status") != "failed"
        or previous.get("failure", {}).get("category") != "prediction_contract"
        or previous.get("classification") != "synthetic"
        or previous.get("phase") != "validation_only"
        or previous.get("test_scored") is not False
        or previous.get("mode") == "prediction_only"
        or previous.get("plan_sha256") != plan_digest(plan)
        or attempt.get("fresh_preflight", {}).get("plan_sha256") != plan_digest(plan)
        or previous.get("evidence") not in ("live_attempt", "offline_mock")
    ):
        raise IntegrationError("unsupported_continuation_source")
    return (
        plan,
        rows,
        previous,
        {
            "source_manifest_sha256": source_hash,
            "plan_sha256": plan_digest(plan),
            "fitted_train_set_id": resource_id(attempt.get("fitted_train_set_id")),
            "test_set_upload_id": resource_id(attempt.get("test_set_upload_id")),
            "prediction_request_limit": 1,
            "rows_uploaded": 0,
            "fit_requests": 0,
            "requested_configuration": config.model_parameters(),
        },
    )


def continue_prediction(
    input_dir,
    prior_run,
    source_hash,
    output,
    *,
    allow_predict=False,
    max_tokens=None,
    env_file=Path(".env"),
    expected_manifest_hash=None,
    client_factory=TabPFNRest,
):
    """Default offline review; explicit approval enables one existing-resource prediction."""
    if allow_predict and (type(max_tokens) is not int or max_tokens <= 0):
        raise IntegrationError("prediction_and_positive_budget_approval_required")
    start = perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "classification": "synthetic",
        "status": "running",
        "phase": "validation_only",
        "mode": "prediction_only",
        "test_scored": False,
        "rows_uploaded": 0,
        "evidence": "offline_plan",
    }
    client = None
    try:
        plan, rows, previous, continuation = continuation_context(
            input_dir, prior_run, source_hash, expected_manifest_hash
        )
        result.update(
            plan_sha256=plan_digest(plan),
            continuation=continuation,
            row_provenance=save_plan(output, plan, rows),
            **provenance(),
        )
        write_json(output / "continuation.json", continuation)
        if not allow_predict:
            result["status"] = "awaiting_prediction_approval"
            write_json(output / "manifest.json", result)
            return result
        if client_factory is TabPFNRest and previous["evidence"] != "live_attempt":
            raise IntegrationError("mock_source_cannot_be_used_live")
        result["evidence"] = "live_attempt" if client_factory is TabPFNRest else "offline_mock"
        write_json(output / "manifest.json", result)
        client = client_factory(tabpfn_token(env_file))

        def save_response(evidence):
            path = output / "response_evidence.json"
            write_json(path, evidence)
            result["response_evidence"] = {
                "path": path.name,
                "sha256": file_hash(path),
                "checks": evidence["checks"],
            }
            result["integration_attempt"] = client.execution_evidence
            result["stages"] = client.stages.copy()
            if client_factory is not TabPFNRest:
                client.execution_evidence["fresh_preflight"]["evidence"] = "offline_mock"
            write_json(output / "manifest.json", result)

        probability, evidence = client.predict_existing(
            plan,
            continuation["fitted_train_set_id"],
            continuation["test_set_upload_id"],
            allow_predict=True,
            max_tokens=max_tokens,
            response_sink=save_response,
        )
        result["integration"] = evidence
        if client_factory is not TabPFNRest:
            evidence["fresh_preflight"]["evidence"] = "offline_mock"
        save_validation_result(output, result, rows, probability)
        result.update(
            status="complete",
            end_to_end_seconds=perf_counter() - start,
            evidence="live_verified" if client_factory is TabPFNRest else "offline_mock",
        )
        write_json(output / "manifest.json", result)
        return result
    except Exception as exc:
        failure = safe_failure(exc, client)
        result.update(status="failed", failure=failure)
        if client:
            result["stages"] = client.stages.copy()
            if client.execution_evidence is not None:
                result["integration_attempt"] = client.execution_evidence
                if client_factory is not TabPFNRest:
                    client.execution_evidence["fresh_preflight"]["evidence"] = "offline_mock"
        if "response_evidence" in result:
            result["unverified_response"] = result["response_evidence"]
        write_json(output / "manifest.json", result)
        raise IntegrationError(**failure) from None
    finally:
        if client:
            client.close()
