---
name: databricks-sa
description: >
  Databricks Solutions Architect knowledge base for Data Warehousing (DW spike), FinServ vertical,
  and design & architecture interview prep. Use when: designing Databricks lakehouse architectures,
  answering Medallion/Delta Lake/Unity Catalog questions, comparing Databricks vs Snowflake/Teradata,
  generating Mermaid architecture diagrams, handling DW migration scenarios, modeling star schema
  or Data Vault on Delta Lake, explaining Liquid Clustering / Photon / Serverless SQL / LakeFlow /
  Lakebridge, or coaching SA interview answers. Keywords: Databricks, lakehouse, Delta Lake,
  medallion, bronze silver gold, Unity Catalog, DW, data warehouse, FinServ, financial services,
  Teradata migration, Snowflake comparison, SCD, slowly changing dimension, Liquid Clustering,
  Photon, Serverless SQL, LakeFlow, Lakebridge, SA interview, solutions architect.
license: MIT
metadata:
  author: Steve Lysik
  version: "1.0.0"
  tags: databricks sa interview dw finserv architecture
allowed-tools: Bash Read
disable-model-invocation: false
---

# Databricks SA Knowledge Base

## Purpose

This skill provides deep Databricks Data Warehousing knowledge for Steve Lysik's SA interview preparation. It contains architecture patterns, feature reference, competitive intelligence, and scenario-based learning material.

**Spike**: Data Warehousing (DW)  
**Vertical**: Financial Services (FinServ)  
**Interview type**: Design & Architecture

---

## Quick Reference: DW Feature Status (2025–2026)

| Feature | Status | Key Talking Point |
|---------|--------|------------------|
| Serverless SQL Warehouse | **GA** | 40% perf gain in 2025; 2–6s startup; IWM + PQE |
| Liquid Clustering | **GA** (DBR 15.2+) | Replaces partitioning + Z-ORDER; `CLUSTER BY AUTO` |
| Predictive Optimization | **GA** (auto-enabled) | Auto OPTIMIZE/VACUUM/ANALYZE on UC managed tables |
| Materialized Views | **GA** | Incremental refresh via serverless DLT; row tracking required |
| AUTO CDC (SCD Type 1/2) | **GA** | `STORED AS SCD TYPE 2`; handles out-of-order via SEQUENCE BY |
| Row Filters | **GA** | SQL UDF evaluated at query time per user identity |
| Column Masks | **GA** | Replace sensitive values based on identity |
| ABAC (tag-based policies) | **Public Preview** | Tag → UC hierarchy inheritance |
| Column Lineage | **GA** | Automatic, runtime, all languages |
| Lakehouse Federation | **GA** | Teradata/Oracle GA July 2025; 12+ connectors |
| Delta Sharing | **GA** | Iceberg-compatible; share MVs cross-org |
| Lakebridge | **GA** | Free migration tooling; 20+ legacy platforms; 80% auto-conversion |
| LakeFlow Connect | **GA** | Managed CDC connectors for Oracle, Salesforce, SQL Server, etc. |
| DLT (Declarative Pipelines) | **GA** | `CREATE FLOW ... AUTO CDC INTO` |
| Photon Engine | **GA** | C++ vectorized; 18x on star joins; 1.5x shuffle throughput |
| IWM (Intelligent Workload Mgmt) | **GA** (serverless only) | ML-driven query resource allocation |
| PQE (Predictive Query Exec) | **GA** (serverless only) | Mid-query replanning for skew |
| Genie (NL→SQL) | **GA** | Conversational BI on top of DBSQL |

---

## Architecture Patterns

### The 5-Layer Template (Use Every Time)
```
SOURCES → INGESTION → MEDALLION (Bronze/Silver/Gold) → GOVERNANCE → CONSUMPTION
```

For each layer, always state:
1. **What** — technology/pattern
2. **Why** — the trade-off rationale
3. **What could go wrong** — failure mode + mitigation

### Medallion Layer Guidance

**Bronze**
- Append-only Delta tables (no deletes)
- Raw schema — store exactly what came from the source
- Audit trail: `_source_system`, `_ingestion_ts`, `_file_path` metadata columns
- No PII masking (raw fidelity for regulatory audit)
- Liquid Cluster on `(ingestion_date, source_system)` for time-windowed queries

**Silver**
- Data integration layer — one record per business entity
- SCD Type 2 for history: use AUTO CDC with `STORED AS SCD TYPE 2 TRACK HISTORY ON`
- Data Vault for complex multi-source integration: Hubs (business keys), Links (relationships), Satellites (context + history)
- Apply column masks for PII at this layer (access Unity Catalog row filters)
- Liquid Cluster on business keys (customer_id, account_id)
- Validate data quality rules here — reject to quarantine tables, don't block Bronze

**Gold**
- Consumption-optimized: star schemas (Kimball) or OBTs for specific use cases
- Materialized Views for heavy aggregations refreshed on schedule
- Liquid Cluster on most-filtered fact columns (e.g., `(transaction_date, product_id)`)
- Photon-optimized for all joins (up to 18x on star joins)
- Separate logical clusters by consumer type: BI, risk, regulatory, API

