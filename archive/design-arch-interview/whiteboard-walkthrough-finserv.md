# Whiteboard Walkthrough — FinServ Bank Corp
### Databricks SA Design & Architecture Interview | Steve Lysik
---

> **How to use this document:** Read the sections in order. Words in *italic* are exact phrases to say aloud. Tables are your safety net when you go deep. The ⚠️ symbols are failure modes to raise proactively — before the interviewer brings them up.

---

## 🗂️ CUSTOMER BRIEF (Know Cold Before You Walk In)

| | |
|---|---|
| **Customer** | FinServ Bank Corp |
| **Headline Pain** | Regulatory reports take 5 days. Real-time KPIs are stale. Risk and compliance data is siloed across 28 systems. |
| **KPIs They Care About** | Reports in 1 day (not 5). Real-time risk dashboards live in 90 days. |
| **Current Stack** | SSIS + custom scheduled jobs. Power BI + VB6 reports. No centralized DW. |
| **Sources** | Temenos (core banking), Fiserv (loans), Bloomberg (market data), custom risk systems, Workday (HR) — 28 total |
| **Cloud** | Azure (enterprise mandate — cannot deviate) |
| **Volume** | 2–3 TB/day, growing 20%/year |
| **Consumers** | 250 knowledge workers + 5 automated systems. Regulators. Execs. Analysts. Data scientists. |
| **Compliance** | GDPR · PCI-DSS · SOX · Basel IV |
| **DR Requirement** | RPO 4 hours, RTO 2 hours (regulatory, non-negotiable) |
| **Peak Period** | Month-end close — 72-hour window. Regulatory deadline sprints. |
| **Their Pain** | SSIS fails silently. Data quality issues not caught until report time. Cross-system reconciliation is manual. |
| **Risk Profile** | High risk aversion. Governance is top priority. Prefer supported platform over DIY open-source. |

---

## STEP 1 — RESTATE THE SCENARIO (say this first, every time)
*Time: 15–20 seconds. Do not skip. This signals you listened.*

> *"Before I start drawing, let me make sure I have the right problem. I'm hearing three things: first, regulatory reporting takes 5 days and you need it down to 1 — that's the burning platform. Second, real-time KPIs are stale because SSIS jobs are batch and fragile. Third, risk and compliance data is siloed across 28 systems, which means your analysts are doing manual reconciliation before every report cycle. Is that the right framing?"*

**[Pause and wait for confirmation or correction before drawing anything.]**

---

## STEP 2 — STATE YOUR ASSUMPTIONS (say this second)
*Time: 10–15 seconds. Shows you're not guessing.*

> *"I'm going to design for Azure — that's your enterprise mandate. I'm going to assume GDPR, PCI-DSS, SOX, and Basel IV are all in scope because you mentioned all four. I'm going to assume near-real-time latency is required for the risk dashboards but regulatory reports can be T+hours, not milliseconds. And I'm going to assume this is a net-new Databricks platform — you're not migrating an existing Databricks environment. Tell me if any of those are off."*

---

## STEP 3 — DRAW THE ARCHITECTURE (narrate as you draw)

### The 5-Layer Map (draw left to right or top to bottom)

```
┌─────────────┐    ┌──────────────┐    ┌──────────────────────────────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│   SOURCES   │───▶│  INGESTION   │───▶│          MEDALLION LAKEHOUSE             │───▶│   GOVERNANCE    │───▶│   CONSUMPTION    │
│  (28 feeds) │    │  (LakeFlow)  │    │  Bronze → Silver → Gold                  │    │ (Unity Catalog) │    │  (Power BI, SQL) │
└─────────────┘    └──────────────┘    └──────────────────────────────────────────┘    └─────────────────┘    └──────────────────┘
                                                          ▲
                                                          │
                                              Delta Lake on ADLS Gen2
                                              (Azure — data never leaves region)
```

> *"I'm going to walk you through each layer and tell you the specific technology choice, why I made it, and what alternative I considered and rejected. I'll also flag failure modes as we go."*

---

## LAYER 1 — SOURCES

