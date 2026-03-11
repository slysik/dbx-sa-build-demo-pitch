# Media Lakehouse — Medallion Pipeline

**Catalog:** `interview` | **Schema:** `media` | **Cluster:** interview-cluster

## Architecture

```mermaid
graph LR
    A[spark.range N] -->|PySpark| B[Bronze Delta]
    B -->|SDP Pipeline| C[Silver MV]
    C -->|SDP Pipeline| D[Gold MV]
    D -->|SQL| E[AI/BI Dashboard]

    subgraph Bronze
        B1[bronze_content] --> B
        B2[bronze_subscribers] --> B
        B3[bronze_stream_events] --> B
    end

    subgraph "Silver — Clean & Type"
        C1[silver_content]
        C2[silver_subscribers]
        C3[silver_stream_events]
    end

    subgraph "Gold — Aggregate"
        D1[gold_daily_streaming]
        D2[gold_content_popularity]
        D3[gold_plan_engagement]
    end
```

## Layers

| Layer | Tables | Method |
|-------|--------|--------|
| Bronze | `bronze_content`, `bronze_subscribers`, `bronze_stream_events` | `spark.range()` → Delta |
| Silver | `silver_content`, `silver_subscribers`, `silver_stream_events` | SDP Materialized View |
| Gold | `gold_daily_streaming`, `gold_content_popularity`, `gold_plan_engagement` | SDP Materialized View |

## Run

```bash
# 1. Deploy bundle
cd media_lakehouse && databricks bundle validate && databricks bundle deploy

# 2. Run Bronze notebook on cluster
# 3. Start SDP pipeline (full refresh)
# 4. Open dashboard
```

## Project Structure

```
src/notebooks/   — PySpark Bronze generation (full inline code)
src/pipeline/    — SQL for SDP Silver/Gold (raw SQL, no notebook headers)
src/dashboard/   — Dashboard JSON definition
docs/            — Architecture diagram and design decisions
tests/           — Test scaffolding
databricks.yml   — Asset Bundle config (pipeline + job)
```
