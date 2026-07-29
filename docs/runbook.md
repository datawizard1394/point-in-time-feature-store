# Feature Store Parity and Freshness Runbook

> Synthetic educational procedure. It does not describe a deployed service.

## Signals

| Signal | Meaning | First action |
|---|---|---|
| Parity failure | Offline and online values differ at the same entity/time | Stop model promotion |
| Missing online entity | Materialization omitted a requested key | Check partition/entity selection |
| Freshness failure | Snapshot exceeds allowed age or is future-dated | Check scheduler and clocks |
| Input validation error | Source violates a feature invariant | Quarantine input |

## First response

1. Preserve `offline-features.csv`, `online-snapshot.json`, and both reports.
2. Record feature-view version and the exact `as_of` timestamp.
3. Stop promotion of training data or models built from the affected view.
4. Scope mismatches by entity and feature from `parity-report.json`.
5. Confirm whether the online snapshot and offline rows were computed at the
   same logical time.

## Parity diagnosis

1. Compare event-time and availability-time predicates.
2. Compare window boundaries and timezone normalization.
3. Confirm status filters and entity keys.
4. Check rounding, decimal conversion, null/default behavior, and field order.
5. Identify whether the mismatch is calculation drift, delayed materialization,
   partial entity selection, or corrupted persisted state.

Do not relax tolerance until the numerical source of drift is understood.

## Freshness diagnosis

1. Validate the materialization timestamp against a trusted UTC clock.
2. Inspect source arrival, orchestration dependencies, and last successful run.
3. Distinguish a stale snapshot from a future-dated clock-skew failure.
4. Re-run the materialization idempotently at an explicit `as_of` time.
5. Confirm freshness and parity before restoring consumers.

## Recovery

```bash
make check
make demo
```

For a targeted comparison:

```bash
PYTHONPATH=src python3 -m feature_store parity \
  --offline <offline.csv> \
  --online <online.json>
```

Close the incident only when the mismatch list is empty, freshness passes, the
feature-view version is unchanged or reviewed, and the exact failing case has a
regression test.

## Post-incident questions

- Which clock or boundary was misunderstood?
- Could a historical training set have been contaminated?
- Which models or predictions consumed the affected view?
- Was materialization idempotent and observable?
- What test, metric, or metadata would have detected the issue earlier?