### What to Say:
> *"We have 28 source systems across five categories: Temenos for core banking, Fiserv for loan origination, Bloomberg for market data, custom risk systems in the middle layer, and Workday for HR. The key insight here is that these sources have very different latency profiles and access patterns — which is exactly why the ingestion layer below can't be a single SSIS job."*

### Key Points to Hit:
- Temenos and Fiserv are **transactional OLTP** → CDC is the right ingestion pattern
- Bloomberg is a **pull-based external API** → scheduled ingestion, not streaming
- Custom risk systems are **semi-structured JSON** → schema inference required
- Workday is **low-volume, daily HR feed** → simple Auto Loader

### Failure Mode to Raise:
> ⚠️ *"One thing I'd flag: the 28 sources have wildly different reliability profiles. SSIS today fails silently — you said so yourself. The architecture has to make failures visible and recoverable, not just faster."*

---

## LAYER 2 — INGESTION (LakeFlow)

### What to Say:
> *"Ingestion is where I'm replacing SSIS entirely, and I'm doing it with two Databricks-native tools: LakeFlow Connect for CDC from the transactional systems, and Auto Loader for file-based and API feeds. Let me explain why."*

### The Three Ingestion Patterns:

| Pattern | Used For | Why This, Not SSIS |
|---|---|---|
| **LakeFlow Connect — CDC** | Temenos (core banking), Fiserv (loans) | Parallelized CDC readers — not single-threaded. Captures every insert/update/delete. Exactly-once delivery into Bronze. |
| **Auto Loader (cloudFiles)** | Bloomberg flat files, Workday HR exports, custom risk system JSON dumps | Serverless, scales automatically, detects new files without polling. File notification mode eliminates directory scan bottleneck. |
| **Structured Streaming** | Any Kafka / Event Hub feeds (real-time risk signals) | Sub-minute latency for the real-time KPI dashboard requirement. |

### Technology Trade-off to State:
> *"The alternative to LakeFlow Connect is writing custom Spark streaming jobs in Python. I'm choosing LakeFlow Connect because it's managed — no cluster to maintain, built-in retry logic, schema evolution handled automatically. The trade-off is you're on Databricks' connector roadmap. For a FinServ customer with high risk aversion who explicitly said they want a supported platform over DIY open-source — that trade-off is exactly right."*

### Failure Mode to Raise:
> ⚠️ *"CDC from Temenos depends on the transaction log being accessible. If the core banking team restricts log access, the fallback is a scheduled full-diff extract into Auto Loader — slower, but safe. I'd confirm that access during discovery. It's the kind of thing that blocks a go-live."*

---

## LAYER 3 — BRONZE (Raw Landing Zone)

### What to Say:
> *"Bronze is the raw, append-only landing zone. Nothing gets transformed here. Nothing gets deleted. The only thing Bronze does is land data exactly as it arrived, with a metadata envelope — source system, ingestion timestamp, file name, batch ID — so we have a complete audit trail from day one."*

### Design Decisions:

| Decision | Choice | Why |
|---|---|---|
| **Write pattern** | Append-only, never overwrite | Full history for regulatory audit. Time Travel means you can reconstruct any point in time. |
| **Schema** | Schema-on-read with schema evolution | 28 sources evolve independently. Bronze doesn't break when Temenos adds a column. |
| **PII handling** | Raw PII lands in Bronze — access controlled via Unity Catalog | You need the raw record for audit. Masking happens in Silver, not here. |
| **Storage** | ADLS Gen2 with GRS (geo-redundant) | RPO 4h / RTO 2h requirement. GRS replicates continuously cross-region — no extra work needed. |
| **Format** | Delta tables | ACID transactions, time travel, CDC feed (CDF) for downstream Silver consumption. |

### Steve's IBM/Netezza Angle:
> *"On the Netezza side, I saw customers throw away the raw data to save storage costs and then spend $500K on a re-extract project 18 months later when the regulator asked for it. Bronze exists precisely to prevent that. Storage on ADLS is cheap. A SOX audit gap is not."*

