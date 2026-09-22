"""Constant training prior and scaled logistic regression."""

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression

from scuba.models.common import MODEL_SEED, LocalModel, encoder


def prior_model():
    return LocalModel("constant_prior", DummyClassifier(strategy="prior", random_state=MODEL_SEED))


def logistic_model():
    return LocalModel(
        "logistic_regression",
        LogisticRegression(
            C=1.0, solver="lbfgs", max_iter=2000, tol=0.0001, random_state=MODEL_SEED
        ),
        encoder(scale=True),
    )
