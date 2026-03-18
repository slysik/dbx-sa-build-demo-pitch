# Databricks notebook source
# MAGIC %md
# MAGIC # FinServ Payment Pipeline — Medallion Architecture Demo
# MAGIC
# MAGIC **Bronze → Silver → Gold** pipeline for payment authorization events.
# MAGIC
# MAGIC | Layer | Table | Purpose |
# MAGIC |-------|-------|---------|
# MAGIC | Bronze | `finserv_demo.bronze.payment_events` | Raw ingest, 1,000 rows (incl. 30 dupes) |
# MAGIC | Silver | `finserv_demo.silver.payment_current` | Deduplicated current-state (ROW_NUMBER + MERGE) |
# MAGIC | Gold | `finserv_demo.gold.payments_agg_1d` | Daily metrics by merchant + currency |
# MAGIC
# MAGIC **Key patterns:** SQL-first, DECIMAL for money, deterministic MERGE, idempotent Gold rebuild,
# MAGIC CHECK constraints, Liquid Clustering, OPTIMIZE + ANALYZE, validation harness.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Discovery Assumptions
# MAGIC
# MAGIC | Question | Answer |
# MAGIC |----------|--------|
# MAGIC | Business key | `txn_id` — unique payment authorization ID |
# MAGIC | Event-time semantics | `event_ts` from source system; `ingest_ts` for pipeline ordering |
# MAGIC | Late data tolerance | Up to 90 days (some reprocessed payments arrive late) |
# MAGIC | Dedup strategy | ROW_NUMBER by `txn_id`, latest `ingest_ts` wins |
# MAGIC | Dashboard KPIs | Total volume, transaction count, decline rate, top merchants |
# MAGIC | Granularity | Daily aggregation (`event_date`) for Gold |

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 0: Environment Setup

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- STEP 0: ENVIRONMENT BOOTSTRAP
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- Talk track: "First thing I do is bootstrap the environment.
# MAGIC -- Three schemas — bronze, silver, gold — in a dedicated catalog.
# MAGIC -- This keeps the demo isolated from production data."
# MAGIC -- ──────────────────────────────────────────────────────────────────
# MAGIC
# MAGIC -- NOTE: On this Azure workspace, CREATE CATALOG requires MANAGED LOCATION.
# MAGIC -- If catalog already exists, this is a no-op.
# MAGIC CREATE CATALOG IF NOT EXISTS finserv_demo
# MAGIC   MANAGED LOCATION 'abfss://unity-catalog-storage@dbstorageihud5phl6ewyg.dfs.core.windows.net/7405613453749188';
# MAGIC
# MAGIC CREATE SCHEMA IF NOT EXISTS finserv_demo.bronze;
# MAGIC CREATE SCHEMA IF NOT EXISTS finserv_demo.silver;
# MAGIC CREATE SCHEMA IF NOT EXISTS finserv_demo.gold;
# MAGIC
# MAGIC USE CATALOG finserv_demo;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Bronze DDL — Raw Payment Events

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- CELL 1: BRONZE DDL — Raw payment authorization events
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- Talk track: "Bronze is our raw landing zone. We capture everything
# MAGIC -- as-is, add ingest metadata, and enforce basic shape constraints
# MAGIC -- at the storage layer so garbage never enters the lakehouse."
# MAGIC -- ──────────────────────────────────────────────────────────────────
# MAGIC
# MAGIC CREATE TABLE IF NOT EXISTS finserv_demo.bronze.payment_events (
# MAGIC   txn_id        STRING        NOT NULL  COMMENT 'Business key — unique payment authorization ID',
# MAGIC   account_id    STRING        NOT NULL  COMMENT 'Customer account identifier',
# MAGIC   merchant_id   STRING        NOT NULL  COMMENT 'Merchant receiving the payment',
# MAGIC   event_ts      TIMESTAMP     NOT NULL  COMMENT 'When the payment event occurred (source system time)',
# MAGIC   amount        DECIMAL(18,2) NOT NULL  COMMENT 'Transaction amount — DECIMAL, never FLOAT for money',
# MAGIC   currency      STRING        NOT NULL  COMMENT 'ISO currency code: USD, EUR, GBP',
# MAGIC   status        STRING        NOT NULL  COMMENT 'Authorization result: APPROVED, DECLINED, REVIEW',
# MAGIC   source_system STRING        NOT NULL  COMMENT 'Originating system identifier',
# MAGIC   ingest_ts     TIMESTAMP     NOT NULL  COMMENT 'When this row landed in Bronze',
# MAGIC   event_date    DATE          GENERATED ALWAYS AS (CAST(event_ts AS DATE)) COMMENT 'Derived cluster key from event_ts'
# MAGIC )
# MAGIC COMMENT 'Raw payment authorization events — append-only Bronze layer'
# MAGIC TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

