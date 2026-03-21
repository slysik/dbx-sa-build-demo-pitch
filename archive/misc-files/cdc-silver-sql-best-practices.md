# CDC into Silver Table with SQL — Best Practices, Simplicity, and Performance

This guide is written for a coding agent that needs to build a **Silver current-state table** from a **Bronze CDC feed** using **Databricks SQL only**.

The goal is to keep the design:
- **Simple** enough to implement correctly
- **Safe** against duplicate and out-of-order CDC events
- **Performant** for large tables
- **Easy to operate** in production

---

## 1) What Silver should represent

For this pattern, **Silver is the current-state table**:
- **One row per business key** (`customer_id` in this example)
- The latest known good state for that entity
- Deletes applied when the CDC feed says the row is deleted

Bronze keeps the raw event history. Silver keeps the latest state.

That means the Silver merge pattern must do four things well:
1. **Deduplicate** multiple CDC events for the same key in the same batch
2. **Order events correctly** so late or replayed data does not corrupt current state
3. **Apply deletes safely**
4. **Avoid unnecessary scans and file churn**

---

## 2) Core design principles

### Keep the target table simple
Do not overload Silver with every raw CDC field. Keep only:
- business columns needed downstream
- one event timestamp that represents last applied business change
- minimal operational metadata such as `_batch_id` and `_ingest_timestamp`

### Deduplicate before MERGE
A MERGE can fail or behave unpredictably if the source contains multiple rows for the same target key in the same batch. Always reduce the source batch to **one row per business key** before the MERGE.

### Make ordering deterministic
Do not order only by `cdc_ts` if ties are possible. Add one or more tie-breakers such as:
- source sequence number
- log sequence number (LSN)
- source commit version
- event id
- ingest timestamp
- batch id

### Use explicit column mapping
Avoid `UPDATE SET *` and `INSERT *` in reference patterns. Explicit mappings are safer, easier to review, and more resilient to schema drift.

### Guard against out-of-order events
The merge should only update or delete the target row if the incoming event is at least as new as the row already in Silver.

### Optimize only where it matters
Do not over-tune too early. Start with:
- Delta table
- deletion vectors enabled
- a sensible clustering key if justified
- validation via transaction log instead of full scans

---

## 3) Recommended source assumptions

This guide assumes Bronze CDC has fields similar to:

- `customer_id` — business key
- `first_name`, `last_name`, `email`, `region`, `status`, `ltv` — business attributes
- `op` — CDC operation such as `INSERT`, `UPDATE`, `UPSERT`, `DELETE`
- `cdc_ts` — source business change timestamp
- `_ingest_timestamp` — ingestion timestamp into Bronze
- `_batch_id` — identifier for the batch being processed

If the source has a stronger sequencing field than `cdc_ts`, such as LSN or source commit version, use that in the ordering logic.

---

## 4) Silver target table — recommended baseline

```sql
-- Create the Silver current-state table once.
-- Keep the schema focused on business columns plus a small amount
-- of operational metadata for observability and replay tracking.
CREATE TABLE IF NOT EXISTS dev_catalog.silver.customers (
    customer_id       BIGINT NOT NULL,
    first_name        STRING,
    last_name         STRING,
    email             STRING,
    region            STRING,
    status            STRING,
    ltv               DOUBLE,
    updated_at        TIMESTAMP,
    _ingest_timestamp TIMESTAMP,
    _batch_id         STRING
)
USING DELTA
CLUSTER BY (customer_id)
TBLPROPERTIES (
    -- Deletion vectors usually improve MERGE / DELETE efficiency by
    -- reducing full file rewrites for row-level changes.
    'delta.enableDeletionVectors' = 'true'
);
```

### Why this is the recommended baseline

#### `CLUSTER BY (customer_id)`
For a Silver current-state table merged on `customer_id`, clustering by the merge key is a sensible default when:
- the table is large
- merges happen frequently
- point lookups or key-based joins are common

Do **not** use `PARTITION BY customer_id`. That creates extreme partition explosion.

If the real workload is dominated by analytics on `region`, `status`, or date windows, revisit the clustering strategy later based on actual query patterns.

#### Keep properties minimal
Use only the properties you clearly need. Minimal baseline configuration is easier to support and reason about.

---

## 5) SQL MERGE pattern — best-practice baseline

This is the recommended SQL-only pattern.

