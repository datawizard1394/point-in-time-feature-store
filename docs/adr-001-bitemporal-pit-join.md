# ADR-001: Use event time and availability time for historical joins

- **Status:** Accepted for this synthetic demo
- **Date:** 2026-07-28
- **Decision owners:** Illustrative data platform team

## Context

An event may occur before a training observation but reach the data platform
after that observation. Joining only on business event time makes that
late-arriving record appear historically knowable and leaks future information
into the training row.

## Decision

Every source fact carries:

- an immutable business `event_time`;
- an immutable platform `available_at`.

For observation time `T`, a fact is eligible only when both timestamps are less
than or equal to `T`. Feature windows are then applied to eligible facts using
`T` as the upper bound.

Offline training rows and online snapshots call the same deterministic feature
function. A separate parity gate compares materialized values at a shared
`as_of` time.

## Consequences

### Positive

- Late-arriving facts cannot rewrite historical knowledge.
- Backfills are reproducible when the availability clock is retained.
- Parity failures identify materialization drift rather than different feature
  implementations.
- The rule is easy to test with boundary fixtures.

### Trade-offs

- Sources must preserve availability metadata.
- Corrected records need explicit versioning in a real bitemporal model.
- Shared code reduces skew but does not prove equivalence across different
  warehouse and serving-store execution engines.
- This in-memory implementation is intentionally not designed for scale.

## Alternatives considered

1. **Event time only:** rejected because late arrivals create label leakage.
2. **Ingestion time only:** rejected because business windows become inaccurate.
3. **Snapshot every raw source:** useful at scale but operationally heavier than
   this educational reference implementation.

## Validation

The fixture contains one future transaction and one transaction with a valid
past event time but future availability. Unit tests assert that both are
excluded from the historical feature row.