# COMMAND ----------

# MAGIC %sql
# MAGIC -- CHECK constraints: enforce data quality at the storage layer
# MAGIC -- Talk track: "These constraints fire at write time. If bad data
# MAGIC -- tries to enter Bronze, Delta rejects the entire write."
# MAGIC
# MAGIC ALTER TABLE finserv_demo.bronze.payment_events
# MAGIC ADD CONSTRAINT chk_currency CHECK (currency IN ('USD', 'EUR', 'GBP'));
# MAGIC
# MAGIC ALTER TABLE finserv_demo.bronze.payment_events
# MAGIC ADD CONSTRAINT chk_status CHECK (status IN ('APPROVED', 'DECLINED', 'REVIEW'));
# MAGIC
# MAGIC ALTER TABLE finserv_demo.bronze.payment_events
# MAGIC ADD CONSTRAINT chk_amount CHECK (amount >= 0);

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Liquid Clustering: align with common query filters
# MAGIC -- Talk track: "In Netezza, we'd pick distribution keys upfront and
# MAGIC -- be locked in. Liquid Clustering gives the same data locality
# MAGIC -- benefit but adapts automatically as query patterns shift."
# MAGIC
# MAGIC ALTER TABLE finserv_demo.bronze.payment_events CLUSTER BY (account_id, event_date);

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Synthetic Data Generation — 1,000 Payment Events

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- CELL 2: SYNTHETIC DATA — 1,000 payment authorization events
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- Talk track: "I'm generating 1,000 realistic payment events using
# MAGIC -- pure SQL. I've seeded in ~30 duplicates and ~20 late-arriving
# MAGIC -- events to prove my dedupe and late-data handling work correctly."
# MAGIC --
# MAGIC -- NOTE: rand() requires a constant seed in Databricks SQL, so we
# MAGIC -- use hash(id, 'salt') with modular arithmetic for deterministic
# MAGIC -- per-row randomness. Also, INTERVAL doesn't accept expressions —
# MAGIC -- use timestampadd() instead.
# MAGIC -- ──────────────────────────────────────────────────────────────────
# MAGIC
# MAGIC INSERT INTO finserv_demo.bronze.payment_events
# MAGIC   (txn_id, account_id, merchant_id, event_ts, amount, currency, status, source_system, ingest_ts)
# MAGIC WITH base AS (
# MAGIC   SELECT
# MAGIC     id,
# MAGIC     concat('TXN-', lpad(cast(id as string), 6, '0')) AS txn_id,
# MAGIC     concat('ACCT-', lpad(cast(abs(hash(id, 'acct')) % 200 + 1 as string), 4, '0')) AS account_id,
# MAGIC     concat('MERCH-', lpad(cast(abs(hash(id, 'merch')) % 50 + 1 as string), 3, '0')) AS merchant_id,
# MAGIC     -- ~20 late events (30-90 days old), rest within last 7 days
# MAGIC     CASE
# MAGIC       WHEN id <= 20 THEN timestampadd(DAY, -(abs(hash(id, 'late')) % 60 + 30), current_timestamp())
# MAGIC       ELSE timestampadd(MINUTE, -(abs(hash(id, 'ts')) % 10080), current_timestamp())
# MAGIC     END AS event_ts,
# MAGIC     -- Amounts: ~5% high-value ($1k-$10k), rest $5-$500
# MAGIC     CASE
# MAGIC       WHEN abs(hash(id, 'hival')) % 100 > 94
# MAGIC         THEN cast(abs(hash(id, 'amt1')) % 9000 + 1000 as DECIMAL(18,2))
# MAGIC       ELSE cast((abs(hash(id, 'amt2')) % 49500 + 500) / 100.0 as DECIMAL(18,2))
# MAGIC     END AS amount,
# MAGIC     -- Currency: 70% USD, 20% EUR, 10% GBP
# MAGIC     CASE
# MAGIC       WHEN abs(hash(id, 'cur')) % 10 < 7 THEN 'USD'
# MAGIC       WHEN abs(hash(id, 'cur')) % 10 < 9 THEN 'EUR'
# MAGIC       ELSE 'GBP'
# MAGIC     END AS currency,
# MAGIC     -- Status: 80% approved, 12% declined, 8% review
# MAGIC     CASE
# MAGIC       WHEN abs(hash(id, 'stat')) % 100 < 80 THEN 'APPROVED'
# MAGIC       WHEN abs(hash(id, 'stat')) % 100 < 92 THEN 'DECLINED'
# MAGIC       ELSE 'REVIEW'
# MAGIC     END AS status,
# MAGIC     CASE
# MAGIC       WHEN abs(hash(id, 'src')) % 10 < 5 THEN 'CORE_BANKING'
# MAGIC       WHEN abs(hash(id, 'src')) % 10 < 8 THEN 'MOBILE_APP'
# MAGIC       ELSE 'POS_TERMINAL'
# MAGIC     END AS source_system
# MAGIC   FROM (SELECT explode(sequence(1, 970)) AS id)
# MAGIC ),
# MAGIC dupes AS (
# MAGIC   -- 30 exact duplicates (same txn_id, later ingest_ts)
# MAGIC   SELECT txn_id, account_id, merchant_id, event_ts, amount, currency, status, source_system
# MAGIC   FROM base WHERE id <= 30
# MAGIC )
# MAGIC -- Original 970 rows
# MAGIC SELECT txn_id, account_id, merchant_id, event_ts, amount, currency, status, source_system,
# MAGIC        current_timestamp() AS ingest_ts
# MAGIC FROM base
# MAGIC UNION ALL
# MAGIC -- 30 duplicate rows (same txn_id, slightly later ingest_ts)
# MAGIC SELECT txn_id, account_id, merchant_id, event_ts, amount, currency, status, source_system,
# MAGIC        timestampadd(SECOND, 1, current_timestamp()) AS ingest_ts
# MAGIC FROM dupes;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Quick sanity check: should see 1,000 rows, 970 unique txn_ids
# MAGIC SELECT count(*) AS total_rows,
# MAGIC        count(DISTINCT txn_id) AS unique_txns,
# MAGIC        min(event_date) AS earliest_date,
# MAGIC        max(event_date) AS latest_date
# MAGIC FROM finserv_demo.bronze.payment_events;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Silver — Dedupe + Current-State MERGE

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- CELL 3: SILVER DDL — Deduplicated current-state payment records
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- Talk track: "Silver is where we enforce data integrity. Delta
# MAGIC -- doesn't have native PK enforcement, so I build it INTO the
# MAGIC -- pipeline — ROW_NUMBER staging guarantees exactly one source row
# MAGIC -- per business key before the MERGE. This is more robust than
# MAGIC -- relying on a constraint violation because we handle it explicitly."
# MAGIC -- ──────────────────────────────────────────────────────────────────
# MAGIC
# MAGIC CREATE TABLE IF NOT EXISTS finserv_demo.silver.payment_current (
# MAGIC   txn_id        STRING        NOT NULL,
# MAGIC   account_id    STRING        NOT NULL,
# MAGIC   merchant_id   STRING        NOT NULL,
# MAGIC   event_ts      TIMESTAMP     NOT NULL,
# MAGIC   amount        DECIMAL(18,2) NOT NULL,
# MAGIC   currency      STRING        NOT NULL,
# MAGIC   status        STRING        NOT NULL,
# MAGIC   source_system STRING        NOT NULL,
# MAGIC   ingest_ts     TIMESTAMP     NOT NULL,
# MAGIC   event_date    DATE          NOT NULL
# MAGIC )
# MAGIC COMMENT 'Deduplicated current-state payment records — one row per txn_id';

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- CELL 4: SILVER MERGE — Deterministic dedupe via ROW_NUMBER
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- Talk track: "The ROW_NUMBER window partitions by txn_id and picks
# MAGIC -- the latest ingest_ts. This means if the same transaction arrives
# MAGIC -- twice, we always keep the most recent version. The MERGE is
# MAGIC -- idempotent — running it again produces the same result."
# MAGIC --
# MAGIC -- WHY inline subquery instead of TEMP VIEW:
# MAGIC -- Each serverless SQL statement runs in its own session, so TEMP
# MAGIC -- VIEWs don't persist. In a notebook they're fine, but inline
# MAGIC -- subqueries work everywhere.
# MAGIC -- ──────────────────────────────────────────────────────────────────
# MAGIC
# MAGIC MERGE INTO finserv_demo.silver.payment_current AS t
# MAGIC USING (
# MAGIC   SELECT txn_id, account_id, merchant_id, event_ts, amount,
# MAGIC          currency, status, source_system, ingest_ts, event_date
# MAGIC   FROM (
# MAGIC     SELECT *, row_number() OVER (
# MAGIC       PARTITION BY txn_id ORDER BY ingest_ts DESC
# MAGIC     ) AS rn
# MAGIC     FROM finserv_demo.bronze.payment_events
# MAGIC   )
# MAGIC   WHERE rn = 1
# MAGIC ) AS s
# MAGIC ON t.txn_id = s.txn_id
# MAGIC WHEN MATCHED AND s.ingest_ts > t.ingest_ts THEN UPDATE SET
# MAGIC   t.account_id    = s.account_id,
# MAGIC   t.merchant_id   = s.merchant_id,
# MAGIC   t.event_ts      = s.event_ts,
# MAGIC   t.amount        = s.amount,
# MAGIC   t.currency      = s.currency,
# MAGIC   t.status        = s.status,
# MAGIC   t.source_system = s.source_system,
# MAGIC   t.ingest_ts     = s.ingest_ts,
# MAGIC   t.event_date    = s.event_date
# MAGIC WHEN NOT MATCHED THEN INSERT (
# MAGIC   txn_id, account_id, merchant_id, event_ts, amount,
# MAGIC   currency, status, source_system, ingest_ts, event_date
# MAGIC ) VALUES (
# MAGIC   s.txn_id, s.account_id, s.merchant_id, s.event_ts, s.amount,
# MAGIC   s.currency, s.status, s.source_system, s.ingest_ts, s.event_date
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Post-MERGE: constraints + clustering + optimize + analyze
# MAGIC ALTER TABLE finserv_demo.silver.payment_current
# MAGIC ADD CONSTRAINT chk_silver_amt CHECK (amount >= 0);

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE finserv_demo.silver.payment_current CLUSTER BY (account_id, event_date);

