"""Frozen local final evaluation with sequential fresh-process timing."""

import json
import os
import platform
import subprocess
import sys
from importlib.metadata import version
from statistics import median
from time import perf_counter

from scuba.artifacts import file_hash, write_json
from scuba.contract import ARCHETYPES
from scuba.evaluation import evaluate_cohort
from scuba.evaluation_runner import read_predictions
from scuba.final_data import ROOT, checked_final_plan, load_final_partitions


def evaluate_partitions(partitions, probabilities, replicates):
    result = {}
    for partition in ("validation", "test"):
        rows = partitions[partition]
        models = {name: p[partition] for name, p in probabilities.items()}
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
                    {name: p[indices] for name, p in models.items()},
                    replicates=replicates,
                )
        result[partition] = {
            "overall": evaluate_cohort(rows, models, replicates=replicates),
            "slices": slices,
        }
    return result


def run_final(input_dir, plan_path, plan_hash, regime, output):
    plan = checked_final_plan(input_dir, plan_path, plan_hash)
    if regime not in plan["regimes"]:
        raise ValueError("regime is not in the frozen plan")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "status": "running",
        "classification": "synthetic",
        "phase": "M4_final",
        "regime": regime,
        "plan_sha256": plan_hash,
        "test_scored": False,
        "api_requests": 0,
        "models": {},
    }
    write_json(output / "manifest.json", manifest)
    try:
        partitions, audit = load_final_partitions(input_dir, plan, regime)
        probabilities = {}
        env = os.environ.copy()
        env.update(
            PYTHONPATH=str(ROOT / "src"),
            OMP_NUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1",
            MKL_NUM_THREADS="1",
        )
        for name in plan["models"]:
            repeats = []
            for repetition in range(plan["repetitions"]):
                folder = output / name / f"repeat-{repetition + 1}"
                spec = {
                    "input": str(input_dir.resolve()),
                    "plan": str(plan_path.resolve()),
                    "plan_sha256": plan_hash,
                    "model": name,
                    "regime": regime,
                }
                spec_path = output / "worker_spec.json"
                write_json(spec_path, spec)
                start = perf_counter()
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "scuba.final_worker",
                        "--spec",
                        str(spec_path),
                        "--output",
                        str(folder),
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                wall = perf_counter() - start
                if completed.returncode:
                    raise ValueError(
                        f"fresh-process worker failed: {name}; no further repetitions executed"
                    )
                measured = json.loads((folder / "manifest.json").read_text())
                measured["timing"]["process_wall_seconds"] = wall
                if repeats and measured["predictions"] != repeats[0]["predictions"]:
                    raise ValueError("predictions changed between fresh-process repetitions")
                repeats.append(measured)
            first = output / name / "repeat-1"
            probabilities[name] = {
                partition: read_predictions(
                    first / f"{partition}_predictions.csv",
                    repeats[0]["predictions"][partition],
                    partitions[partition],
                    repeats[0]["metrics"][partition],
                )
                for partition in ("validation", "test")
            }
            manifest["models"][name] = {
                "settings": plan["models"][name],
                "repetitions": repeats,
                "prediction_replay": "byte_identical",
                "timing_summary": {
                    key: {
                        "median": median(r["timing"][key] for r in repeats),
                        "min": min(r["timing"][key] for r in repeats),
                        "max": max(r["timing"][key] for r in repeats),
                    }
                    for key in repeats[0]["timing"]
                },
            }
            write_json(output / "manifest.json", manifest)
        # Bootstrap work happens after all timing workers in this run have stopped.
        evaluation = {
            "classification": "synthetic",
            "schema": "scuba.final-evaluation/v1",
            "regime": regime,
            "generator_seed": plan["input_parameters"]["generator_seed"],
            "plan_sha256": plan_hash,
            "split_audit": audit,
            "evaluations": evaluate_partitions(
                partitions, probabilities, plan["bootstrap_replicates"]
            ),
            "hosted_evidence": "not_run_no_approved_final_prediction_budget",
        }
        write_json(output / "evaluation.json", evaluation)
        manifest.update(
            status="complete",
            test_scored=True,
            evaluation_sha256=file_hash(output / "evaluation.json"),
            input_files=plan["input_files"],
            source_sha256={
                str(p.relative_to(ROOT)): file_hash(p)
                for p in sorted((ROOT / "src/scuba").rglob("*.py"))
            },
            dependency_lock_sha256=plan["dependency_lock_sha256"],
            runtime={
                "python": platform.python_version(),
                "platform": platform.platform(),
                "logical_cpus": os.cpu_count(),
                "model_threads": 1,
            },
            dependencies={
                name: version(name)
                for name in ("numpy", "pandas", "scikit-learn", "xgboost", "catboost")
            },
            timing_protocol={
                "fresh_process_per_model_repetition": True,
                "repetitions": plan["repetitions"],
                "sequential": True,
                "test_before_validation": True,
                "cache_warmth": "fresh process; OS file cache not flushed",
                "bootstrap_outside_timing": True,
            },
        )
        write_json(output / "manifest.json", manifest)
        return manifest
    except Exception as exc:
        manifest.update(
            status="failed",
            failure_type=type(exc).__name__,
            test_scored=any(output.glob("*/repeat-*/*test_predictions.csv")),
        )
        write_json(output / "manifest.json", manifest)
        raise
