"""Benchmark simulator v1: invented stochastic activity, never imported records."""

import math
import platform
import random
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path

from scuba.artifacts import source_hashes, write_json, write_table
from scuba.contract import (
    ARCHETYPES,
    CHANNELS,
    CUSTOMER_SCHEMA,
    EVENT_SCHEMA,
    PRODUCTS,
    REGIONS,
    SCHEMA_VERSION,
    GeneratorConfig,
)

GENERATOR_VERSION = "1.0.0"
CALENDAR_ORIGIN = date(2032, 1, 1)


def generate_rows(config: GeneratorConfig) -> tuple[list[dict], list[dict]]:
    customers, events = [], []
    for index in range(1, config.customers + 1):
        customer_id = f"SYN-C{index:06d}"
        stream_seed = int(sha256(f"{config.seed}:{customer_id}".encode()).hexdigest(), 16)
        rng = random.Random(stream_seed)
        archetype = rng.choice(ARCHETYPES)
        customers.append(
            {
                "customer_id": customer_id,
                "archetype": archetype,
                "region": rng.choice(REGIONS),
                "channel": rng.choice(CHANNELS),
                "is_synthetic": "true",
            }
        )
        base_rate = rng.uniform(0.025, 0.12) if archetype == "sporadic" else rng.uniform(0.14, 0.60)
        base_value = rng.randint(250, 8_000)
        base_failure = rng.uniform(0.01, 0.10)
        preferred = rng.randrange(len(PRODUCTS))
        adoption_day = rng.randint(0, 240)
        state, declining_days, shock_days = "active", 0, 0
        for offset in range((config.end_exclusive - config.start).days):
            day = config.start + timedelta(days=offset)
            elapsed = (day - CALENDAR_ORIGIN).days
            transition = rng.random()
            if state == "active":
                decline_hazard = {"steady": 0.001, "tapering": 0.005, "sporadic": 0.002}[archetype]
                if transition < 0.0007:
                    state = "dormant"
                elif transition < 0.0007 + decline_hazard * (1 + max(elapsed, 0) / 1200):
                    state, declining_days = "disengaging", 0
            elif state == "disengaging":
                declining_days += 1
                if transition < 0.025:
                    state = "dormant"
                elif transition < 0.037:
                    state = "active"
            else:
                recovery = {"steady": 0.012, "tapering": 0.004, "sporadic": 0.025}[archetype]
                if transition < recovery:
                    state = "active"
            if shock_days:
                shock_days -= 1
            elif rng.random() < 0.003:
                shock_days = rng.randint(3, 12)
            state_factor = (
                0
                if state == "dormant"
                else max(0.03, 1 - declining_days / 50)
                if state == "disengaging"
                else 1
            )
            calendar_factor = 0.95 + 0.08 * math.cos(2 * math.pi * elapsed / 90)
            calendar_factor *= 0.8 if day.weekday() >= 5 else 1
            rate = base_rate * state_factor * calendar_factor * (0.25 if shock_days else 1)
            if rng.random() >= rate:
                continue
            for attempt in range(1, rng.randint(1, 3) + 1):
                failure = (
                    base_failure
                    + (0.10 if state == "disengaging" else 0)
                    + (0.15 if shock_days else 0)
                )
                reversal = 0.02 + (0.04 if shock_days else 0)
                draw = rng.random()
                status = (
                    "failed"
                    if draw < failure
                    else "reversed"
                    if draw < failure + reversal
                    else "success"
                )
                weights = [0.15 + (0.55 if i == preferred else 0) for i in range(len(PRODUCTS))]
                if offset < adoption_day:
                    weights[1] = 0
                product = rng.choices(PRODUCTS, weights=weights, k=1)[0]
                amount = max(
                    1, round(base_value * rng.uniform(0.4, 2.0) * (0.5 + 0.5 * state_factor))
                )
                events.append(
                    {
                        "event_id": f"SYN-E{index:06d}-{day:%Y%m%d}-{attempt:02d}",
                        "customer_id": customer_id,
                        "event_date": day.isoformat(),
                        "product": product,
                        "amount_minor": amount,
                        "status": status,
                        "is_synthetic": "true",
                    }
                )
    return customers, events


def write_sources(
    output: Path, config: GeneratorConfig, customers: list[dict], events: list[dict]
) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    files = {
        "customers.csv": write_table(output / "customers.csv", customers, CUSTOMER_SCHEMA),
        "events.csv": write_table(output / "events.csv", events, EVENT_SCHEMA),
    }
    dates = [event["event_date"] for event in events]
    manifest = {
        "classification": "synthetic",
        "purpose": "benchmark_simulation",
        "generator": "scuba.simulation",
        "generator_version": GENERATOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "seed": config.seed,
        "parameters": {
            "seed": config.seed,
            "customers": config.customers,
            "start": config.start.isoformat(),
            "end_exclusive": config.end_exclusive.isoformat(),
        },
        "coverage": {
            "start_inclusive": config.start.isoformat(),
            "end_exclusive": config.end_exclusive.isoformat(),
            "timezone": "UTC",
        },
        "observed_event_range": {
            "min": min(dates) if dates else None,
            "max": max(dates) if dates else None,
        },
        "source_sha256": source_hashes(),
        "python_version": platform.python_version(),
        "files": files,
    }
    write_json(output / "manifest.json", manifest)
    return manifest
