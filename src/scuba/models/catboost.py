"""Fixed CPU CatBoost comparator with native categorical inputs."""

from catboost import CatBoostClassifier

from scuba.models.common import CATEGORICAL, MODEL_SEED, LocalModel


def catboost_model():
    return LocalModel(
        "catboost",
        CatBoostClassifier(
            iterations=300,
            depth=4,
            learning_rate=0.05,
            loss_function="Logloss",
            task_type="CPU",
            thread_count=1,
            random_seed=MODEL_SEED,
            cat_features=list(CATEGORICAL),
            allow_writing_files=False,
            verbose=False,
        ),
    )