# COMMAND ----------

# MAGIC %sql
# MAGIC OPTIMIZE finserv_demo.silver.payment_current;

# COMMAND ----------

# MAGIC %sql
# MAGIC ANALYZE TABLE finserv_demo.silver.payment_current COMPUTE STATISTICS FOR ALL COLUMNS;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Gold — Daily Aggregates (Idempotent Window Rebuild)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- CELL 5: GOLD DDL — Daily payment aggregates
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- Talk track: "Gold is dashboard-ready. I use daily granularity
# MAGIC -- because our KPIs are daily decline rates and volume. The table
# MAGIC -- is idempotent — I delete-then-insert for a date window so reruns
# MAGIC -- never duplicate data. In Netezza we'd TRUNCATE and reload;
# MAGIC -- this scopes the rebuild to the changed range — same correctness,
# MAGIC -- 100x less I/O at scale."
# MAGIC -- ──────────────────────────────────────────────────────────────────
# MAGIC
# MAGIC CREATE TABLE IF NOT EXISTS finserv_demo.gold.payments_agg_1d (
# MAGIC   event_date      DATE           NOT NULL,
# MAGIC   merchant_id     STRING         NOT NULL,
# MAGIC   currency        STRING         NOT NULL,
# MAGIC   txn_count       BIGINT         NOT NULL,
# MAGIC   total_amount    DECIMAL(38,2)  NOT NULL  COMMENT 'DECIMAL(38,2) for aggregate sums — prevents overflow',
# MAGIC   approved_count  BIGINT         NOT NULL,
# MAGIC   declined_count  BIGINT         NOT NULL,
# MAGIC   review_count    BIGINT         NOT NULL,
# MAGIC   decline_rate    DECIMAL(5,4)            COMMENT 'declined / total — NULL if txn_count = 0'
# MAGIC )
# MAGIC COMMENT 'Daily payment metrics by merchant and currency — idempotent rebuild';

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Idempotent rebuild: delete-window + insert-window
# MAGIC DELETE FROM finserv_demo.gold.payments_agg_1d
# MAGIC WHERE event_date >= (SELECT min(event_date) FROM finserv_demo.silver.payment_current)
# MAGIC   AND event_date <= (SELECT max(event_date) FROM finserv_demo.silver.payment_current);