### Failure Mode to Raise:
> ⚠️ *"Bronze must be idempotent — if LakeFlow Connect replays due to a failure, you can't get duplicate records. Delta's ACID transactions handle this: write with a unique batch ID and Delta deduplicates on commit. That's built in."*

---

## LAYER 4 — SILVER (Integration + Quality Layer)

### What to Say:
> *"Silver is where the real architecture decisions live. This is the integration layer — where 28 sources become a coherent, governed data model. I have three choices here: Data Vault, 3NF, or SCD-only. Let me tell you why I'm choosing Data Vault for this customer."*

### The Three-Way Fork (say this explicitly):

| Option | When It Wins | Decision for FinServ |
|---|---|---|
| **Data Vault** | Multi-source, regulatory audit trail, point-in-time reconstruction, new sources onboard easily | ✅ **Choosing this** — Basel IV requires point-in-time capital reconstruction. SOX requires full audit lineage. 28 sources = Hub/Link pattern prevents key conflicts. |
| **3NF** | Single-source EDW migration, SQL parity for downstream consumers | ❌ — Too many sources. 3NF breaks under multi-source key resolution. |
| **SCD-only** | Simple source, BI-only consumers, no regulatory audit | ❌ — Insufficient for Basel IV capital calculations. |

### Data Vault Components to Name:

> *"In Data Vault terms: Hubs are your business keys — Customer ID, Account Number, Transaction ID — one Hub per entity, one row per unique key, ever. Links are the relationships — Customer-to-Account, Account-to-Transaction. Satellites are the descriptive attributes — the slowly changing data, the PII fields, the status codes. Each Satellite has a load timestamp and a hash diff, so you can reconstruct any entity's state at any point in time. That's what Basel IV needs."*

### SCD Type 2 with AUTO CDC:

> *"For entities that change over time — Customer address, Account status, Risk rating — I use the declarative `APPLY CHANGES INTO ... STORED AS SCD TYPE 2` syntax. The critical detail is the `SEQUENCE BY` clause — I sequence by the **source system timestamp**, not the ingestion timestamp. This handles out-of-order CDC records automatically. If a record from Temenos arrives 10 minutes late, it inserts into history in the right position, not at the end."*

### PII and Compliance at Silver:

> *"Silver is where PII masking goes on — not Bronze. Column masks in Unity Catalog are SQL UDFs that evaluate at query time based on the caller's identity. A compliance analyst sees masked card numbers. The compliance system account sees the full value. Same table. Zero ETL copies."*

### Failure Mode to Raise:
> ⚠️ *"Data quality failures that aren't caught in Silver become regulatory incidents in Gold. I'd add Great Expectations or Databricks Expectations (built into DLT) at the Silver write boundary — check nullability, referential integrity, value ranges — and route failed records to a quarantine table, not silently drop them. The quarantine table is your data quality audit trail."*

---

## LAYER 5 — GOLD (Consumption Layer)

### What to Say:
> *"Gold is optimized purely for consumption. I'm not thinking about auditability here — that's Bronze and Silver's job. I'm thinking about the 50 concurrent Power BI users who need sub-2-second dashboard response and the regulatory system that needs to run a full Basel IV report in under 30 seconds."*

### Design Decisions:

| Decision | Choice | Why |
|---|---|---|
| **Modeling** | Kimball Star Schema | Power BI works best against star schemas. Existing report logic maps directly. Fact tables + conformed dims. |
| **Clustering** | Liquid Clustering on `transaction_date`, `customer_id` | No partition management. Incremental reclustering on OPTIMIZE — only new data moves. Change keys with ALTER TABLE, no rewrite. |
| **Aggregations** | Materialized Views for heavy pre-aggregations | Daily risk summaries, monthly P&L aggregates, regulatory capital roll-ups. MVs refresh automatically when upstream data changes. |
| **Compute** | Serverless SQL Warehouse + Photon | Photon is the vectorized query engine — 2–4x faster on TPC-DS than non-Photon. Serverless scales to zero between reports. Auto-scales during month-end peak. |
| **Month-end isolation** | Dedicated SQL Warehouse for regulatory workloads | Month-end close is a 72-hour high-pressure window. Regulatory warehouse runs independently — analyst ad-hoc queries can't starve a Basel IV report. |

