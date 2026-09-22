import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scuba.cli import main


class CliTests(unittest.TestCase):
    def test_contract_is_explicitly_planned(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["contract"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "planned_experiment")
        self.assertEqual(set(result["windows"]), {"train", "validation", "test"})

    def test_generate_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            capture = io.StringIO()
            with redirect_stdout(capture):
                self.assertEqual(main(["generate", "--output", str(output), "--customers", "2"]), 0)
            self.assertEqual(json.loads(capture.getvalue())["rows"]["customers.csv"], 2)
            self.assertTrue((output / "manifest.json").is_file())
            invalid = Path(directory) / "invalid"
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(["generate", "--output", str(invalid), "--customers", "0"])
            self.assertEqual(caught.exception.code, 2)
            self.assertFalse(invalid.exists())
