"""First-principles smoke fixture; deliberately not a benchmark simulator."""

import csv
import json
import platform
import random
from dataclasses import asdict
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

from scuba import contract
from scuba.contract import (
    ARCHETYPES,
    CHANNELS,
    CUSTOMER_SCHEMA,
    EVENT_SCHEMA,
    PRODUCTS,
    REGIONS,
    SCHEMA_VERSION,
    GeneratorConfig,
)

GENERATOR_VERSION = "0.1.0"


def generate_rows(config: GeneratorConfig) -> tuple[list[dict], list[dict]]:
    """No input records, network, clock or process-global random state are used."""
    rng = random.Random(config.seed)
    customers, events = [], []
    days = (config.end_exclusive - config.start).days
    for index in range(config.customers):
        customer_id = f"SYN-C{index + 1:06d}"
        archetype = rng.choice(ARCHETYPES)
        customers.append(
            {
                "customer_id": customer_id,
                "archetype": archetype,
                "region": rng.choice(REGIONS),
                "channel": rng.choice(CHANNELS),
                "is_synthetic": "true",
            }
        )
        for day in range(days):
            progress = day / max(days - 1, 1)
            probability = {
                "steady": 0.22,
                "sporadic": 0.04,
                "tapering": 0.24 * (1 - progress) + 0.005,
            }[archetype]
            if rng.random() >= probability:
                continue
            status_draw = rng.random()
            status = (
                "failed" if status_draw < 0.10 else "reversed" if status_draw < 0.13 else "success"
            )
            events.append(
                {
                    "event_id": f"SYN-E{len(events) + 1:09d}",
                    "customer_id": customer_id,
                    "event_date": (config.start + timedelta(days=day)).isoformat(),
                    "product": rng.choice(PRODUCTS),
                    "amount_minor": rng.randint(1, 50_000),
                    "status": status,
                    "is_synthetic": "true",
                }
            )
    return customers, events


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_bundle(output: Path, config: GeneratorConfig) -> dict:
    """Create a new local bundle. Existing directories are never overwritten."""
    output = Path(output)
    customers, events = generate_rows(config)
    output.mkdir(parents=True, exist_ok=False)
    tables = (("customers.csv", customers, CUSTOMER_SCHEMA), ("events.csv", events, EVENT_SCHEMA))
    files = {}
    for name, rows, schema in tables:
        path = output / name
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(schema), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        files[name] = {"rows": len(rows), "sha256": file_hash(path), "schema": schema}
    parameters = asdict(config)
    parameters["start"] = config.start.isoformat()
    parameters["end_exclusive"] = config.end_exclusive.isoformat()
    dates = [row["event_date"] for row in events]
    manifest = {
        "classification": "synthetic",
        "purpose": "smoke_fixture",
        "generator": "scuba.generator",
        "generator_version": GENERATOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "seed": config.seed,
        "parameters": parameters,
        "coverage": {
            "start_inclusive": parameters["start"],
            "end_exclusive": parameters["end_exclusive"],
            "timezone": "UTC",
        },
        "observed_event_range": {
            "min": min(dates) if dates else None,
            "max": max(dates) if dates else None,
        },
        "source_sha256": {
            "generator.py": file_hash(Path(__file__)),
            "contract.py": file_hash(Path(contract.__file__)),
        },
        "python_version": platform.python_version(),
        "files": files,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
