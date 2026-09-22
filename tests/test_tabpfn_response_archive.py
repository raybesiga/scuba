import json
import stat
import tempfile
import unittest
from pathlib import Path

import httpx

from scuba.integrations.tabpfn_response_archive import ARCHIVE_NAME, archive_response


class ResponseArchiveTests(unittest.TestCase):
    def test_all_fields_and_long_nested_arrays_survive_without_preview_limits(self):
        body = {
            "metadata": {"feature_names": [f"feature_{i}" for i in range(184)]},
            "timings": {"predict_s": 4.2},
            "unexpected": {"nested": {"values": list(range(200))}},
            "description": "An unfamiliar server explanation " * 200,
        }
        with tempfile.TemporaryDirectory() as directory:
            receipt = archive_response(directory, httpx.Response(200, json=body))
            path = Path(directory) / ARCHIVE_NAME
            saved = json.loads(path.read_text())
            self.assertEqual(saved["body"], body)
            self.assertEqual(saved["redactions"], 0)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(receipt["path"], ARCHIVE_NAME)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                archive_response(directory, httpx.Response(200, json={}))
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_nested_credentials_are_redacted_without_removing_schema_or_counts(self):
        body = {
            "metadata": {
                "feature_names": ["balance", "activity"],
                "token_count": 120,
                "Api-Key": "unknown-private-key",
                "nested": [{"refresh_token": "private-refresh"}],
            },
            "details": "An echo: fictional-token and Bearer unknown-bearer-value",
            "url": "https://user:pass@example.invalid/result?signature=private-signature#private-fragment",
        }
        with tempfile.TemporaryDirectory() as directory:
            archive_response(
                directory, httpx.Response(200, json=body), secrets=("fictional-token",)
            )
            text = (Path(directory) / ARCHIVE_NAME).read_text()
            for secret in (
                "unknown-private-key",
                "private-refresh",
                "fictional-token",
                "unknown-bearer-value",
                "user:pass",
                "private-signature",
                "private-fragment",
            ):
                self.assertNotIn(secret, text)
            saved = json.loads(text)
            self.assertEqual(saved["body"]["metadata"]["token_count"], 120)
            self.assertEqual(saved["body"]["metadata"]["feature_names"], ["balance", "activity"])
            self.assertGreater(saved["redactions"], 0)

    def test_non_json_error_body_remains_available_and_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = archive_response(
                directory,
                httpx.Response(502, text="Incomplete response: fictional-token; password=hidden"),
                secrets=("fictional-token",),
            )
            saved = json.loads((Path(directory) / ARCHIVE_NAME).read_text())
            self.assertEqual(receipt["http_status"], 502)
            self.assertEqual(saved["body_format"], "text")
            self.assertIn("Incomplete response", saved["body"])
            self.assertNotIn("fictional-token", saved["body"])
            self.assertNotIn("hidden", saved["body"])
