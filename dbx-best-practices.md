# dbx-best-practices.md
Databricks Coding Interview Playbook — **Vertical-agnostic, PySpark data gen + SQL transforms**

> Use this as your "skill" / reusable prompt pack for Claude Code + Databricks notebooks.
> Verticals: Retail, Media, or Generic. See `vertical-quick-swap.md` for entity maps.

---

## 0) How to win the interview (what they're grading)
**Mental model + curiosity + explanation > perfect syntax.**

You should consistently demonstrate:
1) **Computational thinking** — break the problem into a clean sequence (Bronze -> Silver -> Gold).
2) **Code stewardship** — generate working code and explain "what happens under the hood."
3) **Resilience** — debug calmly; audit AI outputs; fix determinism/perf issues.
4) **Distributed reasoning** — "What if 1M rows?" scaling talk track at every stage.

**Two-screen vibe**: interviewer watches both agent + workspace. Narrate tradeoffs aloud. Use TALK/SCALING/DW-BRIDGE comments.

### Interview Flow (CRITICAL)
The interview is **interactive, NOT auto-build**:
1. **DataFrame first** — Build ~100k row synthetic dataset as a PySpark DataFrame. STOP here.
2. **Interactive Q&A** — Interviewer asks about the DataFrame: add columns, check partitions, explain plan, optimize. Respond to what they ask.
3. **Medallion / dashboard** — Only build when the interviewer directs. Don't auto-advance.

Be ready for DataFrame questions: `.repartition()`, `.coalesce()`, `df.rdd.getNumPartitions()`, `.explain()`, `.cache()`, `.persist()`, schema inspection, filter/groupBy.

---

## 1) Universal prompt patterns (map any vertical to a template)

| Pattern | Retail Example | Media Example | Generic Example |
|---------|---------------|---------------|-----------------|
| Streaming ingest + dedup | Order events -> deduplicate on order_id | Stream events -> deduplicate on stream_id | Events -> deduplicate on event_id |
| CDC MERGE (I/U/D) | Order status changes | Subscription updates | Entity state changes |
| SCD Type 2 | Customer loyalty tier history | User subscription tier history | Entity attribute history |
| Late events / watermarks | Delayed POS transactions | Buffered stream telemetry | Delayed event processing |
| Data quality / quarantine | Invalid SKUs, negative prices | Invalid content_ids, zero duration | Rule violations, bad references |
| Performance tuning | CLUSTER BY (store_id, order_date) | CLUSTER BY (user_id, stream_date) | CLUSTER BY (entity_id, event_date) |
| Idempotent Gold rebuild | Daily revenue by store | Daily watch time by content | Daily aggregates by category |
| Reconciliation | Orders vs fulfillment | Streams vs billing | Source vs target counts |

---

## 2) Default architecture (vertical-agnostic)
### Medallion with idempotency
- **Bronze**: raw-ish append-only events (retain audit fields and optional raw payload)
- **Silver**: conformed + deduped + current-state (MERGE) or business-ready tables
- **Gold**: aggregates/features/report snapshots (BI-friendly)

**Idempotency patterns**
- Dedupe + deterministic **ROW_NUMBER** in staging, then MERGE
- Gold: delete-and-rebuild for a date range (or overwrite only target partitions)

---

## 3) Delta "constraints reality" (how to talk about PK/FK)
- In Databricks/Delta, rely on **enforced** constraints:
  - `NOT NULL`
  - `CHECK`
  - `GENERATED ALWAYS` columns
- Treat **PK/FK** (if declared) as **informational**: enforce uniqueness and referential integrity in pipeline logic + tests.
- Your integrity story should be:
  **(a) deterministic merges** + **(b) uniqueness tests** + **(c) rule checks** + **(d) quarantine** + **(e) metrics**

---

## 4) DDL templates (vertical-agnostic with `{entity}` placeholders)

### 4.1 Schemas
```sql
CREATE SCHEMA IF NOT EXISTS {catalog}.bronze;
CREATE SCHEMA IF NOT EXISTS {catalog}.silver;
CREATE SCHEMA IF NOT EXISTS {catalog}.gold;
```

