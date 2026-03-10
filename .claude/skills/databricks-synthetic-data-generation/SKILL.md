---
name: databricks-synthetic-data-generation
description: "Generate realistic synthetic data using Faker and Spark, with non-linear distributions, integrity constraints, and save to Databricks. Use when creating test data, demo datasets, or synthetic tables."
---

# Synthetic Data Generation

Generate realistic, story-driven synthetic data for Databricks using Python with Faker and Spark.

## Reference Files

Read these when you need deeper guidance on a specific topic:

| File | When to Read |
|------|-------------|
| [`references/faker-patterns.md`](references/faker-patterns.md) | Faker UDFs, spark.range interview pattern, pandas+Faker generation, custom providers, locales, referential integrity |
| [`references/distributions.md`](references/distributions.md) | Detailed distribution code (Zipf, log-normal, seasonal sinusoidal), time-based patterns, row coherence examples |
| [`references/complete-example.md`](references/complete-example.md) | Full end-to-end script (customers/orders/tickets) with infrastructure, generation, save, and validation |

## Common Libraries

These libraries are useful for generating realistic synthetic data:

- **faker**: Generates realistic names, addresses, emails, companies, dates, etc.
- **holidays**: Provides country-specific holiday calendars for realistic date patterns

These are typically NOT pre-installed on Databricks. Install them using `execute_databricks_command` tool:
- `code`: "%pip install faker holidays"

Save the returned `cluster_id` and `context_id` for subsequent calls.

## Workflow

1. **Write Python code to a local file** in the project (e.g., `scripts/generate_data.py`)
2. **Execute on Databricks** using the `run_python_file_on_databricks` MCP tool
3. **If execution fails**: Edit the local file to fix the error, then re-execute
4. **Reuse the context** for follow-up executions by passing the returned `cluster_id` and `context_id`

**Always work with local files first, then execute.** This makes debugging easier - you can see and edit the code.

### Context Reuse Pattern

The first execution auto-selects a running cluster and creates an execution context. **Reuse this context for follow-up calls** - it's much faster (~1s vs ~15s) and shares variables/imports:

**First execution** - use `run_python_file_on_databricks` tool:
- `file_path`: "scripts/generate_data.py"

Returns: `{ success, output, error, cluster_id, context_id, ... }`

Save `cluster_id` and `context_id` for follow-up calls.

**If execution fails:**
1. Read the error from the result
2. Edit the local Python file to fix the issue
3. Re-execute with same context using `run_python_file_on_databricks` tool:
   - `file_path`: "scripts/generate_data.py"
   - `cluster_id`: "<saved_cluster_id>"
   - `context_id`: "<saved_context_id>"

**Follow-up executions** reuse the context (faster, shares state):
- `file_path`: "scripts/validate_data.py"
- `cluster_id`: "<saved_cluster_id>"
- `context_id`: "<saved_context_id>"

### Handling Failures

When execution fails:
1. Read the error from the result
2. **Edit the local Python file** to fix the issue
3. Re-execute using the same `cluster_id` and `context_id` (faster, keeps installed libraries)
4. If the context is corrupted, omit `context_id` to create a fresh one

### Installing Libraries

Databricks provides Spark, pandas, numpy, and common data libraries by default. **Only install a library if you get an import error.**

Use `execute_databricks_command` tool:
- `code`: "%pip install faker"
- `cluster_id`: "<cluster_id>"
- `context_id`: "<context_id>"

The library is immediately available in the same context.

**Note:** Keeping the same `context_id` means installed libraries persist across calls.

## Storage Destination

### Ask for Schema Name

By default, use the `ai_dev_kit` catalog. Ask the user which schema to use:

> "I'll save the data to `ai_dev_kit.<schema>`. What schema name would you like to use? (You can also specify a different catalog if needed.)"

If the user provides just a schema name, use `ai_dev_kit.{schema}`. If they provide `catalog.schema`, use that instead.

### Create Infrastructure in the Script

Always create the catalog, schema, and volume **inside the Python script** using `spark.sql()`. Do NOT make separate MCP SQL calls - it's much slower.

