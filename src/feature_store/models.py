"""Domain models with explicit event-time and availability-time semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    customer_id: str
    event_time: datetime
    available_at: datetime
    amount_usd: Decimal
    status: str

    def __post_init__(self) -> None:
        if self.available_at < self.event_time:
            raise ValueError(
                f"{self.transaction_id}: available_at cannot precede event_time"
            )
        if self.amount_usd < 0:
            raise ValueError(f"{self.transaction_id}: amount_usd cannot be negative")


@dataclass(frozen=True)
class Observation:
    observation_id: str
    customer_id: str
    label_time: datetime
    label: int

    def __post_init__(self) -> None:
        if self.label not in (0, 1):
            raise ValueError(f"{self.observation_id}: label must be 0 or 1")
