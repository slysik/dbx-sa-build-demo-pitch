# Design & Architecture Interview — Full Prep Guide
## Databricks Solutions Architect | DW Spike | Steve Lysik

---

## PART 1: Discovery Questions Checklist

**Use this as your mental framework in the first 10-15 minutes. Don't rush to whiteboard.**

### Category 1: Business Context (Ask First)
- "What's the primary business problem you're trying to solve?"
- "Who are the end consumers of this data? Analysts? ML models? Regulators? Executives?"
- "What does success look like? What KPIs are you tracking?"
- "What's the timeline? Is there a regulatory deadline or business milestone driving this?"

### Category 2: Current State
- "What systems are you running today?" (legacy DW, Hadoop, cloud DW, SaaS apps)
- "What's your cloud footprint?" (Azure, AWS, GCP, multi-cloud, hybrid)
- "Where does the data live right now?" (on-prem DBs, S3/ADLS, SaaS APIs, mainframes)
- "What BI tools are your users on today?" (Power BI, Tableau, Looker, in-house)
- "How are you handling ETL/ELT today?" (Informatica, SSIS, Airflow, manual scripts)

### Category 3: Data Characteristics
- "What are the key data domains?" (transactions, customers, products, events)
- "What's the data volume? How fast is it growing?" (GB/TB/PB, growth rate)
- "What's the latency requirement?" (real-time, near-real-time, hourly, daily batch)
- "What data formats?" (structured/relational, semi-structured/JSON, unstructured/docs/images)
- "How many source systems are feeding into this?" (5? 50? 500?)

### Category 4: Non-Functional Requirements
- "What are your governance/compliance requirements?" (GDPR, CCPA, PCI-DSS, SOX, HIPAA)
- "What's the disaster recovery expectation?" (RPO/RTO)
- "How many concurrent users need to query this?" (10 analysts vs 10,000 dashboard viewers)
- "What's your budget model?" (CapEx vs OpEx, department chargebacks)
- "Who manages this day-to-day?" (central platform team? decentralized?)

### Category 5: Constraints & Preferences
- "Are there technology mandates from your CTO/CIO?" (e.g., must be Azure)
- "Are there existing contracts or commitments?" (e.g., Microsoft EA, Snowflake contract)
- "What's the team's skill set?" (SQL-heavy? Python? Spark experience?)
- "What's failed before or caused pain?" (this reveals hidden requirements)

### Pro Tips for Discovery
- **Repeat back what you hear**: "So if I'm understanding correctly, the core need is X, constrained by Y, and the primary users are Z."
- **State your assumptions explicitly**: "I'm going to assume [X] — let me know if that's off base."
- **Ask "why" behind requirements**: "You mentioned real-time — is that a true sub-second requirement, or would 5-minute latency actually work?"

---

## PART 2: Architecture Whiteboarding Framework

**Use this structure every time. It gives you a repeatable skeleton.**

### The 5-Layer Architecture Template

```
┌─────────────────────────────────────────────────────┐
│  1. SOURCES                                          │
│     (What data are we ingesting?)                    │
├─────────────────────────────────────────────────────┤
│  2. INGESTION                                        │
│     (How does data get in? Batch/streaming/CDC)      │
├─────────────────────────────────────────────────────┤
│  3. STORAGE & PROCESSING (Medallion Architecture)    │
│     Bronze → Silver → Gold                           │
├─────────────────────────────────────────────────────┤
│  4. GOVERNANCE & SECURITY                            │
│     (Unity Catalog, access control, lineage)         │
├─────────────────────────────────────────────────────┤
│  5. CONSUMPTION                                      │
│     (BI dashboards, ML models, APIs, reports)        │
└─────────────────────────────────────────────────────┘
```

### For Each Layer, State:
1. **What** — the technology/pattern choice
2. **Why** — the trade-off that led you here
3. **What could go wrong** — failure modes and mitigations

### Trade-Off Phrases to Use
- "The trade-off here is [X] vs [Y]. I'm choosing [X] because..."
- "If the requirements change to [Z], I'd reconsider and use [Y] instead."
- "This adds complexity, but the benefit of [X] justifies it because..."
- "A simpler alternative would be [Y], but it wouldn't handle [constraint] well."

---

## PART 3: DW Spike Deep Dive — What They'll Ask

**Your declared spike is DW. Expect 15-20 minutes of pointed questions.**

### Topic 1: Dimensional Modeling on Lakehouse

