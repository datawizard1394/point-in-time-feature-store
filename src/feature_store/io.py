"""CSV and JSON adapters for deterministic fixtures and artifacts."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .models import Observation, Transaction, parse_time


def load_transactions(path: str | Path) -> list[Transaction]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "transaction_id",
        "customer_id",
        "event_time",
        "available_at",
        "amount_usd",
        "status",
    }
    if rows and not required.issubset(rows[0]):
        raise ValueError(f"Transaction CSV is missing: {sorted(required - rows[0].keys())}")
    transactions = [
        Transaction(
            transaction_id=row["transaction_id"],
            customer_id=row["customer_id"],
            event_time=parse_time(row["event_time"]),
            available_at=parse_time(row["available_at"]),
            amount_usd=Decimal(row["amount_usd"]),
            status=row["status"],
        )
        for row in rows
    ]
    identifiers = [item.transaction_id for item in transactions]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("transaction_id values must be unique")
    return sorted(transactions, key=lambda item: (item.event_time, item.transaction_id))


def load_observations(path: str | Path) -> list[Observation]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"observation_id", "customer_id", "label_time", "label"}
    if rows and not required.issubset(rows[0]):
        raise ValueError(f"Observation CSV is missing: {sorted(required - rows[0].keys())}")
    return [
        Observation(
            observation_id=row["observation_id"],
            customer_id=row["customer_id"],
            label_time=parse_time(row["label_time"]),
            label=int(row["label"]),
        )
        for row in rows
    ]


def write_feature_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Cannot write an empty feature set")
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_feature_csv(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
