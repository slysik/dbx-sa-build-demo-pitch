# Payments Lakehouse — Bronze Generation (2026-03-12 Rerun)

**Catalog:** `interview` | **Schema:** `payments_0312` | **Compute:** Serverless SQL
**Scale:** 10K transactions + 100 payment types

## Architecture

```mermaid
graph LR
    A[SQL RANGE 10K] -->|Serverless| B[Bronze Delta]
    B --> C[Genie Space]

    subgraph Bronze
        B1[payment_types 100] --> B
        B2[payment_transactions 10K] --> B
    end
```

## Run
```bash
# All Bronze via serverless SQL — no cluster needed
# Genie Space via data-rooms API
```
