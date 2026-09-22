import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_tabpfn_rest import response_fixture

from scuba.artifacts import file_hash, write_json
from scuba.contract import GeneratorConfig
from scuba.integrations.tabpfn_identity import PLUS_CHECKPOINT
from scuba.integrations.tabpfn_plan import TabPFNConfig, plan_digest, prepare_plan
from scuba.integrations.tabpfn_rest import IntegrationError, prediction_diagnostics
from scuba.integrations.tabpfn_revalidation import revalidate_saved
from scuba.pipeline import prepare_bundle


class RevalidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.input = Path(cls.temp.name) / "input"
        prepare_bundle(cls.input, GeneratorConfig(customers=180))
        cls.expected = file_hash(cls.input / "manifest.json")
        cls.plan, _, _ = prepare_plan(cls.input, TabPFNConfig(), cls.expected)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def source_bundle(self, directory, mutate=lambda evidence: None):
        source = Path(directory) / "source"
        source.mkdir()
        response = response_fixture(self.plan)
        response["metadata"]["tabpfn_config"]["model_path"] = PLUS_CHECKPOINT
        response["metadata"].update(
            billing_model_version="v3.5", execution_mode="standard", classes=[0, 1]
        )
        evidence = prediction_diagnostics(self.plan, response)
        evidence["checks"]["model_path"] = False  # historical strict-alias check
        mutate(evidence)
        write_json(source / "response_evidence.json", evidence)
        write_json(source / "plan.json", {"plan": self.plan, "sha256": plan_digest(self.plan)})
        manifest = {
            "status": "failed",
            "failure": {"category": "prediction_contract"},
            "mode": "prediction_only",
            "phase": "validation_only",
            "classification": "synthetic",
            "test_scored": False,
            "evidence": "offline_mock",
            "plan_sha256": plan_digest(self.plan),
            "response_evidence": {
                "path": "response_evidence.json",
                "sha256": file_hash(source / "response_evidence.json"),
            },
            "integration_attempt": {"fresh_preflight": {"plan_sha256": plan_digest(self.plan)}},
        }
        write_json(source / "manifest.json", manifest)
        return source, file_hash(source / "manifest.json")

    def test_offline_revalidation_recomputes_checks_and_preserves_source(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("socket.socket.connect", side_effect=AssertionError("network forbidden")),
            patch("scuba.integrations.tabpfn_runner.tabpfn_token") as token,
        ):
            source, digest = self.source_bundle(directory)
            before = {p.name: file_hash(p) for p in source.iterdir()}
            output = Path(directory) / "result"
            result = revalidate_saved(
                self.input, source, digest, output, expected_manifest_hash=self.expected
            )
            token.assert_not_called()
            self.assertEqual(result["evidence"], "offline_mock")
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["api_requests"], 0)
            self.assertTrue(result["checks"]["model_path"])
            self.assertFalse(result["test_scored"])
            self.assertTrue((output / "validation_predictions.csv").exists())
            self.assertEqual(before, {p.name: file_hash(p) for p in source.iterdir()})
            with self.assertRaises(FileExistsError):
                revalidate_saved(self.input, source, digest, output)

    def test_tampering_missing_identity_and_malformed_evidence_cannot_be_scored(self):
        cases = {
            "missing_identity": lambda e: e["reported_configuration"].pop("model_path"),
            "different_identity": lambda e: e["reported_configuration"]["model_path"].update(
                value="unknown.ckpt"
            ),
            "redacted": lambda e: e["reported_configuration"]["model_path"].update(
                status="redacted"
            ),
            "transformed": lambda e: e["reported_configuration"]["model_path"].update(
                transformations=["removed_query"]
            ),
            "wrong_plan": lambda e: e.update(plan_sha256="changed"),
            "bad_probability": lambda e: e.update(prediction=[[0.9, 0.9]]),
            "wrong_classes": lambda e: e["reported_metadata"]["classes"]["value"].reverse(),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                source, digest = self.source_bundle(directory, mutate)
                output = Path(directory) / "result"
                with self.assertRaises(IntegrationError):
                    revalidate_saved(
                        self.input, source, digest, output, expected_manifest_hash=self.expected
                    )
                self.assertFalse((output / "validation_predictions.csv").exists())
                self.assertNotIn("metrics", json.loads((output / "manifest.json").read_text()))
        for name in ("manifest", "response", "plan"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                source, digest = self.source_bundle(directory)
                path = (
                    source
                    / {
                        "manifest": "manifest.json",
                        "response": "response_evidence.json",
                        "plan": "plan.json",
                    }[name]
                )
                content = json.loads(path.read_text())
                if name == "plan":
                    content["plan"]["configuration"]["variant"] = "fast"
                else:
                    content["changed"] = True
                write_json(path, content)
                output = Path(directory) / "result"
                with self.assertRaises(IntegrationError):
                    revalidate_saved(
                        self.input, source, digest, output, expected_manifest_hash=self.expected
                    )
                self.assertFalse((output / "validation_predictions.csv").exists())