**Q: "When would you use star schema vs Data Vault vs One Big Table?"**

| Pattern | When to Use | Databricks Fit |
|---------|-------------|----------------|
| **Star Schema (Kimball)** | Known query patterns, BI-heavy, SQL users | Gold layer; Photon delivers up to 18x perf for star joins |
| **Data Vault 2.0** | Many source systems, auditability required, agile teams | Silver layer (Hubs/Links/Satellites); Gold for consumption |
| **One Big Table (OBT)** | Single-purpose analytics, dashboard serving | Gold layer; >20x speedup with Liquid Clustering |

**Your angle**: "In practice, I'd recommend a hybrid — Data Vault or 3NF in Silver for integration and auditability, star schemas or OBTs in Gold for consumption. The medallion architecture gives you a natural separation."

**Q: "How do you implement SCDs on Delta Lake?"**

- **SCD Type 1**: Simple MERGE INTO with UPDATE on match, INSERT on no match
- **SCD Type 2**: Staged union approach with MERGE (manual) OR **LakeFlow AUTO CDC** with `STORED AS SCD TYPE 2` + `TRACK HISTORY ON` (declarative, recommended)
- **SCD Type 3**: MERGE with `SET previous_col = target.col, col = source.col`
- **Key point**: AUTO CDC APIs handle out-of-order records automatically via SEQUENCE BY — huge advantage over hand-rolled SCD logic

### Topic 2: Query Performance & Optimization

**Q: "How do you optimize query performance on Databricks?"**

Walk through this layered approach:

1. **Data layout** — Liquid Clustering (replaces Z-ORDER + partitioning, GA)
   - Up to 4 clustering keys on frequently filtered columns
   - `CLUSTER BY AUTO` lets the platform choose based on query patterns
2. **Table maintenance** — Predictive Optimization (GA, auto-enabled)
   - Automatically runs OPTIMIZE, VACUUM, ANALYZE
   - Zero manual maintenance on Unity Catalog managed tables
3. **Compute** — Serverless SQL Warehouse with Photon
   - IWM (Intelligent Workload Management) auto-scales
   - PQE (Predictive Query Execution) replans mid-query for skew
   - 40% improvement in 2025 with no tuning needed
4. **Semantic** — Materialized Views for frequently-run aggregations
   - Incremental refresh backed by serverless DLT
   - Requires row tracking on source tables

**Q: "What's Liquid Clustering and why does it matter?"**

- Replaces both partitioning AND Z-ORDER in a single feature
- Incremental — only reclusters new/changed data on OPTIMIZE
- Changeable — `ALTER TABLE ... CLUSTER BY (new_cols)` without full rewrite
- Auto mode — `CLUSTER BY AUTO` analyzes query workload to pick columns
- Recommended for ALL new tables per Databricks docs

### Topic 3: Migration from Legacy DW

**Q: "How would you migrate a customer from Teradata/Netezza to Databricks?"**

Your IBM background is GOLD here. Walk through:

1. **Assess** — Use Lakebridge Analyzer to scan legacy environment
   - Classifies tables, views, ETL, stored procedures by complexity
   - Produces automated assessment report in hours, not months
2. **Strategy** — Choose migration approach:
   - **Federation-First** (lowest risk): Lakehouse Federation queries legacy DW in place while you migrate incrementally
   - **Parallel Run**: Both systems live during transition, Lakebridge reconciler validates
   - **Medallion Refactor**: Re-architect into Bronze/Silver/Gold during migration
3. **Convert** — Lakebridge transpilers convert proprietary SQL (BTEQ, T-SQL, PL/SQL)
   - BladeBridge (mature), Morpheus (next-gen), Switch (LLM-powered)
   - Automates up to 80% of conversion
4. **Optimize** — Liquid Clustering + Predictive Optimization + Photon
   - Reported 2.7x faster performance, 12x cost efficiency post-migration
5. **Govern** — Unity Catalog replaces legacy DW security model

**Your personal story**: "At IBM, I spent 8 years helping customers manage Netezza environments. I've seen the pain of proprietary platforms firsthand — the scaling limitations, the vendor lock-in. That's exactly why the open lakehouse approach resonates with me."

### Topic 4: Governance for DW

**Q: "How do you handle data governance on Databricks?"**

Unity Catalog — single governance layer across everything:

