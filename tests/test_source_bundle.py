import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scuba.source_bundle import restore_bundle, verify_bundle


def metadata(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class SourceBundleTests(unittest.TestCase):
    def fixture(self, root):
        bundle = root / "bundle"
        bundle.mkdir()
        payload = b"inert test source, not customer data\n"
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("source.parquet", payload)
            archive.writestr("__MACOSX/._source.parquet", b"ignored metadata")
        original = stream.getvalue()
        parts = [original[:50], original[50:]]
        records = []
        for i, part in enumerate(parts):
            name = f"part-{i}"
            (bundle / name).write_bytes(part)
            records.append({"path": name, **metadata(part)})
        manifest = {
            "schema_version": 1,
            "files": [
                {
                    "name": "source.zip",
                    **metadata(original),
                    "parts": records,
                    "extract": [{"name": "source.parquet", **metadata(payload)}],
                }
            ],
        }
        self.save(bundle, manifest)
        return bundle, manifest, original, payload

    def save(self, bundle, manifest):
        (bundle / "manifest.json").write_text(json.dumps(manifest))

    def test_restores_exact_original_and_only_declared_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, _, original, payload = self.fixture(root)
            self.assertEqual(verify_bundle(bundle), 1)
            output = root / "restored"
            self.assertEqual(restore_bundle(bundle, output), 1)
            self.assertEqual((output / "source.zip").read_bytes(), original)
            self.assertEqual((output / "source.parquet").read_bytes(), payload)
            self.assertEqual(
                {p.name for p in output.iterdir()},
                {"source.zip", "source.parquet", "source_manifest.json"},
            )
            with self.assertRaisesRegex(ValueError, "must be new"):
                restore_bundle(bundle, output)

    def test_corruption_at_each_layer_leaves_no_output(self):
        for layer in ("part", "original", "member", "missing"):
            with self.subTest(layer=layer), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                bundle, manifest, _, _ = self.fixture(root)
                record = manifest["files"][0]
                if layer == "part":
                    (bundle / "part-0").write_bytes(b"corrupt")
                elif layer == "missing":
                    (bundle / "part-0").unlink()
                elif layer == "original":
                    record["sha256"] = "0" * 64
                else:
                    record["extract"][0]["sha256"] = "0" * 64
                self.save(bundle, manifest)
                with self.assertRaises((ValueError, FileNotFoundError)):
                    restore_bundle(bundle, root / "output")
                self.assertFalse((root / "output").exists())
                self.assertEqual({p.name for p in root.iterdir()}, {"bundle"})

    def test_path_escape_and_duplicate_names_rejected(self):
        for location in ("name", "part", "member", "duplicate", "symlink"):
            with self.subTest(location=location), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                bundle, manifest, _, _ = self.fixture(root)
                record = manifest["files"][0]
                if location == "name":
                    record["name"] = "../escaped.zip"
                elif location == "part":
                    record["parts"][0]["path"] = "../outside"
                elif location == "member":
                    record["extract"][0]["name"] = "../escaped.parquet"
                elif location == "duplicate":
                    manifest["files"].append(record.copy())
                else:
                    (bundle / "part-0").unlink()
                    (bundle / "part-0").symlink_to(root / "outside")
                self.save(bundle, manifest)
                with self.assertRaises(ValueError):
                    restore_bundle(bundle, root / "output")
                self.assertFalse((root / "output").exists())
