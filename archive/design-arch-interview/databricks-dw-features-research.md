# Databricks Data Warehousing Features & Capabilities (2025-2026)

## Research Task
Research the latest Databricks data warehousing features and capabilities as of 2026, covering SQL Warehouses, Lakehouse Federation, Materialized Views, Liquid Clustering, query optimization, Unity Catalog governance, dimensional modeling, migration patterns, cost optimization, and predictive optimization. Focus on GA vs preview status for interview preparation for a Databricks Solutions Architect role with a DW spike.

## Summary
Databricks has aggressively matured its data warehousing capabilities through 2025-2026. Serverless SQL Warehouses are the clear strategic direction, delivering up to 40% automatic performance gains in 2025 via Photon, Predictive Query Execution (PQE), and Intelligent Workload Management (IWM). Liquid Clustering (GA in DBR 15.2+) is the recommended replacement for Z-ORDER and Hive-style partitioning on all new tables. Predictive Optimization (GA, auto-enabled for new accounts) eliminates manual OPTIMIZE/VACUUM/ANALYZE. Unity Catalog provides GA row filters and column masks, with ABAC in Public Preview for scalable tag-based governance. Lakehouse Federation is GA for 10+ external connectors. Lakebridge (successor to BladeBridge) provides free, open migration tooling from 20+ legacy DW systems.

---

## 1. Databricks SQL Warehouses (Serverless vs Classic vs Pro)

### Warehouse Type Comparison

| Feature | Classic | Pro | Serverless |
|---|---|---|---|
| **Photon Engine** | Yes | Yes | Yes |
| **Predictive I/O** | No | Yes | Yes |
| **Intelligent Workload Management (IWM)** | No | No | Yes (exclusive) |
| **Predictive Query Execution (PQE)** | No | No | Yes |
| **Photon Vectorized Shuffle** | No | No | Yes |
| **Startup Time** | ~4 min | ~4 min | 2-6 seconds |
| **DBU Rate (AWS)** | Lowest | ~$0.55/DBU | ~$0.70/DBU (includes infra) |
| **Auto-scaling** | Basic | Basic | AI-driven (IWM) |
| **Materialized Views** | No | Yes | Yes |
| **Lakehouse Federation** | No | Yes | Yes |

