"""Verify and restore explicitly supplied source packages offline, without executing them."""

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


def _path(root: Path, name: str) -> Path:
    relative = Path(name)
    if not name or relative.is_absolute() or ".." in relative.parts or "\\" in name:
        raise ValueError("unsafe bundle path")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()) or path.resolve() == root.resolve():
        raise ValueError("unsafe bundle path")
    return path


def _copy_checked(stream, record: dict, output=None) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while block := stream.read(1024 * 1024):
        size += len(block)
        digest.update(block)
        if output is not None:
            output.write(block)
    actual = digest.hexdigest()
    if size != record["bytes"] or actual != record["sha256"]:
        raise ValueError("source integrity mismatch")
    return actual, size


def _read_manifest(bundle: Path) -> dict:
    manifest = json.loads((bundle / "manifest.json").read_text())
    if manifest.get("schema_version") != 1 or not manifest.get("files"):
        raise ValueError("unsupported or empty source manifest")
    names = set()
    for record in manifest["files"]:
        _path(bundle, record["name"])
        if record["name"] in names:
            raise ValueError("duplicate output name")
        names.add(record["name"])
        if not record["parts"]:
            raise ValueError("source has no parts")
        for part in record["parts"]:
            _path(bundle, part["path"])
        for member in record.get("extract", []):
            name = member["name"]
            _path(bundle, name)
            if name in names:
                raise ValueError("duplicate output name")
            names.add(name)
    return manifest


def _assemble(bundle: Path, record: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as output:
        for part in record["parts"]:
            with _path(bundle, part["path"]).open("rb") as source:
                _copy_checked(source, part, output)
    with destination.open("rb") as source:
        _copy_checked(source, record)


def verify_bundle(bundle: Path) -> int:
    """Check each part and its reconstructed original; leave no reconstructed files."""
    bundle = Path(bundle)
    manifest = _read_manifest(bundle)
    with tempfile.TemporaryDirectory(prefix="scuba-source-verify-") as directory:
        for record in manifest["files"]:
            destination = _path(Path(directory), record["name"])
            _assemble(bundle, record, destination)
            if record.get("extract"):
                with zipfile.ZipFile(destination) as archive:
                    for member in record["extract"]:
                        with archive.open(member["name"]) as stream:
                            _copy_checked(stream, member)
    return len(manifest["files"])


def restore_bundle(bundle: Path, output: Path) -> int:
    """Publish a new local directory only after all originals and members verify."""
    bundle, output = Path(bundle), Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("output must be new")
    manifest = _read_manifest(bundle)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".source-restore-", dir=output.parent) as directory:
        staging = Path(directory) / "ready"
        staging.mkdir()
        for record in manifest["files"]:
            destination = _path(staging, record["name"])
            _assemble(bundle, record, destination)
            if record.get("extract"):
                with zipfile.ZipFile(destination) as archive:
                    for member in record["extract"]:
                        target = _path(staging, member["name"])
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(member["name"]) as source, target.open("xb") as sink:
                            _copy_checked(source, member, sink)
        shutil.copyfile(bundle / "manifest.json", staging / "source_manifest.json")
        if output.exists() or output.is_symlink():
            raise ValueError("output must be new")
        staging.rename(output)
    return len(manifest["files"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=Path("datasets/nedbank"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        count = (
            verify_bundle(args.bundle) if args.verify else restore_bundle(args.bundle, args.output)
        )
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Source bundle verification failed ({type(error).__name__}).\n")
    print(
        f"Verified {count} original source files"
        + ("." if args.verify else " and restored bundle.")
    )


if __name__ == "__main__":
    main()
