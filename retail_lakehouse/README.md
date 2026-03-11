# Retail Lakehouse — Medallion Pipeline

**Catalog:** `interview` | **Schema:** `retail` | **Cluster:** interview-cluster

## Architecture

```mermaid
graph LR
    A[spark.range N] -->|PySpark| B[Bronze Delta]
    B -->|SDP Pipeline| C[Silver MV]
    C -->|SDP Pipeline| D[Gold MV]
    D -->|SQL| E[AI/BI Dashboard]

    subgraph Bronze
        B1[dim_products] --> B
        B2[dim_stores] --> B
        B3[fact_transactions] --> B
    end

    subgraph "Silver — Clean & Type"
        C1[silver_transactions]
    end

    subgraph "Gold — Aggregate"
        D1[gold_sales_by_category]
        D2[gold_sales_by_store]
        D3[gold_daily_revenue]
    end
```

## Layers

| Layer | Tables | Method |
|-------|--------|--------|
| Bronze | `bronze_products`, `bronze_stores`, `bronze_transactions` | `spark.range()` → Delta |
| Silver | `silver_transactions` | SDP Materialized View |
| Gold | `gold_sales_by_category`, `gold_sales_by_store`, `gold_daily_revenue` | SDP Materialized View |

## Run

```bash
# 1. Deploy bundle
cd retail_lakehouse
databricks bundle validate && databricks bundle deploy

# 2. Run Bronze notebook on cluster
# 3. Start SDP pipeline (full refresh)
# 4. Open dashboard
```

## Project Structure

```
src/notebooks/   — PySpark Bronze generation (full inline code)
src/pipeline/    — SQL for SDP Silver/Gold (raw SQL, no notebook headers)
src/dashboard/   — AI/BI Dashboard JSON
docs/            — Architecture diagram and design decisions
tests/           — Test scaffolding
databricks.yml   — Asset Bundle config (pipeline + job)
```