### 4.2 Bronze events table (replace `{entity}` with your vertical's transaction)
```sql
CREATE TABLE IF NOT EXISTS {catalog}.bronze.{entity}_events (
  {pk}          STRING NOT NULL,       -- e.g., order_id, stream_id, event_id
  {fk}          STRING,                -- e.g., customer_id, user_id, entity_id
  {ref_id}      STRING,                -- e.g., store_id, content_id, category

  event_ts      TIMESTAMP,
  event_date    DATE GENERATED ALWAYS AS (CAST(event_ts AS DATE)),

  amount        DECIMAL(18,2),         -- or value, duration_min, etc.
  currency      STRING,                -- or content_type, event_type, etc.
  status        STRING,

  ingest_ts     TIMESTAMP,
  source_system STRING,
  raw_payload   STRING                 -- optional: audit/debug
)
USING DELTA;

-- CHECK constraints — adapt values per vertical
ALTER TABLE {catalog}.bronze.{entity}_events
  ADD CONSTRAINT chk_amount_nonneg CHECK (amount IS NULL OR amount >= 0);
```

---

## 5) Modern layout defaults (simple + explainable)

### 5.1 Liquid clustering default (great for multi-filter patterns)
```sql
-- SCALING: Liquid Clustering replaces distribution keys — adaptive, no schema lock-in
ALTER TABLE {catalog}.bronze.{entity}_events
CLUSTER BY ({fk}, event_date);

OPTIMIZE {catalog}.bronze.{entity}_events;

ANALYZE TABLE {catalog}.bronze.{entity}_events COMPUTE STATISTICS;
ANALYZE TABLE {catalog}.bronze.{entity}_events COMPUTE STATISTICS FOR COLUMNS
  {fk}, {ref_id}, event_date, status;
```

**Talk track (20 seconds):**
"I default to clustering when users filter across multiple columns. I optimize to rewrite file layout, then compute stats so the optimizer picks better plans."

---

## 6) PySpark data gen (100k rows, distributed, interview-ready)
> **PySpark is REQUIRED.** Candidates are dinged for SQL-only or pandas-only data gen.

### Pattern: `spark.range()` + hash-based categoricals + Faker UDFs (names only)

```python
# TALK: Using spark.range() for distributed data generation — 100k rows
# SCALING: spark.range() distributes across executors. At 1M rows, just change N.
# DW-BRIDGE: Like nzload parallelizing across SPUs — embarrassingly parallel generation.

from pyspark.sql import functions as F
from pyspark.sql.types import StringType
from faker import Faker

fake = Faker()
fake.seed_instance(42)

# Register Faker UDF for names only (expensive — minimize UDF usage)
@F.udf(StringType())
def fake_name():
    return fake.name()

N = 100_000
N_ENTITIES = 10_000

df = (spark.range(N)
    .withColumn("{pk}", F.concat(F.lit("T"), F.lpad(F.col("id").cast("string"), 10, "0")))
    .withColumn("{fk}", F.concat(F.lit("E"), F.lpad(
        (F.abs(F.hash(F.col("id"), F.lit("fk"))) % N_ENTITIES).cast("string"), 6, "0")))
    # SCALING: hash() is a pure Spark function — no Python serialization overhead
    .withColumn("event_ts", F.timestampadd("SECOND",
        -(F.abs(F.hash(F.col("id"), F.lit("ts"))) % (14 * 86400)).cast("int"),
        F.current_timestamp()))
    .withColumn("amount", F.round(
        F.abs(F.hash(F.col("id"), F.lit("amt"))) % 500000 / 100.0 + 0.99, 2).cast("decimal(18,2)"))
    .withColumn("status", F.when(F.abs(F.hash(F.col("id"), F.lit("st"))) % 100 < 85, "APPROVED")
                           .when(F.abs(F.hash(F.col("id"), F.lit("st"))) % 100 < 95, "PENDING")
                           .otherwise("DECLINED"))
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_demo"))
    .drop("id")
)
# TALK: 100k rows generated in seconds. At 1M, same pattern, just change N.
```

