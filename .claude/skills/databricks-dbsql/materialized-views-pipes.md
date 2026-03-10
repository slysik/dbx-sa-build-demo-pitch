# Materialized Views, Temp Tables/Views, Pipe Syntax

## Table of Contents

- [Materialized Views](#materialized-views)
  - [CREATE MATERIALIZED VIEW](#create-materialized-view)
  - [REFRESH](#refresh)
  - [ALTER / DROP](#alter-and-drop)
  - [Scheduling](#scheduling)
  - [Gotchas](#mv-gotchas)
- [Temporary Tables and Views](#temporary-tables-and-views)
  - [Temp Views](#temp-views)
  - [Temp Tables](#temp-tables)
  - [Scope and Persistence](#scope-and-persistence)
- [Pipe Syntax](#pipe-syntax)
  - [Basic Operators](#basic-operators)
  - [AGGREGATE](#aggregate)
  - [EXTEND and SET](#extend-and-set)
  - [JOIN](#join-in-pipe)
  - [Advanced Patterns](#advanced-patterns)

---

## Materialized Views

### CREATE MATERIALIZED VIEW

**Requires:** Serverless SQL warehouse or Pro warehouse with Unity Catalog

```sql
CREATE [OR REPLACE] [OR REFRESH] MATERIALIZED VIEW [IF NOT EXISTS]
  catalog.schema.view_name
  [ ( column_spec [, ...] ) ]
  [ CLUSTER BY (col1 [, col2, ...]) | CLUSTER BY AUTO ]
  [ PARTITIONED BY (col1 [, ...]) ]
  [ COMMENT 'description' ]
  [ TBLPROPERTIES ('key' = 'value' [, ...]) ]
  [ SCHEDULE EVERY interval | SCHEDULE CRON 'expr' [ AT TIME ZONE 'tz' ] ]
  [ WITH ROW FILTER func ON (col1 [, ...]) ]
AS query
```

**Full example:**
```sql
CREATE OR REPLACE MATERIALIZED VIEW catalog.gold.daily_revenue
  CLUSTER BY (order_date)
  COMMENT 'Daily revenue by region, refreshed hourly'
  TBLPROPERTIES ('pipelines.channel' = 'PREVIEW')
  SCHEDULE EVERY 1 HOUR
AS
SELECT
  order_date,
  region,
  SUM(amount) AS total_revenue,
  COUNT(DISTINCT customer_id) AS unique_customers,
  AVG(amount) AS avg_order_value
FROM catalog.silver.orders
JOIN catalog.silver.stores USING (store_id)
WHERE order_status = 'completed'
GROUP BY order_date, region;
```

**Column-level constraints and masks:**
```sql
CREATE MATERIALIZED VIEW catalog.gold.customer_summary (
  customer_id BIGINT NOT NULL COMMENT 'Primary key',
  email STRING MASK mask_email,
  total_spend DECIMAL(12,2),
  CONSTRAINT pk_customer PRIMARY KEY (customer_id)
)
AS SELECT customer_id, email, SUM(amount) AS total_spend
   FROM catalog.silver.orders GROUP BY customer_id, email;
```

### REFRESH

```sql
-- Manual refresh (full or incremental, chosen automatically)
REFRESH MATERIALIZED VIEW catalog.gold.daily_revenue;

-- Force full refresh
REFRESH MATERIALIZED VIEW catalog.gold.daily_revenue FULL;
```

**Incremental refresh** is automatic when the MV query uses only:
- Filters, projections, aggregations
- Inner joins
- Source tables that are Delta

If the query includes outer joins, non-deterministic functions, or non-Delta sources, refresh is always **full**.

### ALTER and DROP

```sql
-- Change schedule
ALTER MATERIALIZED VIEW catalog.gold.daily_revenue
  SCHEDULE EVERY 30 MINUTES;

-- Change to cron
ALTER MATERIALIZED VIEW catalog.gold.daily_revenue
  SCHEDULE CRON '0 0 * * *' AT TIME ZONE 'America/New_York';

-- Remove schedule (manual only)
ALTER MATERIALIZED VIEW catalog.gold.daily_revenue
  DROP SCHEDULE;

-- Drop
DROP MATERIALIZED VIEW [IF EXISTS] catalog.gold.daily_revenue;
```

### Scheduling

| Syntax | Example | Notes |
|--------|---------|-------|
| `EVERY n unit` | `EVERY 1 HOUR`, `EVERY 30 MINUTES` | Simple interval |
| `CRON 'expr'` | `CRON '0 6 * * *'` | Quartz cron format |
| `AT TIME ZONE` | `AT TIME ZONE 'US/Pacific'` | Only with CRON |
| `TRIGGER ON UPDATE` | `AT MOST EVERY 1 HOUR` | Beta: refresh when source changes |

### MV Gotchas

| Issue | Detail |
|-------|--------|
| **Serverless/Pro only** | Classic warehouses cannot create or refresh MVs |
| **No streaming sources** | MV queries cannot read from streaming tables directly |
| **TBLPROPERTIES channel** | Use `'pipelines.channel' = 'PREVIEW'` for preview features (e.g., ai_query in MV) |
| **Schema evolution** | Adding columns to source table does NOT auto-update MV schema -- must recreate |
| **OR REFRESH** | Creates if not exists, refreshes if exists -- idempotent pattern |
| **Cost** | Each refresh runs a full query; schedule wisely |
| **No MERGE target** | MVs are read-only; cannot be targets of INSERT/UPDATE/DELETE/MERGE |

---

## Temporary Tables and Views

### Temp Views

```sql
-- Session-scoped (visible only in current SparkSession)
CREATE OR REPLACE TEMPORARY VIEW v_active_users AS
SELECT * FROM catalog.schema.users WHERE is_active = true;

-- Global temp view (visible across sessions in same cluster)
CREATE OR REPLACE GLOBAL TEMPORARY VIEW g_active_users AS
SELECT * FROM catalog.schema.users WHERE is_active = true;

-- Access global temp views via special schema
SELECT * FROM global_temp.g_active_users;
```

### Temp Tables

```sql
-- Session-scoped temporary table (Delta-backed)
CREATE OR REPLACE TEMPORARY TABLE t_staging (
  id BIGINT,
  name STRING,
  amount DECIMAL(10,2)
);

-- Populate
INSERT INTO t_staging SELECT id, name, amount FROM source;
```

### Scope and Persistence

| Object | Scope | Persists After Session? | Serverless Behavior | UC Registered? |
|--------|-------|----------------------|---------------------|----------------|
| `TEMPORARY VIEW` | Session | No | **Lost between `execute_sql` calls** | No |
| `GLOBAL TEMPORARY VIEW` | Cluster | No (lost on cluster restart) | Not supported on serverless | No |
| `TEMPORARY TABLE` | Session | No | **Lost between `execute_sql` calls** | No |
| `MATERIALIZED VIEW` | Catalog | Yes | Fully supported | Yes |
| Regular `VIEW` | Catalog | Yes | Fully supported | Yes |
| Regular `TABLE` | Catalog | Yes | Fully supported | Yes |

**Critical gotcha for MCP/serverless:** Each `execute_sql` call is a **separate session**. Temp views and temp tables created in one call are invisible in the next. Use CTEs, subqueries, or persist to a real table instead.

**Notebook behavior:** Temp views and tables persist across cells within the same notebook session (shared SparkSession).

---

## Pipe Syntax

**Availability:** DBR 16.1+ / DBSQL Serverless

The pipe operator `|>` chains SQL operations left-to-right for improved readability. Each pipe takes the result of the previous step as input.

### Basic Syntax

```sql
FROM catalog.schema.table_name
  |> WHERE condition
  |> SELECT col1, col2, expr AS alias
  |> ORDER BY col1 DESC
  |> LIMIT 100;
```

Equivalent traditional SQL:
```sql
SELECT col1, col2, expr AS alias
FROM catalog.schema.table_name
WHERE condition
ORDER BY col1 DESC
LIMIT 100;
```

### Basic Operators

| Operator | Purpose | Notes |
|----------|---------|-------|
| `WHERE` | Filter rows | Same as traditional WHERE |
| `SELECT` | Project columns | Replaces all columns (like traditional SELECT) |
| `ORDER BY` | Sort | `ASC`/`DESC`, `NULLS FIRST`/`LAST` |
| `LIMIT` | Restrict rows | With optional `OFFSET` |
| `DISTINCT` | Deduplicate | After SELECT in pipe chain |
| `AS alias` | Name the pipe result | For self-joins or subqueries |
| `TABLESAMPLE` | Random sample | `TABLESAMPLE (10 PERCENT)` |

### AGGREGATE

The `AGGREGATE` operator replaces `GROUP BY` in pipe syntax.

```sql
FROM catalog.schema.orders
  |> WHERE order_date >= '2024-01-01'
  |> AGGREGATE
       SUM(amount) AS total_revenue,
       COUNT(*) AS order_count,
       COUNT(DISTINCT customer_id) AS unique_customers
     GROUP BY region, product_category
  |> WHERE total_revenue > 10000
  |> ORDER BY total_revenue DESC;
```

**Without GROUP BY** (full-table aggregation):
```sql
FROM catalog.schema.orders
  |> AGGREGATE COUNT(*) AS total, SUM(amount) AS revenue;
```

### EXTEND and SET

`EXTEND` adds new columns (like adding computed columns). `SET` modifies existing columns.

```sql
-- EXTEND: add new columns without dropping existing ones
FROM catalog.schema.orders
  |> EXTEND amount * tax_rate AS tax_amount
  |> EXTEND amount + tax_amount AS total_with_tax
  |> SELECT order_id, amount, tax_amount, total_with_tax;

-- SET: modify existing columns in place
FROM catalog.schema.customers
  |> SET name = upper(name),
         email = lower(email)
  |> SELECT *;
```

| Operator | Behavior | Analogy |
|----------|----------|---------|
| `EXTEND` | Adds columns, keeps all existing | `SELECT *, expr AS new_col` |
| `SET` | Replaces column values, keeps all columns | `SELECT *, new_val AS existing_col` (overwrites) |

### JOIN in Pipe

```sql
FROM catalog.schema.orders
  |> JOIN catalog.schema.customers USING (customer_id)
  |> JOIN catalog.schema.products ON orders.product_id = products.id
  |> WHERE customers.region = 'US'
  |> SELECT
       orders.order_id,
       customers.name,
       products.product_name,
       orders.amount;
```

Supported join types: `JOIN`, `LEFT JOIN`, `RIGHT JOIN`, `FULL JOIN`, `CROSS JOIN`, `SEMI JOIN`, `ANTI JOIN`.

### Advanced Patterns

**Window functions in pipe:**
```sql
FROM catalog.schema.orders
  |> EXTEND ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
  |> WHERE rn = 1
  |> SELECT customer_id, order_id, order_date, amount;
```

**Chaining aggregations (two-level rollup):**
```sql
FROM catalog.schema.events
  |> AGGREGATE COUNT(*) AS event_count GROUP BY user_id, event_date
  |> AGGREGATE AVG(event_count) AS avg_daily_events GROUP BY user_id
  |> ORDER BY avg_daily_events DESC;
```

**Subquery with pipe:**
```sql
FROM (
  FROM catalog.schema.orders
    |> WHERE status = 'completed'
    |> AGGREGATE SUM(amount) AS total GROUP BY customer_id
) AS customer_totals
  |> WHERE total > 1000
  |> ORDER BY total DESC;
```

**Pipe with CTEs:**
```sql
WITH active_customers AS (
  FROM catalog.schema.customers
    |> WHERE is_active = true
)
FROM catalog.schema.orders
  |> JOIN active_customers USING (customer_id)
  |> AGGREGATE SUM(amount) AS revenue GROUP BY region;
```

### Pipe Syntax Gotchas

| Issue | Detail |
|-------|--------|
| **SELECT replaces** | `SELECT` in pipe drops columns not listed (unlike `EXTEND`) |
| **No SET without pipe** | `SET` as column modifier is pipe-only syntax |
| **Order matters** | `WHERE` before `AGGREGATE` = pre-filter; after = post-filter (like HAVING) |
| **FROM required** | Must start with `FROM table` (not `SELECT`) |
| **Cannot mix** | Don't mix pipe and traditional syntax in the same query level |
| **Aliases** | Use `AS alias` on the pipe result when you need to self-reference |
