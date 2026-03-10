# Data Warehouse Architecture on Databricks Lakehouse: Technical Deep Dive

## Research Task
Research current best practices and patterns for data warehouse architecture on Databricks Lakehouse as of 2026, covering modeling patterns (star schema, data vault, OBT), SCD implementations, fact table design, SQL warehouse sizing, Photon engine, competitive landscape, migration challenges, and FinServ use cases.

## Summary
Databricks Lakehouse has matured into a full data warehousing platform competitive with Snowflake and traditional EDWs. The platform supports all major DW modeling patterns (star schema, data vault, OBT) on Delta Lake, with Liquid Clustering replacing Z-ordering as the primary physical optimization technique. SCD Type 1 and 2 are natively supported via both manual MERGE patterns and the declarative AUTO CDC INTO APIs in LakeFlow Declarative Pipelines. The Photon engine (C++, vectorized) delivers up to 12x price/performance improvement over competing cloud DWs. Serverless SQL Warehouses with Intelligent Workload Management (IWM) are now the recommended compute model. Lakebridge (formerly Remorph) provides automated migration from Teradata, Netezza, and 10+ other platforms. Financial services is a top vertical with 600+ FS customers using purpose-built solution accelerators.

---

## 1. Star Schema vs Data Vault vs One Big Table (OBT) on Delta Lake

### Star Schema