### Key principles:
1. **`spark.range(N)`** — distributed scaffold, no driver bottleneck
2. **`F.hash(col, lit("salt")) % N`** — deterministic per-row randomness, no UDF needed
3. **Faker UDFs** — only for names/addresses (expensive). Everything else via hash + modular arithmetic
4. **Always seed** — `Faker.seed(42)` for reproducibility
5. **100k default** — mention "scales to 1M+" in narration

### Load into Bronze (SQL)
```sql
-- TALK: Loading into Bronze as append-only. No transforms — raw data preserved.
INSERT INTO {catalog}.bronze.{entity}_events
SELECT * FROM {staging_view_or_table};
```

---

## 7) Silver templates (current-state, CDC MERGE, SCD2)

### 7.1 Current-state table (idempotent MERGE)
```sql
-- TALK: Silver MERGE — dedup on business key, keep latest record
-- SCALING: ROW_NUMBER triggers a shuffle (PARTITION BY). CLUSTER BY pre-sorts for merge-join.
-- DW-BRIDGE: In Netezza, distribution key on the join column gives same locality.

CREATE TABLE IF NOT EXISTS {catalog}.silver.{entity}_current (
  {pk}          STRING NOT NULL,
  {fk}          STRING,
  event_ts      TIMESTAMP,
  event_date    DATE,
  amount        DECIMAL(18,2),
  status        STRING,
  last_updated  TIMESTAMP,
  source_system STRING
)
USING DELTA;

ALTER TABLE {catalog}.silver.{entity}_current
CLUSTER BY ({fk}, event_date);

MERGE INTO {catalog}.silver.{entity}_current t
USING (
  SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY {pk} ORDER BY ingest_ts DESC) AS rn
    FROM {catalog}.bronze.{entity}_events
  ) WHERE rn = 1
) s ON t.{pk} = s.{pk}
WHEN MATCHED THEN UPDATE SET
  {fk} = s.{fk}, event_ts = s.event_ts, event_date = s.event_date,
  amount = s.amount, status = s.status,
  last_updated = s.ingest_ts, source_system = s.source_system
WHEN NOT MATCHED THEN INSERT (
  {pk}, {fk}, event_ts, event_date, amount, status, last_updated, source_system
) VALUES (
  s.{pk}, s.{fk}, s.event_ts, s.event_date, s.amount, s.status, s.ingest_ts, s.source_system
);
```

**Narrate:** "ROW_NUMBER makes the merge deterministic. MERGE gives idempotent reruns."

---

### 7.2 CDC MERGE with deletes (I/U/D)
```sql
-- TALK: CDC pattern — handle inserts, updates, AND deletes in one MERGE
MERGE INTO {catalog}.silver.{entity}_current t
USING (
  SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY {pk} ORDER BY commit_ts DESC) AS rn
    FROM {catalog}.bronze.{entity}_cdc
  ) WHERE rn = 1
) s ON t.{pk} = s.{pk}
WHEN MATCHED AND s.op = 'D' THEN DELETE
WHEN MATCHED AND s.op IN ('U','I') THEN UPDATE SET *
WHEN NOT MATCHED AND s.op IN ('I','U') THEN INSERT *;
```

---

### 7.3 SCD Type 2 dimension
```sql
-- TALK: SCD2 — track attribute changes over time with effective_from/to
-- DW-BRIDGE: Classic EDW pattern. Delta makes it append-friendly with MERGE.
CREATE TABLE IF NOT EXISTS {catalog}.gold.dim_{entity} (
  {pk}            STRING NOT NULL,
  attr1           STRING,
  attr2           STRING,
  hashdiff        STRING,
  effective_from  TIMESTAMP,
  effective_to    TIMESTAMP,
  is_current      BOOLEAN
)
USING DELTA;

MERGE INTO {catalog}.gold.dim_{entity} d
USING (
  SELECT {pk}, attr1, attr2,
         sha2(concat_ws('||', attr1, attr2), 256) AS hashdiff,
         updated_ts
  FROM {catalog}.bronze.{entity}_updates
) s
ON d.{pk} = s.{pk} AND d.is_current = true
WHEN MATCHED AND d.hashdiff <> s.hashdiff THEN
  UPDATE SET d.effective_to = s.updated_ts, d.is_current = false
WHEN NOT MATCHED THEN
  INSERT ({pk}, attr1, attr2, hashdiff, effective_from, effective_to, is_current)
  VALUES (s.{pk}, s.attr1, s.attr2, s.hashdiff, s.updated_ts, null, true);
```

