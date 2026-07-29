"""CLI for building and verifying synthetic point-in-time features."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .engine import (
    build_offline_features,
    freshness_report,
    materialize_online,
    parity_report,
)
from .io import (
    load_observations,
    load_transactions,
    read_feature_csv,
    read_json,
    write_feature_csv,
    write_json,
)
from .models import parse_time


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="pit-feature-store")
    commands = root.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("demo", help="run the deterministic end-to-end demo")
    demo.add_argument("--transactions", type=Path, required=True)
    demo.add_argument("--observations", type=Path, required=True)
    demo.add_argument("--as-of", type=parse_time, required=True)
    demo.add_argument("--output-dir", type=Path, default=Path(".artifacts/demo"))
    demo.add_argument("--max-age-minutes", type=float, default=60)

    parity = commands.add_parser("parity", help="compare offline and online values")
    parity.add_argument("--offline", type=Path, required=True)
    parity.add_argument("--online", type=Path, required=True)

    freshness = commands.add_parser("freshness", help="check online materialization age")
    freshness.add_argument("--online", type=Path, required=True)
    freshness.add_argument("--now", type=parse_time, required=True)
    freshness.add_argument("--max-age-minutes", type=float, required=True)
    return root


def run_demo(args: argparse.Namespace) -> int:
    transactions = load_transactions(args.transactions)
    observations = load_observations(args.observations)
    offline = build_offline_features(transactions, observations)
    online = materialize_online(
        transactions,
        [item.customer_id for item in observations],
        as_of=args.as_of,
    )
    parity = parity_report(offline, online)
    freshness = freshness_report(
        online,
        now=args.as_of,
        max_age_minutes=args.max_age_minutes,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_feature_csv(args.output_dir / "offline-features.csv", offline)
    write_json(args.output_dir / "online-snapshot.json", online)
    write_json(args.output_dir / "parity-report.json", parity)
    write_json(args.output_dir / "freshness-report.json", freshness)
    summary = {
        "status": (
            "PASS"
            if parity["status"] == "PASS" and freshness["status"] == "PASS"
            else "FAIL"
        ),
        "offline_rows": len(offline),
        "online_entities": len(online["entities"]),
        "parity": parity["status"],
        "freshness": freshness["status"],
        "synthetic_demo": True,
    }
    write_json(args.output_dir / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "demo":
            return run_demo(args)
        if args.command == "parity":
            result = parity_report(read_feature_csv(args.offline), read_json(args.online))
        else:
            result = freshness_report(
                read_json(args.online),
                now=args.now,
                max_age_minutes=args.max_age_minutes,
            )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