### Liquid Clustering Talking Point:
> *"Liquid Clustering replaces both partitioning AND Z-ORDER in a single feature. It's incremental — only reclusters new data on OPTIMIZE — so it doesn't block writes. And you can change clustering keys with a single ALTER TABLE, no full table rewrite. For a fact table that's growing 20% a year, that's huge — you don't re-architect the table every time query patterns shift."*

### Materialized Views Talking Point:
> *"The regulatory reporting team today runs a 5-day process because every report re-derives aggregates from raw transaction data. With Materialized Views, those aggregations are pre-computed and incrementally maintained. The report query hits a pre-built summary, not a 2TB fact table. That's the primary mechanism for getting from 5 days to 1 day."*

### Failure Mode to Raise:
> ⚠️ *"Gold tables are the consumer-facing layer, so schema changes need to be managed carefully. I'd use the `Delta schema evolution` with `mergeSchema` controlled at the pipeline level, not ad-hoc. And I'd add the Gold table DDL to the CI/CD pipeline so a developer can't accidentally drop a column that Power BI is using."*

---

## LAYER 6 — GOVERNANCE (Unity Catalog)

### What to Say:
> *"Unity Catalog is the single governance layer across every data asset — tables, files in Volumes, ML models, functions. It's not a separate tool. It's built into the Databricks control plane. Every query against every table generates lineage automatically — no agents to deploy, no configuration."*

### The Four Governance Controls:

| Control | Applies To | FinServ Use Case |
|---|---|---|
| **Row Filters** | Silver + Gold tables | GDPR: European customer records filtered by region tag. Basel IV: jurisdiction-specific capital rows visible only to authorized systems. |
| **Column Masks** | Silver tables (PII Satellites) | PCI-DSS: card numbers masked for all non-compliance roles. GDPR: SSN / DOB masked for analysts. Full value visible to compliance system account only. |
| **ABAC Tag Policies** | Multi-jurisdiction datasets | Tag `pii:true`, `jurisdiction:eu`, `sensitivity:restricted` at the column level. Policy evaluates at query time — no manual access list maintenance. |
| **Column Lineage** | All tables | Auto-captured. No config. Regulator asks "where did this capital number come from?" — you can trace it back to the Temenos transaction in 30 seconds. |

### Key Differentiator to State:
> *"The thing that makes Unity Catalog different from legacy DW security is that the row filters and column masks travel with the data. It doesn't matter whether the analyst is querying from Power BI, a DBSQL notebook, or a Python script via JDBC — the policy evaluates at query time based on their identity. You define governance once, it inherits down catalog → schema → table → column. That's the architecture that makes a GDPR audit tractable instead of terrifying."*

### Audit Trail Point:
> *"Unity Catalog system tables capture every query, every access, every identity, every object change. SOX quarterly compliance certification? That's a SQL query against the audit system table. You're not asking 10 teams to produce access logs — it's one place."*

---

## LAYER 7 — CONSUMPTION

### What to Say:
> *"Consumption is where the business actually sees the value. I have four consumer profiles here, and each gets the right tool for their workflow — I'm not forcing everyone into one interface."*

### Consumer Map:

| Consumer | Tool | Why |
|---|---|---|
| **Executive dashboards** | Power BI Direct Query → Serverless SQL | Existing Power BI investment preserved. Direct Query means data is always fresh — no scheduled refresh lag. Photon makes DQ fast enough that Import mode isn't needed. |
| **Regulatory reports** | Databricks SQL (DBSQL) scheduled queries | Dedicated SQL Warehouse. Reports run on a schedule, results exported to regulatory format. Replaces VB6 reports with maintainable SQL. |
| **Self-service analysts** | AI/BI Genie | Natural language to SQL. Analysts ask "show me top 10 customers by transaction volume in Q3" — Genie writes and executes the SQL. No ticket to the data team. This is the data democratization use case. |
| **Data scientists** | MLflow + Databricks Notebooks | Risk models trained on Gold features. MLflow tracks experiments, registers models, serves predictions via Model Serving endpoints. |
| **Regulators / external sharing** | Delta Sharing | Share specific Gold tables with regulators without copying data. They query via standard Spark/Python/SQL. Data never leaves your ADLS. |