| Feature | Status | What It Does |
|---------|--------|-------------|
| Row Filters | **GA** | SQL UDFs that filter rows at query time by user/role |
| Column Masks | **GA** | Replace sensitive column values based on identity |
| ABAC | **Public Preview** | Tag-based policies that inherit down catalog → schema → table |
| Table + Column Lineage | **GA** | Automatic, runtime, all languages |
| Data Classification | **GA** | Auto-detect PII |
| Budget Policies | **GA** | Tag-based cost attribution for serverless |

### Topic 5: Databricks vs Snowflake (They WILL ask)

**Be diplomatic but clear on differentiators:**

| Dimension | Databricks Wins | Snowflake Wins |
|-----------|----------------|----------------|
| **Price/Performance** | 2.8x faster, 3.6x less cost (TPC-DS-like) | Simpler pricing model |
| **Streaming** | Native Structured Streaming, DLT, Auto Loader | Snowpipe is simpler for light CDC |
| **AI/ML** | Native MLflow, Feature Store, Model Serving | Snowpark growing but less mature |
| **Open Formats** | Delta Lake, no vendor lock-in | Iceberg support added recently |
| **Governance** | Unity Catalog (multi-cloud, multi-language) | Strong SQL-level policies |
| **BI concurrency** | Improving rapidly with IWM | Historical strength |
| **Ease of use** | More powerful but steeper curve | Simpler for SQL-only teams |

**Diplomatic framing**: "Both platforms have strengths. Databricks differentiates on the unified platform story — data engineering, DW, and ML on one platform with open formats. For a customer doing more than just BI, the TCO advantage is significant because you eliminate the integration tax between separate systems."

---

## PART 4: Mock Scenario — Practice Walkthrough

### Scenario: Global FinServ Data Platform

> "A multinational bank (50 countries, $200B AUM) wants to consolidate their
> data infrastructure. They currently run Teradata on-prem for their data
> warehouse (15 years old, 500TB), Oracle for transactional systems, and have
> various departmental Snowflake instances. They need a unified platform for
> regulatory reporting (Basel III/IV), risk analytics, and customer 360.
> They're on Azure. Go."

### How You Should Walk Through It

**1. Discovery (5-7 min)**

Ask:
- "Which regulatory bodies are primary? OCC, ECB, local central banks?"
- "What's the mix of batch vs real-time requirements? Is risk calculation real-time?"
- "How many users will access this? What's the BI tool landscape?"
- "What's the migration timeline? Big bang or phased?"
- "What's the data sensitivity classification? Are there data residency requirements by country?"
- "Who's managing this — central platform team or federated by LOB?"

State assumptions: "I'll assume Azure is mandated, Basel III reporting has specific deadlines, the Teradata migration is the critical path, and we want to preserve existing Snowflake investments during transition."

**2. Architecture Whiteboard (15-20 min)**

Draw the 5 layers:

```
SOURCES                          INGESTION                    PROCESSING
┌──────────┐                    ┌──────────┐               ┌──────────────────┐
│ Teradata │──Federation/LFC──→│ LakeFlow │──CDC──→       │ BRONZE           │
│  (500TB) │                    │ Connect  │               │ Raw Delta tables │
├──────────┤                    ├──────────┤               │ Append-only      │
│ Oracle   │──LakeFlow──────→  │ Auto     │──Stream──→    │ Regulatory audit │
│ (OLTP)   │  Connect          │ Loader   │               ├──────────────────┤
├──────────┤                    ├──────────┤               │ SILVER           │
│Snowflake │──Federation/      │ Kafka/EH │──Structured──→│ Data Vault model │
│(departm) │  Delta Sharing    │          │  Streaming    │ SCD Type 2       │
├──────────┤                    └──────────┘               │ PII masked       │
│ Market   │                                              ├──────────────────┤
│ Data APIs│                                              │ GOLD             │
└──────────┘                                              │ Star schemas:    │
                                                          │ - Regulatory     │
                                                          │ - Risk analytics │
                                                          │ - Customer 360   │
                                                          └────────┬─────────┘
                                                                   │
GOVERNANCE (Unity Catalog)                            CONSUMPTION   │
┌────────────────────────┐                          ┌──────────────┴──┐
│ • Row filters/col masks│                          │ DBSQL Serverless│
│ • ABAC tag policies    │                          │ Power BI DirectQ│
│ • Column-level lineage │                          │ MLflow models   │
│ • Data residency tags  │                          │ Regulatory feeds│
│ • Budget policies/LOB  │                          │ Delta Sharing   │
└────────────────────────┘                          └─────────────────┘
```

