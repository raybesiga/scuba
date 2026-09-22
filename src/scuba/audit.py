"""Data support and split evidence; no model quality estimates."""

from collections import Counter
from itertools import combinations

from scuba.contract import ARCHETYPES, DEFAULT_SEED
from scuba.features import FEATURE_COLUMNS, PREDICTION_DATES
from scuba.splits import PARTITIONS, validate_temporal_split

MIN_SUPPORT = {"rows": 50, "positives": 10, "negatives": 10}


def cohort_stats(rows: list[dict]) -> dict:
    positives = sum(row["dormant_30d"] for row in rows)
    negatives = len(rows) - positives
    return {
        "rows": len(rows),
        "customers": len({r["customer_id"] for r in rows}),
        "positives": positives,
        "negatives": negatives,
        "dormancy_rate": positives / len(rows) if rows else None,
        "sparse_support": len(rows) < 20 or min(positives, negatives) < 5,
    }


def split_audit(partitions: dict[str, list[dict]]) -> dict:
    result = {}
    for name in PARTITIONS:
        rows = partitions[name]
        dates = [r["prediction_date"] for r in rows]
        result[name] = {
            **cohort_stats(rows),
            "prediction_dates": sorted(set(dates)),
            "by_archetype": {
                a: cohort_stats([r for r in rows if r["archetype"] == a]) for a in ARCHETYPES
            },
            "by_activity_level": {
                a: cohort_stats([r for r in rows if r["activity_level"] == a])
                for a in ("low", "medium", "high")
            },
        }
    groups = {name: {r["customer_id"] for r in partitions[name]} for name in PARTITIONS}
    overlaps = {
        f"{left}__{right}": len(groups[left] & groups[right])
        for left, right in combinations(PARTITIONS, 2)
    }
    return {"partitions": result, "customer_overlap_counts": overlaps}


def build_audit(
    snapshots: list[dict],
    exclusions: list[dict],
    temporal: dict,
    reference: dict,
    split_seed: int = DEFAULT_SEED,
) -> dict:
    validate_temporal_split(temporal, split_seed)
    main = split_audit(temporal)
    support_failures = [
        f"{name}.{metric}={main['partitions'][name][metric]} < {minimum}"
        for name in PARTITIONS
        for metric, minimum in MIN_SUPPORT.items()
        if main["partitions"][name][metric] < minimum
    ]
    feature_summary = {}
    for name in FEATURE_COLUMNS:
        values = [r[name] for r in snapshots if r[name] is not None]
        entry = {"missing": len(snapshots) - len(values)}
        if name in ("region", "channel"):
            entry["categories"] = dict(sorted(Counter(values).items()))
        else:
            entry.update(
                {"min": min(values) if values else None, "max": max(values) if values else None}
            )
        feature_summary[name] = entry
    return {
        "classification": "synthetic",
        "purpose": "data_and_split_audit_no_model_scores",
        "candidate_rows": len(snapshots) + len(exclusions),
        "eligible": cohort_stats(snapshots),
        "excluded": dict(sorted(Counter(r["reason"] for r in exclusions).items())),
        "by_prediction_date": {
            day.isoformat(): {
                "eligible": cohort_stats(
                    [r for r in snapshots if r["prediction_date"] == day.isoformat()]
                ),
                "excluded": dict(
                    sorted(
                        Counter(
                            r["reason"]
                            for r in exclusions
                            if r["prediction_date"] == day.isoformat()
                        ).items()
                    )
                ),
            }
            for day in PREDICTION_DATES
        },
        "temporal_grouped": {
            **main,
            "validation": "passed",
            "omitted_eligible_rows": len(snapshots) - sum(len(v) for v in temporal.values()),
        },
        "random_reference": {
            **split_audit(reference),
            "deployment_valid": False,
            "interpretation": "Diagnostic only; cohort, date and customer overlap differences are confounded.",
        },
        "feature_summary": feature_summary,
        "minimum_main_partition_support": MIN_SUPPORT,
        "main_support_passed": not support_failures,
        "support_failures": support_failures,
    }
