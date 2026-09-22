"""Build a local Financial Stress workspace from pinned validation evidence."""

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from scuba.evaluation import point_metrics
from scuba.financial_stress import TARGET, digest, load_validation_rows, write_json
from scuba.integrations.tabpfn_rest import validate_prediction
from scuba.integrations.tabpfn_revalidation import retained_value

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = [
    "paybill",
    "merchantpay",
    "transfer_from_bank",
    "mm_send",
    "received",
    "deposit",
    "withdraw",
]


def read(path):
    return json.loads(Path(path).read_text())


def pinned(path, reference):
    if digest(path) != digest(reference):
        raise ValueError("evidence differs from pinned reference")
    return read(path)


def checked_predictions(
    folder, manifest, validation, models, *, filename="validation_predictions.csv"
):
    path = folder / filename
    if digest(path) != manifest["predictions_sha256"]:
        raise ValueError("prediction checksum mismatch")
    frame = pd.read_csv(path, float_precision="round_trip", dtype={"ID": str})
    if (
        frame.ID.tolist() != validation.ID.tolist()
        or frame[TARGET].tolist() != validation[TARGET].tolist()
    ):
        raise ValueError("prediction IDs or labels do not match validation")
    result = {}
    for model in models:
        p = frame[model].to_numpy()
        if model == "xgboost":
            p = p.astype(np.float32).astype(float)
        metrics = point_metrics(validation[TARGET], p, validation.ID.tolist())
        metrics["roc_auc"] = float(roc_auc_score(validation[TARGET], p))
        saved = manifest["metrics"] if model == "tabpfn_3_5_plus" else manifest["metrics"][model]
        if metrics != saved:
            raise ValueError("saved metrics do not match predictions")
        result[model] = p
    return result


def cohort_audit(validation, probability):
    dimensions = {
        name: validation[name].astype(str)
        for name in ("region", "segment", "earning_pattern", "gender")
    }
    dimensions["age_band"] = pd.cut(
        validation.age,
        [17, 29, 44, 59, float("inf")],
        labels=["18–29", "30–44", "45–59", "60+"],
        right=True,
    ).astype(str)
    order = np.lexsort((validation.ID.to_numpy(), -probability))
    selected = {str(q): set(order[: int(np.ceil(q * len(validation)))]) for q in (0.05, 0.1)}
    output = []
    for dimension, groups in dimensions.items():
        for group in sorted(groups.unique()):
            mask = (groups == group).to_numpy()
            indices = np.flatnonzero(mask)
            labels = validation[TARGET].to_numpy()[mask]
            m = point_metrics(labels, probability[mask], validation.ID[mask].tolist())
            output.append(
                {
                    "dimension": dimension,
                    "group": group,
                    "rows": len(indices),
                    "positives": int(labels.sum()),
                    "prevalence": float(labels.mean()),
                    "mean_probability": float(probability[mask].mean()),
                    "log_loss": m["log_loss"],
                    "sparse": m["sparse"],
                    "roc_auc": float(roc_auc_score(labels, probability[mask]))
                    if len(set(labels)) == 2
                    else None,
                    "budgets": {
                        q: {
                            "selected": sum(i in members for i in indices),
                            "captured": sum(
                                int(validation[TARGET].iloc[i]) for i in indices if i in members
                            ),
                        }
                        for q, members in selected.items()
                    },
                }
            )
    return output


def review_snapshots(validation, p):
    snapshots = []
    for index, row in validation.iterrows():
        series = {
            family: [int(row[f"m{m}_{family}_volume"]) for m in range(6, 0, -1)]
            for family in FAMILIES
        }
        snapshots.append(
            {
                "id": row.ID,
                "probability": float(p[index]),
                "region": row.region,
                "segment": row.segment,
                "earning_pattern": row.earning_pattern,
                "activity": series,
                "balance": [float(row[f"m{m}_daily_avg_bal"]) for m in range(6, 0, -1)],
            }
        )
    snapshots.sort(key=lambda r: (-r["probability"], r["id"]))
    return snapshots


