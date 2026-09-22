import unittest

import numpy as np
from test_models import invented_rows

from scuba.models.catboost import catboost_model
from scuba.models.common import feature_frame


class CatBoostTests(unittest.TestCase):
    def test_native_categories_missing_values_and_replay(self):
        rows = invented_rows()
        frame = feature_frame(rows)
        labels = [r["dormant_30d"] for r in rows]
        model = catboost_model().fit(frame, labels)
        validation = invented_rows(3)
        for row in validation:
            row["channel"] = "Unseen fictional channel"
            row["gap_trend_days"] = None
        probabilities, _ = model.predict(feature_frame(validation))
        self.assertTrue(np.isfinite(probabilities).all())
        replay = catboost_model().fit(frame, labels)
        np.testing.assert_array_equal(model.predict(frame)[0], replay.predict(frame)[0])