---

## 8) Gold templates (BI-friendly aggregates, idempotent rebuild)

```sql
-- TALK: Gold layer — pre-computed aggregates for dashboards
-- SCALING: Delete-window + insert-window avoids full table scan — touches <1% at scale
-- DW-BRIDGE: In Netezza, we'd TRUNCATE+reload. This is 100x less I/O.

CREATE TABLE IF NOT EXISTS {catalog}.gold.{entity}_agg_1d (
  event_date    DATE,
  {group_col}   STRING,
  status        STRING,
  event_count   BIGINT,
  total_value   DECIMAL(38,2)
)
USING DELTA;

ALTER TABLE {catalog}.gold.{entity}_agg_1d
CLUSTER BY ({group_col}, event_date);

-- Idempotent rebuild window (last 14 days)
DELETE FROM {catalog}.gold.{entity}_agg_1d
WHERE event_date >= date_sub(current_date(), 14);

INSERT INTO {catalog}.gold.{entity}_agg_1d
SELECT
  event_date,
  {group_col},
  status,
  count(*) AS event_count,
  CAST(sum(amount) AS DECIMAL(38,2)) AS total_value
FROM {catalog}.silver.{entity}_current
WHERE event_date >= date_sub(current_date(), 14)
GROUP BY event_date, {group_col}, status;
```

---

## 9) Data quality + quarantine pattern (SQL-first)
```sql
-- TALK: Data quality — split valid from invalid, quarantine bad rows
-- SCALING: This is a single-pass filter — O(n) regardless of data size

-- Quarantine table (schema matches Bronze)
CREATE TABLE IF NOT EXISTS {catalog}.silver.{entity}_quarantine
USING DELTA
AS SELECT *, CAST(NULL AS STRING) AS reject_reason
FROM {catalog}.bronze.{entity}_events WHERE 1=0;

-- Insert invalid rows
INSERT INTO {catalog}.silver.{entity}_quarantine
SELECT *, 'failed_rules_v1' AS reject_reason
FROM {catalog}.bronze.{entity}_events
WHERE {pk} IS NULL
   OR event_ts IS NULL
   OR amount < 0;
```

---

## 10) Reconciliation template
```sql
-- TALK: Reconciliation — prove source and target agree
WITH source AS (
  SELECT {pk}, amount FROM {catalog}.bronze.{entity}_events
),
target AS (
  SELECT {pk}, amount FROM {catalog}.silver.{entity}_current
)
SELECT
  COALESCE(s.{pk}, t.{pk}) AS {pk},
  CASE
    WHEN s.{pk} IS NULL THEN 'MISSING_IN_SOURCE'
    WHEN t.{pk} IS NULL THEN 'MISSING_IN_TARGET'
    WHEN s.amount <> t.amount THEN 'MISMATCH'
    ELSE 'MATCH'
  END AS recon_status
FROM source s
FULL OUTER JOIN target t ON s.{pk} = t.{pk};
```

---

## 11) Validation + performance harness (the "integrity story")
Run these after each stage; narrate what each proves.

```sql
-- A) counts
SELECT
  (SELECT count(*) FROM {catalog}.bronze.{entity}_events) AS bronze_rows,
  (SELECT count(*) FROM {catalog}.silver.{entity}_current) AS silver_rows,
  (SELECT count(*) FROM {catalog}.gold.{entity}_agg_1d) AS gold_rows;

-- B) uniqueness (PK substitute)
SELECT {pk}, count(*) AS c
FROM {catalog}.silver.{entity}_current
GROUP BY {pk}
HAVING c > 1
LIMIT 20;

-- C) rule checks
SELECT count(*) AS bad_amount
FROM {catalog}.silver.{entity}_current
WHERE amount < 0;

-- D) "pruning-friendly" sample query (filters align with clustering keys)
-- SCALING: EXPLAIN shows "files pruned" — proves CLUSTER BY is working
SELECT {fk}, count(*) AS cnt, CAST(sum(amount) AS DECIMAL(18,2)) AS total
FROM {catalog}.silver.{entity}_current
WHERE event_date >= date_sub(current_date(), 7)
  AND {fk} = 'E000123'
GROUP BY {fk};
```

