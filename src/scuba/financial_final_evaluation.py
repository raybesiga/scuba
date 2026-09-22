"""Reverify retained Financial Stress final evidence without service calls or fitting."""

import argparse

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from scuba.financial_dashboard import checked_predictions, cohort_audit, read
from scuba.financial_final import final_context, final_plan
from scuba.financial_stress import TARGET, digest, new_output, write_json
from scuba.integrations.tabpfn_plan import plan_digest
from scuba.integrations.tabpfn_rest import validate_prediction
from scuba.integrations.tabpfn_revalidation import retained_value


def verify(prepared, protocol, local, hosted, approved_plan, output):
    frozen, pm, _, rows = final_context(prepared, protocol)
    plan, _, _ = final_plan(prepared, protocol)
    if read(approved_plan) != {"plan": plan, "sha256": plan_digest(plan)}:
        raise ValueError("final plan changed")
    lm, hm = read(local / "metrics.json"), read(hosted / "manifest.json")
    if lm["protocol_sha256"] != plan_digest(frozen) or hm["protocol_sha256"] != plan_digest(frozen):
        raise ValueError("results use different frozen protocols")
    if (
        lm["settings"] != frozen["local_settings"]
        or lm["feature_columns"] != pm["features"]
        or lm["excluded_features"]
    ):
        raise ValueError("local recipe changed")
    if any(m["evaluation_partition"] != "final" or not m["final_evaluated"] for m in (lm, hm)):
        raise ValueError("final evaluation evidence required")
    if (
        hm["status"] != "complete"
        or hm["evidence"] != "live_verified"
        or hm["plan_sha256"] != plan_digest(plan)
    ):
        raise ValueError("verified hosted final result required")
    probabilities = checked_predictions(
        local, lm, rows, lm["metrics"], filename="final_predictions.csv"
    )
    probabilities.update(
        checked_predictions(hosted, hm, rows, ["tabpfn_3_5_plus"], filename="final_predictions.csv")
    )
    response = hosted / "response_evidence.json"
    if digest(response) != hm["response_sha256"]:
        raise ValueError("response checksum mismatch")
    evidence = read(response)
    if evidence["plan_sha256"] != plan_digest(plan):
        raise ValueError("response plan mismatch")
    metadata = {
        k: retained_value(v) for k, v in evidence["reported_metadata"].items() if v["present"]
    }
    metadata["tabpfn_config"] = {
        k: retained_value(v) for k, v in evidence["reported_configuration"].items()
    }
    probability, _ = validate_prediction(
        plan, {"prediction": evidence["prediction"], "metadata": metadata}
    )
    if not np.array_equal(probability, probabilities["tabpfn_3_5_plus"]):
        raise ValueError("hosted response differs from saved probabilities")
    metrics = {**lm["metrics"], "tabpfn_3_5_plus": hm["metrics"]}
    for model, p in probabilities.items():
        m = metrics[model]
        independent = {
            "log_loss": log_loss(rows[TARGET], p),
            "roc_auc": roc_auc_score(rows[TARGET], p),
            "average_precision": average_precision_score(rows[TARGET], p),
            "brier_score": brier_score_loss(rows[TARGET], p),
        }
        if any(
            not np.isclose(value, m[key], rtol=0, atol=1e-12) for key, value in independent.items()
        ):
            raise ValueError("independent metric verification failed")
        order = sorted(range(len(rows)), key=lambda i: (-p[i], rows.ID.iloc[i]))
        for q in (0.05, 0.1):
            k = int(np.ceil(q * len(rows)))
            if int(rows[TARGET].iloc[order[:k]].sum()) != m["top_budgets"][str(q)]["tp"]:
                raise ValueError("independent review capture verification failed")
    result = {
        "status": "verified_final",
        "prepared_manifest_sha256": digest(prepared / "manifest.json"),
        "protocol_sha256": plan_digest(frozen),
        "cohort": pm["partitions"]["final"],
        "metrics": metrics,
        "cohort_audit": cohort_audit(rows, probability),
        "identity": hm["integration"]["checkpoint_identity"],
        "sources": {
            "local": digest(local / "metrics.json"),
            "hosted": digest(hosted / "manifest.json"),
            "response": digest(response),
        },
        "verification": {
            "model_count": len(metrics),
            "rows": len(rows),
            "independent_metrics": True,
            "api_requests": 0,
            "fit_requests": 0,
        },
    }
    with new_output(output) as out:
        write_json(out / "evaluation.json", result)
    return result


if __name__ == "__main__":
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("prepared", "protocol", "local", "hosted", "approved-plan", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    result = verify(**vars(parser.parse_args()))
    print(result["status"])