def presentation_data(prepared, local, hosted, ablation, references=ROOT / "docs/reference"):
    prepared, local, hosted, ablation = map(Path, (prepared, local, hosted, ablation))
    pm = pinned(prepared / "manifest.json", references / "financial-stress-preparation-v1.json")
    lm = pinned(local / "metrics.json", references / "financial-stress-comparison-v1.json")
    hm = pinned(hosted / "manifest.json", references / "financial-stress-hosted-validation-v1.json")
    am = pinned(
        ablation / "metrics.json", references / "financial-stress-without-age-gender-v1.json"
    )
    expected = digest(prepared / "manifest.json")
    if any(m["prepared_manifest_sha256"] != expected for m in (lm, hm, am)):
        raise ValueError("model runs use different prepared data")
    if hm.get("status") != "complete" or hm.get("evidence") != "live_verified":
        raise ValueError("verified hosted result required")
    if any(m.get("final_evaluated") is not False for m in (lm, hm, am)):
        raise ValueError("validation-only evidence required")
    if am.get("excluded_features") != ["age", "gender"] or am["feature_columns"] != [
        f for f in pm["features"] if f not in ("age", "gender")
    ]:
        raise ValueError("expected age/gender exclusion comparison")
    _, _, validation = load_validation_rows(prepared)
    probabilities = checked_predictions(local, lm, validation, lm["metrics"])
    probabilities.update(checked_predictions(hosted, hm, validation, ["tabpfn_3_5_plus"]))
    checked_predictions(ablation, am, validation, am["metrics"])
    response = hosted / "response_evidence.json"
    if digest(response) != hm["response_sha256"]:
        raise ValueError("hosted response checksum mismatch")
    evidence = read(response)
    approved = read(references / "financial-stress-hosted-plan-v1.json")
    if evidence["plan_sha256"] != hm["plan_sha256"] or hm["plan_sha256"] != approved["sha256"]:
        raise ValueError("hosted plan mismatch")
    metadata = {
        k: retained_value(v) for k, v in evidence["reported_metadata"].items() if v["present"]
    }
    metadata["tabpfn_config"] = {
        k: retained_value(v) for k, v in evidence["reported_configuration"].items()
    }
    verified, _ = validate_prediction(
        approved["plan"], {"prediction": evidence["prediction"], "metadata": metadata}
    )
    if not np.array_equal(verified, probabilities["tabpfn_3_5_plus"]):
        raise ValueError("saved hosted probabilities differ from verified response")
    p = probabilities["tabpfn_3_5_plus"]
    snapshots = review_snapshots(validation, p)
    return {
        "dataset": "financial_stress",
        "classification": "external_challenge_data_origin_unverified",
        "status": "verified_validation",
        "source_manifest_sha256": expected,
        "cohorts": pm["partitions"],
        "features": len(pm["features"]),
        "metrics": {**lm["metrics"], "tabpfn_3_5_plus": hm["metrics"]},
        "snapshots": snapshots,
        "cohort_audit": cohort_audit(validation, p),
        "ablation": am["metrics"],
        "identity": hm["integration"]["checkpoint_identity"],
        "sources": {
            "prepared": expected,
            "local": digest(local / "metrics.json"),
            "hosted": digest(hosted / "manifest.json"),
            "ablation": digest(ablation / "metrics.json"),
        },
        "final_evaluated": False,
    }


def build(prepared, local, hosted, ablation, output, archive, final=None):
    if output.exists():
        raise ValueError("output directory must be new")
    data = presentation_data(prepared, local, hosted, ablation)
    if final is not None:
        final_data = pinned(
            Path(final), ROOT / "docs/reference/financial-stress-final-evaluation-v1.json"
        )
        if (
            final_data["prepared_manifest_sha256"] != data["source_manifest_sha256"]
            or final_data["status"] != "verified_final"
        ):
            raise ValueError("final evidence belongs to another experiment")
        data["final_evaluation"] = final_data
        data["sources"]["final_evaluation"] = digest(final)
    # Preserve an existing complete synthetic dashboard, including its evidence.
    archive_manifest = read(archive / "manifest.json")
    if archive_manifest.get("classification") != "synthetic":
        raise ValueError("synthetic archive required")
    for name, key in [("index.html", "html_sha256"), ("evidence.json", "evidence_sha256")]:
        if digest(archive / name) != archive_manifest[key]:
            raise ValueError("archive checksum mismatch")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".financial-ui-", dir=output.parent) as tmp:
        tmp = Path(tmp)
        write_json(tmp / "data.json", data)
        subprocess.run(
            ["node", str(ROOT / "report-ui/build.mjs"), str(tmp / "data.json"), str(tmp / "site")],
            check=True,
        )
        shutil.copytree(archive, tmp / "site/archive")
        manifest = read(tmp / "site/manifest.json")
        manifest["archive_manifest_sha256"] = digest(archive / "manifest.json")
        manifest["export_source_sha256"] = digest(Path(__file__))
        manifest["data_sources"] = data["sources"]
        write_json(tmp / "site/manifest.json", manifest)
        (tmp / "site").rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prepared", "local", "hosted", "ablation", "output", "archive"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--final", type=Path)
    args = parser.parse_args()
    build(**vars(args))
