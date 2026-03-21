# Discovery Brief — Wealth Management Data  (Bronze)

**Date:** 2026-03-11
**Domain:** FinServ 
**Entity:** wealth_mangagement (fact), customer  (dim)
**Scale:** 10M fact rows + 10K dim rows
**Processing:** Batch (PySpark notebook → Delta Bronze)
**Layers:** Bronze only
**DQ:** CHECK constraints on Bronze tables

## Assumptions
- `spark.range(100_000_000)` native PySpark data gen, no Faker
- Dimension: `spark.range(10_000)` — small, broadcastable
- Bronze: append-only with ingestion metadata (`ingest_ts`, `source_system`, `batch_id`)
- Liquid clustering on `transaction_ts` for fact table
- Catalog: `interview` | Schema: `payments`
- Deterministic data via `hash()` + modular arithmetic (no `rand()`)
- Currency: USD-weighted with some EUR/GBP/JPY via hash distribution
- Status: COMPLETED (70%), PENDING (15%), FAILED (10%), REVERSED (5%)

## Key Deliverables
- [ ] PySpark notebook: 100M payment transactions → Bronze Delta
- [ ] PySpark notebook: 10K payment types dim → Bronze Delta
- [ ] Unity Catalog tables: `interview.payments.bronze_payment_transactions`, `interview.payments.bronze_payment_types`
- [ ] CHECK constraints (DQ gates on Bronze tables)
- [ ] Validation: row counts, null audit, constraint verification, sample data

## Features to Demonstrate
- `spark.range()` at scale (100M rows, single-param scaling)
- Hash-based deterministic data generation
- Broadcast join (dim into fact)
- Liquid clustering
- Unity Catalog 3-level namespace
- Bronze metadata columns
- CHECK constraints (DQ enforcement at Bronze — amount > 0, valid status, NOT NULL on keys)

## Entity Model
| Table | Layer | Type | Columns |
|-------|-------|------|---------|
| `bronze_payment_types` | Bronze | Dim | payment_type_id, type_name, category, processor, is_active, ingest_ts |
| `bronze_payment_transactions` | Bronze | Fact | transaction_id, payment_type_id, amount, currency, sender_id, receiver_id, status, transaction_ts, ingest_ts, source_system, batch_id |

## Dedup Key
- `transaction_id` (natural key)

## Partition Strategy
- Liquid clustering on `transaction_ts` (fact)
- No clustering on dim (10K rows, trivial)

## Narration Points
1. Why `spark.range()` over Faker — native Spark, no Python UDF serialization overhead, scales linearly
2. Hash-based deterministic generation — reproducible datasets, same seed = same data
3. Broadcast join for dim enrichment — 10K rows fits in driver memory, avoids shuffle
4. Liquid clustering over legacy partitioning — auto-optimized, no skew risk on high-cardinality timestamps
5. Bronze metadata columns — lineage tracking, batch replay, source auditing
6. 100M rows tests real cluster behavior — AQE, shuffle partitions, spill-to-disk visibility
7. CHECK constraints at Bronze — shift-left DQ, catch bad data at ingestion not downstream
