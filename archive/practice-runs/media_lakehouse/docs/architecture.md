# Architecture — Media Lakehouse (CDC)

## Design Decisions

1. **spark.range() for data generation** — distributed, no driver pressure, scales linearly
2. **CDC at Bronze** — `_change_type` + `_commit_timestamp` columns simulate a real CDC feed (event corrections, late-arriving updates, cancellations)
3. **APPLY CHANGES at Silver** — SDP handles sequencing, dedup, and delete propagation automatically — no manual MERGE logic
4. **SCD Type 1** — latest state only (no history) — appropriate for streaming events where corrections replace originals
5. **Metric view with star-schema joins** — governed KPIs that join Silver fact with Bronze dims in YAML, consistent across all consumers
6. **Liquid clustering** — auto-optimized file layout on `event_ts` (Silver) and date dims (Gold)

## Medallion Flow

```mermaid
graph TD
    GEN[spark.range 100K + CDC columns] --> BRONZE[Bronze Delta Tables]
    BRONZE -->|APPLY CHANGES SCD1| SILVER[Silver — Latest State 99K]
    SILVER -->|MV + dim joins| GOLD[Gold — Aggregated]
    GOLD -->|SQL| DASH[AI/BI Dashboard]
    SILVER -->|YAML joins| METRIC[Metric View — Governed KPIs]
```

## CDC Flow Detail

```mermaid
sequenceDiagram
    participant B as Bronze (105K rows)
    participant S as Silver (99K rows)
    Note over B: 100K INSERTs (base events)
    Note over B: 4K UPDATEs (corrected watch_minutes)
    Note over B: 1K DELETEs (removed events)
    B->>S: APPLY CHANGES (SEQUENCE BY _commit_timestamp)
    Note over S: UPDATEs overwrite INSERTs (same event_id)
    Note over S: DELETEs remove rows
    Note over S: Result: 99K rows = latest state
```

## Scaling Strategy

| Scale | N_EVENTS | Bronze Rows | Silver Rows | Runtime |
|-------|----------|-------------|-------------|---------|
| Dev | 100 | 105 | 99 | < 5 sec |
| Demo | 100,000 | 105,000 | 99,000 | < 30 sec |
| Prod | 1,000,000+ | 1,050,000 | 990,000 | < 2 min |

Zero code changes — only `N_EVENTS` parameter changes.

## What I'd Add in Production

- [ ] Service principal for job ownership
- [ ] CI/CD with `bundle validate` + `bundle deploy` in GitHub Actions
- [ ] SDP `EXPECT` constraints on Silver (null checks, range validation)
- [ ] SCD Type 2 for subscriber dim (track plan changes over time)
- [ ] Monitoring: row count alerts, CDC lag tracking, SLA breach notifications
- [ ] Multi-environment targets: dev → staging → prod
- [ ] Streaming ingestion from Kafka/Event Hubs for real-time CDC
