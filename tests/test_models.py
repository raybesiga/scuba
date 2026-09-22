"""Model contract tests use only invented feature rows, never library datasets."""

import unittest

import numpy as np

from scuba.features import FEATURE_COLUMNS
from scuba.models.baselines import logistic_model, prior_model
from scuba.models.common import feature_frame, positive_probability


def invented_rows(count=40):
    rows = []
    for i in range(count):
        row = {name: float((i % 7) + 1) for name in FEATURE_COLUMNS}
        row.update(
            channel="Kite App" if i % 2 else "Pebble Menu",
            region="Luma Reach",
            gap_trend_days=None if i % 3 else float(i % 5),
            customer_id=f"SYN-C{i:06}",
            prediction_date="2032-04-01",
            archetype="test metadata",
            is_synthetic="true",
            dormant_30d=int(i % 4 == 0),
        )
        rows.append(row)
    return rows


class BaselineTests(unittest.TestCase):
    def test_feature_allowlist_and_invalid_values(self):
        rows = invented_rows()
        self.assertEqual(tuple(feature_frame(rows).columns), FEATURE_COLUMNS)
        rows[0]["recency_days"] = float("inf")
        with self.assertRaises(ValueError):
            feature_frame(rows)
        rows[0]["recency_days"] = None
        with self.assertRaises(ValueError):
            feature_frame(rows)

    def test_prior_is_training_prevalence(self):
        rows = invented_rows()
        frame = feature_frame(rows)
        labels = [r["dormant_30d"] for r in rows]
        model = prior_model().fit(frame, labels)
        np.testing.assert_array_equal(model.predict(frame.iloc[:3])[0], [0.25] * 3)
        with self.assertRaises(ValueError):
            prior_model().fit(frame, [0] * len(rows))

    def test_logistic_train_only_transform_and_replay(self):
        rows = invented_rows()
        train = feature_frame(rows)
        labels = [r["dormant_30d"] for r in rows]
        model = logistic_model().fit(train, labels)
        transformer = model.transform
        before = transformer.named_transformers_["numeric"].named_steps["impute"].statistics_.copy()
        validation = invented_rows(4)
        for row in validation:
            row["region"] = "Unseen fictional region"
            row["recency_days"] = 1000000
        probabilities, _ = model.predict(feature_frame(validation))
        self.assertTrue(np.isfinite(probabilities).all())
        np.testing.assert_array_equal(
            before, transformer.named_transformers_["numeric"].named_steps["impute"].statistics_
        )
        self.assertNotIn(
            "Unseen fictional region", transformer.named_transformers_["categorical"].categories_[1]
        )
        replay = logistic_model().fit(train, labels)
        np.testing.assert_array_equal(model.predict(train)[0], replay.predict(train)[0])

    def test_all_missing_gap_column_is_retained(self):
        rows = invented_rows()
        for row in rows:
            row["gap_trend_days"] = None
        model = logistic_model().fit(feature_frame(rows), [r["dormant_30d"] for r in rows])
        self.assertTrue(np.isfinite(model.predict(feature_frame(rows))[0]).all())

    def test_probability_class_order_and_rejections(self):
        class Fake:
            classes_ = np.array([1, 0])

            def predict_proba(self, features):
                return np.array([[0.8, 0.2]])

        np.testing.assert_array_equal(positive_probability(Fake(), [[1]]), [0.8])
        fake = Fake()
        fake.predict_proba = lambda features: np.array([[0.8, 0.8]])
        with self.assertRaises(ValueError):
            positive_probability(fake, [[1]])
        fake.predict_proba = lambda features: np.array([[float("nan"), 0.2]])
        with self.assertRaises(ValueError):
            positive_probability(fake, [[1]])