```sql
-- MERGE one CDC batch from Bronze into the Silver current-state table.
--
-- IMPORTANT:
-- 1) Deduplicate the source batch before MERGE
-- 2) Use deterministic ordering when choosing the winning event per key
-- 3) Apply UPDATE / DELETE only when the source event is at least as new
--    as the row already stored in Silver
-- 4) Use explicit column mapping for clarity and safety
MERGE INTO dev_catalog.silver.customers AS t
USING (
    SELECT
        customer_id,
        first_name,
        last_name,
        email,
        region,
        status,
        ltv,
        op,
        cdc_ts,
        _ingest_timestamp,
        _batch_id
    FROM (
        SELECT
            customer_id,
            first_name,
            last_name,
            email,
            region,
            status,
            ltv,
            op,
            cdc_ts,
            _ingest_timestamp,
            _batch_id,

            -- Keep exactly one row per business key for this batch.
            --
            -- Order by newest business event first.
            -- Add tie-breakers so the selected row is deterministic even
            -- when two events share the same cdc_ts.
            ROW_NUMBER() OVER (
                PARTITION BY customer_id
                ORDER BY
                    cdc_ts DESC,
                    _ingest_timestamp DESC,
                    _batch_id DESC
            ) AS rn
        FROM dev_catalog.bronze.customers_cdc

        -- Process exactly one Bronze batch at a time.
        -- Replace the value below using your job / notebook parameterization
        -- approach in Databricks SQL.
        WHERE _batch_id = :batch_id
    ) AS deduped
    WHERE rn = 1
) AS s
ON t.customer_id = s.customer_id

-- Delete only when the incoming delete is as new or newer than the row
-- currently stored in Silver. This prevents an old delete event from
-- removing a newer row that was already applied.
WHEN MATCHED
  AND s.op = 'DELETE'
  AND s.cdc_ts >= t.updated_at
THEN DELETE

-- Update only when the incoming event is newer than the row currently
-- stored in Silver. This protects against replays and late-arriving events.
WHEN MATCHED
  AND s.op IN ('INSERT', 'UPDATE', 'UPSERT')
  AND s.cdc_ts > t.updated_at
THEN UPDATE SET
    t.first_name        = s.first_name,
    t.last_name         = s.last_name,
    t.email             = s.email,
    t.region            = s.region,
    t.status            = s.status,
    t.ltv               = s.ltv,
    t.updated_at        = s.cdc_ts,
    t._ingest_timestamp = CURRENT_TIMESTAMP(),
    t._batch_id         = s._batch_id

-- Insert a brand-new current-state row when the key does not exist yet.
-- Never insert DELETE records for unknown keys.
WHEN NOT MATCHED
  AND s.op <> 'DELETE'
THEN INSERT (
    customer_id,
    first_name,
    last_name,
    email,
    region,
    status,
    ltv,
    updated_at,
    _ingest_timestamp,
    _batch_id
)
VALUES (
    s.customer_id,
    s.first_name,
    s.last_name,
    s.email,
    s.region,
    s.status,
    s.ltv,
    s.cdc_ts,
    CURRENT_TIMESTAMP(),
    s._batch_id
);
```

---

## 6) Why this pattern is the best balance of simplicity and performance

### A. Source dedup before MERGE
This is mandatory best practice.

Without deduplication, a batch containing multiple rows for the same `customer_id` can cause:
- MERGE ambiguity
- non-deterministic outcomes
- runtime failure

Using `ROW_NUMBER()` keeps the source to **one row per target key**.

### B. Deterministic ordering
Ordering by only `cdc_ts DESC` is not enough if two events share the same timestamp.

Use tie-breakers. In this guide:
- `cdc_ts DESC`
- `_ingest_timestamp DESC`
- `_batch_id DESC`

If your source provides a real sequence field, use that instead because it is stronger than ingestion metadata.

### C. Safe update guard
This clause is critical:

```sql
AND s.cdc_ts > t.updated_at
```

It prevents:
- replayed events from overwriting the same row repeatedly
- late events from corrupting a newer current-state record

### D. Safe delete guard
This clause matters just as much:

```sql
AND s.cdc_ts >= t.updated_at
```

It prevents an old delete event from deleting a row that was already updated later.

### E. Explicit mappings
Explicit `UPDATE SET` and `INSERT (...) VALUES (...)` are best practice because they:
- make the business logic obvious
- avoid surprises from extra source columns
- handle schema changes more safely
- make code review easier

---

## 7) Strong recommendation: normalize CDC op values first

If Bronze may contain multiple operation formats such as:
- `I`, `U`, `D`
- `INSERT`, `UPDATE`, `DELETE`
- `UPSERT`

normalize them before the MERGE.

Example:

```sql
-- Optional normalization step inside the USING subquery.
-- This makes Silver logic consistent even when Bronze CDC sources differ.
SELECT
    customer_id,
    first_name,
    last_name,
    email,
    region,
    status,
    ltv,
    CASE
        WHEN op IN ('I', 'INSERT') THEN 'INSERT'
        WHEN op IN ('U', 'UPDATE') THEN 'UPDATE'
        WHEN op IN ('UPSERT')      THEN 'UPSERT'
        WHEN op IN ('D', 'DELETE') THEN 'DELETE'
        ELSE 'UNKNOWN'
    END AS op,
    cdc_ts,
    _ingest_timestamp,
    _batch_id
FROM dev_catalog.bronze.customers_cdc;
```

Best practice: either normalize in Bronze-to-Silver logic or create a cleaned Bronze view used by all downstream transformations.

---

## 8) Validation best practice — use the Delta transaction log first

Avoid expensive full-table checks after every MERGE.

