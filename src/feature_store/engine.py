"""Leakage-safe feature computation and offline/online consistency checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable

from .io import iso
from .models import Observation, Transaction


FEATURE_NAMES = (
    "tx_count_24h",
    "spend_usd_24h",
    "tx_count_7d",
    "spend_usd_7d",
    "tx_count_30d",
    "spend_usd_30d",
    "avg_ticket_usd_30d",
    "last_transaction_age_hours",
)


def _eligible(
    transactions: Iterable[Transaction],
    *,
    customer_id: str,
    as_of: datetime,
) -> list[Transaction]:
    """Apply the two clocks required for a leakage-safe point-in-time join.

    A transaction must have happened before the observation and must also have
    been available to the feature pipeline by that time. The second predicate
    prevents late-arriving facts from leaking into historical training rows.
    """

    return [
        item
        for item in transactions
        if item.customer_id == customer_id
        and item.status == "completed"
        and item.event_time <= as_of
        and item.available_at <= as_of
    ]


def compute_features(
    transactions: Iterable[Transaction],
    *,
    customer_id: str,
    as_of: datetime,
) -> dict[str, int | float | None]:
    eligible = _eligible(transactions, customer_id=customer_id, as_of=as_of)

    def window(hours: int) -> list[Transaction]:
        lower = as_of - timedelta(hours=hours)
        return [item for item in eligible if lower < item.event_time <= as_of]

    day = window(24)
    week = window(24 * 7)
    month = window(24 * 30)

    def total(items: list[Transaction]) -> Decimal:
        return sum((item.amount_usd for item in items), start=Decimal("0"))

    month_total = total(month)
    average = month_total / len(month) if month else Decimal("0")
    latest = max((item.event_time for item in eligible), default=None)
    age = (
        round((as_of - latest).total_seconds() / 3600, 4)
        if latest is not None
        else None
    )
    return {
        "tx_count_24h": len(day),
        "spend_usd_24h": float(round(total(day), 2)),
        "tx_count_7d": len(week),
        "spend_usd_7d": float(round(total(week), 2)),
        "tx_count_30d": len(month),
        "spend_usd_30d": float(round(month_total, 2)),
        "avg_ticket_usd_30d": float(round(average, 2)),
        "last_transaction_age_hours": age,
    }


def build_offline_features(
    transactions: list[Transaction], observations: list[Observation]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for observation in observations:
        rows.append(
            {
                "observation_id": observation.observation_id,
                "customer_id": observation.customer_id,
                "label_time": iso(observation.label_time),
                **compute_features(
                    transactions,
                    customer_id=observation.customer_id,
                    as_of=observation.label_time,
                ),
                "label": observation.label,
                "synthetic_demo": True,
            }
        )
    return rows


def materialize_online(
    transactions: list[Transaction],
    customers: Iterable[str],
    *,
    as_of: datetime,
) -> dict[str, Any]:
    return {
        "feature_view": "customer_transaction_features",
        "version": "1.0.0",
        "materialized_at": iso(as_of),
        "synthetic_demo": True,
        "entities": {
            customer: compute_features(
                transactions,
                customer_id=customer,
                as_of=as_of,
            )
            for customer in sorted(set(customers))
        },
    }


def parity_report(
    offline_rows: list[dict[str, Any]],
    online_snapshot: dict[str, Any],
    *,
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    entities = online_snapshot.get("entities", {})
    for row in offline_rows:
        customer = row["customer_id"]
        online = entities.get(customer)
        if online is None:
            mismatches.append(
                {"customer_id": customer, "feature": "*", "reason": "missing online"}
            )
            continue
        for feature in FEATURE_NAMES:
            left = _number(row[feature])
            right = _number(online.get(feature))
            if left is None or right is None:
                equal = left is right
            else:
                equal = abs(left - right) <= tolerance
            if not equal:
                mismatches.append(
                    {
                        "customer_id": customer,
                        "feature": feature,
                        "offline": left,
                        "online": right,
                    }
                )
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "rows_compared": len(offline_rows),
        "features_compared": len(offline_rows) * len(FEATURE_NAMES),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "synthetic_demo": True,
    }


def freshness_report(
    online_snapshot: dict[str, Any],
    *,
    now: datetime,
    max_age_minutes: float,
) -> dict[str, Any]:
    materialized = datetime.fromisoformat(
        str(online_snapshot["materialized_at"]).replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    now_utc = now.astimezone(timezone.utc)
    age = (now_utc - materialized).total_seconds() / 60
    healthy = 0 <= age <= max_age_minutes
    return {
        "status": "PASS" if healthy else "FAIL",
        "materialized_at": iso(materialized),
        "observed_age_minutes": round(age, 4),
        "max_age_minutes": max_age_minutes,
        "synthetic_demo": True,
    }


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
