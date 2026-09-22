import copy
import unittest

from scuba.integrations.tabpfn_identity import IDENTITY_POLICY, PLUS_CHECKPOINT
from scuba.integrations.tabpfn_plan import TabPFNConfig
from scuba.integrations.tabpfn_rest import (
    IntegrationError,
    prediction_diagnostics,
    validate_prediction,
)


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "configuration": {"variant": "plus"},
            "cohorts": {"validation": {"rows": 2}},
            "feature_columns": ["fictional_feature"],
            "class_order": [0, 1],
        }
        self.response = {
            "prediction": [[0.8, 0.2], [0.3, 0.7]],
            "metadata": {
                "test_set_num_rows": 2,
                "test_set_num_cols": 1,
                "task": "classification",
                "package_version": "8.5.0",
                "billing_model_version": "v3.5",
                "execution_mode": "standard",
                "classes": [0, 1],
                "tabpfn_config": {
                    **TabPFNConfig().model_parameters(),
                    "model_path": PLUS_CHECKPOINT,
                },
            },
        }

    def test_exact_documented_checkpoint_and_supporting_metadata_are_accepted(self):
        probability, metadata = validate_prediction(self.plan, self.response)
        self.assertEqual(probability.tolist(), [0.2, 0.7])
        self.assertEqual(metadata["identity_validation"]["policy"], IDENTITY_POLICY)
        self.assertEqual(metadata["identity_validation"]["reported_model_path"], PLUS_CHECKPOINT)
        self.assertTrue(all(prediction_diagnostics(self.plan, self.response)["checks"].values()))

    def test_similar_paths_versions_and_missing_evidence_are_rejected(self):
        cases = [
            ("model_path", PLUS_CHECKPOINT.replace("20260909", "20260910")),
            ("model_path", PLUS_CHECKPOINT.replace("v3.5-", "v3.5-fast-")),
            ("model_path", PLUS_CHECKPOINT.replace(".safetensors", "_multiclass.safetensors")),
            ("model_path", PLUS_CHECKPOINT + "?extra=1"),
            ("model_path", PLUS_CHECKPOINT.replace("/app/", "/elsewhere/")),
            ("model_path", [PLUS_CHECKPOINT]),
            ("billing_model_version", "v3.5-fast"),
            ("execution_mode", "thinking"),
            ("classes", [1, 0]),
            ("classes", [False, True]),
            ("classes", ["0", "1"]),
            ("n_estimators", 4),
            ("random_state", 7),
            ("fit_mode", "low_memory"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                bad = copy.deepcopy(self.response)
                target = bad["metadata"]
                if key in TabPFNConfig().model_parameters():
                    target = target["tabpfn_config"]
                target[key] = value
                with self.assertRaises(IntegrationError):
                    validate_prediction(self.plan, bad)
        for field in ("classes", "billing_model_version", "execution_mode"):
            bad = copy.deepcopy(self.response)
            del bad["metadata"][field]
            with self.assertRaises(IntegrationError):
                validate_prediction(self.plan, bad)
        for variant in ("fast", "thinking"):
            plan = copy.deepcopy(self.plan)
            plan["configuration"]["variant"] = variant
            with self.assertRaises(IntegrationError):
                validate_prediction(plan, self.response)

    def test_returned_class_order_is_checked_even_when_alias_matches(self):
        self.response["metadata"]["tabpfn_config"]["model_path"] = "v3.5_default"
        self.response["metadata"]["classes"] = [1, 0]
        with self.assertRaises(IntegrationError):
            validate_prediction(self.plan, self.response)
        self.assertFalse(prediction_diagnostics(self.plan, self.response)["checks"]["class_order"])
