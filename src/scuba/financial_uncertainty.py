"""Post-hoc paired row-bootstrap intervals for frozen Financial Stress predictions."""

import numpy as np


def paired_intervals(labels, plus, baseline, ids, *, repeats=2000, seed=3501):
    y, a, b = (np.asarray(v, dtype=float) for v in (labels, plus, baseline))
    ids = np.asarray(ids, dtype=str)
    if (
        y.ndim != 1
        or not len(y)
        or a.shape != y.shape
        or b.shape != y.shape
        or ids.shape != y.shape
        or len(set(ids)) != len(ids)
        or not np.isin(y, [0, 1]).all()
        or any(not np.isfinite(p).all() or ((p < 0) | (p > 1)).any() for p in (a, b))
        or repeats < 2
    ):
        raise ValueError("aligned binary labels, unique IDs and valid probabilities required")
    eps = np.finfo(float).eps

    def losses(p):
        p = np.clip(p, eps, 1 - eps)
        return -(y * np.log(p) + (1 - y) * np.log1p(-p))

    loss_delta = losses(a) - losses(b)
    budgets = (0.05, 0.1)

    def capture_delta(indices, q):
        k = int(np.ceil(len(indices) * q))
        left = np.lexsort((ids[indices], -a[indices]))[:k]
        right = np.lexsort((ids[indices], -b[indices]))[:k]
        return float(y[indices[left]].sum() - y[indices[right]].sum())

    original = np.arange(len(y))
    draws = {"log_loss": [], **{f"capture_{q}": [] for q in budgets}}
    rng = np.random.default_rng(seed)
    for _ in range(repeats):
        indices = rng.integers(0, len(y), len(y))
        draws["log_loss"].append(float(loss_delta[indices].mean()))
        for q in budgets:
            draws[f"capture_{q}"].append(capture_delta(indices, q))
    observed = {
        "log_loss": float(loss_delta.mean()),
        **{f"capture_{q}": capture_delta(original, q) for q in budgets},
    }
    return {
        "method": "paired ordinary row bootstrap; percentile 95% intervals",
        "post_hoc": True,
        "independent_rows_assumed": True,
        "repeats": repeats,
        "seed": seed,
        "rows": len(y),
        "comparison": "tabpfn_3_5_plus minus xgboost",
        "differences": {
            key: {
                "estimate": observed[key],
                "lower": float(np.quantile(values, 0.025)),
                "upper": float(np.quantile(values, 0.975)),
            }
            for key, values in draws.items()
        },
    }