---

## 12) AI audit checklist (use aloud when AI generates code)
If AI outputs code, you (the pilot) quickly validate:
- Does it compile in Databricks SQL / notebook? (functions exist, correct data types)
- Is MERGE deterministic? (no multiple matches -> add `ROW_NUMBER` staging)
- Is it idempotent? (rerun-safe without duplicating data)
- Is it scalable? (avoid unnecessary shuffles; narrow columns early; layout aligns with filters)
- Are there comments explaining "why" not just "what"?
- Are TALK/SCALING/DW-BRIDGE narration comments present?
- Is the data gen PySpark (not pandas-only or SQL-only)?
- Is it vertical-agnostic (no hardcoded FinServ terms)?
- Add a tiny validation harness at the end.

---

## 13) Scaling Discussion Framework

Per-stage DW-bridge talk tracks for "What if 1M rows?":

| Stage | Scaling Point | DW Bridge |
|-------|--------------|-----------|
| **Data Gen** | `spark.range()` distributes generation across executors. Change N, same code. | "Like nzload parallelizing across SPUs — embarrassingly parallel." |
| **Bronze** | Append-only Delta writes are embarrassingly parallel. Liquid Clustering replaces distribution keys. | "In Netezza, we'd pick distribution keys upfront and be locked in. Liquid Clustering adapts." |
| **Silver MERGE** | ROW_NUMBER shuffle is the expensive op. CLUSTER BY pre-sorts for merge-join. | "Distribution key on the join column — same locality principle." |
| **Gold** | Delete-window + insert-window avoids full table scan — touches <1% at scale. | "In Netezza, TRUNCATE+reload rewrites 100%. Window-delete: same correctness, 100x less I/O." |
| **Dashboard** | Pre-aggregated Gold means dashboard queries scan KB not TB. | "Summary tables in EDW — same principle, Delta just versions them." |

---

## 14) Master prompt (paste into scratchpad)
```text
You are generating Databricks code for an INTERACTIVE coding interview.
Vertical: determined by the prompt (retail/media/generic). See vertical-quick-swap.md.
PySpark for data gen (~100k rows via spark.range + hash). SQL for transforms (when directed).

FLOW (interactive, NOT auto-build):
1) Start with 2-3 discovery questions: keys, latency, late data tolerance, outputs.
2) Generate synthetic data with PySpark (spark.range + Faker UDFs). NEVER SQL-only.
3) STOP after DataFrame is ready. Wait for interviewer direction.
4) Answer DataFrame questions: add columns, partitions, explain, optimize, cache/persist.
5) Only build medallion layers (Bronze -> Silver -> Gold) when interviewer directs.
6) Only build dashboard/validation when interviewer directs.

Always:
- Include TALK/SCALING/DW-BRIDGE narration comments in ALL code.
- Have dbx_toolkit ready for DataFrame analysis (profile, skew, nulls, keys, plan).
- Be ready for "What if 1M rows?" at every stage.
- Enforce integrity when building layers: ROW_NUMBER staging, MERGE, CHECK constraints.

Make code workspace-ready, compile-safe, and narration-rich.
```

---

## 15) Fast "think out loud" script (30 seconds)
1) "Let me confirm the business key and what 'correct' means (dedupe? late events?)."
2) "I'll model this as Bronze -> Silver -> Gold with idempotent reruns."
3) "I'll use PySpark with spark.range for the synthetic data — distributes across executors."
4) "I'll ensure deterministic merges, then prove integrity with tests."
5) "I'll align clustering with common filters and validate pruning via sample queries."
6) "If this scales to 1M rows, here's what changes at each stage..."

---

**End of playbook.**
