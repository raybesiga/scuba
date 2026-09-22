"""Compare actual emitted JSON to frozen public REST/SDK contract observations."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from test_tabpfn_rest import FakeService

from scuba.artifacts import file_hash
from scuba.contract import GeneratorConfig
from scuba.integrations.tabpfn_plan import TabPFNConfig, prepare_plan
from scuba.integrations.tabpfn_rest import TabPFNRest
from scuba.pipeline import prepare_bundle

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/tabpfn_contracts_2026_09_20.json").read_text()
)


def conforms_to_fields(body, schema):
    """Field audit only: not a substitute for vendor/runtime schema validation."""
    return set(schema["required"]) <= body.keys() <= set(schema["properties"])


class RequestContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / "input"
        prepare_bundle(cls.root, GeneratorConfig(customers=180))
        cls.expected = file_hash(cls.root / "manifest.json")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_wire_requests_match_rest_and_document_sdk_fit_discrepancy(self):
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            for variant in ("plus", "fast", "thinking"):
                with self.subTest(variant=variant):
                    plan, payloads, _ = prepare_plan(
                        self.root, TabPFNConfig(variant), self.expected
                    )
                    service = FakeService(plan)
                    client = TabPFNRest("fictional-token", transport=httpx.MockTransport(service))
                    try:
                        client.execute(plan, payloads, allow_upload=True, max_tokens=20000)
                    finally:
                        client.close()
                    sent = {
                        request.url.path: json.loads(request.content)
                        for request in service.requests
                        if request.url.path in ("/tabpfn/fit", "/tabpfn/predict")
                    }
                    reference = FIXTURE["requests"][variant]
                    fit, predict = sent["/tabpfn/fit"], sent["/tabpfn/predict"]
                    self.assertEqual(fit, reference["rest_fit"])
                    self.assertEqual(predict, reference["rest_and_sdk_predict"])
                    schemas = FIXTURE["schemas"]
                    self.assertTrue(conforms_to_fields(fit, schemas["rest"]["FitRequest"]))
                    self.assertFalse(conforms_to_fields(fit, schemas["sdk"]["FitRequest"]))
                    self.assertTrue(
                        conforms_to_fields(reference["sdk_fit"], schemas["sdk"]["FitRequest"])
                    )
                    for source in ("rest", "sdk"):
                        self.assertTrue(
                            conforms_to_fields(predict, schemas[source]["PredictRequest"])
                        )
                        task = predict["task_config"]
                        self.assertTrue(
                            conforms_to_fields(task, schemas[source]["ClassifierConfig"])
                        )
                        self.assertTrue(
                            conforms_to_fields(
                                task["tabpfn_config"], schemas[source]["ClassifierTabPFNConfig"]
                            )
                        )
                    # Compare meaning after documenting the distinct envelopes.
                    sdk_task = reference["sdk_fit"]["task_config"]
                    self.assertEqual(fit["task"], sdk_task["task"])
                    self.assertEqual(fit["tabpfn_config"], sdk_task["tabpfn_config"])
                    self.assertEqual(fit["tabpfn_systems"], reference["sdk_fit"]["tabpfn_systems"])
                    if variant == "thinking":
                        thinking = reference["sdk_fit"]["thinking_config"]
                        self.assertEqual(fit["thinking_effort"], thinking["effort"])
                        self.assertEqual(fit["thinking_timeout_s"], thinking["timeout_secs"])
                        self.assertEqual(fit["thinking_effort_metric"], thinking["metric"])

    def test_field_audit_rejects_silent_envelope_changes_and_missing_ids(self):
        original = FIXTURE["requests"]["plus"]["rest_fit"]
        schema = FIXTURE["schemas"]["rest"]["FitRequest"]
        for field in ("train_set_upload_id", "task"):
            changed = copy.deepcopy(original)
            del changed[field]
            self.assertFalse(conforms_to_fields(changed, schema))
        self.assertFalse(conforms_to_fields(FIXTURE["requests"]["plus"]["sdk_fit"], schema))