# COMMAND ----------

# MAGIC %sql
# MAGIC INSERT INTO finserv_demo.gold.payments_agg_1d
# MAGIC SELECT
# MAGIC   event_date,
# MAGIC   merchant_id,
# MAGIC   currency,
# MAGIC   count(*)                                                    AS txn_count,
# MAGIC   cast(sum(amount) as DECIMAL(38,2))                          AS total_amount,
# MAGIC   count(CASE WHEN status = 'APPROVED' THEN 1 END)            AS approved_count,
# MAGIC   count(CASE WHEN status = 'DECLINED' THEN 1 END)            AS declined_count,
# MAGIC   count(CASE WHEN status = 'REVIEW'   THEN 1 END)            AS review_count,
# MAGIC   cast(
# MAGIC     count(CASE WHEN status = 'DECLINED' THEN 1 END) * 1.0
# MAGIC     / count(*)
# MAGIC   as DECIMAL(5,4))                                            AS decline_rate
# MAGIC FROM finserv_demo.silver.payment_current
# MAGIC GROUP BY event_date, merchant_id, currency;

# COMMAND ----------

# MAGIC %sql
# MAGIC ALTER TABLE finserv_demo.gold.payments_agg_1d CLUSTER BY (event_date, merchant_id);

# COMMAND ----------

