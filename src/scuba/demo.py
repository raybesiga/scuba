"""Build the frozen demo or export its allowlisted evidence, entirely offline."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECIPE = ROOT / "docs/demo-inputs.json"


def verified_files(evidence_root, recipe):
    """Read only pinned report inputs; reject missing, changed or escaping paths."""
    root = evidence_root.resolve()
    result = {}
    for name, expected in recipe["files"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or relative.parts[0] != "artifacts":
            raise ValueError("demo evidence path must remain under artifacts")
        path = root / relative
        if not path.resolve().is_relative_to(root):
            raise ValueError("demo evidence path escapes evidence root")
        if not path.is_file():
            raise ValueError(f"missing demo evidence: {name}; restore the saved evidence bundle")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"demo evidence changed: {name}")
        result[name] = data
    return result


def export_evidence(evidence_root, output, recipe):
    if output.exists():
        raise ValueError("output directory must be new")
    files = verified_files(evidence_root, recipe)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return len(files)


def build_demo(evidence_root, output, recipe):
    if output.exists():
        raise ValueError("output directory must be new")
    verified_files(evidence_root, recipe)
    # Run with the evidence bundle as cwd so historical relative references retain
    # their original meaning. The implementation and UI come from this checkout.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scuba.radix_report",
            "--source",
            recipe["source"],
            "--manifest-sha256",
            recipe["source_manifest_sha256"],
            "--validation-run",
            recipe["validation_run"],
            "--output",
            str(output.resolve()),
        ],
        cwd=evidence_root.resolve(),
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "export-evidence"))
    parser.add_argument("--evidence-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    recipe = json.loads(RECIPE.read_text())
    try:
        if args.action == "build":
            build_demo(args.evidence_root, args.output, recipe)
        else:
            count = export_evidence(args.evidence_root, args.output, recipe)
            print(json.dumps({"status": "complete", "evidence_files": count}))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Demo failed: {error}\n")


if __name__ == "__main__":
    main()
