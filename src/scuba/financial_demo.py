"""Export and rebuild the frozen Financial Stress demo from portable local evidence."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from scuba.financial_dashboard import build, presentation_data
from scuba.financial_final_evaluation import verify
from scuba.financial_stress import digest, new_output, write_json

FILES = {
    "prepared-v1": ["manifest.json", "train.csv", "validation.csv", "final.csv", "membership.csv"],
    "comparison-verified-v1": ["metrics.json", "validation_predictions.csv"],
    "hosted-validation-v1": [
        "manifest.json",
        "validation_predictions.csv",
        "response_evidence.json",
    ],
    "without-age-gender-v1": ["metrics.json", "validation_predictions.csv"],
    "final-freeze-v1": ["protocol.json"],
    "final-local-v1": ["metrics.json", "final_predictions.csv"],
    "final-hosted-v1": ["manifest.json", "final_predictions.csv", "response_evidence.json"],
    "final-live-review-v1": ["plan.json", "manifest.json"],
    "final-verified-v1": ["evaluation.json"],
}


def paths(root):
    root = Path(root)
    return dict(
        prepared=root / "prepared-v1",
        local=root / "comparison-verified-v1",
        hosted=root / "hosted-validation-v1",
        ablation=root / "without-age-gender-v1",
    )


def verify_sources(root):
    root = Path(root)
    presentation_data(**paths(root))
    with tempfile.TemporaryDirectory(prefix="scuba-final-recheck-") as tmp:
        result = verify(
            root / "prepared-v1",
            root / "final-freeze-v1/protocol.json",
            root / "final-local-v1",
            root / "final-hosted-v1",
            root / "final-live-review-v1/plan.json",
            Path(tmp) / "verified",
        )
    if result != json.loads((root / "final-verified-v1/evaluation.json").read_text()):
        raise ValueError("final evaluation summary mismatch")
    manifest = json.loads((root / "prepared-v1/manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if digest(root / "prepared-v1" / name) != expected:
            raise ValueError("prepared artifact changed")


def export(root, archive, attribution, output):
    root, archive, attribution = map(Path, (root, archive, attribution))
    verify_sources(root)
    am = json.loads((archive / "manifest.json").read_text())
    for name, key in (("index.html", "html_sha256"), ("evidence.json", "evidence_sha256")):
        if digest(archive / name) != am[key]:
            raise ValueError("archive artifact changed")
    with new_output(output) as out:
        records = {}
        for directory, names in {
            **FILES,
            "archive": ["index.html", "manifest.json", "evidence.json"],
        }.items():
            source = archive if directory == "archive" else root / directory
            (out / directory).mkdir()
            for name in names:
                target = out / directory / name
                shutil.copyfile(source / name, target)
                records[f"{directory}/{name}"] = digest(target)
        shutil.copyfile(attribution, out / "DATA_ATTRIBUTION.md")
        records["DATA_ATTRIBUTION.md"] = digest(out / "DATA_ATTRIBUTION.md")
        write_json(
            out / "bundle.json",
            {
                "version": "scuba.financial-demo/v1",
                "classification": "external_challenge_data_origin_unverified",
                "files": records,
                "contains_credentials": False,
                "publication_status": "local_draft_not_published",
            },
        )


def rebuild(evidence, output):
    evidence = Path(evidence)
    manifest = json.loads((evidence / "bundle.json").read_text())
    expected = {f"{directory}/{name}" for directory, names in FILES.items() for name in names}
    expected |= {
        "archive/index.html",
        "archive/manifest.json",
        "archive/evidence.json",
        "DATA_ATTRIBUTION.md",
    }
    if manifest.get("version") != "scuba.financial-demo/v1" or set(manifest["files"]) != expected:
        raise ValueError("unexpected evidence bundle contents")
    for name, value in manifest["files"].items():
        path = evidence / name
        if not path.resolve().is_relative_to(evidence.resolve()) or digest(path) != value:
            raise ValueError("evidence checksum or path mismatch")
    verify_sources(evidence)
    build(
        **paths(evidence),
        output=Path(output),
        archive=evidence / "archive",
        final=evidence / "final-verified-v1/evaluation.json",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    exp = sub.add_parser("export")
    for name in ("root", "archive", "attribution", "output"):
        exp.add_argument("--" + name, type=Path, required=True)
    rep = sub.add_parser("build")
    for name in ("evidence", "output"):
        rep.add_argument("--" + name, type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    (export if command == "export" else rebuild)(**args)
    print(json.dumps({"status": "complete", "command": command}))
