"""Portable export allowlist and tamper checks, using invented artifacts."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scuba.financial_demo import FILES, export, rebuild
from scuba.financial_stress import digest, write_json


class PortableFinancialDemoTests(unittest.TestCase):
    def test_export_omits_unlisted_files_and_rebuild_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            for directory, names in FILES.items():
                (source / directory).mkdir(parents=True)
                for name in names:
                    (source / directory / name).write_text("invented fixture")
            (source / ".env").write_text("fixture credential excluded")
            archive = root / "archive"
            archive.mkdir()
            for name in ("index.html", "evidence.json"):
                (archive / name).write_text("invented archive")
            write_json(
                archive / "manifest.json",
                {
                    "html_sha256": digest(archive / "index.html"),
                    "evidence_sha256": digest(archive / "evidence.json"),
                },
            )
            attribution = root / "attribution.md"
            attribution.write_text("invented attribution")
            with patch("scuba.financial_demo.verify_sources"):
                export(source, archive, attribution, root / "export")
                self.assertFalse((root / "export/.env").exists())
                with patch("scuba.financial_demo.build") as builder:
                    rebuild(root / "export", root / "site")
                    builder.assert_called_once()
                target = root / "export/prepared-v1/train.csv"
                target.write_text("changed")
                with self.assertRaisesRegex(ValueError, "checksum"):
                    rebuild(root / "export", root / "bad")
                m = json.loads((root / "export/bundle.json").read_text())
                m["files"]["../outside"] = "hash"
                write_json(root / "export/bundle.json", m)
                with self.assertRaisesRegex(ValueError, "contents"):
                    rebuild(root / "export", root / "escape")
