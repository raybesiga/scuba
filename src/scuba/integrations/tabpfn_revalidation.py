"""Offline acceptance of a hashed, captured live response; never call the API."""

import json

from scuba.artifacts import file_hash, write_json
from scuba.integrations.tabpfn_plan import TabPFNConfig, plan_digest, prepare_plan
from scuba.integrations.tabpfn_rest import (
    IntegrationError,
    prediction_diagnostics,
    validate_prediction,
)
from scuba.integrations.tabpfn_runner import provenance, save_plan, save_validation_result


def retained_value(field):
    if (
        field.get("present") is not True
        or field.get("status") != "retained"
        or field.get("transformations") != []
    ):
        raise IntegrationError("incomplete_saved_metadata")
    value = field.get("value")
    if field.get("type") == "list":
        if not isinstance(value, list) or field.get("original_length") != len(value):
            raise IntegrationError("incomplete_saved_metadata")
        return [retained_value(item) for item in value]
    if (
        field.get("type") not in ("str", "int", "float", "bool")
        or type(value).__name__ != field["type"]
    ):
        raise IntegrationError("incomplete_saved_metadata")
    return value


def revalidate_saved(input_dir, source, source_hash, output, *, expected_manifest_hash=None):
    """Write a separate derived result, leaving the original failed attempt intact."""
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "status": "running",
        "classification": "synthetic",
        "phase": "validation_only",
        "test_scored": False,
        "evidence": "offline_revalidation",
        "source_manifest_sha256": source_hash,
        "api_requests": 0,
        "rows_uploaded": 0,
    }
    try:
        if file_hash(source / "manifest.json") != source_hash:
            raise IntegrationError("source_manifest_changed")
        manifest = json.loads((source / "manifest.json").read_text())
        if (
            manifest.get("status") != "failed"
            or manifest.get("failure", {}).get("category") != "prediction_contract"
            or manifest.get("mode") != "prediction_only"
            or manifest.get("classification") != "synthetic"
            or manifest.get("phase") != "validation_only"
            or manifest.get("test_scored") is not False
            or manifest.get("evidence") not in ("live_attempt", "offline_mock")
        ):
            raise IntegrationError("unsupported_revalidation_source")
        reference = manifest["response_evidence"]
        path = source / "response_evidence.json"
        if reference["path"] != path.name or file_hash(path) != reference["sha256"]:
            raise IntegrationError("saved_response_changed")
        approved = json.loads((source / "plan.json").read_text())
        config = TabPFNConfig(**approved["plan"]["configuration"])
        plan, _, rows = prepare_plan(input_dir, config, expected_manifest_hash)
        if (
            approved != {"plan": plan, "sha256": plan_digest(plan)}
            or manifest["plan_sha256"] != plan_digest(plan)
            or manifest["integration_attempt"]["fresh_preflight"]["plan_sha256"]
            != plan_digest(plan)
        ):
            raise IntegrationError("approved_plan_changed")
        saved = json.loads(path.read_text())
        if (
            saved.get("plan_sha256") != plan_digest(plan)
            or saved.get("classification") != "synthetic"
            or saved.get("requested_configuration") != config.model_parameters()
            or saved.get("requested_variant") != config.variant
        ):
            raise IntegrationError("saved_response_plan_changed")
        # Reconstruct only retained fields, not redacted/transformed approximations.
        # Old stored check booleans are historical; recompute acceptance from values.
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
            name: retained_value(saved["reported_configuration"][name])
            for name in config.model_parameters()
        }
        response = {"metadata": metadata, "prediction": saved["prediction"]}
        probability, accepted = validate_prediction(plan, response)
        result.update(
            plan_sha256=plan_digest(plan),
            requested_variant=config.variant,
            source_response_sha256=reference["sha256"],
            identity_validation=accepted["identity_validation"],
            server_metadata=accepted,
            checks=prediction_diagnostics(plan, response)["checks"],
            original_integration_attempt=manifest["integration_attempt"],
            row_provenance=save_plan(output, plan, rows),
            **provenance(),
        )
        save_validation_result(output, result, rows, probability)
        result.update(
            status="complete",
            evidence="offline_revalidated_live_response"
            if manifest["evidence"] == "live_attempt"
            else "offline_mock",
        )
        write_json(output / "manifest.json", result)
        return result
    except Exception as exc:
        category = exc.category if isinstance(exc, IntegrationError) else "invalid_saved_evidence"
        result.update(status="failed", failure={"category": category, "billing_uncertain": False})
        write_json(output / "manifest.json", result)
        raise IntegrationError(category) from None