Use `DESCRIBE HISTORY` first because the Delta transaction log already records MERGE metrics.

```sql
-- Read the most recent MERGE metrics from the Delta transaction log.
-- This is much cheaper than scanning the full Silver table.
SELECT
    timestamp,
    operation,
    operationMetrics['numSourceRows']           AS source_rows_read,
    operationMetrics['numTargetRowsInserted']   AS rows_inserted,
    operationMetrics['numTargetRowsUpdated']    AS rows_updated,
    operationMetrics['numTargetRowsDeleted']    AS rows_deleted,
    operationMetrics['numTargetRowsCopied']     AS rows_copied,
    operationParameters['predicate']            AS merge_predicate
FROM (
    DESCRIBE HISTORY dev_catalog.silver.customers
)
WHERE operation = 'MERGE'
ORDER BY timestamp DESC
LIMIT 1;
```

### How to interpret the metrics

- `source_rows_read`: how many source rows were read by the MERGE
- `rows_inserted`: new keys inserted into Silver
- `rows_updated`: existing keys updated in Silver
- `rows_deleted`: keys removed from Silver
- `rows_copied`: rows rewritten without direct logical change; rising values can indicate the MERGE is touching too many files

Important: do **not** assume:

```text
rows_inserted + rows_updated + rows_deleted = source_rows_read
```

That may be false when:
- replays become no-ops because of the timestamp guard
- late deletes hit unknown keys
- older updates are ignored by the freshness condition

A better rule is:
- the changed row counts should be explainable by the deduplicated source batch and the no-op guards

---

## 9) Optional scoped validation for the processed batch

If you need a quick quality check, scope it narrowly to the rows touched by the batch.

```sql
-- Quick scoped validation for the current batch.
-- This is still a table query, but much cheaper than scanning the entire table
-- when _batch_id is reasonably selective and file layout supports it.
SELECT
    COUNT(*)                                              AS batch_rows,
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS null_keys,
    SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END)       AS null_emails,
    MIN(updated_at)                                       AS earliest_updated_at,
    MAX(updated_at)                                       AS latest_updated_at
FROM dev_catalog.silver.customers
WHERE _batch_id = :batch_id;
```

Important note:
- this is a useful operational check
- but do **not** assume `_batch_id` is automatically optimized unless your file layout and clustering strategy support it

---

## 10) Performance guidance that actually matters

### Most important performance practices

#### 1. Deduplicate the source before MERGE
This is both correctness and performance. Smaller source input means less work.

#### 2. Merge one bounded batch at a time
Use `_batch_id` or another batch predicate to limit the source. Avoid merging the full Bronze history repeatedly.

#### 3. Cluster on the merge key when write pattern is key-centric
For a current-state Silver table merged by `customer_id`, clustering by `customer_id` is a practical default.

#### 4. Use deletion vectors
Deletion vectors usually reduce rewrite cost for row-level CDC patterns.

#### 5. Validate from history before scanning tables
Prefer transaction-log metrics first. Only query the table when you need targeted data quality checks.

### What not to do

#### Do not partition by high-cardinality business keys
Never partition Silver by `customer_id`.

#### Do not use wildcard SET / INSERT in best-practice reference code
It is convenient, but it hides logic and increases risk.

#### Do not run broad validation scans after every batch
That turns a fast pipeline into an expensive one.

#### Do not assume all CDC sources are perfectly ordered
Always build in ordering protection.

---

## 11) Recommended coding-agent implementation notes

A coding agent building this pattern should do the following:

1. Create the Silver table if it does not exist
2. Read one Bronze batch at a time using `_batch_id`
3. Deduplicate to one row per business key inside the `USING` subquery
4. Use deterministic ordering when choosing the winning source row
5. Apply guarded DELETE, guarded UPDATE, and non-delete INSERT logic
6. Read Delta history after the MERGE for operational metrics
7. Only run targeted validation queries when needed

---

## 12) Simple “what to say in review” summary

Use this explanation in code review or architecture review:

- **Silver is current state**: one row per customer, not full change history
- **Bronze keeps raw CDC**: Silver applies the latest valid state
- **Source is deduplicated before merge**: one source row per key avoids ambiguity
- **Ordering is deterministic**: ties are resolved consistently
- **Updates and deletes are freshness-guarded**: late or replayed events do not corrupt current state
- **Column mappings are explicit**: safer than wildcard merge syntax
- **Delta history is used for cheap validation**: avoids unnecessary full scans

---

## 13) Final recommended baseline

If simplicity is the top priority, use this baseline:

- current-state Silver table in Delta
- `CLUSTER BY (customer_id)`
- deletion vectors enabled
- one-batch-at-a-time MERGE
- `ROW_NUMBER()` dedup in the source
- deterministic ordering with tie-breakers
- guarded delete and guarded update
- explicit insert and update mappings
- validation through `DESCRIBE HISTORY`

This is the best balance of **simplicity, correctness, and production-grade performance** for SQL-based CDC into a Silver current-state table.