**Key decisions to explain:**

| Decision | Why | Trade-off |
|----------|-----|-----------|
| **Federation-first for Teradata** | De-risks migration, no big bang cutover | Slightly slower queries vs native Delta, but worth the safety |
| **Data Vault in Silver** | 50+ countries, many source systems, full auditability | More complex than 3NF, but pays off for regulatory traceability |
| **Star schemas in Gold** | Known BI query patterns, Photon-optimized | Less flexible than Data Vault for ad-hoc, but 18x faster for dashboards |
| **LakeFlow Connect for CDC** | Managed connectors for Oracle, Teradata | Less flexible than custom Kafka, but operational simplicity wins |
| **Serverless SQL for BI** | Auto-scaling, IWM, no idle costs | Higher per-DBU than Classic, but lower TCO for bursty workloads |
| **Unity Catalog ABAC** | 50 countries = need tag-based governance at scale | Public Preview, so might need manual row filters as fallback |

**3. DW Deep Dive (10-15 min)**

When they drill in, be ready for:

- **"How would you model the regulatory reporting Gold tables?"**
  → Star schema: fact_regulatory_positions (daily snapshot), dim_entity, dim_instrument, dim_jurisdiction, dim_reporting_period
  → Liquid Clustering on (reporting_date, jurisdiction_code)
  → Materialized views for pre-aggregated Basel ratios

- **"How do you handle SCD for the customer dimension across 50 countries?"**
  → AUTO CDC with `STORED AS SCD TYPE 2` + `TRACK HISTORY ON` for material changes (address, risk rating)
  → Type 1 for non-material (last login date)
  → Data residency handled via Unity Catalog row filters on country tags

- **"What about performance for the risk analytics queries?"**
  → Large fact tables with Liquid Clustering on (trade_date, instrument_type)
  → Photon engine for complex aggregations (VaR calculations)
  → Materialized views for pre-computed risk metrics refreshed on schedule
  → Serverless SQL Warehouse with IWM for burst capacity during month-end

- **"How do you migrate 500TB off Teradata?"**
  → Phase 1: Lakebridge Analyzer to assess and prioritize
  → Phase 2: Lakehouse Federation — query in place, no disruption
  → Phase 3: Migrate by domain (customer first, then risk, then regulatory)
  → Phase 4: Lakebridge transpiler for SQL conversion (80% automated)
  → Phase 5: Reconcile with Lakebridge reconciler, cut over by domain

---

## PART 5: Quick Reference Card (Print This)

### 10 Things to Say in the Interview

1. "Let me start with some discovery questions before I whiteboard."
2. "The trade-off here is [X] vs [Y] — I'm choosing [X] because..."
3. "In my experience at IBM/Microsoft with similar customers..."
4. "Liquid Clustering replaces both partitioning and Z-ORDER — it's the new default."
5. "Predictive Optimization eliminates manual OPTIMIZE/VACUUM entirely."
6. "Unity Catalog provides a single governance layer across all data assets."
7. "Lakehouse Federation lets us query the legacy DW in place while we migrate."
8. "Lakebridge automates 80% of the SQL conversion from legacy platforms."
9. "The open format advantage means zero vendor lock-in on the data itself."
10. "One platform for DE + DW + ML eliminates the integration tax."

### 5 Things to NEVER Say

1. "I'd just do a lift-and-shift." (Shows no architecture thinking)
2. "Snowflake is bad." (Shows bias, not consultative judgment)
3. "Let me start drawing the architecture." (Discovery first!)
4. "That's how we always do it." (Rigid thinking — a listed pitfall)
5. "I'm not sure about that." (Instead: "Let me think through the options...")

### Your Personal Differentiators

- **8 years at IBM/Netezza**: Deep DW migration experience from the legacy side
- **3.5 years at Microsoft Data & AI**: $50M+ in Azure AI/Data sales across Fortune 500
- **Hands-on pipeline**: Your FinServ Bronze → Silver → Gold → MLflow demo
- **FinServ domain**: You speak the language (MCC codes, PCI-DSS, Basel, SARs)

---

## Reference Files (Also in this directory)

- `databricks-dw-features-research.md` — Detailed DW feature reference (GA/Preview status)
- `databricks-dw-architecture-report.md` — Architecture patterns deep dive
- `databricks_genie_vs_powerbi.md` — BI strategy talking points
- `notebooks/` — Your working FinServ pipeline demo
