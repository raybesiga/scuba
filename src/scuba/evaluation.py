"""Offline probability diagnostics and paired customer-bootstrap AP intervals."""

import math

import numpy as np

EVALUATION_VERSION = "scuba.validation-evaluation/v1"
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 4401


def aligned_arrays(labels, probability):
    y, p = np.asarray(labels), np.asarray(probability, dtype=float)
    if (
        y.ndim != 1
        or p.shape != y.shape
        or not np.isin(y, [0, 1]).all()
        or not np.isfinite(p).all()
        or (p < 0).any()
        or (p > 1).any()
    ):
        raise ValueError("expected aligned binary labels and finite probabilities in [0, 1]")
    return y.astype(int), p


def average_precision(y, p):
    """Stepwise AP; ties share a threshold. Single-class inputs are unavailable."""
    positives = int(y.sum())
    if not positives or positives == len(y):
        return None
    order = np.argsort(-p, kind="stable")
    ranked, counts = p[order], np.cumsum(y[order])
    ends = np.r_[np.flatnonzero(np.diff(ranked)), len(y) - 1]
    true_positives = counts[ends]
    return float(
        np.sum(np.diff(np.r_[0, true_positives]) / positives * true_positives / (ends + 1))
    )


def confusion(y, selected):
    return {
        "tp": int(np.sum((y == 1) & selected)),
        "fp": int(np.sum((y == 0) & selected)),
        "tn": int(np.sum((y == 0) & ~selected)),
        "fn": int(np.sum((y == 1) & ~selected)),
    }


def point_metrics(labels, probability, keys):
    y, p = aligned_arrays(labels, probability)
    n, positives = len(y), int(y.sum())
    if len(keys) != n or len(set(keys)) != n:
        raise ValueError("snapshot keys must be unique and aligned")
    bins = []
    bin_ids = np.minimum((p * 10).astype(int), 9)
    for index in range(10):
        mask = bin_ids == index
        count = int(mask.sum())
        bins.append(
            {
                "lower": index / 10,
                "upper": (index + 1) / 10,
                "upper_inclusive": index == 9,
                "rows": count,
                "mean_probability": float(p[mask].mean()) if count else None,
                "observed_fraction": float(y[mask].mean()) if count else None,
            }
        )
    ece = (
        sum(
            b["rows"] * abs(b["mean_probability"] - b["observed_fraction"])
            for b in bins
            if b["rows"]
        )
        / n
        if n
        else None
    )
    clipped = np.clip(p, np.finfo(float).eps, 1 - np.finfo(float).eps)
    ranking = sorted(range(n), key=lambda i: (-p[i], keys[i]))
    top = {}
    for fraction in (0.05, 0.10):
        k = math.ceil(fraction * n)
        selected = np.zeros(n, dtype=bool)
        selected[ranking[:k]] = True
        counts = confusion(y, selected)
        top[str(fraction)] = {
            "selected": k,
            "effective_fraction": k / n if n else None,
            "boundary_probability": float(p[ranking[k - 1]]) if k else None,
            "capture": counts["tp"] / positives if positives else None,
            "lift": (counts["tp"] / k) / (positives / n) if positives else None,
            **counts,
        }
    return {
        "rows": n,
        "positives": positives,
        "negatives": n - positives,
        "prevalence": positives / n if n else None,
        "sparse": n < 50 or min(positives, n - positives) < 10,
        "average_precision": average_precision(y, p),
        "ap_unavailable_reason": "empty"
        if not n
        else "single_class"
        if positives in (0, n)
        else None,
        "log_loss": float(-np.mean(y * np.log(clipped) + (1 - y) * np.log1p(-clipped)))
        if n
        else None,
        "brier_score": float(np.mean((p - y) ** 2)) if n else None,
        "ece_10_bins": ece,
        "reliability": bins,
        "threshold_0.5": confusion(y, p >= 0.5),
        "top_budgets": top,
    }


def cluster_draws(customers, replicates, seed):
    groups = {}
    for index, customer in enumerate(customers):
        groups.setdefault(customer, []).append(index)
    clusters = [np.array(groups[key], dtype=int) for key in sorted(groups)]
    rng = np.random.default_rng(seed)
    for _ in range(replicates):
        yield np.concatenate([clusters[i] for i in rng.integers(len(clusters), size=len(clusters))])


def percentile_interval(values, replicates, *, reason=None):
    valid = len(values)
    unavailable = reason or (
        "insufficient_valid_draws" if valid < math.ceil(0.8 * replicates) else None
    )
    return {
        "level": 0.95,
        "method": "customer_cluster_percentile",
        "replicates": replicates,
        "valid_draws": valid,
        "invalid_single_class_draws": replicates - valid if not reason else 0,
        "attempted_draws": replicates if not reason else 0,
        "lower": float(np.quantile(values, 0.025, method="linear")) if not unavailable else None,
        "upper": float(np.quantile(values, 0.975, method="linear")) if not unavailable else None,
        "unavailable_reason": unavailable,
    }


def evaluate_cohort(rows, probabilities, *, replicates=BOOTSTRAP_REPLICATES, seed=BOOTSTRAP_SEED):
    if type(replicates) is not int or replicates < 1 or type(seed) is not int or seed < 0:
        raise ValueError(
            "bootstrap requires positive integer replicates and nonnegative integer seed"
        )
    if not probabilities:
        raise ValueError("at least one model is required")
    keys = [(r["customer_id"], r["prediction_date"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate snapshot keys")
    order = sorted(range(len(rows)), key=lambda i: keys[i])
    keys = [keys[i] for i in order]
    customers = [rows[i]["customer_id"] for i in order]
    labels = [r["dormant_30d"] for r in rows]
    arrays = {
        name: aligned_arrays(labels, p)[1][order] for name, p in sorted(probabilities.items())
    }
    y = np.asarray(labels, dtype=int)[order]
    models = {name: point_metrics(y, p, keys) for name, p in arrays.items()}
    draws = {name: [] for name in arrays}
    reason = "empty" if not len(y) else "single_class" if len(set(y)) < 2 else None
    if reason is None:
        for indices in cluster_draws(customers, replicates, seed):
            sampled = y[indices]
            if len(set(sampled)) < 2:
                continue
            for name, p in arrays.items():
                draws[name].append(average_precision(sampled, p[indices]))
    for name, model in models.items():
        model["ap_interval"] = percentile_interval(draws[name], replicates, reason=reason)
    comparisons = {}
    pairs = [
        (name, "xgboost")
        for name in arrays
        if name not in ("xgboost", "constant_prior") and "xgboost" in arrays
    ]
    if "hosted_plus" in arrays and "catboost" in arrays:
        pairs.append(("hosted_plus", "catboost"))
    for candidate, reference in pairs:
        difference = np.asarray(draws[candidate]) - np.asarray(draws[reference])
        comparisons[f"{candidate}_minus_{reference}"] = {
            "candidate": candidate,
            "reference": reference,
            "ap_difference": models[candidate]["average_precision"]
            - models[reference]["average_precision"]
            if not reason
            else None,
            "interval": percentile_interval(difference, replicates, reason=reason),
        }
    return {
        "rows": len(rows),
        "customers": len(set(customers)),
        "bootstrap_seed": seed,
        "models": models,
        "paired_comparisons": comparisons,
    }