The `spark` variable is available by default on Databricks clusters.

```python
# =============================================================================
# CREATE INFRASTRUCTURE (inside the Python script)
# =============================================================================
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.raw_data")
```

### Save to Volume as Raw Data (Never Tables)

**Always save data to a Volume as parquet files, never directly to tables** (unless the user explicitly requests tables). This is the input for the downstream Spark Declarative Pipeline (SDP) that will handle bronze/silver/gold layers.

```python
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

# Save as parquet files (raw data)
spark.createDataFrame(customers_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/customers")
spark.createDataFrame(orders_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/orders")
spark.createDataFrame(tickets_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/tickets")
```

## Raw Data Only - No Pre-Aggregated Fields (Unless Instructed Otherwise)

**By default, generate raw, transactional data only.** Do not create fields that represent sums, totals, averages, or counts.

- One row = one event/transaction/record
- No columns like `total_orders`, `sum_revenue`, `avg_csat`, `order_count`
- Each row has its own individual values, not rollups

**Why?** A Spark Declarative Pipeline (SDP) will typically be built after data generation to:
- Ingest raw data (bronze layer)
- Clean and validate (silver layer)
- Aggregate and compute metrics (gold layer)

The synthetic data is the **source** for this pipeline. Aggregations happen downstream.

**Note:** If the user specifically requests aggregated fields or summary tables, follow their instructions.

```python
# GOOD - Raw transactional data
# Customer table: one row per customer, no aggregated fields
customers_data.append({
    "customer_id": cid,
    "name": fake.company(),
    "tier": "Enterprise",
    "region": "North",
})

# Order table: one row per order
orders_data.append({
    "order_id": f"ORD-{i:06d}",
    "customer_id": cid,
    "amount": 150.00,  # This order's amount
    "order_date": "2024-10-15",
})

# BAD - Don't add pre-aggregated fields
# customers_data.append({
#     "customer_id": cid,
#     "total_orders": 47,        # NO - this is an aggregation
#     "total_revenue": 12500.00, # NO - this is a sum
#     "avg_order_value": 265.95, # NO - this is an average
# })
```

## Temporality and Data Volume

### Date Range: Last 6 Months from Today

**Always generate data for the last ~6 months ending at the current date.** This ensures:
- Data feels current and relevant for demos
- Recent patterns are visible in dashboards
- Downstream aggregations (daily/weekly/monthly) have enough history

```python
from datetime import datetime, timedelta

# Dynamic date range - last 6 months from today
END_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
START_DATE = END_DATE - timedelta(days=180)

# Place special events within this range (e.g., incident 3 weeks ago)
INCIDENT_END = END_DATE - timedelta(days=21)
INCIDENT_START = INCIDENT_END - timedelta(days=10)
```

### Data Volume for Aggregation

Generate enough data so patterns remain visible after downstream aggregation (SDP pipelines often aggregate by day/week/region/category). Rules of thumb:

| Grain | Minimum Records | Rationale |
|-------|-----------------|-----------|
| Daily time series | 50-100/day | See trends after weekly rollup |
| Per category | 500+ per category | Statistical significance |
| Per customer | 5-20 events/customer | Enough for customer-level analysis |
| Total rows | 10K-50K minimum | Patterns survive GROUP BY |

```python
# Example: 8000 tickets over 180 days = ~44/day average
# After weekly aggregation: ~310 records per week per category
# After monthly by region: still enough to see patterns
N_TICKETS = 8000
N_CUSTOMERS = 2500  # Each has ~3 tickets on average
N_ORDERS = 25000    # ~10 orders per customer average
```

## Script Structure

Always structure scripts with configuration variables at the top:

```python
"""Generate synthetic data for [use case]."""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker
import holidays
from pyspark.sql import SparkSession

# =============================================================================
# CONFIGURATION - Edit these values
# =============================================================================
CATALOG = "my_catalog"
SCHEMA = "my_schema"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

# Data sizes - enough for aggregation patterns to survive
N_CUSTOMERS = 2500
N_ORDERS = 25000
N_TICKETS = 8000

# Date range - last 6 months from today
END_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
START_DATE = END_DATE - timedelta(days=180)

# Special events (within the date range)
INCIDENT_END = END_DATE - timedelta(days=21)
INCIDENT_START = INCIDENT_END - timedelta(days=10)

# Holiday calendar for realistic patterns
US_HOLIDAYS = holidays.US(years=[START_DATE.year, END_DATE.year])

# Reproducibility
SEED = 42

# =============================================================================
# SETUP
# =============================================================================
np.random.seed(SEED)
Faker.seed(SEED)
fake = Faker()
spark = SparkSession.builder.getOrCreate()

# ... rest of script
```

## Distribution Quick Reference

| Data Type | Distribution | Example |
|-----------|-------------|---------|
| Prices, salaries, amounts | Log-normal | `np.random.lognormal(mean=4.5, sigma=0.8, size=N)` |
| Popularity, page views | Pareto/Zipf | `(np.random.pareto(a=2.5, size=N) + 1) * 10` |
| Time between events | Exponential | `np.random.exponential(scale=24, size=N)` |
| Categories | Weighted choice | `np.random.choice(items, size=N, p=[0.4, 0.3, 0.2, 0.1])` |
| Counts per entity | Poisson | `np.random.poisson(lam=5, size=N)` |
| Scores, ratings | Beta (scaled) | `np.random.beta(a=2, b=5, size=N) * 5` |

**Never use uniform distributions** - real data is rarely uniform. See [`references/distributions.md`](references/distributions.md) for detailed patterns with code examples.

## Key Principles

1. **PySpark-first (interviews)**: Use `spark.range()` + `F.hash()` for distributed gen; Faker UDFs only for names/addresses. See [`references/faker-patterns.md`](references/faker-patterns.md).
2. **Pandas for non-interview**: Generate with pandas, convert to Spark for saving. See [`references/faker-patterns.md`](references/faker-patterns.md).
3. **Referential integrity**: Master tables first, then child tables with valid foreign keys and weighted sampling.
4. **Non-linear distributions**: Log-normal for values, exponential for times, weighted categorical. See [`references/distributions.md`](references/distributions.md).
5. **Time patterns**: Weekday/weekend, holidays, seasonality, event spikes. See [`references/distributions.md`](references/distributions.md).
6. **Row coherence**: Attributes within a row correlate (tier affects amount, priority affects resolution time, etc.).

## Best Practices

1. **Ask for schema**: Default to `ai_dev_kit` catalog, ask user for schema name
2. **Create infrastructure**: Use `CREATE CATALOG/SCHEMA/VOLUME IF NOT EXISTS`
3. **Raw data only**: No `total_x`, `sum_x`, `avg_x` fields - SDP pipeline computes those
4. **Save to Volume, not tables**: Write parquet to `/Volumes/{catalog}/{schema}/raw_data/<input_datasource_name>`
5. **Configuration at top**: All sizes, dates, and paths as variables
6. **Dynamic dates**: Use `datetime.now() - timedelta(days=180)` for last 6 months
7. **Master tables first**: Generate customers, then orders reference customer_ids
8. **Weighted sampling**: Enterprise customers generate more activity
9. **Volume for aggregation**: 10K-50K rows minimum so patterns survive GROUP BY
10. **Always use files**: Write to local file, execute, edit if error, re-execute
11. **Context reuse**: Pass `cluster_id` and `context_id` for faster iterations
12. **Libraries**: Install `faker` and `holidays` first; most others are pre-installed

## Related Skills

- **[databricks-spark-declarative-pipelines](../databricks-spark-declarative-pipelines/SKILL.md)** - for building bronze/silver/gold pipelines on top of generated data
- **[databricks-aibi-dashboards](../databricks-aibi-dashboards/SKILL.md)** - for visualizing the generated data in dashboards
- **[databricks-unity-catalog](../databricks-unity-catalog/SKILL.md)** - for managing catalogs, schemas, and volumes where data is stored
