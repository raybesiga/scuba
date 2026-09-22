import random
import unittest
from datetime import date

from scuba.contract import GeneratorConfig
from scuba.features import validate_sources
from scuba.simulation import generate_rows


class SimulationTests(unittest.TestCase):
    def test_determinism_schema_and_seed_sensitivity(self):
        state = random.getstate()
        config = GeneratorConfig(customers=20)
        first = generate_rows(config)
        self.assertEqual(first, generate_rows(config))
        self.assertNotEqual(first, generate_rows(GeneratorConfig(customers=20, seed=3502)))
        validate_sources(*first, config)
        self.assertEqual(state, random.getstate())
        customers, events = first
        self.assertEqual({c["archetype"] for c in customers}, {"steady", "tapering", "sporadic"})
        self.assertEqual({e["status"] for e in events}, {"success", "failed", "reversed"})
        self.assertTrue(all("state" not in r for r in customers + events))

    def test_customer_count_extension_preserves_existing_customers(self):
        customers, events = generate_rows(GeneratorConfig(customers=5))
        expanded_customers, expanded_events = generate_rows(GeneratorConfig(customers=8))
        ids = {c["customer_id"] for c in customers}
        self.assertEqual(customers, expanded_customers[:5])
        self.assertEqual(events, [e for e in expanded_events if e["customer_id"] in ids])

    def test_future_horizon_extension_cannot_change_historical_events(self):
        short = GeneratorConfig(customers=5, end_exclusive=date(2032, 6, 1))
        customers, events = generate_rows(short)
        expanded_customers, expanded_events = generate_rows(GeneratorConfig(customers=5))
        self.assertEqual(customers, expanded_customers)
        self.assertEqual(events, [e for e in expanded_events if e["event_date"] < "2032-06-01"])
