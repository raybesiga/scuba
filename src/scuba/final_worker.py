"""One fresh-process, single-thread fit and test/validation prediction repetition."""

from time import perf_counter

IMPORT_START = perf_counter()

import argparse  # noqa: E402
import json  # noqa: E402
import warnings  # noqa: E402
from pathlib import Path  # noqa: E402

from sklearn.exceptions import ConvergenceWarning  # noqa: E402

from scuba.artifacts import file_hash, write_json, write_table  # noqa: E402
from scuba.final_data import checked_final_plan, load_final_partitions  # noqa: E402
from scuba.models.common import feature_frame  # noqa: E402
from scuba.models.runner import FACTORIES, PREDICTION_SCHEMA, validation_metrics  # noqa: E402

IMPORT_SECONDS = perf_counter() - IMPORT_START


def run_worker(spec, output):
    start = perf_counter()
    input_dir = Path(spec["input"])
    plan = checked_final_plan(input_dir, Path(spec["plan"]), spec["plan_sha256"])
    partitions, _ = load_final_partitions(input_dir, plan, spec["regime"])
    load_seconds = perf_counter() - start
    frame_start = perf_counter()
    frames = {name: feature_frame(rows) for name, rows in partitions.items()}
    feature_seconds = perf_counter() - frame_start
    factories = {factory().name: factory for factory in FACTORIES}
    model = factories[spec["model"]]()
    output.mkdir(parents=True, exist_ok=False)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(frames["train"], [r["dormant_30d"] for r in partitions["train"]])
    result = {
        "classification": "synthetic",
        "model": model.name,
        "regime": spec["regime"],
        "plan_sha256": spec["plan_sha256"],
        "predictions": {},
        "metrics": {},
        "timing": {
            "imports_seconds": IMPORT_SECONDS,
            "load_verify_seconds": load_seconds,
            "feature_table_seconds": feature_seconds,
            **model.fit_times,
        },
    }
    for partition in ("test", "validation"):
        probability, timing = model.predict(frames[partition])
        result["timing"].update({f"{partition}_{k}": v for k, v in timing.items()})
        rows = partitions[partition]
        result["metrics"][partition] = validation_metrics(
            [r["dormant_30d"] for r in rows], probability
        )
        result["predictions"][partition] = write_table(
            output / f"{partition}_predictions.csv",
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
    if (
        spec["regime"] == "temporal"
        and file_hash(output / "validation_predictions.csv")
        != plan["validation_prediction_hashes"][model.name]
    ):
        raise ValueError("temporal refit failed to reproduce the frozen M2 validation predictions")
    result["timing"]["worker_body_seconds"] = perf_counter() - start
    result["status"] = "complete"
    write_json(output / "manifest.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run_worker(json.loads(args.spec.read_text()), args.output)