- Serverless warehouses are the **strategic direction** -- they include all performance features and infrastructure costs are bundled into the DBU rate<sup>[1](#sources)</sup>
- Classic warehouses are **not deprecated** but are positioned as entry-level only<sup>[1](#sources)</sup>
- **Photon** is a native C++ vectorized query engine that processes data in columnar batches, leveraging modern CPU instruction sets. It is included in all warehouse types<sup>[2](#sources)</sup>
- **Predictive I/O** is a suite of features for speeding up selective scan operations in SQL queries<sup>[1](#sources)</sup>
- **Intelligent Workload Management (IWM)** uses ML to predict the compute cost of each incoming query and dynamically allocate resources -- serverless only<sup>[3](#sources)</sup>

### Key Talking Point
> Serverless SQL Warehouses delivered **up to 40% performance improvement** across production workloads in 2025, with no tuning or query rewrites required. Queries are up to **25% faster** on top of the existing 5x gains from prior years. Photon Vectorized Shuffle alone delivers **1.5x higher shuffle throughput**<sup>[3](#sources)</sup>.

---

## 2. Lakehouse Federation

**Status: GA** (across AWS, Azure, GCP)<sup>[4](#sources)</sup>

### Connector GA Status

| Connector | Status |
|---|---|
| MySQL | **GA** |
| PostgreSQL | **GA** |
| Amazon Redshift | **GA** |
| Snowflake | **GA** |
| Azure SQL Database | **GA** |
| Microsoft SQL Server | **GA** |
| Azure Synapse | **GA** |
| Google BigQuery | **GA** (DBR 16.1+) |
| Salesforce Data Cloud | **GA** |
| Teradata | **GA** (as of July 2025) |
| Oracle | **GA** (as of July 2025) |
| Hive Metastore | **GA** |

- Lakehouse Federation allows querying external data sources **in place** without data movement, governed through Unity Catalog<sup>[4](#sources)</sup>
- Catalog federation enables Unity Catalog features (column masks, AI comments, lineage) on Hive metastore and Glue tables<sup>[5](#sources)</sup>
- Supports predicate pushdown to minimize data transfer from external sources<sup>[6](#sources)</sup>

### Key Talking Point
> Federation is a powerful tool for **incremental migration** -- query legacy DW data in place while migrating tables to Delta Lake, avoiding a "big bang" cutover.

---

## 3. Materialized Views

**Status: GA** for Databricks SQL<sup>[7](#sources)</sup>

- Created via `CREATE MATERIALIZED VIEW` in Databricks SQL or DLT pipelines<sup>[7](#sources)</sup>
- When created in a SQL warehouse, a **serverless DLT pipeline** is automatically created to manage refreshes<sup>[8](#sources)</sup>
- **Incremental refresh** is supported (serverless only) -- detects changes in source data and incrementally computes the result, saving compute costs<sup>[8](#sources)</sup>
- Incremental refresh requires **row tracking** enabled on source Delta tables<sup>[8](#sources)</sup>
- Supports incremental refresh for: inner joins, left joins, UNION ALL, and window functions (OVER)<sup>[8](#sources)</sup>
- Can now be **shared via Delta Sharing** (GA) to external Iceberg clients like Snowflake, Trino, Flink, and Spark<sup>[9](#sources)</sup>
- Scheduled or on-demand refresh supported; warehouse timeout settings apply to MVs created after August 14, 2025<sup>[9](#sources)</sup>
- `DESCRIBE EXTENDED AS JSON` now includes refresh metadata (last refresh time, type, status, schedule)<sup>[9](#sources)</sup>

### Key Talking Point
> Materialized views on Databricks are **not just cached query results** -- they use incremental refresh backed by serverless DLT, making them a production-grade alternative to traditional DW materialized views with automatic maintenance.

---

## 4. Delta Lake Liquid Clustering

**Status: GA** for Delta Lake tables (DBR 15.2+); **Public Preview** for Apache Iceberg tables (DBR 16.4 LTS+)<sup>[10](#sources)</sup>

### How It Replaces Z-ORDER + Partitioning

| Aspect | Hive Partitioning + Z-ORDER | Liquid Clustering |
|---|---|---|
| Data layout defined | Per OPTIMIZE run | Table property (persisted) |
| Changing keys | Requires full rewrite | No rewrite needed (`ALTER TABLE ... CLUSTER BY`) |
| New data handling | Must recluster all data | Incremental clustering on write |
| Partition management | Manual, rigid | Automatic, adaptive |
| Concurrency | Limited | Better concurrent write support |

### Syntax

```sql
-- Create new table
CREATE TABLE events (id INT, ts TIMESTAMP, region STRING) CLUSTER BY (region, ts);

-- Enable on existing table
ALTER TABLE events CLUSTER BY (region, ts);

-- Automatic column selection (DBR 15.4+)
ALTER TABLE events CLUSTER BY AUTO;

-- Trigger clustering
OPTIMIZE events;          -- Incremental
OPTIMIZE events FULL;     -- Full recluster
```

### Best Practices
- Databricks recommends **liquid clustering for ALL new tables**, including streaming tables and materialized views<sup>[10](#sources)</sup>
- Limit to **1-4 clustering keys**; more keys on smaller tables (<10 TB) may degrade single-column filter performance<sup>[10](#sources)</sup>
- Supported data types: Date, Timestamp, TimestampNTZ, String, numeric types (Int/Long/Short/Byte/Float/Double/Decimal)<sup>[10](#sources)</sup>
- `CLUSTER BY AUTO` (DBR 15.4+) analyzes historical query workload to automatically select optimal clustering columns<sup>[10](#sources)</sup>
- Use with **Predictive Optimization** for automatic OPTIMIZE execution on Unity Catalog managed tables<sup>[10](#sources)</sup>
- Liquid clustering is **not compatible** with partitioning and Z-ordering -- choose one approach<sup>[10](#sources)</sup>

### Clustering-on-Write Thresholds

| Keys | Unity Catalog Tables | Other Tables |
|---|---|---|
| 1 key | 64 MB | 256 MB |
| 2 keys | 256 MB | 1 GB |
| 3 keys | 512 MB | 2 GB |
| 4 keys | 1 GB | 4 GB |

---

## 5. Databricks SQL Query Optimization Features

### Automatic Optimizations (Serverless Only)

| Feature | Description | Impact |
|---|---|---|
| **Predictive Query Execution (PQE)** | Monitors running tasks in real-time; detects data skew or memory spills and replans query stages immediately. Evolution of AQE (which could only replan after stage completion) | Up to 25% faster queries<sup>[3](#sources)</sup> |
| **Photon Vectorized Shuffle** | Keeps data in compact columnar format, sorts within CPU cache, vectorized instructions | 1.5x higher shuffle throughput<sup>[3](#sources)</sup> |
| **Intelligent Workload Management (IWM)** | ML-based prediction of query compute cost; dynamic resource allocation vs static thresholds | Optimizes both cost and performance<sup>[1](#sources)</sup> |
| **Automatic Statistics (ANALYZE)** | GA -- removes need to manually run ANALYZE commands | 22% average performance increase<sup>[3](#sources)</sup> |
| **Adaptive Query Execution (AQE)** | Runtime query plan adjustment based on statistics collected during execution | Improved join strategies, partition coalescing<sup>[11](#sources)</sup> |

### Additional 2025 Performance Gains
- Spatial SQL queries ran up to **17x faster** (R-tree indexing, optimized spatial joins in Photon)<sup>[3](#sources)</sup>
- Delta Sharing queries ran up to **30% faster**<sup>[3](#sources)</sup>
- AI functions became up to **85x faster**<sup>[3](#sources)</sup>

### Key Talking Point
> The Databricks SQL optimizer is now **self-tuning** on serverless warehouses. PQE, IWM, and automatic statistics management together mean customers get continuous performance improvements without manual intervention -- a significant differentiator vs traditional DW tuning.

---

## 6. Unity Catalog Governance for Data Warehousing

### Feature Status Summary

| Feature | Status |
|---|---|
| Row Filters (manual assignment) | **GA** |
| Column Masks (manual assignment) | **GA** |
| ABAC (Attribute-Based Access Control) | **Public Preview** |
| Table-level lineage | **GA** |
| Column-level lineage | **GA** |
| External lineage (outside Databricks) | **Public Preview** |
| Governed Tags | **GA** |
| Data Classification (auto PII detection) | **GA** |

### Row Filters & Column Masks

- **Row Filters**: SQL UDFs that evaluate conditions at query time to control which rows a user can access<sup>[12](#sources)</sup>
- **Column Masks**: Replace column references with masking function results (must return same data type); used for PII redaction based on user identity/role<sup>[12](#sources)</sup>
- Supported on tables (including foreign tables via Federation), materialized views, and streaming tables<sup>[12](#sources)</sup>
- **Cannot** be applied to views or managed Iceberg tables<sup>[12](#sources)</sup>
- MERGE statements have restrictions with nested/aggregated policies<sup>[12](#sources)</sup>

### ABAC (Public Preview)

- Tag-based policy framework: define policies centrally using governed tags that apply dynamically across catalogs, schemas, and tables<sup>[13](#sources)</sup>
- Policies attach at catalog, schema, or table level and **inherit downward** to child objects<sup>[13](#sources)</sup>
- Pairs with Data Classification to **automatically mask PII** fields<sup>[13](#sources)</sup>
- Supports Delta Sharing, materialized views, streaming tables, and foreign tables<sup>[13](#sources)</sup>
- AI-powered policy creation converts natural language to performant SQL functions<sup>[13](#sources)</sup>

### Data Lineage

- Captured automatically at runtime for **all languages** (SQL, Python, Scala, R)<sup>[14](#sources)</sup>
- Available at both **table-level and column-level** granularity<sup>[14](#sources)</sup>
- Includes notebooks, jobs, and dashboards related to each query<sup>[14](#sources)</sup>
- Aggregated across **all workspaces** in a metastore<sup>[14](#sources)</sup>
- Accessible via Catalog Explorer UI, REST API, and lineage system tables<sup>[14](#sources)</sup>

### Key Talking Point
> Unity Catalog provides **a single governance layer** across all data assets -- Delta tables, external federated sources, materialized views, and streaming tables. ABAC with governed tags moves Databricks toward enterprise-grade, scalable governance comparable to or exceeding legacy DW security models.

---

## 7. Star Schema / Dimensional Modeling on Databricks Lakehouse

### Architecture Placement
- Star schemas are typically built in the **Gold layer** of the Medallion Architecture (Bronze -> Silver -> Gold)<sup>[15](#sources)</sup>
- The Gold layer contains denormalized/flattened data models, typically Kimball-style dimensional models<sup>[15](#sources)</sup>

### Best Practices

- **Surrogate keys**: Use system-generated surrogate keys as primary/foreign keys in fact/dimension tables<sup>[15](#sources)</sup>
- **Constraints**: Databricks supports `PRIMARY KEY`, `FOREIGN KEY`, `NOT NULL`, and `CHECK` constraints (informational for optimizer, not enforced except `NOT NULL`)<sup>[15](#sources)</sup>
- **Liquid Clustering**: Use on fact tables with 1-4 high-cardinality filter columns (e.g., date, customer_id)<sup>[10](#sources)</sup>
- **Statistics collection**: Run `ANALYZE TABLE` on all fact and dimension tables -- reported **22% performance improvement** for dimensional model joins<sup>[3](#sources)</sup>
- **Multi-statement transactions**: Available for ETL operations that load multiple related tables atomically<sup>[15](#sources)</sup>
- **Metric Views (Public Preview)**: Announced at Data + AI Summit 2025 -- semantic modeling layer in Unity Catalog that breaks free from vendor lock-in<sup>[16](#sources)</sup>

### Modeling Approaches Compared

| Approach | Best For | Notes |
|---|---|---|
| **Star Schema (Kimball)** | BI/reporting, known query patterns | Most common; excellent Photon join optimization |
| **One Big Table (OBT)** | Simple analytics, few dimensions | Denormalized; good for dashboards |
| **Data Vault** | Auditability, multiple source systems | More complex; good for raw-to-silver layer |

### Key Talking Point
> Star schemas translate "exceptionally well" to Delta tables on the Lakehouse, often with **superior performance** to traditional DWs thanks to Photon's columnar engine, AQE for join optimization, and liquid clustering for data layout<sup>[15](#sources)</sup>.

---

## 8. Migration Patterns from Legacy Data Warehouses

### Lakebridge (Free, Open Source Migration Tool)

**Launched June 2025** -- successor to BladeBridge (acquired by Databricks February 2025)<sup>[17](#sources)</sup>

| Component | Function |
|---|---|
| **Analyzer** | Scans legacy environment (tables, views, ETL, stored procedures); classifies by complexity |
| **Transpilers** | BladeBridge (mature, 20+ dialects), Morpheus (next-gen, dbt support), Switch (LLM-powered) |
| **Reconciler** | Data validation post-migration |

- Automates **up to 80%** of migration tasks<sup>[17](#sources)</sup>
- Converts proprietary syntax: BTEQ (Teradata), T-SQL (Microsoft), PL/SQL (Oracle) to ANSI-compliant SQL<sup>[18](#sources)</sup>
- Supports **20+ source systems**: Teradata, Snowflake, Redshift, SQL Server, Oracle, Azure Synapse, Hive, Informatica, and more<sup>[17](#sources)</sup>
- Produces automated assessment reports within hours, not months<sup>[18](#sources)</sup>
- Partner solutions (e.g., Lovelytics) report **2.7x faster performance** and **12x cost efficiency** vs Snowflake<sup>[19](#sources)</sup>

### Migration Strategies

1. **Lift and Shift**: Direct SQL conversion + data migration using Lakebridge
2. **Federation-First**: Use Lakehouse Federation to query legacy DW in place; migrate tables incrementally
3. **Parallel Run**: Run both systems simultaneously during transition; reconcile with Lakebridge reconciler
4. **Medallion Refactor**: Re-architect into Bronze/Silver/Gold layers during migration

### Key Talking Point
> Databricks now owns the **end-to-end migration story** with Lakebridge: free, open-source, AI-powered, supporting 20+ source systems. The federation-first pattern using Lakehouse Federation is particularly compelling for risk-averse enterprises.

---

## 9. Cost Optimization for DW Workloads

### Compute Cost Strategies

| Strategy | Detail |
|---|---|
| **Serverless for bursty workloads** | Spin up in 2-6 sec; pay only when queries run; no idle cluster costs<sup>[20](#sources)</sup> |
| **Classic/Pro for steady workloads** | Lower DBU rate + reserved instance pricing for predictable heavy usage<sup>[21](#sources)</sup> |
| **IWM auto-scaling** | ML-based scaling on serverless avoids over-provisioning<sup>[1](#sources)</sup> |
| **Auto-stop** | Configure warehouse to auto-suspend after idle period |
| **Query result caching** | Serverless and Pro cache results; repeated queries are free |

### Storage Cost Strategies

| Strategy | Detail |
|---|---|
| **Predictive Optimization** | Auto-VACUUM removes obsolete files (7-day retention default)<sup>[22](#sources)</sup> |
| **Liquid Clustering** | Replaces partition overhead; more efficient file layout<sup>[10](#sources)</sup> |
| **Delta Lake VACUUM** | Remove old versions to reduce storage<sup>[22](#sources)</sup> |

### Cost Monitoring & Control

- **Budget Policies** (GA): Tag-based cost attribution for serverless compute by user, group, or project<sup>[23](#sources)</sup>
- **system.billing.usage** system table for detailed DBU consumption analysis<sup>[23](#sources)</sup>
- **Cost Management Dashboards** in account console<sup>[23](#sources)</sup>
- Budget policies apply tags **automatically** -- no dependency on users to tag resources<sup>[23](#sources)</sup>

### Pricing Quick Reference (AWS)

| SKU | DBU Rate | Notes |
|---|---|---|
| SQL Classic | ~$0.22/DBU | + cloud infra costs |
| SQL Pro | ~$0.55/DBU | + cloud infra costs |
| SQL Serverless | ~$0.70/DBU | Infra included |

### Key Talking Point
> Despite the higher per-DBU rate, **serverless is often cheaper** for DW workloads due to 2-6 second startup, aggressive scale-down, and zero idle costs. Budget policies provide enterprise-grade cost governance without relying on user discipline.

---

## 10. Predictive Optimization

**Status: GA** -- auto-enabled for accounts created after November 11, 2024; rolling out to existing accounts (started May 7, 2025, expected completion February 2026)<sup>[22](#sources)</sup>

### Automated Operations

| Operation | What It Does |
|---|---|
| **OPTIMIZE** | Compacts fragmented/oversized files; triggers incremental liquid clustering for enabled tables |
| **VACUUM** | Removes unreferenced data files (7-day retention default, regardless of table config) |
| **ANALYZE** | Incremental statistics updates for query optimization |

### Requirements & Scope
- **Premium plan** or higher<sup>[22](#sources)</sup>
- **Unity Catalog managed tables only** -- does not work on external tables or Delta Sharing recipient tables<sup>[22](#sources)</sup>
- SQL warehouses or DBR 12.2 LTS+<sup>[22](#sources)</sup>
- Runs on **serverless compute for jobs** (billed at serverless jobs SKU)<sup>[22](#sources)</sup>
- Does **not** execute Z-order (use liquid clustering instead)<sup>[22](#sources)</sup>

### Configuration Hierarchy
```sql
-- Account level: via Settings > Feature enablement (account admins)
-- Catalog level:
ALTER CATALOG my_catalog ENABLE PREDICTIVE OPTIMIZATION;
-- Schema level:
ALTER SCHEMA my_schema ENABLE PREDICTIVE OPTIMIZATION;
-- Inheritance:
ALTER SCHEMA my_schema INHERIT PREDICTIVE OPTIMIZATION;
```

### Observability
- Track operations via system table: `system.storage.predictive_optimization_operations_history`<sup>[22](#sources)</sup>

### Key Talking Point
> Predictive Optimization eliminates the #1 operational burden in DW management -- **manual table maintenance**. Combined with liquid clustering, it means zero-touch data layout optimization. This is a direct answer to the "who runs OPTIMIZE?" question that plagues every Databricks deployment.

---

## GA vs Preview Quick Reference

| Feature | Status |
|---|---|
| Serverless SQL Warehouses | **GA** |
| Photon Engine | **GA** |
| Predictive I/O | **GA** |
| Intelligent Workload Management | **GA** (serverless only) |
| Predictive Query Execution | **GA** (serverless only) |
| Liquid Clustering (Delta) | **GA** (DBR 15.2+) |
| Liquid Clustering (Iceberg) | **Public Preview** |
| CLUSTER BY AUTO | **GA** (DBR 15.4+) |
| Materialized Views (DBSQL) | **GA** |
| MV Incremental Refresh | **GA** (serverless only) |
| Lakehouse Federation | **GA** (10+ connectors) |
| Predictive Optimization | **GA** (rolling enablement) |
| Unity Catalog Row Filters | **GA** |
| Unity Catalog Column Masks | **GA** |
| ABAC (tag-based policies) | **Public Preview** |
| Data Lineage (table + column) | **GA** |
| External Lineage | **Public Preview** |
| Budget Policies | **GA** |
| Lakebridge Migration Tool | **GA** (free, open source) |
| Metric Views (semantic layer) | **Public Preview** |

---

## Concerns/Notes

- Classic warehouses are not deprecated but receive no new features; expect eventual EOL pressure
- ABAC is still in Public Preview -- for interviews, note that manual row filter/column mask assignment is GA but the scalable tag-based approach is not yet GA
- Predictive Optimization only works on Unity Catalog **managed** tables -- external tables are excluded, which matters for migration scenarios where tables may start as external
- Serverless pricing includes infrastructure costs, making direct DBU-rate comparisons with Classic/Pro misleading without factoring in cloud compute costs
- Liquid clustering is incompatible with existing partitioning; migration from partitioned tables requires table recreation or CTAS
- MV incremental refresh has limited SQL support (inner join, left join, UNION ALL, window functions) -- complex aggregations may require full refresh
- Lakebridge LLM-powered transpiler (Switch) is experimental and may produce SQL requiring manual review

---

## Sources

1. SQL warehouse types - Databricks Docs - https://docs.databricks.com/aws/en/compute/sql-warehouse/warehouse-types
2. What is Photon? - Databricks Docs - https://docs.databricks.com/aws/en/compute/photon
3. 2025 in Review: Databricks SQL, faster for every workload - Databricks Blog - https://www.databricks.com/blog/2025-review-databricks-sql-faster-every-workload
4. Announcing General Availability of Lakehouse Federation - Databricks Blog - https://www.databricks.com/blog/announcing-general-availability-lakehouse-federation
5. Announcing GA of Lakehouse Federation for BigQuery and Preview for Teradata/Oracle - Databricks Blog - https://www.databricks.com/blog/announcing-general-availability-lakehouse-federation-google-bigquery-and-public-preview
6. What is Lakehouse Federation? - Databricks Docs - https://docs.databricks.com/aws/en/query-federation/
7. Announcing GA of Materialized Views and Streaming Tables for Databricks SQL - Databricks Blog - https://www.databricks.com/blog/announcing-general-availability-materialized-views-and-streaming-tables-databricks-sql
8. Incremental refresh for materialized views - Databricks Docs - https://docs.databricks.com/aws/en/optimizations/incremental-refresh
9. Now GA: Share Materialized Views and Streaming Tables with Delta Sharing - Databricks Blog - https://www.databricks.com/blog/now-ga-share-materialized-views-and-streaming-tables-delta-sharing
10. Use liquid clustering for tables - Databricks Docs - https://docs.databricks.com/aws/en/delta/clustering
11. Databricks SQL release notes 2025 - https://docs.databricks.com/aws/en/sql/release-notes/2025
12. Row filters and column masks - Databricks Docs - https://docs.databricks.com/aws/en/data-governance/unity-catalog/filters-and-masks/
13. How to scale data governance with ABAC in Unity Catalog - Databricks Blog - https://www.databricks.com/blog/how-scale-data-governance-attribute-based-access-control-unity-catalog
14. View data lineage using Unity Catalog - Databricks Docs - https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage
15. Data Modeling Best Practices & Implementation on Modern Lakehouse - Databricks Blog - https://www.databricks.com/blog/data-modeling-best-practices-implementation-modern-lakehouse
16. Lakehouse Modeling Playbook - Dhristhi - https://www.dhristhi.com/data-engineering/2025/09/24/lakehouse-modeling-playbook-when-to-use-star-schemas-obts-or-data-vault-on-databricks.html
17. Introducing Lakebridge: Free, Open Data Migration to Databricks SQL - Databricks Blog - https://www.databricks.com/blog/introducing-lakebridge-free-open-data-migration-databricks-sql
18. Welcoming BladeBridge to Databricks - Databricks Blog - https://www.databricks.com/blog/welcoming-bladebridge-databricks-accelerating-data-warehouse-migrations-lakehouse
19. Lovelytics Snowflake Migration Solution - Databricks Partner Solutions - https://www.databricks.com/company/partners/consulting-and-si/partner-solutions/lovelytics-snowflake-migration
20. Best practices for cost optimization - Databricks Docs - https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices
21. Databricks SQL Pricing - https://www.databricks.com/product/pricing/databricks-sql
22. Predictive optimization for Unity Catalog managed tables - Databricks Docs - https://docs.databricks.com/aws/en/optimizations/predictive-optimization
23. Attribute usage with serverless budget policies - Databricks Docs - https://docs.databricks.com/aws/en/admin/usage/budget-policies
