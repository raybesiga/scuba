"""Executable boundaries shared by the fixture and future snapshot pipeline."""

from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256

SCHEMA_VERSION = "0.1.0"
LOOKBACK_DAYS = 60
ACTIVE_DAYS = 30
HORIZON_DAYS = 30
DEFAULT_SEED = 3501
TRAIN_DATES = (date(2032, 4, 1), date(2032, 5, 1), date(2032, 6, 1))
VALIDATION_DATE = date(2032, 8, 1)
TEST_DATE = date(2032, 10, 1)

ARCHETYPES = ("steady", "tapering", "sporadic")
REGIONS = ("Luma Reach", "Vela Plain", "Nori Vale")
CHANNELS = ("Kite App", "Pebble Menu", "Lantern Agent")
PRODUCTS = ("Drift Transfer", "Orbit Merchant", "Pocket Cash")
STATUSES = ("success", "failed", "reversed")

CUSTOMER_SCHEMA = {
    "customer_id": "string",
    "archetype": "string",
    "region": "string",
    "channel": "string",
    "is_synthetic": "boolean",
}
EVENT_SCHEMA = {
    "event_id": "string",
    "customer_id": "string",
    "event_date": "date:YYYY-MM-DD",
    "product": "string",
    "amount_minor": "positive integer:fictional minor units",
    "status": "enum:success|failed|reversed",
    "is_synthetic": "boolean",
}


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = DEFAULT_SEED
    customers: int = 60
    start: date = date(2032, 1, 1)
    end_exclusive: date = date(2032, 11, 1)

    def __post_init__(self) -> None:
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer")
        if type(self.customers) is not int or self.customers < 1:
            raise ValueError("customers must be a positive integer")
        if type(self.start) is not date or type(self.end_exclusive) is not date:
            raise ValueError("coverage boundaries must be dates")
        if self.end_exclusive <= self.start:
            raise ValueError("end_exclusive must follow start")


def snapshot_windows(prediction_date: date) -> dict[str, tuple[date, date]]:
    """All windows are start-inclusive and end-exclusive, at midnight UTC."""
    return {
        "features": (prediction_date - timedelta(days=LOOKBACK_DAYS), prediction_date),
        "active": (prediction_date - timedelta(days=ACTIVE_DAYS), prediction_date),
        "outcome": (prediction_date, prediction_date + timedelta(days=HORIZON_DAYS)),
    }


def require_complete_coverage(prediction_date: date, config: GeneratorConfig) -> None:
    windows = snapshot_windows(prediction_date)
    if windows["features"][0] < config.start:
        raise ValueError("incomplete feature history")
    if windows["outcome"][1] > config.end_exclusive:
        raise ValueError("censored outcome window")


def customer_partition(customer_id: str, seed: int = DEFAULT_SEED) -> str:
    """Stable customer assignment independent of row order and Python hash salt."""
    if not customer_id:
        raise ValueError("customer_id must not be empty")
    bucket = int(sha256(f"{seed}:{customer_id}".encode("utf-8")).hexdigest(), 16) % 100
    return "train" if bucket < 60 else "validation" if bucket < 80 else "test"