---

## STEP 4 — PROACTIVELY RAISE FAILURE MODES
*Say this before the interviewer asks. It's the single biggest signal of senior architectural thinking.*

> *"Before I take questions, let me call out the three failure modes I'd want to design against explicitly..."*

### Failure Mode 1 — Month-End Surge
> *"Month-end close is a 72-hour window where every finance analyst, every regulatory system, and every automated job is hitting the platform simultaneously. My mitigation: dedicated serverless SQL Warehouses per workload class so regulatory workloads can't be starved by analyst ad-hoc queries. Serverless auto-scales to meet the peak — you're not capacity planning for 72 hours/month by leaving compute idle the rest of the year."*

### Failure Mode 2 — SSIS Fails Silently (Their Stated Pain)
> *"Their existing SSIS jobs fail silently — they find out at report time. My mitigation: every LakeFlow Connect pipeline and Spark Declarative Pipeline emits job metrics to Azure Monitor and Datadog (both of which they already have). I'd add row-count expectations at the Bronze write — if Temenos sends 10% fewer records than yesterday's watermark, alert before it becomes a data quality problem downstream."*

### Failure Mode 3 — DR and the RPO/RTO Requirement
> *"RPO 4 hours, RTO 2 hours is a regulatory hard requirement. My mitigation: ADLS Gen2 with geo-redundant storage — Delta files are continuously replicated. Recovery is a `RESTORE TABLE AS OF` to the last clean commit. Unity Catalog metastore is managed by Databricks on a geo-redundant control plane. What I'd add is a documented and tested runbook — because an untested DR plan is not a DR plan. I'd schedule a quarterly DR drill as part of the platform ops model."*

---

## STEP 5 — OPEN QUESTIONS TO SURFACE
*If you have time, or if the interviewer asks "what would you still need to know?" — use these.*

> *"There are a few things I'd want to nail down before I finalized this design..."*

1. **"Is the Bloomberg feed via API pull or do you have a Bloomberg B-PIPE subscription?"** → Affects whether it's Auto Loader or Structured Streaming
2. **"For the Basel IV capital calculations — are those running SQL queries on the EDW today, or does a separate risk platform like AxiomSL own that calculation?"** → If EDW, Silver needs full Data Vault. If AxiomSL, you only need to feed it clean data.
3. **"How many people write their own SQL today vs. consume pre-built reports?"** → High SQL ratio → DBSQL + Genie is the story. Low ratio → focus on Power BI.
4. **"What's the data residency requirement for your Azure region?"** → UK South? West Europe? This affects Unity Catalog metastore placement and GRS pair selection.
5. **"Is there a semantic layer today — SSAS, Power BI Premium dataset, or Business Objects — sitting above the current reports?"** → If yes, preserve it. DBSQL has an XMLA endpoint that's compatible with existing SSAS semantic models.

---

## STEP 6 — THE CLOSING STATEMENT
*Land the plane with a business outcome, not a technology list.*

> *"So to bring it back to your KPIs: the Materialized Views in Gold, fed by near-real-time CDC from LakeFlow, are what gets you from 5-day reporting to 1-day — or better. The dedicated regulatory SQL Warehouse with Photon is what gives you the <2-second executive dashboard. And the Unity Catalog governance layer with auto-lineage is what makes your GDPR audit in Q3 and your regulatory deadline in Q4 tractable instead of a fire drill. I've built a working version of this pipeline — Bronze through Gold to MLflow — if you'd like to go deeper on any layer."*

---

## QUICK REFERENCE — KEY TECHNOLOGY CHOICES

