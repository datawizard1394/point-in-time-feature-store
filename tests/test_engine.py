import unittest
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from feature_store.engine import (
    build_offline_features,
    compute_features,
    freshness_report,
    materialize_online,
    parity_report,
)
from feature_store.io import load_observations, load_transactions
from feature_store.models import Transaction, parse_time


ROOT = Path(__file__).resolve().parents[1]
AS_OF = parse_time("2026-07-28T12:00:00Z")


class PointInTimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.transactions = load_transactions(ROOT / "data/transactions.csv")
        cls.observations = load_observations(ROOT / "data/observations.csv")

    def test_future_event_is_excluded(self) -> None:
        features = compute_features(
            self.transactions, customer_id="cus-101", as_of=AS_OF
        )
        self.assertEqual(features["spend_usd_30d"], 70.0)
        self.assertNotEqual(features["spend_usd_30d"], 1069.0)

    def test_late_arriving_event_is_excluded_from_historical_row(self) -> None:
        features = compute_features(
            self.transactions, customer_id="cus-101", as_of=AS_OF
        )
        self.assertEqual(features["tx_count_24h"], 1)
        self.assertEqual(features["spend_usd_24h"], 20.0)

    def test_offline_online_parity_passes_at_same_as_of(self) -> None:
        offline = build_offline_features(self.transactions, self.observations)
        online = materialize_online(
            self.transactions,
            [item.customer_id for item in self.observations],
            as_of=AS_OF,
        )
        report = parity_report(offline, online)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["features_compared"], 32)

    def test_parity_detects_drift(self) -> None:
        offline = build_offline_features(self.transactions, self.observations)
        online = materialize_online(
            self.transactions,
            [item.customer_id for item in self.observations],
            as_of=AS_OF,
        )
        online["entities"]["cus-101"]["spend_usd_24h"] = 999
        report = parity_report(offline, online)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["mismatch_count"], 1)

    def test_freshness_boundary(self) -> None:
        online = materialize_online(self.transactions, ["cus-101"], as_of=AS_OF)
        self.assertEqual(
            freshness_report(
                online, now=AS_OF + timedelta(minutes=60), max_age_minutes=60
            )["status"],
            "PASS",
        )
        self.assertEqual(
            freshness_report(
                online, now=AS_OF + timedelta(minutes=61), max_age_minutes=60
            )["status"],
            "FAIL",
        )

    def test_rejects_impossible_availability_clock(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot precede"):
            Transaction(
                transaction_id="bad",
                customer_id="cus",
                event_time=AS_OF,
                available_at=AS_OF - timedelta(seconds=1),
                amount_usd=Decimal("1"),
                status="completed",
            )


if __name__ == "__main__":
    unittest.main()
