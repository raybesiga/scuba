"""Fixed CPU XGBoost comparator with train-fitted encoding."""

from xgboost import XGBClassifier

from scuba.models.common import MODEL_SEED, LocalModel, encoder


def xgboost_model():
    return LocalModel(
        "xgboost",
        XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=1.0,
            objective="binary:logistic",
            tree_method="hist",
            device="cpu",
            n_jobs=1,
            random_state=MODEL_SEED,
            eval_metric="logloss",
        ),
        encoder(scale=False),
    )
