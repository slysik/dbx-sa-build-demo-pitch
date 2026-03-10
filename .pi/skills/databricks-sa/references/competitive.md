# Databricks Competitive Intelligence — SA Interview Reference

## The Golden Rule for All Competitive Questions
**Never disparage the competitor. Be diplomatic, differentiated, and customer-focused.**

Frame: *"Both platforms have strengths. Here's where Databricks differentiates for YOUR use case..."*

---

## Databricks vs. Snowflake

### When They Ask Directly
> "Both are strong platforms. Snowflake excels for SQL-heavy BI teams with a simpler operational model. Databricks differentiates when you need a unified platform spanning data engineering, warehousing, AND machine learning — because that integration tax between separate systems is real and it compounds. On pure price/performance for complex analytics, TPC-DS benchmarks show 2.8x faster at 3.6x less cost, but the real TCO story is platform consolidation."

### Battle Card

| Dimension | Databricks Wins | Snowflake Wins |
|-----------|----------------|----------------|
| **Price/Performance** | 2.8x faster, 3.6x less cost (TPC-DS) | Simpler pricing model, easier to forecast |
| **Streaming / CDC** | Native Structured Streaming, DLT, Auto Loader, LakeFlow | Snowpipe simpler for light CDC |
| **AI/ML** | Native MLflow, Feature Store, Model Serving, Agent Bricks | Snowpark ML growing but less mature |
| **Open Formats** | Delta Lake + Iceberg native; zero lock-in on the data | Iceberg support added recently; still Snowflake proprietary storage |
| **Multi-language** | Python, Scala, R, SQL, Java on the same engine | SQL-first; Snowpark adds Python/Java |
| **Governance** | Unity Catalog: multi-cloud, multi-language, ML artifacts | Strong SQL-level policies; Horizon for data sharing |
| **BI Concurrency** | Improving fast with IWM + serverless | Historical strength; strong for pure BI |
| **Ease of Use** | More powerful, steeper initial learning curve | Simpler for SQL-only teams with no Spark background |
| **Data Sharing** | Delta Sharing (open protocol, Iceberg compatible) | Secure Data Sharing (proprietary) |
| **Cost Model** | Compute + storage separate; serverless removes idle cost | Separate compute/storage; credits can be complex |

### If They're Already Using Snowflake
> "Lakehouse Federation actually lets us query Snowflake in place from Unity Catalog without data movement. So this doesn't have to be a rip-and-replace — we can federate your Snowflake data under the same governance umbrella and migrate workloads incrementally as it makes sense."

---

## Databricks vs. Azure Synapse / Microsoft Fabric

### Battle Card

> "Synapse was a warehouse bolted onto Spark as an afterthought. Databricks was purpose-built for the lakehouse pattern from day one — every feature decision optimizes for that. Microsoft Fabric is newer and interesting but less mature and still fragmented across OneLake, Power BI, Synapse Analytics, and Data Factory as separate surfaces. For customers with complex data engineering + ML workloads alongside BI, Databricks is the proven, unified platform."

**Key angles:**
- If they're on Azure: Databricks runs natively on Azure (Azure Databricks) with full Azure AD integration, ADLS Gen2 native, AAD pass-through to Unity Catalog
- If they have Power BI: Power BI Direct Query on Databricks SQL is supported and performant
- Microsoft EA context: Many Azure customers can run Databricks under their Microsoft EA via Azure Marketplace
- Fabric risk: Fabric is still assembling itself; Databricks is production-proven at PB scale

---

## Databricks vs. AWS Native (Glue + Redshift + SageMaker)

> "The challenge with assembling Glue for ETL, Redshift for DW, and SageMaker for ML is that each tool has its own metadata model, its own governance layer, its own operational plane. You end up with three separate data copies, three catalogs to reconcile, three monitoring surfaces. Databricks gives you one platform — and Unity Catalog is the single governance layer across all of it."

**Key angles:**
- EMR → Databricks: Managed, auto-scaling, no cluster management overhead
- Glue → DLT: Declarative pipelines with FLOW GRANT and built-in data quality
- Redshift → DBSQL: Photon vectorized engine; serverless warehouse eliminates cluster management
- SageMaker → MLflow + Model Serving: Tighter integration with feature data; unified lineage

---

## Databricks vs. dbt + Redshift / BigQuery / Synapse

> "dbt is a great transformation tool, but it's only transformations — you still need a separate ingestion layer, a separate ML platform, a separate governance tool. Databricks is the full pipeline from raw ingest through DLT to serving, with Unity Catalog governance across all of it. Some customers use dbt with Databricks as the compute layer — that's valid — but you get more value from DLT's declarative streaming + quality enforcement natively."

---

## Objection Handlers

### "Snowflake is simpler."
> "You're right — for a SQL-only team with pure BI workloads, Snowflake has a lower ramp. The question is whether your platform needs to grow. Once you add real-time pipelines, ML, and multi-cloud governance, the integration tax of assembling multiple tools erodes that simplicity advantage quickly."

### "We have a Snowflake contract."
> "That's a real constraint and I respect it. Two options worth considering: Lakehouse Federation to govern and query Snowflake data from Unity Catalog without moving it, or Delta Sharing to share Delta Lake data back into Snowflake. A hybrid model often makes more sense than a forced migration."

### "Our team doesn't know Spark."
> "That's actually increasingly a non-issue — Serverless SQL Warehouse means your SQL analysts never touch Spark. They just write SQL. The data engineering team benefits from Spark, but your BI users get a pure SQL experience with Photon performance."

### "Databricks is more expensive."
> "The per-DBU rate can look higher than Snowflake credits, but TCO tells a different story. Serverless eliminates idle compute cost — you pay for queries, not uptime. And consolidating DE + DW + ML onto one platform eliminates the integration tax of three separate licensing agreements, three data copy costs, three operational support contracts."

### "We're already on AWS/Azure/GCP and don't want another vendor."
> "Databricks is native on all three clouds — Azure Databricks runs in YOUR Azure subscription, billed through your existing Azure account, fully integrated with Azure AD and ADLS. It's not an external vendor relationship; it's a first-class Azure service."

---

## Competitors to Know by Account Type

| Account Type | Most Likely Competitor | Winning Angle |
|-------------|----------------------|---------------|
| FinServ (Azure) | Synapse / Fabric | Lakehouse pattern maturity; Unity Catalog compliance |
| FinServ (AWS) | Redshift + SageMaker | Platform consolidation; open Delta format |
| Retail / e-commerce | Snowflake | Streaming + ML native; real-time demand forecasting |
| Healthcare | Databricks wins on HIPAA + Unity Catalog | Emphasize compliance features |
| Manufacturing (IoT) | AWS + Kinesis | Structured Streaming native; sensor data at PB scale |
| Legacy DW migration | Snowflake | Lakebridge + Federation = lower-risk migration path |