### Star Schema on Databricks
- Fact tables: Liquid Clustered on date + FK dimensions most filtered
- Dimension tables: small dims → broadcast join; large dims → Liquid Cluster on PK
- Photon delivers up to 18x for star schema workloads specifically
- Recommended pattern: dimensional marts in Gold, Data Vault raw vault in Silver

### Data Vault on Databricks
Maps to Medallion:
- **Bronze → Staging Area** (raw ingest)
- **Silver → Raw Vault** (Hubs, Links, Satellites with `_LoadDate`, `_RecordSource`)
- **Silver/Gold boundary → Business Vault** (derived satellite calculations)
- **Gold → Data Marts** (Kimball star schemas for consumption)
- Identity columns for surrogate key generation
- PIT (Point-in-Time) and Bridge tables in Gold to pre-join satellites

---

## Migration Framework (Teradata/Netezza → Databricks)

Steve's IBM background is a key differentiator here. Walk-through:

1. **Assess** — Lakebridge Analyzer scans legacy environment
   - Classifies tables, views, ETL, stored procedures by complexity
   - Produces automated report in hours, not months
   
2. **Strategy** — Three migration approaches:
   - **Federation-First** (lowest risk): Lakehouse Federation queries legacy DW in place; migrate incrementally domain by domain
   - **Parallel Run**: Both systems live; Lakebridge reconciler validates parity row-by-row
   - **Medallion Refactor**: Re-architect into Bronze/Silver/Gold during migration (highest value, highest effort)

3. **Convert** — Lakebridge transpilers:
   - BladeBridge (mature, Teradata BTEQ)
   - Morpheus (next-gen, T-SQL, PL/SQL)
   - Switch (LLM-powered, experimental)
   - Automates up to **80%** of SQL conversion

4. **Optimize** — Liquid Clustering + Predictive Optimization + Photon
   - Reported results: 2.7x faster, 12x cost efficiency post-migration
   
5. **Govern** — Unity Catalog replaces legacy DW security model

**Steve's personal angle**: "At IBM I spent 8 years helping customers manage Netezza environments. I've seen the pain of proprietary platforms firsthand — the scaling limitations, the vendor lock-in, the forklift upgrade cycles. That's exactly why the open lakehouse approach resonates with me deeply."

---

## Competitive Intelligence

### Databricks vs Snowflake

| Dimension | Databricks | Snowflake |
|-----------|------------|-----------|
| **Price/Performance** | 2.8x faster, 3.6x less cost (TPC-DS-like) | Simpler pricing model |
| **Streaming** | Native Structured Streaming, DLT, Auto Loader | Snowpipe simpler for light CDC |
| **AI/ML** | Native MLflow, Feature Store, Model Serving | Snowpark growing but less mature |
| **Open Formats** | Delta Lake + Iceberg; zero vendor lock-in | Iceberg support added recently |
| **Governance** | Unity Catalog (multi-cloud, multi-language) | Strong SQL-level policies |
| **BI Concurrency** | Improving rapidly with IWM | Historical strength |
| **Ease of Use** | More powerful, steeper curve | Simpler for SQL-only teams |

**Diplomatic framing** (never say Snowflake is bad):
> "Both platforms have strengths. Databricks differentiates on the unified platform story — data engineering, DW, and ML on one platform with open formats. For a customer doing more than just BI, the TCO advantage is significant because you eliminate the integration tax between separate systems."

### Databricks vs Synapse / Fabric

> "Azure Synapse was a warehouse bolted onto Spark as an afterthought. Databricks was built Spark-native from day one — every feature decision is optimized for the lakehouse pattern. Microsoft Fabric is newer and interesting but less mature. For a customer with complex data engineering + ML workloads alongside BI, Databricks is the proven platform."

---

## Reference Files

Load these on demand for deeper detail:

| File | When to Load |
|------|-------------|
| [references/dw-architecture.md](references/dw-architecture.md) | Detailed DW patterns, SCD code, Liquid Clustering syntax |
| [references/competitive.md](references/competitive.md) | Full competitive battle cards and objection handling |
| [references/discovery-framework.md](references/discovery-framework.md) | Complete discovery question bank by category |

## Scenario Files

Practice scenarios with pre-populated discovery answers:

| File | Scenario |
|------|----------|
| [scenarios/finserv.yaml](scenarios/finserv.yaml) | FinServ bank — regulatory reporting, real-time risk |
| [scenarios/dw-migration.yaml](scenarios/dw-migration.yaml) | 500TB Teradata migration to Databricks |
| [scenarios/wegmans.yaml](scenarios/wegmans.yaml) | Retail — demand forecasting, real-time inventory |

## Scripts

| Script | Purpose |
|--------|---------|
| [scripts/gen-arch.sh](scripts/gen-arch.sh) | Generate architecture diagram from a scenario YAML |
| [scripts/open-live.sh](scripts/open-live.sh) | Open live-arch.md in browser for real-time preview |
