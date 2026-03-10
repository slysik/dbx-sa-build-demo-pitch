# Data Modeling, Performance, and Best Practices

## Table of Contents

- [Data Modeling Patterns](#data-modeling-patterns)
  - [Star Schema](#star-schema)
  - [One Big Table (OBT)](#one-big-table)
  - [When to Use Which](#when-to-use-which)
- [Liquid Clustering](#liquid-clustering)
  - [Syntax](#lc-syntax)
  - [Key Selection](#key-selection)
  - [CLUSTER BY AUTO](#cluster-by-auto)
  - [Migration from Z-ORDER](#migration-from-z-order)
- [PK/FK Constraints](#pkfk-constraints)
- [OPTIMIZE and ANALYZE TABLE](#optimize-and-analyze)
- [Performance Patterns](#performance-patterns)
  - [Predicate Pushdown](#predicate-pushdown)
  - [Column Pruning](#column-pruning)
  - [Broadcast Joins](#broadcast-joins)
  - [Adaptive Query Execution](#adaptive-query-execution)
- [Data Type Best Practices](#data-types)
- [Anti-Patterns](#anti-patterns)
- [Medallion Architecture Tips](#medallion-tips)

---

## Data Modeling Patterns

### Star Schema

Best for **Gold layer** and BI/dashboard consumption.

```sql
-- Fact table (events, transactions, measures)
CREATE TABLE catalog.gold.fact_orders (
  order_id BIGINT NOT NULL,
  customer_key BIGINT NOT NULL,
  product_key BIGINT NOT NULL,
  store_key BIGINT NOT NULL,
  order_date DATE NOT NULL,
  quantity INT,
  unit_price DECIMAL(10,2),
  total_amount DECIMAL(12,2),
  CONSTRAINT pk_fact_orders PRIMARY KEY (order_id),
  CONSTRAINT fk_customer FOREIGN KEY (customer_key) REFERENCES catalog.gold.dim_customer(customer_key),
  CONSTRAINT fk_product FOREIGN KEY (product_key) REFERENCES catalog.gold.dim_product(product_key),
  CONSTRAINT fk_store FOREIGN KEY (store_key) REFERENCES catalog.gold.dim_store(store_key)
)
CLUSTER BY (order_date, store_key);

-- Dimension table (descriptive attributes)
CREATE TABLE catalog.gold.dim_customer (
  customer_key BIGINT NOT NULL,
  customer_id STRING NOT NULL,
  name STRING,
  email STRING COLLATE UTF8_LCASE,
  segment STRING,
  region STRING,
  valid_from TIMESTAMP,
  valid_to TIMESTAMP,
  is_current BOOLEAN,
  CONSTRAINT pk_dim_customer PRIMARY KEY (customer_key)
);
```

**Star schema advantages:**
- Query optimizer uses PK/FK for join elimination and reordering
- BI tools auto-detect relationships
- Clean separation of measures vs attributes
- Efficient aggregation on fact table

### One Big Table (OBT)

Pre-joined denormalized table. Best for **Silver layer** or specific high-performance queries.

```sql
CREATE TABLE catalog.silver.orders_enriched (
  order_id BIGINT,
  order_date DATE,
  customer_id STRING,
  customer_name STRING,
  customer_segment STRING,
  product_name STRING,
  product_category STRING,
  store_name STRING,
  store_region STRING,
  quantity INT,
  amount DECIMAL(12,2)
)
CLUSTER BY (order_date, store_region);
```

### When to Use Which

| Pattern | Best For | Avoid When |
|---------|----------|-----------|
| **Star Schema** | Gold layer, BI dashboards, ad-hoc queries, multiple query patterns | Single known query pattern, ML feature tables |
| **OBT** | ML feature stores, single known query, embedded analytics | Multiple query patterns, storage-constrained, frequently updated dimensions |
| **Data Vault** | Enterprise DW, audit trail, multi-source integration | Small teams, simple pipelines, quick iteration |
| **Wide Fact** | IoT/telemetry with many measures | When dimensions change frequently |

---

## Liquid Clustering

Replaces partitioning and Z-ORDER for most use cases. Incrementally reorganizes data on write.

### LC Syntax

```sql
-- New table
CREATE TABLE catalog.schema.events (
  event_id BIGINT,
  event_date DATE,
  user_id BIGINT,
  event_type STRING,
  payload STRING
)
CLUSTER BY (event_date, event_type);

-- Existing table (migrate from partitioned or Z-ORDERed)
ALTER TABLE catalog.schema.events CLUSTER BY (event_date, event_type);

-- Remove clustering
ALTER TABLE catalog.schema.events CLUSTER BY NONE;
```

### Key Selection

| Rule | Detail |
|------|--------|
| **1-4 keys max** | More keys = less effective. Start with 2. |
| **High-cardinality first** | Put the most-filtered column first (often a date) |
| **Common filter columns** | Choose columns used in WHERE clauses most often |
| **Join columns** | Include columns used in frequent JOINs |
| **NOT: high-update columns** | Avoid columns that change frequently |

**Good examples:**

| Table Type | Clustering Keys | Rationale |
|-----------|----------------|-----------|
| Fact orders | `(order_date, region)` | Date range + region filters |
| User events | `(event_date, user_id)` | Date range + user lookup |
| IoT readings | `(device_id, reading_time)` | Device + time range queries |
| Logs | `(log_date, severity)` | Date + severity filtering |

### CLUSTER BY AUTO

Let Databricks automatically select and maintain clustering keys based on query patterns.

```sql
-- New table
CREATE TABLE catalog.schema.events (...)
CLUSTER BY AUTO;

-- Existing table
ALTER TABLE catalog.schema.events CLUSTER BY AUTO;
```

**When to use AUTO:**
- Unsure which columns to cluster by
- Query patterns change over time
- Want zero-maintenance optimization

**When to use explicit keys:**
- Known, stable query patterns
- Performance-critical tables
- Want predictable behavior

### Migration from Z-ORDER

```sql
-- Step 1: Convert table to Liquid Clustering
ALTER TABLE catalog.schema.events
  CLUSTER BY (event_date, user_id);
-- This replaces: OPTIMIZE ... ZORDER BY (event_date, user_id)

-- Step 2: Trigger initial clustering
OPTIMIZE catalog.schema.events;

-- Step 3: Remove old OPTIMIZE ZORDER jobs (they will error on LC tables)
```

**Key differences from Z-ORDER:**

| Feature | Z-ORDER | Liquid Clustering |
|---------|---------|-------------------|
| When applied | Manual OPTIMIZE only | On write (incremental) |
| Key changes | Requires full rewrite | `ALTER TABLE ... CLUSTER BY` |
| Partition required | Often used with partitions | Replaces partitioning |
| Max keys | Unlimited (but diminishing returns) | 1-4 recommended |
| Serverless | Not optimized | Fully optimized |

---

## PK/FK Constraints

Informational only (not enforced on write) but used by the **query optimizer**.

```sql
-- Primary Key
ALTER TABLE catalog.gold.dim_customer
  ADD CONSTRAINT pk_customer PRIMARY KEY (customer_key);

-- Foreign Key
ALTER TABLE catalog.gold.fact_orders
  ADD CONSTRAINT fk_customer
  FOREIGN KEY (customer_key) REFERENCES catalog.gold.dim_customer(customer_key);

-- NOT NULL (enforced)
ALTER TABLE catalog.gold.dim_customer
  ALTER COLUMN customer_key SET NOT NULL;

-- CHECK constraint (enforced)
ALTER TABLE catalog.gold.fact_orders
  ADD CONSTRAINT chk_positive_amount CHECK (total_amount >= 0);

-- View constraints
DESCRIBE TABLE EXTENDED catalog.gold.fact_orders;
SHOW TBLPROPERTIES catalog.gold.fact_orders;
```

**Optimizer benefits:**
- **Join elimination:** optimizer skips joins where result is provably unchanged
- **Join reordering:** knows which side is unique (PK), optimizes join order
- **BI tool discovery:** tools like Tableau auto-detect relationships via PK/FK

**Gotcha:** PK/FK are **NOT enforced**. You must ensure data integrity via MERGE logic, ROW_NUMBER dedup, or CHECK constraints.

---

## OPTIMIZE and ANALYZE

### OPTIMIZE

Compacts small files into larger ones. Triggers Liquid Clustering if enabled.

```sql
-- Basic (compact files + apply clustering)
OPTIMIZE catalog.schema.events;

-- With predicate (only optimize matching partitions/files)
OPTIMIZE catalog.schema.events WHERE event_date >= '2024-01-01';

-- Z-ORDER (legacy, non-LC tables only)
OPTIMIZE catalog.schema.events ZORDER BY (user_id, event_type);
```

**When to run:**
- After large batch writes
- As scheduled job (daily/hourly depending on write volume)
- After bulk DELETEs (to reclaim space after VACUUM)

### ANALYZE TABLE

Collects column statistics for the query optimizer.

```sql
-- All columns
ANALYZE TABLE catalog.schema.events COMPUTE STATISTICS;

-- Specific columns (faster)
ANALYZE TABLE catalog.schema.events
  COMPUTE STATISTICS FOR COLUMNS event_date, user_id, event_type;

-- Check existing stats
DESCRIBE TABLE EXTENDED catalog.schema.events;
```

**When to run:**
- After initial load or large data changes
- Before critical reporting queries
- After schema evolution (new columns)

---

## Performance Patterns

### Predicate Pushdown

Filters pushed to scan level -- reads fewer files.

```sql
-- GOOD: Direct column filter (pushdown works)
SELECT * FROM catalog.schema.events
WHERE event_date = '2024-03-01' AND user_id = 42;

-- BAD: Function on column (prevents pushdown)
SELECT * FROM catalog.schema.events
WHERE year(event_date) = 2024 AND month(event_date) = 3;
-- FIX: Use range
WHERE event_date >= '2024-03-01' AND event_date < '2024-04-01';
```

### Column Pruning

Only read columns you need -- especially important for wide tables.

```sql
-- BAD
SELECT * FROM catalog.schema.wide_table WHERE id = 42;

-- GOOD
SELECT id, name, amount FROM catalog.schema.wide_table WHERE id = 42;
```

### Broadcast Joins

Small dimension tables should be broadcast to avoid shuffles.

```sql
-- Automatic: tables < 10MB auto-broadcast (spark.sql.autoBroadcastJoinThreshold)
SELECT /*+ BROADCAST(d) */ f.*, d.name
FROM catalog.gold.fact_orders f
JOIN catalog.gold.dim_store d ON f.store_key = d.store_key;

-- Check size
DESCRIBE DETAIL catalog.gold.dim_store;  -- look at sizeInBytes
```

### Adaptive Query Execution

Enabled by default on Databricks. Auto-optimizes at runtime:
- Coalesces small shuffle partitions
- Converts sort-merge joins to broadcast when data is small
- Handles skewed joins

No action needed -- just be aware it is active and may change explain plans.

---

## Data Types

| Type | Use | Avoid |
|------|-----|-------|
| `DECIMAL(p,s)` | Money, financial amounts | `DOUBLE`, `FLOAT` (rounding errors) |
| `DATE` | Calendar dates | `STRING` for dates |
| `TIMESTAMP` | Events, audit columns | `STRING`, `LONG` epoch |
| `BIGINT` | IDs, counts | `INT` (may overflow at scale) |
| `STRING` | Text, codes, enums | `VARCHAR(n)` (Delta ignores length) |
| `BOOLEAN` | Flags | `INT` (0/1), `STRING` ('Y'/'N') |
| `BINARY` | Raw bytes, images | `STRING` with base64 |

**Gotcha:** Delta Lake ignores `VARCHAR(n)` and `CHAR(n)` length constraints -- they are stored as `STRING`. Use CHECK constraints if you need length enforcement.

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| **Over-partitioning** | Thousands of tiny partitions (< 1GB each) | Use Liquid Clustering instead |
| **Wide tables (500+ cols)** | Slow scans, poor compression | Split into fact + dimensions |
| **SELECT *** | Reads all columns from Parquet | Explicit column list |
| **Functions on filter columns** | Prevents data skipping | Filter on raw column values |
| **DOUBLE for money** | Floating-point rounding: `0.1 + 0.2 != 0.3` | `DECIMAL(10,2)` |
| **No OPTIMIZE schedule** | Small file problem over time | Weekly/daily OPTIMIZE job |
| **Missing PK/FK** | Optimizer cannot eliminate joins | Define constraints on Gold tables |
| **MERGE without dedup** | Duplicates cause non-deterministic updates | ROW_NUMBER() before MERGE |
| **INSERT overwrite loop** | Full rewrites instead of incremental | MERGE or append + compact |
| **String dates** | Cannot use date functions, no data skipping | `DATE` or `TIMESTAMP` type |
| **Z-ORDER on LC table** | Errors out; Z-ORDER incompatible with LC | Remove ZORDER jobs after migration |
| **Temp views via MCP** | Lost between `execute_sql` calls | Use CTEs or persist to table |
| **Parallel ALTER on same table** | `ProtocolChangedException` | Run ALTERs sequentially |

---

## Medallion Tips

### Bronze

- Raw data, no transforms. Append-only.
- Include metadata: `_ingest_timestamp`, `_source_file`, `_batch_id`
- Use Auto Loader (`STREAM read_files(...)`) for production ingestion
- Schema: match source exactly (STRING for uncertain types)
- Cluster by `_ingest_timestamp` or primary identifier

### Silver

- Cleaned, validated, deduped, PII-masked
- Enforce data types (cast STRINGs to proper types)
- Add CHECK constraints for data quality
- SCD Type 2 for slowly changing dimensions
- `ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1` for dedup

### Gold

- Business-level aggregates, star schema, feature tables
- Define PK/FK constraints
- Use Materialized Views for scheduled aggregations
- `ANALYZE TABLE` after major loads
- Liquid Clustering on most-queried columns
- Consider `DECIMAL` for all monetary aggregates

### Cross-Cutting

```sql
-- Idempotent Gold rebuild pattern
CREATE OR REPLACE TABLE catalog.gold.daily_metrics AS
SELECT
  order_date,
  region,
  SUM(amount) AS total_revenue,
  COUNT(DISTINCT customer_id) AS unique_customers
FROM catalog.silver.orders_current
GROUP BY order_date, region;

-- Then add constraints and clustering
ALTER TABLE catalog.gold.daily_metrics ADD CONSTRAINT pk PRIMARY KEY (order_date, region);
ALTER TABLE catalog.gold.daily_metrics CLUSTER BY (order_date, region);
OPTIMIZE catalog.gold.daily_metrics;
ANALYZE TABLE catalog.gold.daily_metrics COMPUTE STATISTICS;
```
