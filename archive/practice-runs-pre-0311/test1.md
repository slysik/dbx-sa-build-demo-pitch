You are a Databricks Solutions Architect in a Databricks Free Edition workspace.

## Use case
Goal: simulate a real-time pipeline that streams **1,000 JSON records** using **Zerobus Ingest** into a **Bronze streaming Delta table**, transforms through **Silver** and **Gold** (medallion architecture), then builds a simple **dashboard** on the **Gold Delta table** using Databricks SQL queries.

## Constraints
- Prefer **SQL-first** for transformations (DDL/DML/aggregations/dashboard queries).
- Use **Python only** for:
  1) generating synthetic events
  2) sending those events via **Zerobus** (SDK or REST/gRPC) into a target table/stream
- Code must be **workspace-ready**, compile-safe, and heavily commented so I can explain it.
- Must be **idempotent** (reruns don’t duplicate data).
- Include a **validation harness** (row counts, uniqueness checks, rule checks, sample dashboard queries).
- Apply best practices: checkpointing where relevant, watermark + dedupe logic, deterministic MERGE, OPTIMIZE + ANALYZE, and clustering keys aligned to common filters.

## Important: Free Edition fallback
If Zerobus Ingest is not available in this workspace, implement a fallback:
- Python writes 1,000 JSON files to a landing path
- Use Auto Loader / Structured Streaming to ingest those files into Bronze
Keep the rest of the pipeline identical.

## Data model (Payment authorization events)
Each JSON record must include:
- txn_id (string, unique-ish)
- account_id (string)
- merchant_id (string)
- event_ts (timestamp ISO8601)
- amount (decimal)
- currency (USD/EUR/GBP)
- status (APPROVED/DECLINED/REVIEW)
- source_system (string)
- ingest_ts (timestamp added on ingest)

## Deliverable: produce a single notebook (ordered cells)

### 1) Discovery assumptions (short)
- Define business key, event-time semantics, late data tolerance, and dashboard KPIs.

### 2) Python: generate 1,000 events + send via Zerobus
- Generate 1,000 JSON events (include a few duplicates + a few late timestamps).
- Use Zerobus SDK (preferred) or REST/gRPC to ingest into the target Bronze table/stream.
- If Zerobus not available, fallback: write JSON files and ingest with Auto Loader.

### 3) Bronze (Delta table)
SQL:
- Create schemas: finserv_bronze / finserv_silver / finserv_gold
- Create `finserv_bronze.payment_events` with:
  - NOT NULL + CHECK constraints
  - generated column `event_date` from `event_ts`
  - `ingest_ts`
- If using Auto Loader fallback: provide the streaming write code (Python) into Bronze with checkpointing.

### 4) Silver (clean + dedupe + current-state)
SQL:
- Create `finserv_silver.payment_current`
- Create a deterministic dedupe view:
  - `ROW_NUMBER() OVER (PARTITION BY txn_id ORDER BY ingest_ts DESC) = 1`
- `MERGE` into `payment_current` (idempotent)
- Apply clustering `(account_id, event_date)`, then `OPTIMIZE` + `ANALYZE`

### 5) Gold (dashboard-ready)
SQL:
- Create `finserv_gold.payments_agg` (choose 1m/1h/1d granularity)
- Metrics:
  - txn_count
  - total_amount
  - approved_count / declined_count
  - decline_rate
- Build from Silver, idempotent (delete+insert for a date range)
- Apply clustering keys and run `OPTIMIZE` + `ANALYZE`

### 6) Dashboard queries (Databricks SQL)
Provide 6 dashboard-ready queries, e.g.:
1) approvals vs declines trend over time
2) top merchants by volume/amount
3) accounts with highest decline_rate
4) recent “spike” merchants (last hour vs baseline)
5) recent transactions (latest 100)
6) anomaly candidates (high amount + review/declined)

### 7) Validation harness (SQL)
- row counts (bronze/silver/gold)
- uniqueness check: duplicates txn_id in Silver (should be 0)
- constraint sanity checks (bad currency/status/negative amount)
- one pruning-friendly query filtered on `event_date` + `account_id`

### 8) Explain distributed reasoning (short notes)
Explain:
- where shuffles happen (window/merge/groupBy)
- why dedupe + deterministic merge matters
- how clustering + OPTIMIZE reduce scans
- how this scales beyond 1,000 events (keys, partition/clustering, incremental processing)

## Output format
Return:
1) architecture summary (Bronze → Silver → Gold)
2) ordered notebook cells (Python then SQL, with comments)
3) run instructions (what to execute first/next)
4) “talk track” bullets I can say while demoing
