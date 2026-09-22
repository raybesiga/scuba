"""Offline-first entry points with explicit guards for remote model operations."""

import argparse
import json
from pathlib import Path

from scuba.contract import (
    DEFAULT_SEED,
    TEST_DATE,
    TRAIN_DATES,
    VALIDATION_DATE,
    GeneratorConfig,
    require_complete_coverage,
    snapshot_windows,
)
from scuba.generator import write_bundle
from scuba.pipeline import prepare_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SCUBA fictional data scaffold (offline)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("contract", help="validate and show the planned snapshot windows")
    generate = commands.add_parser("generate", help="write a synthetic smoke fixture")
    generate.add_argument("--output", required=True, type=Path)
    generate.add_argument("--seed", type=int, default=DEFAULT_SEED)
    generate.add_argument("--customers", type=int, default=60)
    prepare = commands.add_parser(
        "prepare", help="generate benchmark snapshots and split audit offline"
    )
    prepare.add_argument("--output", required=True, type=Path)
    prepare.add_argument("--seed", type=int, default=DEFAULT_SEED)
    prepare.add_argument("--split-seed", type=int, default=DEFAULT_SEED)
    prepare.add_argument("--customers", type=int, default=15_000)
    benchmark = commands.add_parser(
        "benchmark", help="fit local comparators; score validation only"
    )
    benchmark.add_argument("--input", required=True, type=Path)
    benchmark.add_argument("--output", required=True, type=Path)
    preflight = commands.add_parser(
        "tabpfn-preflight", help="prepare an offline plan; optionally check live limits/costs"
    )
    preflight.add_argument("--input", required=True, type=Path)
    preflight.add_argument("--output", required=True, type=Path)
    preflight.add_argument("--variant", choices=("plus", "fast", "thinking"), default="plus")
    preflight.add_argument(
        "--online", action="store_true", help="request limits/estimates only; never upload rows"
    )
    preflight.add_argument("--env-file", type=Path, default=Path(".env"))
    remote = commands.add_parser(
        "tabpfn-run", help="execute an explicitly approved validation upload and run"
    )
    remote.add_argument("--input", required=True, type=Path)
    remote.add_argument("--plan", required=True, type=Path)
    remote.add_argument("--output", required=True, type=Path)
    remote.add_argument("--allow-upload", action="store_true")
    remote.add_argument(
        "--max-estimated-tokens",
        type=int,
        required=True,
        help="approved estimate ceiling; actual charges can differ",
    )
    remote.add_argument("--env-file", type=Path, default=Path(".env"))
    continuation = commands.add_parser(
        "tabpfn-continue", help="review offline; optionally predict once with saved resources"
    )
    continuation.add_argument("--input", required=True, type=Path)
    continuation.add_argument("--prior-run", required=True, type=Path)
    continuation.add_argument("--source-manifest-sha256", required=True)
    continuation.add_argument("--output", required=True, type=Path)
    continuation.add_argument("--allow-predict", action="store_true")
    continuation.add_argument("--max-estimated-tokens", type=int)
    continuation.add_argument("--env-file", type=Path, default=Path(".env"))
    evaluate = commands.add_parser(
        "evaluate", help="evaluate pinned saved validation predictions offline"
    )
    evaluate.add_argument("--input", required=True, type=Path)
    evaluate.add_argument("--local-run", required=True, type=Path)
    evaluate.add_argument("--local-manifest-sha256", required=True)
    evaluate.add_argument("--hosted-run", type=Path)
    evaluate.add_argument("--hosted-manifest-sha256")
    evaluate.add_argument("--output", required=True, type=Path)
    final_plan = commands.add_parser(
        "final-plan", help="freeze local final-evaluation settings before test scoring"
    )
    final_plan.add_argument("--input", required=True, type=Path)
    final_plan.add_argument("--local-run", required=True, type=Path)
    final_plan.add_argument("--local-manifest-sha256", required=True)
    final_plan.add_argument("--output", required=True, type=Path)
    final_run = commands.add_parser(
        "final-run", help="run frozen final local evaluation in fresh processes"
    )
    final_run.add_argument("--input", required=True, type=Path)
    final_run.add_argument("--plan", required=True, type=Path)
    final_run.add_argument("--plan-sha256", required=True)
    final_run.add_argument("--regime", choices=("temporal", "random_reference"), required=True)
    final_run.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "contract":
        config = GeneratorConfig()
        schedule = {"train": TRAIN_DATES, "validation": (VALIDATION_DATE,), "test": (TEST_DATE,)}
        windows = {}
        for partition, dates in schedule.items():
            windows[partition] = {}
            for prediction_date in dates:
                require_complete_coverage(prediction_date, config)
                windows[partition][prediction_date.isoformat()] = snapshot_windows(prediction_date)
        print(
            json.dumps({"status": "planned_experiment", "windows": windows}, default=str, indent=2)
        )
        return 0
    try:
        if args.command in ("final-plan", "final-run"):
            from scuba.final_data import digest, prepare_final_plan
            from scuba.final_runner import run_final

            if args.command == "final-plan":
                plan = prepare_final_plan(
                    args.input, args.local_run, args.local_manifest_sha256, args.output
                )
                result = {"status": "frozen", "plan_sha256": digest(plan)}
            else:
                run_final(args.input, args.plan, args.plan_sha256, args.regime, args.output)
                result = {"status": "complete", "regime": args.regime}
            print(json.dumps({**result, "output": str(args.output)}))
            return 0
        if args.command == "evaluate":
            try:
                from scuba.evaluation_runner import evaluate_saved
            except ImportError:
                parser.exit(
                    2,
                    "scuba: install evaluation dependencies with uv sync --locked --extra models\n",
                )

            result = evaluate_saved(
                args.input,
                args.local_run,
                args.local_manifest_sha256,
                args.output,
                hosted_run=args.hosted_run,
                hosted_hash=args.hosted_manifest_sha256,
            )
            print(
                json.dumps(
                    {
                        "status": "complete",
                        "partition": "validation",
                        "output": str(args.output),
                        "models": list(result["overall"]["models"]),
                    }
                )
            )
            return 0
        if args.command in ("tabpfn-preflight", "tabpfn-run", "tabpfn-continue"):
            try:
                from scuba.integrations.tabpfn_plan import TabPFNConfig
                from scuba.integrations.tabpfn_rest import IntegrationError
                from scuba.integrations.tabpfn_runner import (
                    continue_prediction,
                    preflight_bundle,
                    run_approved,
                )
            except ImportError:
                parser.exit(
                    2,
                    "scuba: install integration dependencies with uv sync --locked --extra models --extra tabpfn\n",
                )
            try:
                if args.command == "tabpfn-preflight":
                    result = preflight_bundle(
                        args.input,
                        args.output,
                        TabPFNConfig(args.variant),
                        online=args.online,
                        env_file=args.env_file,
                    )
                elif args.command == "tabpfn-continue":
                    result = continue_prediction(
                        args.input,
                        args.prior_run,
                        args.source_manifest_sha256,
                        args.output,
                        allow_predict=args.allow_predict,
                        max_tokens=args.max_estimated_tokens,
                        env_file=args.env_file,
                    )
                else:
                    result = run_approved(
                        args.input,
                        args.plan,
                        args.output,
                        allow_upload=args.allow_upload,
                        max_tokens=args.max_estimated_tokens,
                        env_file=args.env_file,
                    )
            except IntegrationError as exc:
                parser.exit(2, f"scuba: {exc}; see the local manifest when present.\n")
            print(
                json.dumps(
                    {
                        "status": result["status"],
                        "evidence": result["evidence"],
                        "output": str(args.output),
                        "plan_sha256": result["plan_sha256"],
                    },
                    indent=2,
                )
            )
            return 0
        if args.command == "benchmark":
            try:
                from scuba.models.runner import run_comparators
            except ImportError as exc:
                parser.exit(
                    2,
                    f"scuba: model dependencies unavailable; run uv sync --locked --extra models ({exc.name})\n",
                )
            result = run_comparators(args.input, args.output)
            print(
                json.dumps(
                    {
                        "classification": "synthetic",
                        "status": result["status"],
                        "phase": result["phase"],
                        "output": str(args.output),
                        "models": {
                            name: model["metrics"] for name, model in result["models"].items()
                        },
                    },
                    indent=2,
                )
            )
            return 0
        if args.command == "prepare":
            audit = prepare_bundle(
                args.output,
                GeneratorConfig(seed=args.seed, customers=args.customers),
                args.split_seed,
            )
            print(
                json.dumps(
                    {
                        "classification": "synthetic",
                        "output": str(args.output),
                        "eligible_rows": audit["eligible"]["rows"],
                        "main_support_passed": audit["main_support_passed"],
                        "support_failures": audit["support_failures"],
                    },
                    indent=2,
                )
            )
            return 0 if audit["main_support_passed"] else 1
        manifest = write_bundle(
            args.output, GeneratorConfig(seed=args.seed, customers=args.customers)
        )
    except (ValueError, OSError) as exc:
        parser.exit(2, f"scuba: {exc}\n")
    print(
        json.dumps(
            {
                "classification": manifest["classification"],
                "purpose": manifest["purpose"],
                "output": str(args.output),
                "rows": {name: info["rows"] for name, info in manifest["files"].items()},
            },
            indent=2,
        )
    )
    return 0