| Layer | Technology | One-Line Rationale |
|---|---|---|
| Ingestion | LakeFlow Connect (CDC) | Parallelized, managed, exactly-once. Replaces SSIS. |
| Ingestion | Auto Loader (cloudFiles) | Serverless file ingestion. Scales horizontally. File notification mode. |
| Bronze | Append-only Delta + ADLS GRS | Full audit history. Time Travel. Geo-redundant for RPO/RTO. |
| Silver | Data Vault + SCD Type 2 (AUTO CDC) | Basel IV point-in-time reconstruction. 28-source key resolution. |
| Silver | Unity Catalog Column Masks | PCI-DSS card masking. GDPR PII masking. Evaluates at query time. |
| Gold | Kimball Star Schema | Power BI optimized. Existing report logic maps directly. |
| Gold | Liquid Clustering (transaction_date, customer_id) | No partition management. Incremental. Changeable keys. |
| Gold | Materialized Views | Pre-aggregated regulatory summaries. 5-day → 1-day reports. |
| Compute | Serverless SQL Warehouse + Photon | Auto-scale for month-end peak. 2–4x query speedup. |
| Governance | Unity Catalog Row Filters + ABAC | GDPR regional filtering. Tag-based, inherits down the hierarchy. |
| Consumption | Power BI Direct Query | Existing investment preserved. Always-fresh data. |
| Consumption | AI/BI Genie | Self-service analytics. NL → SQL. Data democratization. |
| Consumption | Delta Sharing | Regulator access without data copies. |
| Consumption | MLflow Model Serving | Risk/fraud ML models. Feature Store on Gold. |

---

## PHRASES TO HAVE READY

| Situation | What to Say |
|---|---|
| Asked why not Snowflake | *"Snowflake is a strong SQL platform. Where Databricks wins here is that your data scientists and your SQL analysts are on the same platform — same governance, same data, no copy tax. The Basel IV capital models and the Power BI dashboards run on the same Gold layer. That's one audit scope, not two."* |
| Asked about Data Vault complexity | *"Data Vault adds upfront modeling work. The payoff is that when source 29 gets added, you add a Satellite — you don't restructure your fact tables. For a bank with 28 sources today and a regulatory mandate to add new reporting domains, that's not complexity, it's insurance."* |
| Asked why not just use dbt | *"dbt is a great transformation framework — it works on top of Databricks. I'd absolutely use it for the Gold layer SQL transformations if the team is already dbt-fluent. The Bronze and Silver ingestion patterns — CDC, SCD Type 2, schema evolution — are better served by Spark Declarative Pipelines or LakeFlow. They're complementary, not competing."* |
| If you go blank | *"Let me think through the options here before I commit to a choice..."* — then use the three-way fork technique. |
| When they push back on a decision | *"You're right that's a trade-off. Let me go back to first principles: the non-negotiable constraint here is [X]. If that constraint changed, I'd reconsider. Given it doesn't, I'd stay with [Y] because..."* |

---

## STEVE'S PERSONAL ANGLES (weave in naturally)

- **On SSIS pain:** *"I've seen this pattern at every large bank I worked with at IBM — the batch ETL works fine at 1TB and then quietly falls apart at 5TB. Nobody changes the monitoring thresholds. You find out at report time."*
- **On Basel IV:** *"Basel IV capital calculations require point-in-time reconstruction of your risk positions. That's not a nice-to-have in the data model — it's a regulatory requirement. Data Vault's satellite timestamps give you that for free. A star schema does not."*
- **On Microsoft/Azure:** *"I spent 3.5 years at Microsoft and I understand the Azure EA relationship. Databricks on Azure is a first-party integration — it appears in the Azure Marketplace, counts toward Azure commit, and is jointly sold with Microsoft. That matters when you're navigating the enterprise procurement conversation."*
- **On governance as a differentiator:** *"Every bank I've talked to has the same story: governance is managed in spreadsheets and tribal knowledge. Unity Catalog auto-lineage means a regulator can ask 'where did this number come from?' and you answer in 30 seconds with a query, not a 3-week investigation."*

---

*Document generated for Steve Lysik — FinServ Bank Corp scenario — Databricks SA Design & Architecture Interview*
*To import to Google Docs: docs.google.com → New → File → Open → Upload this .md file*
