import tempfile
import unittest
from pathlib import Path

from scuba.artifacts import file_hash, write_json
from scuba.radix_report import presentation_data


class RadixEvidenceGateTests(unittest.TestCase):
    def source(self, root):
        source = root / "source"
        source.mkdir()
        (source / "index.html").write_text("synthetic fixture")
        write_json(source / "report.json", {"status": "local_final_complete_hosted_pending"})
        write_json(
            source / "manifest.json",
            {
                "status": "complete",
                "classification": "synthetic",
                "html_sha256": file_hash(source / "index.html"),
                "report_sha256": file_hash(source / "report.json"),
            },
        )
        return source

    def test_changed_report_rejected_before_loading_result_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            expected = file_hash(source / "manifest.json")
            (source / "report.json").write_text('{"status":"final_complete"}')
            with self.assertRaisesRegex(ValueError, "source report changed"):
                presentation_data(source, expected, root / "absent-validation")
            with self.assertRaisesRegex(ValueError, "manifest changed"):
                presentation_data(source, "0" * 64, root / "absent-validation")

    def test_unfinished_hosted_evidence_cannot_be_presented_as_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            with self.assertRaisesRegex(ValueError, "complete hosted final comparison required"):
                presentation_data(source, file_hash(source / "manifest.json"), root / "absent")
