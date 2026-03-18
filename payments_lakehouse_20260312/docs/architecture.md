# Architecture — Payments Lakehouse (2026-03-12)

## Design Decisions
1. **SQL RANGE(N) on serverless** — no cluster needed, identical to spark.range()
2. **Direct to Bronze Delta** — no intermediate files
3. **Hash-based deterministic generation** — reproducible datasets
4. **CHECK constraints at Bronze** — shift-left DQ
5. **Genie Space for exploration** — natural language analytics
