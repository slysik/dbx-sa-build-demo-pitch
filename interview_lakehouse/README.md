# Interview Lakehouse — Medallion Pipeline

**Catalog:** `dbx_weg` | **Schema:** `interview` | **Cluster:** interview-cluster

## Architecture

```mermaid
graph LR
    A[spark.range N] -->|PySpark| B[Bronze Delta]
    B -->|SDP Pipeline| C[Silver MV]
    C -->|SDP Pipeline| D[Gold MV]
    D -->|SQL| E[AI/BI Dashboard]

    subgraph Bronze
        B1[dim_interviewers] --> B
        B2[dim_candidates] --> B
        B3[fact_interviews] --> B
    end

    subgraph "Silver — Clean & Type"
        C
    end

    subgraph "Gold — Aggregate"
        D
    end
```

## Layers

| Layer | Tables | Method |
|-------|--------|--------|
| Bronze | `dim_interviewers`, `dim_candidates`, `fact_interviews` | `spark.range()` → Delta |
| Silver | `silver_interview_sessions` | SDP Materialized View |
| Gold | `gold_interview_readiness` | SDP Materialized View |

## Run

```bash
# 1. Deploy bundle
databricks bundle validate && databricks bundle deploy

# 2. Run Bronze notebook on cluster
# 3. Start SDP pipeline (full refresh)
# 4. Open dashboard
```

## Project Structure

```
src/notebooks/   — PySpark Bronze generation (full inline code)
src/pipeline/    — SQL for SDP Silver/Gold (raw SQL, no notebook headers)
docs/            — Architecture diagram and design decisions
tests/           — Test scaffolding
databricks.yml   — Asset Bundle config (pipeline + job)
```
