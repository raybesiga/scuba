import unittest

import numpy as np
from test_models import invented_rows

from scuba.models.common import feature_frame
from scuba.models.xgboost import xgboost_model


class XGBoostTests(unittest.TestCase):
    def test_native_fit_unknown_categories_and_replay(self):
        rows = invented_rows()
        frame = feature_frame(rows)
        labels = [r["dormant_30d"] for r in rows]
        model = xgboost_model().fit(frame, labels)
        validation = invented_rows(3)
        for row in validation:
            row["channel"] = "Unseen fictional channel"
        probabilities, _ = model.predict(feature_frame(validation))
        self.assertTrue(np.isfinite(probabilities).all())
        self.assertNotIn(
            "Unseen fictional channel",
            model.transform.named_transformers_["categorical"].categories_[0],
        )
        replay = xgboost_model().fit(frame, labels)
        np.testing.assert_array_equal(model.predict(frame)[0], replay.predict(frame)[0])
