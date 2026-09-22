"""Deterministic local CSV/JSON bundles shared by M1 pipeline stages."""

import csv
import json
from hashlib import sha256
from pathlib import Path


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def write_table(path: Path, rows: list[dict], schema: dict) -> dict:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(schema), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {"rows": len(rows), "sha256": file_hash(path), "schema": schema}


def source_hashes() -> dict[str, str]:
    """Record every package source file, including schema and entry-point code."""
    return {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