Star schema remains the most common DW modeling pattern on Databricks<sup>[1](#sources)</sup>. It denormalizes business data into dimension and fact tables, optimizing for read-heavy analytical queries.

**When to use:**
- BI/reporting workloads with known, stable query patterns
- Environments where business users write SQL directly
- Moderate data volumes with well-understood dimensional relationships

**Databricks-specific best practices:**
- Use Liquid Clustering on fact tables keyed to frequently filtered dimension foreign keys (up to 4 clustering keys)<sup>[2](#sources)</sup>
- Enable Predictive Optimization to let the platform auto-select optimal clustering keys based on query patterns<sup>[2](#sources)</sup>
- Photon's query optimizer delivers up to 18x increased performance for star schema workloads specifically<sup>[3](#sources)</sup>
- Dimension tables should be small enough to broadcast; large dimensions benefit from Liquid Clustering on their primary keys

### Data Vault 2.0

Data Vault maps naturally to the Medallion Architecture<sup>[4](#sources)</sup><sup>[5](#sources)</sup>:

| Medallion Layer | Data Vault Component | Purpose |
|----------------|----------------------|---------|
| Bronze | Staging Area | Raw ingestion from sources |
| Silver | Raw Vault (Hubs, Links, Satellites) | Integration layer, historical tracking |
| Silver/Gold boundary | Business Vault | Derived business structures |
| Gold | Data Marts (Dimensional) | Kimball-style star schemas for consumption |

**When to use:**
- Highly agile environments with frequently changing source systems<sup>[4](#sources)</sup>
- Regulatory environments requiring full auditability and historicity
- Multiple source systems requiring complex integration
- Large enterprises with many development teams loading in parallel

**Databricks implementation details:**
- Hubs use Identity columns for surrogate key generation<sup>[5](#sources)</sup>
- Use OPTIMIZE and Liquid Clustering on all join keys of Hubs, Links, and Satellites<sup>[5](#sources)</sup>
- Create Point-in-Time (PIT) tables and Bridge tables as query-helper structures in the Gold layer to pre-join satellites/hubs and improve query performance<sup>[5](#sources)</sup>
- LakeFlow Declarative Pipelines automate satellite loading with CDC

### One Big Table (OBT)

OBT pre-joins all dimensions into a single wide, denormalized table, eliminating query-time joins<sup>[6](#sources)</sup>.

**When to use:**
- Single-purpose analytical datasets serving a specific dashboard or use case
- Environments where compute cost exceeds storage cost concerns
- Workloads where join elimination provides significant latency reduction

**Performance characteristics on Databricks:**
- Eliminates shuffle-intensive join operations in distributed Spark/Photon execution<sup>[6](#sources)</sup>
- Delta Lake's columnar Parquet storage compresses repeated dimension values efficiently, mitigating storage bloat<sup>[6](#sources)</sup>
- Liquid Clustering + OPTIMIZE on an OBT yielded >20x task speed-up and >3x reduction in wall-clock duration in documented benchmarks<sup>[6](#sources)</sup>
- Risk: full table scans become expensive at scale without proper clustering and column pruning

**Recommended hybrid approach:** Use Data Vault or normalized models in Silver, star schemas or OBTs in Gold, choosing per use case<sup>[5](#sources)</sup><sup>[6](#sources)</sup>.

---

## 2. Slowly Changing Dimensions (SCD) on Delta Lake

### SCD Type 1 (Overwrite)

Overwrites dimension attributes in place. No history retained.

**Manual MERGE pattern:**
```sql
MERGE INTO dim_customer AS target
USING staging_customer AS source
ON target.customer_id = source.customer_id
WHEN MATCHED THEN
  UPDATE SET target.name = source.name,
             target.address = source.address,
             target.updated_at = current_timestamp()
WHEN NOT MATCHED THEN
  INSERT (customer_id, name, address, updated_at)
  VALUES (source.customer_id, source.name, source.address, current_timestamp())
```

**LakeFlow AUTO CDC (declarative):**
```sql
CREATE OR REFRESH STREAMING TABLE dim_customer;
CREATE FLOW customer_flow AS AUTO CDC INTO dim_customer
FROM stream(cdc_data.customers)
KEYS (customer_id)
SEQUENCE BY seq_num
COLUMNS * EXCEPT (operation, seq_num)
STORED AS SCD TYPE 1;
```
<sup>[7](#sources)</sup><sup>[8](#sources)</sup>

### SCD Type 2 (Historical Tracking)

Inserts new version rows with effective date ranges and an is_current flag.

**Manual MERGE pattern (staged union approach):**
```sql
-- Step 1: Create staged changes with two row types per changed record
CREATE OR REPLACE TEMP VIEW staged_updates AS
SELECT customer_id AS merge_key, * FROM staging_customers  -- for UPDATE match
UNION ALL
SELECT NULL AS merge_key, * FROM staging_customers          -- for INSERT new version
WHERE customer_id IN (
  SELECT customer_id FROM dim_customer
  WHERE is_current = true
    AND (dim_customer.name != staging_customers.name
      OR dim_customer.city != staging_customers.city)
);

-- Step 2: Execute MERGE
MERGE INTO dim_customer AS target
USING staged_updates AS source
ON target.customer_id = source.merge_key AND target.is_current = true
WHEN MATCHED AND (target.name != source.name OR target.city != source.city) THEN
  UPDATE SET
    target.is_current = false,
    target.effective_end_date = current_date()
WHEN NOT MATCHED THEN
  INSERT (customer_id, name, city, effective_start_date, effective_end_date, is_current)
  VALUES (source.customer_id, source.name, source.city, current_date(), '9999-12-31', true)
```

**LakeFlow AUTO CDC (declarative, recommended):**
```sql
CREATE OR REFRESH STREAMING TABLE dim_customer;
CREATE FLOW customer_flow AS AUTO CDC INTO dim_customer
FROM stream(cdc_data.customers)
KEYS (customer_id)
SEQUENCE BY sequenceNum
COLUMNS * EXCEPT (operation, sequenceNum)
STORED AS SCD TYPE 2
TRACK HISTORY ON * EXCEPT (last_login_date);
```
This automatically adds `__START_AT` and `__END_AT` columns and handles out-of-order records<sup>[7](#sources)</sup>.

### SCD Type 3 (Previous Value Column)

Adds a `previous_value` column alongside the current value. Implemented as a standard MERGE with SET:

```sql
MERGE INTO dim_customer AS target
USING staging_customer AS source
ON target.customer_id = source.customer_id
WHEN MATCHED AND target.city != source.city THEN
  UPDATE SET
    target.previous_city = target.city,
    target.city = source.city,
    target.city_changed_date = current_date()
WHEN NOT MATCHED THEN
  INSERT (customer_id, city, previous_city, city_changed_date)
  VALUES (source.customer_id, source.city, NULL, NULL)
```

### MERGE Performance Optimization Tips

- Filter source/target by date ranges to limit scan scope (e.g., last 7 days only)<sup>[8](#sources)</sup>
- Pre-deduplicate the source dataset before merging<sup>[8](#sources)</sup>
- Use Liquid Clustering on merge key columns
- Use `WHEN NOT MATCHED BY SOURCE` (DBR 12.2+) for delete detection<sup>[8](#sources)</sup>
- For streaming, use `foreachBatch` with MERGE for continuous deduplication<sup>[8](#sources)</sup>

---

## 3. Fact Table Design Patterns on Delta Lake

| Pattern | Description | Delta Lake Implementation | Use Case |
|---------|-------------|--------------------------|----------|
| **Transaction Fact** | One row per discrete event | Append-only Delta table with Liquid Clustering on date + key dims; use Auto Loader for streaming ingestion | Sales transactions, trades, clicks |
| **Periodic Snapshot** | One row per entity per time period | Scheduled batch job using MERGE or overwrite partition; cluster by snapshot_date + entity_key | Daily account balances, monthly inventory levels |
| **Accumulating Snapshot** | One row per process instance, updated at milestones | MERGE on process_key, updating milestone date columns as events arrive; Delta's ACID guarantees consistency | Order fulfillment, loan origination, claims processing |

**Key Databricks features for fact tables:**
- **Auto Loader** (cloudFiles): Incrementally ingests new files for transaction facts<sup>[9](#sources)</sup>
- **Liquid Clustering**: Replace partitioning and Z-order; cluster fact tables on date columns and high-cardinality filter keys<sup>[2](#sources)</sup>
- **Predictive Optimization**: Automatically runs OPTIMIZE, VACUUM, and selects clustering keys<sup>[2](#sources)</sup>
- **Delta Change Data Feed (CDF)**: Enables downstream consumers to read only changed rows from fact tables
- **AUTO CDC FROM SNAPSHOT**: Ingests periodic snapshots from source systems and automatically computes CDC<sup>[7](#sources)</sup>

---

## 4. Databricks SQL Warehouse Sizing and Performance Tuning

### Warehouse Types (2026)

| Type | Status | Key Feature |
|------|--------|-------------|
| **Serverless** | Recommended | Intelligent Workload Management (IWM), instant scaling |
| **Pro** | Available | Manual scaling, advanced security |
| **Classic** | Deprecated pathway | Basic manual scaling |

### Serverless SQL Warehouse with IWM

Intelligent Workload Management uses ML models to predict query resource requirements and dynamically allocate compute<sup>[10](#sources)</sup><sup>[11](#sources)</sup>:
- New query arrives -> IWM predicts resource needs -> checks available capacity
- If capacity exists, query starts immediately
- If not, query queues and system scales clusters as needed
- Rapid upscaling for low latency; cost-efficient downscaling after 15 min low demand

### Classic/Pro Sizing Reference

| Size | Worker Count | Typical Use |
|------|-------------|-------------|
| 2X-Small | 1 worker | Dev/test, light queries |
| X-Small | 2 workers | Small team ad-hoc |
| Small | 4 workers | Departmental BI |
| Medium | 8 workers | Production BI dashboards |
| Large | 16 workers | Enterprise BI, concurrent users |
| X-Large | 32 workers | Heavy ETL + BI mixed |
| 2X-Large | 64 workers | Large-scale analytics |
| 3X-Large | 128 workers | Enterprise DW workloads |
| 4X-Large | 256 workers | Largest analytical workloads |

<sup>[11](#sources)</sup>

### Performance Tuning Best Practices

1. **Start large, size down**: More efficient than scaling up reactively<sup>[10](#sources)</sup>
2. **Monitor disk spills**: If queries spill to disk, increase cluster size<sup>[11](#sources)</sup>
3. **Multi-warehouse architecture**: Segment by workload type (interactive BI, scheduled ETL, ad-hoc exploration) for independent sizing and monitoring<sup>[10](#sources)</sup>
4. **Auto-stop with serverless**: Rapid cold start (seconds) makes auto-stop a major cost saver<sup>[10](#sources)</sup>
5. **Liquid Clustering + Predictive Optimization**: Ensure data layout enables maximal file pruning/data skipping<sup>[2](#sources)</sup>
6. **Monitor "Peak Queued Queries"**: Consistently >0 indicates need for more capacity<sup>[11](#sources)</sup>
7. **Concurrency limit**: Classic/Pro = 10 concurrent queries per cluster; max 1000 in queue<sup>[11](#sources)</sup>

---

## 5. How Photon Engine Accelerates DW Queries

### Architecture

Photon is a vectorized query engine written from the ground up in C++, replacing the JVM-based Spark SQL execution layer for supported operations<sup>[3](#sources)</sup><sup>[12](#sources)</sup>.

**Three core components:**

| Component | Function | Impact |
|-----------|----------|--------|
| **Query Optimizer** | Extends Spark 3.0 cost-based optimizer | Up to 18x performance for star schema workloads |
| **Caching Layer** | Transcodes data to CPU-efficient formats on NVMe SSDs | Up to 5x faster scan performance |
| **Native Vectorized Engine** | Processes data in columnar batches, not row-by-row | Leverages SIMD, CPU parallelism |

<sup>[3](#sources)</sup>

### Key Optimizations

- **Join acceleration**: Replaces sort-merge joins with hash-joins<sup>[3](#sources)</sup>
- **Aggregation redesign**: Group-by operations vectorized for batch processing<sup>[3](#sources)</sup>
- **Scan performance**: Columnar memory layout handles wide tables and small files efficiently<sup>[3](#sources)</sup>
- **Photon Vectorized Shuffle**: Reduces data movement overhead in distributed operations<sup>[12](#sources)</sup>
- **Predictive Query Execution**: Pre-stages resources based on predicted query plans<sup>[12](#sources)</sup>

### 2025 Performance Gains

| Workload Type | Improvement | Notes |
|---------------|-------------|-------|
| Exploratory/ad-hoc | ~40% faster | Faster analyst iteration on large datasets |
| BI dashboards | ~20% faster | More responsive under concurrency |
| ETL pipelines | ~10% faster | Shorter pipeline runtimes |
| Spatial SQL | Up to 17x faster | R-tree indexing, optimized spatial joins |

<sup>[12](#sources)</sup>

### When to Enable Photon

- **Enable**: Large-scale transforms (>100GB), complex analytical queries with joins/aggregations, DW workloads, interactive analytics<sup>[3](#sources)</sup>
- **Skip**: Queries completing in <2 seconds, UDF/RDD-heavy workloads, stateful streaming<sup>[3](#sources)</sup>
- **Compatibility**: 100% compatible with DataFrame and Spark SQL APIs; hybrid execution routes unsupported ops to standard Spark transparently<sup>[3](#sources)</sup>

---

## 6. Databricks Lakehouse DW vs Snowflake vs Traditional DW

| Dimension | Databricks Lakehouse | Snowflake | Teradata/Netezza (Traditional) |
|-----------|---------------------|-----------|-------------------------------|
| **Architecture** | Open lakehouse (Delta Lake on cloud object storage) | Proprietary multi-cluster shared data (+ Iceberg support) | MPP appliance / on-prem |
| **Storage Format** | Open (Delta/Parquet, Iceberg interop) | Proprietary micro-partitions | Proprietary |
| **Compute Model** | Spark clusters, Photon engine, SQL Warehouses | Virtual Warehouses (T-shirt sizing) | Fixed MPP nodes |
| **Scaling** | Independent compute + storage; serverless auto-scaling | Independent compute + storage; elastic VWs | Coupled; scale by adding nodes |
| **SQL Performance** | Photon: 2.8x faster than Snowflake Gen2 (TPC-DS-like benchmarks)<sup>[13](#sources)</sup> | Strong for high-concurrency BI | Excellent for complex joins at scale |
| **Price/Performance** | Up to 12x better than legacy cloud DWs<sup>[12](#sources)</sup>; 3.6x less cost than Snowflake Gen2<sup>[13](#sources)</sup> | Credits-per-second + per-TB storage | High TCO (licensing, hardware, admin) |
| **Streaming** | Native (Structured Streaming, DLT, Auto Loader) | Snowpipe Streaming, Streams/Tasks | Limited CDC capabilities |
| **AI/ML** | Native (MLflow, Feature Store, Model Serving, Vector Search) | Snowpark, Cortex AI (emerging) | Minimal |
| **Governance** | Unity Catalog (multi-cloud, multi-language, lineage) | Object tagging, masking, row access policies | Vendor-specific |
| **Data Sharing** | Delta Sharing (open protocol) | Secure Data Sharing + Marketplace | N/A |
| **Semi/Unstructured Data** | Native support | VARIANT type support | Limited |
| **Vendor Lock-in** | Low (open formats) | Moderate (proprietary storage) | High |

<sup>[14](#sources)</sup><sup>[15](#sources)</sup>

**Strategic positioning**: Databricks excels for engineering-heavy, AI-focused, or streaming-intensive workloads. Snowflake leads in SQL-first, high-concurrency BI with minimal ops. Teradata remains relevant for large enterprises with hybrid infrastructure and strict SLAs who have not yet migrated<sup>[14](#sources)</sup>.

---

## 7. Common DW Migration Challenges and How Databricks Addresses Them

### Top Migration Challenges

| Challenge | Databricks Solution |
|-----------|-------------------|
| **Proprietary SQL dialect conversion** (BTEQ, T-SQL, PL/SQL) | **Lakebridge** (fka Remorph): open-source transpiler converting to ANSI-compliant Databricks SQL/Spark SQL<sup>[16](#sources)</sup> |
| **Migration scoping and complexity assessment** | Lakebridge **Analyzer**: scans legacy tables, views, ETL jobs, stored procedures; classifies by complexity<sup>[16](#sources)</sup> |
| **Data model incompatibility** (lift-and-shift fails) | Medallion Architecture re-modeling; consulting guidance on normalization evolution<sup>[17](#sources)</sup> |
| **ETL/ELT pipeline conversion** | LakeFlow Connect (ingestion), LakeFlow Declarative Pipelines (orchestration), Auto Loader (file-based CDC)<sup>[17](#sources)</sup> |
| **Performance regression after migration** | Photon engine, Liquid Clustering, Predictive Optimization<sup>[2](#sources)</sup> |
| **Governance and security gaps** | Unity Catalog (centralized permissions, lineage, audit)<sup>[14](#sources)</sup> |
| **Multi-cloud and vendor lock-in concerns** | Open Delta Lake format, Delta Sharing protocol, multi-cloud deployment<sup>[14](#sources)</sup> |

### Migration Strategies

1. **ETL-First**: Build full Lakehouse data model (Bronze/Silver/Gold), set up Unity Catalog governance, ingest via LakeFlow Connect with CDC, convert legacy ETL<sup>[17](#sources)</sup>
2. **BI-First**: Modernize BI layer first for early user access; use "Federate, Then Migrate" or "Replicate, Then Migrate" for phased approach<sup>[17](#sources)</sup>

### Lakebridge Tool Suite

- Supports migration from 10+ platforms: Teradata, Snowflake, Oracle, SQL Server, Netezza, and more<sup>[16](#sources)</sup>
- Automated code conversion saves developers >80% of development time<sup>[16](#sources)</sup>
- Free and open-source (Databricks Labs project)<sup>[16](#sources)</sup>
- Demonstrated 2.7x faster performance and 12x cost efficiency post-migration<sup>[16](#sources)</sup>

---

## 8. Real-World FinServ DW Use Cases on Databricks

### Platform Foundation

Databricks Lakehouse for Financial Services incorporates best practices from 600+ FS customers with purpose-built solution accelerators<sup>[18](#sources)</sup>.

### Key Use Cases

**Regulatory Reporting and Compliance**
- Unified data platform consolidates risk data, finance data, and reporting processes<sup>[19](#sources)</sup>
- Unity Catalog with full Apache Iceberg support provides unified governance across all data assets, simplifying audits<sup>[20](#sources)</sup>
- Waterbear component interprets enterprise-wide data models for regulatory reporting, pre-provisions tables, processes, and data quality rules<sup>[18](#sources)</sup>
- Databricks Clean Rooms (GA) enable secure, privacy-safe collaboration with regulators<sup>[20](#sources)</sup>
- Example: Raiffeisen implemented scope-based data access with Unity Catalog for regulatory-compliant data management; Rabobank Credit built audit-ready credit analytics architecture<sup>[21](#sources)</sup>

**Risk Analytics**
- Integrates risk data, finance data, and risk analytics processes on a single platform<sup>[19](#sources)</sup>
- Gen AI capabilities provide deep insights into institution-specific data ecosystems<sup>[19](#sources)</sup>
- Real-time risk calculations using Structured Streaming + Delta Lake
- Monte Carlo simulations and VaR calculations leverage distributed Spark compute
- Reference architecture available for investment management with risk overlay<sup>[22](#sources)</sup>

**Customer 360**
- Reference architecture using Auto Loader -> Delta Lake -> Medallion Architecture<sup>[21](#sources)</sup>
- LakeFlow Declarative Pipelines for entity resolution, de-duplication, schema enforcement, and business rule application<sup>[21](#sources)</sup>
- Databricks SQL for KPI dashboards, segmentation analysis, and persona-based insights<sup>[21](#sources)</sup>
- Feature Store for ML-driven customer propensity models
- Delta Sharing enables cross-LOB customer data sharing without data copies

**Fraud Detection**
- Real-time transaction scoring via Structured Streaming
- ML model training and serving with MLflow on historical transaction data
- Graph analytics on transaction networks
- Solution accelerators provide pre-built notebooks and pipelines<sup>[18](#sources)</sup>

### FinServ Architecture Pattern

```
Sources (Core Banking, Trading, CRM, Market Data)
    |
    v
[Bronze] Auto Loader / LakeFlow Connect -> Raw Delta Tables
    |
    v
[Silver] LakeFlow Declarative Pipelines -> Conformed/Integrated (Data Vault or 3NF)
    |          - Entity resolution, SCD Type 2, data quality rules
    v
[Gold] Star Schemas / OBTs -> Regulatory Reports, Risk Dashboards, Customer 360
    |
    v
[Serving] Databricks SQL Warehouses -> BI Tools (Tableau, Power BI)
          Model Serving -> Real-time scoring (fraud, credit risk)
```

### Key Databricks Products for FinServ DW

| Product | FinServ Role |
|---------|-------------|
| Unity Catalog | Centralized governance, lineage, audit trail for regulators |
| LakeFlow Connect | CDC ingestion from core banking, trading platforms |
| LakeFlow Declarative Pipelines | Automated SCD, data quality, pipeline orchestration |
| Databricks SQL (Serverless) | BI serving for regulatory dashboards, risk reports |
| Photon | Query acceleration for complex risk calculations |
| MLflow + Model Serving | Fraud scoring, credit risk models, customer churn |
| Delta Sharing | Cross-LOB data sharing, regulator data submission |
| Clean Rooms | Privacy-safe collaboration with partners/regulators |
| Liquid Clustering | Performance optimization for large fact tables (trades, transactions) |
| Predictive Optimization | Auto-tuning table layout based on query patterns |

---

## Concerns/Notes

- Databricks-published benchmarks (e.g., 2.8x faster than Snowflake Gen2) should be validated against specific workload profiles; real-world results vary<sup>[13](#sources)</sup>
- OBT performance advantages depend heavily on Liquid Clustering being properly configured; without it, full table scans can be slower than star schema with joins<sup>[6](#sources)</sup>
- Data Vault on Databricks adds query complexity (many joins across hubs/links/satellites); PIT and Bridge tables in Gold are essential for acceptable BI query performance<sup>[5](#sources)</sup>
- LakeFlow AUTO CDC APIs require Serverless or Pro/Advanced edition pipelines<sup>[7](#sources)</sup>
- Photon does not accelerate UDF-heavy, RDD-based, or stateful streaming workloads<sup>[3](#sources)</sup>
- Teradata-specific features (e.g., temporal tables, QUALIFY, recursive queries) may require manual conversion even with Lakebridge<sup>[16](#sources)</sup>

---

## Sources

1. Databricks Blog - "Five Simple Steps for Implementing a Star Schema in Databricks with Delta Lake" - https://www.databricks.com/blog/five-simple-steps-for-implementing-a-star-schema-in-databricks-with-delta-lake
2. Databricks Docs - "Use Liquid Clustering for Tables" - https://docs.databricks.com/aws/en/delta/clustering
3. Flexera/ChaosGenius - "Databricks Photon 101: Query Acceleration Guide" - https://www.flexera.com/blog/finops/databricks-photon
4. Databricks Blog - "Prescriptive Guidance for Implementing a Data Vault Model on the Databricks Lakehouse Platform" - https://www.databricks.com/blog/2022/06/24/prescriptive-guidance-for-implementing-a-data-vault-model-on-the-databricks-lakehouse-platform.html
5. Databricks Blog - "Data Vault Best Practice Implementation on the Lakehouse" - https://www.databricks.com/blog/data-vault-best-practice-implementation-lakehouse
6. Dhristhi - "Lakehouse Modeling Playbook: When to Use Star Schemas, OBTs, or Data Vault on Databricks" - https://www.dhristhi.com/data-engineering/2025/09/24/lakehouse-modeling-playbook-when-to-use-star-schemas-obts-or-data-vault-on-databricks.html
7. Databricks Docs - "AUTO CDC APIs: Simplify change data capture with pipelines" - https://docs.databricks.com/aws/en/ldp/cdc
8. Databricks Docs - "Upsert into a Delta Lake table using merge" - https://docs.databricks.com/aws/en/delta/merge
9. Databricks Docs - "Delta Lake" - https://docs.databricks.com/aws/en/delta/
10. Databricks Blog - "Architecting a High-Concurrency, Low-Latency Data Warehouse on Databricks That Scales" - https://www.databricks.com/blog/architecting-high-concurrency-low-latency-data-warehouse-databricks-scales
11. Databricks Docs - "SQL warehouse sizing, scaling, and queuing behavior" - https://docs.databricks.com/aws/en/compute/sql-warehouse/warehouse-behavior
12. Databricks Blog - "2025 in Review: Databricks SQL, faster for every workload" - https://www.databricks.com/blog/2025-review-databricks-sql-faster-every-workload
13. DBSQL SME Engineering (Medium) - "Databricks SQL vs. Snowflake: Up to 5x Faster & 4x Lower Cost for ETL" - https://medium.com/dbsql-sme-engineering/benchmarking-etl-with-the-tpc-di-snowflake-cb0a83aaad5b
14. Bix Tech - "Databricks vs. Snowflake in 2026: Architecture-Level Guide to Lakehouse Decisions" - https://bix-tech.com/databricks-vs-snowflake-in-2026-the-architecture-level-guide-to-lakehouse-decisions/
15. Trantor Inc - "Databricks vs Snowflake: 2026 Comparison Guide" - https://www.trantorinc.com/blog/databricks-vs-snowflake
16. Databricks Blog - "Introducing Lakebridge: Free, Open Data Migration to Databricks SQL" - https://www.databricks.com/blog/introducing-lakebridge-free-open-data-migration-databricks-sql
17. Databricks Blog - "Navigating Your Migration to Databricks: Architectures and Strategic Approaches" - https://www.databricks.com/blog/navigating-your-migration-databricks-architectures-and-strategic-approaches
18. Databricks Blog - "Automated Deployment of the Databricks Lakehouse Architecture for Financial Services" - https://www.databricks.com/blog/2022/06/22/lakehouse-for-financial-services-blueprints.html
19. Databricks Blog - "Transforming Regulatory Data Management and Risk Analytics" - https://www.databricks.com/blog/transforming-regulatory-data-and-risk-analytics-power-data-intelligence-platform
20. Databricks Blog - "Shifting to Financial Intelligence: Financial Services at the Data + AI Summit 2025" - https://www.databricks.com/blog/shifting-financial-intelligence-financial-services-data-ai-summit-2025
21. Databricks - "Customer 360 Reference Architecture for Insurance" - https://www.databricks.com/resources/architectures/c360-reference-architecture-for-insurance
22. Databricks - "Financial Services Investment Management Reference Architecture" - https://www.databricks.com/resources/architectures/financial-services-investment-management-reference-architecture
