"""Rebuild the verified report as a self-contained local Radix presentation."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from scuba.artifacts import file_hash, write_json
from scuba.final_report import build_report

ROOT = Path(__file__).resolve().parents[2]


def presentation_data(source, expected_hash, validation_run):
    if file_hash(source / "manifest.json") != expected_hash:
        raise ValueError("source report manifest changed")
    manifest = json.loads((source / "manifest.json").read_text())
    if (
        manifest.get("status") != "complete"
        or manifest.get("classification") != "synthetic"
        or file_hash(source / "report.json") != manifest["report_sha256"]
        or file_hash(source / "index.html") != manifest["html_sha256"]
    ):
        raise ValueError("source report changed or incomplete")
    summary = json.loads((source / "report.json").read_text())
    if summary.get("status") != "final_complete" or not summary.get("hosted_final_source"):
        raise ValueError("complete hosted final comparison required")
    refs = [(Path(s["run"]), s["manifest_sha256"]) for s in summary["sources"]]
    hosted = summary["hosted_final_source"]
    # Reuse the existing evidence gate before changing presentation technology.
    with tempfile.TemporaryDirectory() as directory:
        build_report(
            refs,
            (validation_run, summary["validation_source_manifest_sha256"]),
            Path(directory) / "checked",
            hosted_ref=(Path(hosted["run"]), hosted["manifest_sha256"]),
        )
    return {
        "classification": "synthetic",
        "source_manifest_sha256": expected_hash,
        "sources": summary,
        "validation": json.loads((validation_run / "evaluation.json").read_text()),
        "hosted": json.loads((Path(hosted["run"]) / "evaluation.json").read_text()),
        "runs": [
            {
                "evaluation": json.loads((folder / "evaluation.json").read_text()),
                "manifest": json.loads((folder / "manifest.json").read_text()),
            }
            for folder, _ in refs
        ],
    }


def build_radix_report(source, expected_hash, validation_run, output):
    data = presentation_data(source, expected_hash, validation_run)
    if output.exists():
        raise ValueError("output directory must be new")
    with tempfile.TemporaryDirectory() as directory:
        payload = Path(directory) / "data.json"
        write_json(payload, data)
        subprocess.run(
            ["node", str(ROOT / "report-ui/build.mjs"), str(payload), str(output.resolve())],
            check=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--validation-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_radix_report(args.source, args.manifest_sha256, args.validation_run, args.output)
