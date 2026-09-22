import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scuba.integrations.secrets import MissingToken, tabpfn_token


class SecretTests(unittest.TestCase):
    def test_explicit_file_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('TABPFN_TOKEN="fictional-file-value"\nUNRELATED=ignore\n')
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(tabpfn_token(path), "fictional-file-value")
                self.assertNotIn("TABPFN_TOKEN", os.environ)
                self.assertNotIn("UNRELATED", os.environ)
            with patch.dict(os.environ, {"TABPFN_TOKEN": "fictional-environment-value"}):
                self.assertEqual(tabpfn_token(path), "fictional-environment-value")
            with patch.dict(os.environ, {"TABPFN_TOKEN": ""}):
                with self.assertRaises(MissingToken):
                    tabpfn_token(path)

    def test_missing_and_invalid_values_do_not_leak(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / ".env"
            with self.assertRaises(MissingToken):
                tabpfn_token(path)
            path.write_text('TABPFN_TOKEN="fictional secret with spaces"\n')
            with self.assertRaises(MissingToken) as raised:
                tabpfn_token(path)
            self.assertNotIn("fictional secret", str(raised.exception))