# MAGIC %sql
# MAGIC OPTIMIZE finserv_demo.gold.payments_agg_1d;

# COMMAND ----------

# MAGIC %sql
# MAGIC ANALYZE TABLE finserv_demo.gold.payments_agg_1d COMPUTE STATISTICS FOR ALL COLUMNS;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Proof Points

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- PROOF POINT 1: Constraint Enforcement
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- Talk track: "Delta enforces CHECK constraints at write time.
# MAGIC -- Watch this INSERT get rejected — negative amount violates our
# MAGIC -- chk_silver_amt constraint."
# MAGIC -- ──────────────────────────────────────────────────────────────────
# MAGIC
# MAGIC -- This SHOULD fail with: CHECK constraint chk_silver_amt (amount >= 0) violated
# MAGIC INSERT INTO finserv_demo.silver.payment_current VALUES
# MAGIC   ('BAD-TXN-001', 'ACCT-9999', 'MERCH-999', current_timestamp(),
# MAGIC    -100.00, 'USD', 'APPROVED', 'TEST', current_timestamp(), current_date());

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- PROOF POINT 2: Pruning Proof (EXPLAIN)
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- Talk track: "My CLUSTER BY keys match my WHERE clause. Look at
# MAGIC -- DataFilters in the plan — the engine skips irrelevant files."
# MAGIC -- ──────────────────────────────────────────────────────────────────
# MAGIC
# MAGIC EXPLAIN SELECT * FROM finserv_demo.silver.payment_current
# MAGIC WHERE account_id = 'ACCT-0001' AND event_date >= '2026-02-01';

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- PROOF POINT 3: Time Travel
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- Talk track: "Full audit trail built into Delta — no extra
# MAGIC -- infrastructure. I can query any historical version."
# MAGIC -- ──────────────────────────────────────────────────────────────────
# MAGIC
# MAGIC DESCRIBE HISTORY finserv_demo.silver.payment_current;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Query the table as it was at creation time (empty — before MERGE)
# MAGIC SELECT count(*) AS rows_at_version_0
# MAGIC FROM finserv_demo.silver.payment_current VERSION AS OF 0;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Dashboard Queries

