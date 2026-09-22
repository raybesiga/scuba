"""Shared feature boundary, train-fitted transforms and probability contract."""

from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from scuba.features import FEATURE_COLUMNS

MODEL_SEED = 3501
CATEGORICAL = ("channel", "region")
NUMERIC = tuple(name for name in FEATURE_COLUMNS if name not in CATEGORICAL)


def feature_frame(rows: list[dict]) -> pd.DataFrame:
    """Ignore metadata; reject invalid predictors before fitting or scoring."""
    frame = pd.DataFrame(
        [{name: row[name] for name in FEATURE_COLUMNS} for row in rows], columns=FEATURE_COLUMNS
    )
    for name in NUMERIC:
        frame[name] = pd.to_numeric(frame[name].replace("", np.nan), errors="raise").astype(float)
        values = frame[name].to_numpy()
        if np.isinf(values).any() or (name != "gap_trend_days" and np.isnan(values).any()):
            raise ValueError(f"invalid numeric feature: {name}")
    for name in CATEGORICAL:
        if not frame[name].map(lambda value: isinstance(value, str) and bool(value)).all():
            raise ValueError(f"invalid categorical feature: {name}")
    return frame


def encoder(*, scale: bool) -> ColumnTransformer:
    steps = [("impute", SimpleImputer(strategy="median", keep_empty_features=True))]
    if scale:
        steps.append(("scale", StandardScaler()))
    return ColumnTransformer(
        [
            ("numeric", Pipeline(steps), list(NUMERIC)),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(CATEGORICAL),
            ),
        ],
        remainder="drop",
        sparse_threshold=0,
    )


def positive_probability(estimator, features) -> np.ndarray:
    classes = list(estimator.classes_)
    if sorted(classes) != [0, 1]:
        raise ValueError("estimator must expose exactly classes 0 and 1")
    probabilities = np.asarray(estimator.predict_proba(features), dtype=float)
    if (
        probabilities.shape != (len(features), 2)
        or not np.isfinite(probabilities).all()
        or (probabilities < 0).any()
        or (probabilities > 1).any()
        or not np.allclose(probabilities.sum(axis=1), 1, atol=1e-6, rtol=0)
    ):
        raise ValueError("invalid binary probabilities")
    return probabilities[:, classes.index(1)]


class LocalModel:
    """One fixed estimator, with transforms fitted exclusively on training data."""

    def __init__(self, name, estimator, transform=None):
        self.name = name
        self.estimator = estimator
        self.transform = transform
        self.fitted = False
        self.fit_times = {}

    def fit(self, features, labels):
        labels = np.asarray(labels)
        if labels.ndim != 1 or len(features) != len(labels) or set(labels.tolist()) != {0, 1}:
            raise ValueError("training requires aligned rows and both binary classes")
        with threadpool_limits(limits=1):
            start = perf_counter()
            encoded = (
                self.transform.fit_transform(features) if self.transform is not None else features
            )
            preprocessing_seconds = perf_counter() - start
            start = perf_counter()
            self.estimator.fit(encoded, labels)
            fit_seconds = perf_counter() - start
        self.fit_times = {
            "preprocessing_fit_seconds": preprocessing_seconds,
            "estimator_fit_seconds": fit_seconds,
        }
        self.fitted = True
        return self

    def predict(self, features):
        if not self.fitted:
            raise ValueError("fit the model before prediction")
        with threadpool_limits(limits=1):
            start = perf_counter()
            encoded = self.transform.transform(features) if self.transform is not None else features
            preprocessing_seconds = perf_counter() - start
            start = perf_counter()
            probability = positive_probability(self.estimator, encoded)
            predict_seconds = perf_counter() - start
        return probability, {
            "preprocessing_predict_seconds": preprocessing_seconds,
            "estimator_predict_seconds": predict_seconds,
        }

    def settings(self):
        return {
            "estimator": self.estimator.get_params(deep=False),
            "preprocessing": "native"
            if self.transform is None
            else {
                "numeric": list(NUMERIC),
                "categorical": list(CATEGORICAL),
                "imputation": "training median; all-empty columns retained as zero",
                "scaling": "scale" in self.transform.transformers[0][1].named_steps,
                "encoding": "training one-hot; unknown categories ignored",
            },
            "thread_limit": 1,
        }
