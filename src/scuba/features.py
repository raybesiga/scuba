"""Point-in-time features and separately derived future labels."""

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

from scuba.contract import (
    ARCHETYPES,
    CHANNELS,
    CUSTOMER_SCHEMA,
    EVENT_SCHEMA,
    PRODUCTS,
    REGIONS,
    STATUSES,
    TEST_DATE,
    TRAIN_DATES,
    VALIDATION_DATE,
    GeneratorConfig,
    snapshot_windows,
)

FEATURE_VERSION = "1.0.0"
PREDICTION_DATES = (*TRAIN_DATES, VALIDATION_DATE, TEST_DATE)
FEATURE_SCHEMA = {
    "recency_days": "integer:days",
    "frequency_trend": "float:smoothed relative change",
    "value_trend": "float:smoothed relative change in fictional minor units",
    "gap_trend_days": "nullable float:days",
    "product_diversity": "integer:products",
    "merchant_adoption": "integer:0|1",
    "product_concentration": "float:share",
    "active_day_trend": "float:smoothed relative change",
    "failure_reversal_rate": "float:share",
    "channel": "category",
    "region": "category",
}
FEATURE_COLUMNS = tuple(FEATURE_SCHEMA)
SNAPSHOT_SCHEMA = {
    "customer_id": "string",
    "prediction_date": "date:YYYY-MM-DD",
    **FEATURE_SCHEMA,
    "dormant_30d": "integer:0|1",
    "archetype": "category:evaluation only",
    "activity_level": "category:low|medium|high",
    "success_count_60d": "integer:evaluation only",
    "is_synthetic": "boolean",
}
EXCLUSION_SCHEMA = {
    "customer_id": "string",
    "prediction_date": "date:YYYY-MM-DD",
    "reason": "enum:incomplete_history|censored_outcome|inactive",
    "is_synthetic": "boolean",
}


def is_synthetic(value: object) -> bool:
    return value is True or value == "true"


def validate_sources(customers: list[dict], events: list[dict], config: GeneratorConfig) -> None:
    ids, event_ids = set(), set()
    if len(customers) != config.customers:
        raise ValueError("customer count does not match generation configuration")
    for customer in customers:
        if set(customer) != set(CUSTOMER_SCHEMA) or not is_synthetic(customer["is_synthetic"]):
            raise ValueError("customer schema or synthetic flag invalid")
        identifier = customer["customer_id"]
        if (
            not isinstance(identifier, str)
            or not identifier.startswith("SYN-C")
            or identifier in ids
        ):
            raise ValueError("invalid or duplicate customer key")
        ids.add(identifier)
        if (
            customer["archetype"] not in ARCHETYPES
            or customer["channel"] not in CHANNELS
            or customer["region"] not in REGIONS
        ):
            raise ValueError("unknown fictional customer category")
    for event in events:
        if set(event) != set(EVENT_SCHEMA) or not is_synthetic(event["is_synthetic"]):
            raise ValueError("event schema or synthetic flag invalid")
        identifier = event["event_id"]
        if (
            not isinstance(identifier, str)
            or not identifier.startswith("SYN-E")
            or identifier in event_ids
        ):
            raise ValueError("invalid or duplicate event key")
        event_ids.add(identifier)
        if event["customer_id"] not in ids:
            raise ValueError("event references an unknown customer")
        if event["product"] not in PRODUCTS or event["status"] not in STATUSES:
            raise ValueError("unknown event product or status")
        if type(event["amount_minor"]) is not int or event["amount_minor"] <= 0:
            raise ValueError("amount_minor must be a positive integer")
        day = date.fromisoformat(event["event_date"])
        if day.isoformat() != event["event_date"] or not config.start <= day < config.end_exclusive:
            raise ValueError("event date is invalid or outside observed coverage")


def model_inputs(rows: list[dict]) -> list[dict]:
    """The sole model-facing projection; target and audit metadata cannot enter."""
    return [{name: row[name] for name in FEATURE_COLUMNS} for row in rows]


def _trend(recent: float, prior: float) -> float:
    return (recent - prior) / (prior + 1)


def _gap(rows: list[dict]) -> float | None:
    if len(rows) < 2:
        return None
    return mean((right["_day"] - left["_day"]).days for left, right in zip(rows, rows[1:]))


def _features(history: list[dict], prediction_date: date) -> dict:
    successes = [e for e in history if e["status"] == "success"]
    middle = prediction_date - timedelta(days=30)
    prior = [e for e in successes if e["_day"] < middle]
    recent = [e for e in successes if e["_day"] >= middle]
    value_by_product = defaultdict(int)
    for event in successes:
        value_by_product[event["product"]] += event["amount_minor"]
    prior_gap, recent_gap = _gap(prior), _gap(recent)
    return {
        "recency_days": (prediction_date - successes[-1]["_day"]).days,
        "frequency_trend": _trend(len(recent), len(prior)),
        "value_trend": _trend(
            sum(e["amount_minor"] for e in recent), sum(e["amount_minor"] for e in prior)
        ),
        "gap_trend_days": None
        if prior_gap is None or recent_gap is None
        else recent_gap - prior_gap,
        "product_diversity": len(value_by_product),
        "merchant_adoption": int(PRODUCTS[1] in value_by_product),
        "product_concentration": max(value_by_product.values()) / sum(value_by_product.values()),
        "active_day_trend": _trend(
            len({e["_day"] for e in recent}), len({e["_day"] for e in prior})
        ),
        "failure_reversal_rate": sum(e["status"] != "success" for e in history) / len(history),
    }


def build_snapshots(
    customers: list[dict],
    events: list[dict],
    config: GeneratorConfig,
    prediction_dates: tuple[date, ...] = PREDICTION_DATES,
) -> tuple[list[dict], list[dict]]:
    validate_sources(customers, events, config)
    if len(set(prediction_dates)) != len(prediction_dates):
        raise ValueError("duplicate prediction dates")
    by_customer = defaultdict(list)
    for event in events:
        by_customer[event["customer_id"]].append(
            {**event, "_day": date.fromisoformat(event["event_date"])}
        )
    for history in by_customer.values():
        history.sort(key=lambda e: (e["_day"], e["event_id"]))
    snapshots, exclusions = [], []
    for customer in sorted(customers, key=lambda c: c["customer_id"]):
        customer_events = by_customer[customer["customer_id"]]
        for origin in sorted(prediction_dates):
            windows = snapshot_windows(origin)
            reason = None
            if windows["features"][0] < config.start:
                reason = "incomplete_history"
            elif windows["outcome"][1] > config.end_exclusive:
                reason = "censored_outcome"
            history = [e for e in customer_events if windows["features"][0] <= e["_day"] < origin]
            active = any(
                e["status"] == "success" and e["_day"] >= windows["active"][0] for e in history
            )
            if reason is None and not active:
                reason = "inactive"
            key = {"customer_id": customer["customer_id"], "prediction_date": origin.isoformat()}
            if reason:
                exclusions.append({**key, "reason": reason, "is_synthetic": "true"})
                continue
            future_success = any(
                e["status"] == "success" and origin <= e["_day"] < windows["outcome"][1]
                for e in customer_events
            )
            count = sum(e["status"] == "success" for e in history)
            snapshots.append(
                {
                    **key,
                    **_features(history, origin),
                    "channel": customer["channel"],
                    "region": customer["region"],
                    "dormant_30d": int(not future_success),
                    "archetype": customer["archetype"],
                    "success_count_60d": count,
                    "activity_level": "low" if count <= 5 else "medium" if count <= 20 else "high",
                    "is_synthetic": "true",
                }
            )
    return snapshots, exclusions
