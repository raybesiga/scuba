import hashlib
import tempfile
import unittest
from pathlib import Path

from scuba.demo import export_evidence, verified_files


class DemoEvidenceTests(unittest.TestCase):
    def fixture(self, root):
        path = root / "artifacts/report/evaluation.json"
        path.parent.mkdir(parents=True)
        data = b'{"classification":"synthetic"}\n'
        path.write_bytes(data)
        recipe = {"files": {"artifacts/report/evaluation.json": hashlib.sha256(data).hexdigest()}}
        return path, recipe

    def test_export_is_portable_exact_and_excludes_unlisted_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, recipe = self.fixture(root)
            (root / ".env").write_text("fixture must not be copied")
            (path.parent / "unlisted.json").write_text("not part of demo")
            output = root / "bundle"
            self.assertEqual(export_evidence(root, output, recipe), 1)
            self.assertEqual(verified_files(root, recipe), verified_files(output, recipe))
            self.assertEqual(
                [str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()],
                list(recipe["files"]),
            )
            with self.assertRaisesRegex(ValueError, "must be new"):
                export_evidence(root, output, recipe)

    def test_missing_or_changed_evidence_leaves_no_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, recipe = self.fixture(root)
            path.write_text("changed")
            with self.assertRaisesRegex(ValueError, "evidence changed"):
                export_evidence(root, root / "bundle", recipe)
            path.unlink()
            with self.assertRaisesRegex(ValueError, "missing demo evidence"):
                export_evidence(root, root / "bundle", recipe)
            self.assertFalse((root / "bundle").exists())

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("../outside", "/tmp/outside", "artifacts/../../outside", ".env"):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "under artifacts"):
                    verified_files(root, {"files": {name: "0" * 64}})
            (root / "artifacts").symlink_to(root.parent, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "escapes evidence root"):
                verified_files(root, {"files": {"artifacts/outside": "0" * 64}})
