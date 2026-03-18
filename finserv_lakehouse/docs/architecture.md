# Architecture — Finserv Lakehouse

## Design Decisions

1. **PySpark for synthetic data** — distributed generation of 1000 finserv records.
2. **Zerobus Ingest API** — used for streaming JSON records to Databricks directly via gRPC, acting as a message bus substitute.
3. **Trickle data** — records are sent in small batches to mimic real-time velocity.
4. **Genie Space** — enables conversational AI exploration over the streaming Delta table.