# COMMAND ----------

# MAGIC %sql
# MAGIC -- DASHBOARD 1: Approvals vs Declines trend over time
# MAGIC SELECT event_date,
# MAGIC        sum(approved_count) AS approved,
# MAGIC        sum(declined_count) AS declined,
# MAGIC        sum(review_count)   AS review
# MAGIC FROM finserv_demo.gold.payments_agg_1d
# MAGIC GROUP BY event_date
# MAGIC ORDER BY event_date;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- DASHBOARD 2: Top merchants by volume
# MAGIC SELECT merchant_id,
# MAGIC        cast(sum(total_amount) as DECIMAL(38,2)) AS total_volume,
# MAGIC        sum(txn_count) AS txn_count
# MAGIC FROM finserv_demo.gold.payments_agg_1d
# MAGIC GROUP BY merchant_id
# MAGIC ORDER BY total_volume DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- DASHBOARD 3: Accounts with highest decline rate
# MAGIC SELECT account_id,
# MAGIC        count(*) AS total_txns,
# MAGIC        count(CASE WHEN status = 'DECLINED' THEN 1 END) AS declined,
# MAGIC        cast(count(CASE WHEN status = 'DECLINED' THEN 1 END) * 1.0 / count(*) as DECIMAL(5,4)) AS decline_rate
# MAGIC FROM finserv_demo.silver.payment_current
# MAGIC GROUP BY account_id
# MAGIC HAVING count(*) >= 3
# MAGIC ORDER BY decline_rate DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- DASHBOARD 4: Recent transactions (latest 100)
# MAGIC SELECT txn_id, account_id, merchant_id, event_ts, amount, currency, status
# MAGIC FROM finserv_demo.silver.payment_current
# MAGIC ORDER BY event_ts DESC
# MAGIC LIMIT 100;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- DASHBOARD 5: Anomaly candidates (high amount + review/declined)
# MAGIC SELECT txn_id, account_id, merchant_id, amount, status, event_ts
# MAGIC FROM finserv_demo.silver.payment_current
# MAGIC WHERE amount > 1000 AND status IN ('DECLINED', 'REVIEW')
# MAGIC ORDER BY amount DESC
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- DASHBOARD 6: Currency breakdown
# MAGIC SELECT currency,
# MAGIC        sum(txn_count) AS txn_count,
# MAGIC        cast(sum(total_amount) as DECIMAL(38,2)) AS total_volume
# MAGIC FROM finserv_demo.gold.payments_agg_1d
# MAGIC GROUP BY currency
# MAGIC ORDER BY total_volume DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Validation Harness

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- VALIDATION HARNESS — Pipeline integrity checks
# MAGIC -- ══════════════════════════════════════════════════════════════════
# MAGIC -- Talk track: "This is the equivalent of the ETL reconciliation
# MAGIC -- counts we'd run after every load in an EDW. But here I also
# MAGIC -- prove data skipping works."
# MAGIC -- ──────────────────────────────────────────────────────────────────
# MAGIC
# MAGIC -- 1. Row counts across layers (Bronze >= Silver, Silver = sum(Gold))
# MAGIC SELECT 'LAYER COUNTS' AS check_name,
# MAGIC   (SELECT count(*) FROM finserv_demo.bronze.payment_events) AS bronze_rows,
# MAGIC   (SELECT count(*) FROM finserv_demo.silver.payment_current) AS silver_rows,
# MAGIC   (SELECT sum(txn_count) FROM finserv_demo.gold.payments_agg_1d) AS gold_txn_sum;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 2. Uniqueness check — duplicates in Silver (should be 0)
# MAGIC SELECT 'SILVER UNIQUENESS' AS check_name,
# MAGIC        count(*) AS duplicate_txn_ids
# MAGIC FROM (
# MAGIC   SELECT txn_id FROM finserv_demo.silver.payment_current
# MAGIC   GROUP BY txn_id HAVING count(*) > 1
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 3. Constraint sanity — rule violations in Silver
# MAGIC SELECT 'RULE VIOLATIONS' AS check_name,
# MAGIC        count(CASE WHEN amount < 0 THEN 1 END) AS negative_amounts,
# MAGIC        count(CASE WHEN currency NOT IN ('USD','EUR','GBP') THEN 1 END) AS bad_currency,
# MAGIC        count(CASE WHEN status NOT IN ('APPROVED','DECLINED','REVIEW') THEN 1 END) AS bad_status
# MAGIC FROM finserv_demo.silver.payment_current;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 4. Gold aggregate integrity
# MAGIC SELECT 'GOLD INTEGRITY' AS check_name,
# MAGIC        count(*) AS total_gold_rows,
# MAGIC        count(CASE WHEN decline_rate < 0 OR decline_rate > 1 THEN 1 END) AS bad_decline_rates,
# MAGIC        cast(sum(total_amount) as DECIMAL(38,2)) AS grand_total_volume
# MAGIC FROM finserv_demo.gold.payments_agg_1d;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 5. Pruning-friendly query — filters match CLUSTER BY keys
# MAGIC SELECT 'PRUNING TEST' AS check_name, count(*) AS matching_rows
# MAGIC FROM finserv_demo.silver.payment_current
# MAGIC WHERE account_id = 'ACCT-0001' AND event_date >= '2026-02-01';

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: Distributed Execution Notes
# MAGIC
# MAGIC ### Where shuffles happen
# MAGIC | Operation | Shuffle? | Why |
# MAGIC |-----------|----------|-----|
# MAGIC | ROW_NUMBER (Silver) | Yes | Window function partitions by `txn_id` — requires data redistribution |
# MAGIC | MERGE (Silver) | Yes | Join on `txn_id` between source and target |
# MAGIC | GROUP BY (Gold) | Yes | Aggregation by `event_date, merchant_id, currency` |
# MAGIC | SELECT with WHERE (Dashboard) | No | Filter + scan only, no redistribution |
# MAGIC
# MAGIC ### Why dedupe + deterministic MERGE matters
# MAGIC - Delta doesn't enforce PKs → duplicates silently accumulate
# MAGIC - ROW_NUMBER staging ensures exactly 1 source row per key → MERGE never gets "multiple source rows" error
# MAGIC - `WHEN MATCHED AND s.ingest_ts > t.ingest_ts` prevents stale updates from overwriting newer data
# MAGIC
# MAGIC ### How clustering + OPTIMIZE reduce scans
# MAGIC - `CLUSTER BY (account_id, event_date)` co-locates related data in the same files
# MAGIC - OPTIMIZE compacts small files and applies clustering
# MAGIC - ANALYZE computes column statistics for the optimizer
# MAGIC - Result: queries filtering on cluster keys skip irrelevant files (see EXPLAIN proof point)
# MAGIC
# MAGIC ### Scaling beyond 1,000 events
# MAGIC - **Bronze**: Auto Loader or Zerobus for continuous ingest (append-only, no dedup needed here)
# MAGIC - **Silver MERGE**: Only process NEW Bronze rows (add `WHERE ingest_ts > last_watermark`)
# MAGIC - **Gold rebuild**: Narrow the date window to just the affected range (not full table)
# MAGIC - **Clustering**: Adapts automatically as data grows — no manual repartitioning
# MAGIC - **Serverless**: Auto-scales compute for burst workloads without cluster management
