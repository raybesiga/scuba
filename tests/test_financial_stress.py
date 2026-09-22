"""Invented fixtures only: partition, leakage and evidence-boundary checks."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from scuba.financial_stress import (
    TARGET,
    baseline,
    digest,
    make_pipeline,
    prepare,
    split_rows,
    validate_tables,
)


def fixture():
    def rows(start, count):
        return pd.DataFrame(
            {
                "ID": [f"FIXTURE-{i:04d}" for i in range(start, start + count)],
                "amount": np.arange(start, start + count, dtype=float),
                "category": ["invented-a" if i % 3 else "invented-b" for i in range(count)],
            }
        )

    train = rows(0, 200)
    train[TARGET] = [int(i % 5 == 0) for i in range(200)]
    test = rows(1000, 40)
    dictionary = pd.DataFrame(
        {
            "column_name": ["ID", "amount", "category", TARGET],
            "data_type": ["string", "float64", "object", "int64"],
        }
    )
    submission = test[["ID"]].assign(Target=0.0)
    return train, test, dictionary, submission


def source_bundle(root):
    source = root / "source"
    files = source / "files"
    files.mkdir(parents=True)
    names = ["Train.csv", "Test.csv", "data_dictionary.csv", "SampleSubmission.csv"]
    records = []
    for name, frame in zip(names, fixture(), strict=True):
        path = files / name
        frame.to_csv(path, index=False)
        metadata = {"bytes": path.stat().st_size, "sha256": digest(path)}
        records.append({"name": name, **metadata, "parts": [{"path": "files/" + name, **metadata}]})
    (source / "manifest.json").write_text(json.dumps({"schema_version": 1, "files": records}))
    return source


class FinancialStressTests(unittest.TestCase):
    def test_split_is_order_independent_disjoint_and_stratified(self):
        train, *_ = fixture()
        first = split_rows(train)
        second = split_rows(train.sample(frac=1, random_state=91))
        self.assertEqual([len(first[k]) for k in first], [120, 40, 40])
        seen = set()
        for key in first:
            pd.testing.assert_frame_equal(first[key], second[key])
            ids = set(first[key].ID)
            self.assertFalse(ids & seen)
            seen |= ids
            self.assertAlmostEqual(first[key][TARGET].mean(), 0.2)
        self.assertEqual(seen, set(train.ID))

    def test_contract_rejects_identity_schema_and_target_errors(self):
        for corruption in ("overlap", "duplicate", "target", "schema", "infinity", "matching"):
            with self.subTest(corruption=corruption):
                train, test, dictionary, submission = fixture()
                if corruption == "overlap":
                    test.loc[0, "ID"] = train.loc[0, "ID"]
                elif corruption == "duplicate":
                    train.loc[1, "ID"] = train.loc[0, "ID"]
                elif corruption == "target":
                    train.loc[0, TARGET] = 2
                elif corruption == "schema":
                    test["future_outcome"] = 1
                elif corruption == "infinity":
                    train.loc[0, "amount"] = np.inf
                else:
                    test.loc[0, ["amount", "category"]] = train.loc[0, ["amount", "category"]]
                with self.assertRaises(ValueError):
                    validate_tables(train, test, dictionary, submission)

    def test_preprocessing_learns_only_from_fitting_rows_and_handles_unknowns(self):
        train, *_ = fixture()
        train.loc[0, "amount"] = np.nan
        pipeline = make_pipeline(["amount"], ["category"])
        pipeline.fit(train[["amount", "category"]], train[TARGET])
        preprocessor = pipeline.named_steps["preprocess"]
        numeric = preprocessor.named_transformers_["numeric"]
        self.assertEqual(numeric.named_steps["impute"].statistics_[0], train.amount.median())
        imputed = train.amount.fillna(train.amount.median())
        self.assertAlmostEqual(numeric.named_steps["scale"].mean_[0], imputed.mean())
        incoming = pd.DataFrame({"amount": [1e9, np.nan], "category": ["unseen", "unseen"]})
        p = pipeline.predict_proba(incoming)
        self.assertTrue(np.isfinite(p).all())
        self.assertAlmostEqual(numeric.named_steps["scale"].mean_[0], imputed.mean())
        encoder = preprocessor.named_transformers_["category"].named_steps["encode"]
        self.assertNotIn("unseen", encoder.categories_[0])

    def test_replay_final_is_never_read_and_partition_corruption_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = source_bundle(root)
            first = prepare(source, root / "prepared")
            second = prepare(source, root / "replayed")
            self.assertEqual(first, second)
            self.assertNotIn("ID", first["features"])
            self.assertNotIn(TARGET, first["features"])
            final_path = root / "prepared" / "final.csv"
            final_path.write_text("SEALED: this is deliberately not a CSV")
            read = pd.read_csv

            def guarded(path, *args, **kwargs):
                self.assertNotEqual(Path(path).name, "final.csv")
                self.assertNotEqual(Path(path).name, "Test.csv")
                return read(path, *args, **kwargs)

            with patch("scuba.financial_stress.pd.read_csv", side_effect=guarded):
                result = baseline(root / "prepared", root / "baseline")
            self.assertFalse(result["final_evaluated"])
            self.assertEqual(result["hosted_calls"], 0)
            self.assertAlmostEqual(result["metrics"]["constant_prior"]["roc_auc"], 0.5)
            predictions = pd.read_csv(root / "baseline" / "validation_predictions.csv")
            self.assertEqual(len(predictions), 40)
            self.assertTrue(np.allclose(predictions.constant_prior, 0.2))
            with self.assertRaisesRegex(ValueError, "must be new"):
                prepare(source, root / "prepared")
            (root / "prepared" / "train.csv").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "checksum"):
                baseline(root / "prepared", root / "bad")
            self.assertFalse((root / "bad").exists())

    def test_source_corruption_creates_no_prepared_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = source_bundle(root)
            (source / "files" / "Train.csv").write_text("changed")
            with self.assertRaises(ValueError):
                prepare(source, root / "prepared")
            self.assertFalse((root / "prepared").exists())
