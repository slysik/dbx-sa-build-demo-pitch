# Databricks SA Discovery Questions & Design Interview Preparation

## Research Task
Research common Databricks Solutions Architect discovery questions used during the 60-minute Design & Architecture Interview, covering: (1) discovery questions that reveal hidden requirements, (2) DW migration-specific questions, (3) data mesh/governance/multi-region questions, (4) consultative thinking techniques, and (5) deep-dive technical questions on DW performance features.

## Summary
The Databricks Design & Architecture Interview is a 60-minute session where interviewers act as customer stakeholders and present a high-level business scenario (e.g., "global data ingestion for a large client" or "data warehouse migration to lakehouse"). Candidates are evaluated on three axes: Discovery & Problem Framing, Core Architecture Design, and Technical Spike depth (DE, DW, or AI/ML)<sup>[1](#sources)</sup>. The single most important differentiator between strong and weak candidates is **starting with discovery questions before whiteboarding** -- the official prep guide explicitly warns against "jumping the gun"<sup>[1](#sources)</sup>. Top SAs use structured discovery frameworks (SPIN, MEDDIC) adapted to technical contexts, peel the onion on each topic rather than skipping across surface-level questions, and resist the urge to pitch solutions before fully understanding the problem<sup>[7](#sources)</sup><sup>[8](#sources)</sup>.

---

## Detailed Findings

### 1. Discovery Questions That Reveal Hidden Requirements

These are organized from broad business context down to specific technical constraints. The sequence matters -- top SAs follow a funnel pattern<sup>[7](#sources)</sup>.

#### A. Business Context & Motivation
| # | Question | What It Reveals |
|---|----------|----------------|
| 1 | "What is the business outcome you are trying to achieve with this initiative?" | Whether this is cost reduction, time-to-insight, regulatory compliance, or new revenue -- shapes every downstream decision<sup>[9](#sources)</sup> |
| 2 | "What prompted this project now? Was there a triggering event?" | Urgency, executive sponsorship, regulatory deadline, or competitive pressure. Reveals timeline constraints<sup>[7](#sources)</sup> |
| 3 | "Who are the primary consumers of this data, and what decisions do they make with it?" | Identifies personas (analysts, data scientists, applications) and their latency/freshness requirements |
| 4 | "What does success look like in 6 months? In 2 years?" | Separates MVP scope from long-term vision; prevents over-engineering |
| 5 | "What happens if this project fails or is delayed?" | Reveals true business criticality and risk tolerance |
| 6 | "Are there any organizational changes (mergers, reorgs, new business units) on the horizon?" | Hidden scope changes that will affect architecture decisions |

#### B. Current State & Pain Points
| # | Question | What It Reveals |
|---|----------|----------------|
| 7 | "Walk me through a typical day for your data engineering team -- where do they spend the most time?" | Operational pain points, manual processes, firefighting vs. building |
| 8 | "What is your current data freshness SLA, and are you meeting it?" | Gap between current state and requirements; whether streaming is truly needed or batch suffices<sup>[2](#sources)</sup> |
| 9 | "How many data sources feed into your current platform, and what formats/protocols do they use?" | Integration complexity, schema diversity, CDC requirements |
| 10 | "What are your current query performance SLAs? Which queries are problematic?" | Identifies whether the problem is ingestion, transformation, or serving |
| 11 | "What keeps your team up at night regarding data quality or reliability?" | Data quality gaps, missing monitoring, silent failures |
| 12 | "How do you handle schema changes from upstream sources today?" | Schema evolution maturity; Delta Lake schema enforcement/evolution becomes a natural value prop |

#### C. Constraints & Non-Functional Requirements (The Hidden Requirement Gold Mine)
| # | Question | What It Reveals |
|---|----------|----------------|
| 13 | "What regulatory or compliance frameworks apply to this data? (GDPR, CCPA, SOX, HIPAA, PCI-DSS)" | Data residency requirements, encryption needs, audit trail requirements, PII handling<sup>[5](#sources)</sup> |
| 14 | "Do you have data sovereignty requirements that restrict where data can be stored or processed?" | Multi-region architecture needs; may eliminate certain design patterns entirely |
| 15 | "What is your RPO (Recovery Point Objective) and RTO (Recovery Time Objective)?" | DR/HA requirements that fundamentally shape architecture (active-active vs. active-passive, cross-region replication)<sup>[2](#sources)</sup> |
| 16 | "What is your budget model -- are you CapEx or OpEx oriented? Do you have a target cost per TB?" | Serverless vs. provisioned compute; reserved capacity vs. on-demand |
| 17 | "Who needs to approve architectural decisions, and what is your change management process?" | Decision-making process, organizational friction, hidden stakeholders |
| 18 | "Are there existing enterprise standards for cloud provider, networking, or security tooling?" | Constraints that narrow the solution space (e.g., must use Azure Private Link, must integrate with CyberArk) |
| 19 | "What is your team's current skill set? Do you have Spark/Python expertise, or is your team primarily SQL-based?" | Determines whether to recommend DBSQL, notebooks, DLT with SQL, or PySpark-heavy approaches |
| 20 | "What downstream systems consume this data? BI tools, ML platforms, operational applications, APIs?" | Integration requirements that affect the Gold layer design and serving strategy<sup>[5](#sources)</sup> |

---

### 2. DW Migration-Specific Discovery Questions (Teradata / Netezza / Snowflake to Databricks)

These questions are critical because DW migrations have a high failure rate driven by hidden complexity. One retail company discovered over 3,000 stored procedures but only 200 were actively used in the last 6 months -- drastically simplifying their migration scope<sup>[4](#sources)</sup>.

#### A. Workload Assessment
| # | Question | What It Reveals |
|---|----------|----------------|
| 21 | "Can you provide a workload profile? What percentage is ETL vs. BI/reporting vs. ad-hoc queries vs. ML?" | Shapes compute sizing strategy; ETL-heavy = jobs clusters, BI-heavy = SQL Warehouses<sup>[3](#sources)</sup> |
| 22 | "How many stored procedures, views, and UDFs exist in the current system? How many are actively used?" | True migration scope -- often 60-80% of objects are unused. Lakebridge can inventory and classify by complexity<sup>[4](#sources)</sup> |
| 23 | "What proprietary SQL extensions or features are you using? (BTEQ, QUALIFY, MERGE with complex logic, temporal tables)" | Conversion complexity. Teradata's BTEQ, Netezza's nzsql, and Snowflake's VARIANT handling all require specific translation strategies<sup>[4](#sources)</sup><sup>[6](#sources)</sup> |
| 24 | "What is your current concurrency profile? How many simultaneous users/queries at peak?" | SQL Warehouse sizing, auto-scaling configuration, and whether serverless is appropriate |
| 25 | "Do you have workload management/priority queues in your current DW?" | Maps to DBSQL Warehouse queuing and query prioritization |
| 26 | "What is your data retention policy? How much historical data needs to migrate vs. archive?" | Migration timeline and storage cost projections; often only recent data needs hot migration |

#### B. Technical Compatibility
| # | Question | What It Reveals |
|---|----------|----------------|
| 27 | "What ETL/ELT tools orchestrate your current pipelines? (Informatica, DataStage, SSIS, Airflow, dbt)" | Integration points; some tools have Databricks connectors, others need replacement |
| 28 | "What BI tools connect to your warehouse? (Tableau, Power BI, Looker, MicroStrategy)" | Connector compatibility; may need JDBC/ODBC configuration; AI/BI Dashboards as alternative<sup>[5](#sources)</sup> |
| 29 | "How are you handling CDC (Change Data Capture) from source systems today?" | Determines if existing CDC tooling (Qlik Replicate, Fivetran, Debezium) can be reused or if DLT with Auto Loader is better |
| 30 | "Are there any real-time/streaming workloads currently served by the DW, or is it purely batch?" | Identifies whether the migration can unlock new streaming capabilities or must replicate batch patterns |
| 31 | "What data formats are in play? Are you using any proprietary compression or file formats?" | Conversion requirements for Delta format; affects migration tooling selection |
| 32 | "Do you have materialized views, indexed views, or aggregate tables in the current system?" | Maps to Databricks materialized views and streaming tables; important for performance parity<sup>[14](#sources)</sup> |

#### C. Migration Strategy
| # | Question | What It Reveals |
|---|----------|----------------|
| 33 | "Do you want to run both systems in parallel during migration, or are you planning a hard cutover?" | Dual-write complexity, data synchronization needs, validation approach |
| 34 | "What is your validation strategy for ensuring the migrated system produces identical results?" | Data reconciliation approach; row counts, checksums, business logic validation<sup>[5](#sources)</sup> |
| 35 | "Have you budgeted for running dual infrastructure during the migration period?" | Cost reality check -- migrations always take longer than planned |
| 36 | "Is this a lift-and-shift, or are you looking to re-architect during migration?" | Scope and timeline implications. Lift-and-shift is faster but misses Lakehouse optimization opportunities<sup>[3](#sources)</sup> |

---

### 3. Data Mesh / Data Governance / Multi-Region Questions

#### A. Data Governance & Unity Catalog
| # | Question | What It Reveals |
|---|----------|----------------|
| 37 | "How is data ownership defined today? Is there a central data team or are domains self-serve?" | Data mesh readiness; Unity Catalog's model of federated ownership with centralized governance<sup>[10](#sources)</sup> |
| 38 | "How do you handle access control today? Row-level? Column-level? Dynamic masking?" | Maps to Unity Catalog's fine-grained access control, row filters, and column masks |
| 39 | "Do you have a data catalog or metadata management tool today?" | Unity Catalog replacement opportunity or integration requirement |
| 40 | "How do you track data lineage today? Is it manual or automated?" | Unity Catalog provides automated lineage at the column level -- major value differentiator |
| 41 | "What is your PII handling strategy? Do you need tokenization, masking, or encryption?" | Drives Silver layer design patterns; dynamic masking in Unity Catalog vs. ETL-time masking |

#### B. Multi-Region Architecture
| # | Question | What It Reveals |
|---|----------|----------------|
| 42 | "Which regions do you operate in, and where are your data sources and consumers located?" | One Unity Catalog metastore per region; cannot assign workspaces cross-region<sup>[11](#sources)</sup> |
| 43 | "Do you need cross-region data access, or is regional isolation acceptable?" | Delta Sharing for cross-region data distribution; egress cost implications<sup>[11](#sources)</sup> |
| 44 | "What are your data residency requirements per region?" | Whether data can be replicated or must stay in-region; affects whether you use Delta Sharing with managed replicas<sup>[11](#sources)</sup> |
| 45 | "How do you handle disaster recovery across regions today?" | Active-active vs. active-passive patterns; cross-region failover costs<sup>[2](#sources)</sup> |
| 46 | "Do you need a unified global view of data, or are regional views sufficient?" | Determines if you need Lakehouse Federation across metastores or if Delta Sharing suffices<sup>[11](#sources)</sup> |

#### C. Data Mesh Readiness
| # | Question | What It Reveals |
|---|----------|----------------|
| 47 | "How mature are your domain teams in terms of data engineering capability?" | Whether domain teams can own their data products or need a central platform team |
| 48 | "Do different business units have conflicting data definitions for the same concepts (e.g., 'customer', 'revenue')?" | Need for shared semantic layer; Gold layer design implications |
| 49 | "How do teams share data today? File drops, APIs, shared databases, nothing?" | Delta Sharing and data product publishing opportunities |

---

### 4. Consultative Thinking: Frameworks, Techniques & Anti-Patterns

#### A. Discovery Frameworks Adapted for Technical SA Work

**SPIN Selling (adapted for SA discovery)**<sup>[8](#sources)</sup>:
- **Situation**: "Walk me through your current architecture end-to-end"
- **Problem**: "Where are the biggest bottlenecks or failures?"
- **Implication**: "When that pipeline fails at 2am, what is the downstream business impact?"
- **Need-Payoff**: "If you could get that SLA from 4 hours to 15 minutes, what would that unlock for the business?"

**Process Discovery Framework**<sup>[9](#sources)</sup>:
1. Business Objective Articulation -- what outcome are we driving toward?
2. Current Processes and Pain Points -- people, processes, systems involved
3. Desired End State -- must-haves vs. nice-to-haves

**MVP-First Approach** (recommended by Databricks interviewers)<sup>[2](#sources)</sup>:
- Start with a simple system for a single region or dataset
- Explain how it scales globally
- Show iterative refinement rather than a monolithic design

#### B. What Great SA Discovery Looks Like

| Behavior | Why It Matters | Source |
|----------|---------------|--------|
| Ask 8-12 discovery questions before any whiteboarding | Shows discipline and consultative mindset; the prep guide explicitly says "avoid the temptation to start whiteboarding immediately"<sup>[1](#sources)</sup> | Official Prep Guide |
| Peel the onion -- go deep on one topic before moving to the next | Elite SAs discuss one topic at a time rather than jumping across surface-level questions<sup>[7](#sources)</sup> | SparXiq |
| Restate and confirm understanding before designing | Validates assumptions, shows active listening | Presales Collective<sup>[9](#sources)</sup> |
| Proactively surface constraints the customer did not mention | Demonstrates experience -- e.g., "You mentioned GDPR -- have you considered right-to-erasure implications on your Delta tables?" | Databricks Prep Guide<sup>[1](#sources)</sup> |
| Acknowledge trade-offs in your own design | "The weakness of this approach is X, but I chose it because Y" -- the prep guide calls this out as a key evaluation criterion<sup>[1](#sources)</sup> | Official Prep Guide |
| Think out loud continuously | The prep guide calls this "the most important requirement"<sup>[1](#sources)</sup> | Official Prep Guide |

#### C. Common Anti-Patterns (What to Avoid)

| Anti-Pattern | Why It Fails | Source |
|-------------|-------------|--------|
| **Jumping the Gun** -- whiteboarding before gathering context | Official pitfall from the prep guide; shows lack of consultative discipline<sup>[1](#sources)</sup> | Official Prep Guide |
| **Pitching too early** -- describing Databricks features before understanding the problem | "The most common and detrimental mistake Sales Engineers make in Discovery calls is selling too much"<sup>[12](#sources)</sup> | LinkedIn / SE community |
| **Rigid Thinking** -- anchoring on a single pattern without exploring alternatives | Official pitfall; shows inability to adapt to constraints<sup>[1](#sources)</sup> | Official Prep Guide |
| **Ignoring Failure Modes** -- no DR, no error handling, no monitoring | Official pitfall; designs must be "operational and resilient," not just functional<sup>[1](#sources)</sup> | Official Prep Guide |
| **Surface-level questions** -- asking "what cloud are you on?" and moving on | Elite SAs dig deeper: "Why that cloud? Any multi-cloud strategy? Vendor lock-in concerns?"<sup>[7](#sources)</sup> | SparXiq |
| **Checkbox discovery** -- finding the use case and considering discovery done | "You need to continue until you unearth the biggest challenge your customer is facing"<sup>[12](#sources)</sup> | Presales community |
| **Ignoring cost** -- designing without discussing budget or TCO | Interviewers expect "explicit discussion of trade-offs... weighing real-time versus batch-processing costs"<sup>[2](#sources)</sup> | System Design Handbook |

---

### 5. Technical Deep-Dive Questions (DW Performance Features)

These are the questions interviewers will ask **you** during the "Technical Spike" portion. You need to be able to discuss these fluently.

#### A. Liquid Clustering
| Question the Interviewer May Ask | Key Points to Cover |
|----------------------------------|-------------------|
| "When would you recommend Liquid Clustering vs. partitioning + Z-order?" | Databricks recommends LC for all new tables. LC is ideal for write-heavy workloads with evolving access patterns; partition+Z-order may still edge out for very stable, single-column filtering on tables >10TB<sup>[13](#sources)</sup> |
| "How does Liquid Clustering actually work under the hood?" | Uses ZCube IDs tracked in the transaction log; OPTIMIZE only reorganizes unclustered ZCubes (incremental). Up to 4 clustering keys supported. Keys can be changed without rewriting data<sup>[13](#sources)</sup><sup>[15](#sources)</sup> |
| "What is Automatic Liquid Clustering?" | Requires DBR 15.4+. Uses `CLUSTER BY AUTO`. Predictive Optimization analyzes query patterns and automatically selects/evolves clustering keys based on cost-benefit analysis<sup>[15](#sources)</sup> |
| "How do you choose clustering keys?" | Mirror common filter/group-by columns (e.g., date, region, customer_id). Select columns with high statistical variance. Max 4 keys<sup>[15](#sources)</sup> |

#### B. Photon Engine
| Question the Interviewer May Ask | Key Points to Cover |
|----------------------------------|-------------------|
| "When does Photon help and when does it not?" | Photon is a C++ vectorized query engine that accelerates SQL and Spark DataFrame operations. Greatest benefit on scan-heavy, filter-heavy, and join-heavy workloads. Less benefit on UDF-heavy Python workloads that cannot be vectorized |
| "How does Photon interact with Predictive I/O?" | Photon applies AI-assisted selective reading and parallel IO to skip non-matching data blocks without manual indexing<sup>[15](#sources)</sup> |

#### C. Predictive Optimization
| Question the Interviewer May Ask | Key Points to Cover |
|----------------------------------|-------------------|
| "What does Predictive Optimization do?" | Automatically runs OPTIMIZE (file compaction + clustering), VACUUM (dead file cleanup), and ANALYZE (statistics refresh) on Unity Catalog managed tables using serverless compute<sup>[16](#sources)</sup> |
| "How does it decide what to optimize?" | Analyzes table usage patterns, data layout characteristics, and performance metrics. Weighs expected benefit against compute cost. Uses an inheritance model (account > catalog > schema > table)<sup>[16](#sources)</sup> |
| "What are the limitations?" | Only UC managed tables. No external tables or Delta Sharing recipient tables. Does not run Z-order operations. Not available in all regions. Requires Premium plan+<sup>[16](#sources)</sup> |
| "How do you observe what it is doing?" | `system.storage.predictive_optimization_operations_history` system table<sup>[16](#sources)</sup> |

#### D. Materialized Views & Streaming Tables
| Question the Interviewer May Ask | Key Points to Cover |
|----------------------------------|-------------------|
| "When would you use a materialized view vs. a regular view vs. a Gold table?" | MVs precompute and incrementally update results. Best for expensive aggregations queried frequently. Regular views are computed on-read. Gold tables via DLT for complex multi-step transformations<sup>[14](#sources)</sup> |
| "How does incremental refresh work?" | Detects changes in source Delta tables (requires row tracking enabled). Automatically picks best refresh strategy. Supports inner joins, left joins, UNION ALL, and window functions<sup>[14](#sources)</sup> |
| "What compute runs MV refreshes?" | Serverless pipeline compute, not the SQL warehouse compute. Important cost distinction<sup>[14](#sources)</sup> |

#### E. Performance Architecture Decisions
| Question the Interviewer May Ask | Key Points to Cover |
|----------------------------------|-------------------|
| "How would you design a high-concurrency, low-latency DW on Databricks?" | Serverless SQL Warehouses for auto-scaling; MVs for precomputed aggregations; Liquid Clustering on filter columns; Photon enabled; Predictive Optimization for automatic maintenance<sup>[2](#sources)</sup> |
| "Batch vs. Streaming -- how do you decide?" | Business SLA driven. Do not over-optimize for sub-second latency when daily reports suffice. Consider cost of streaming compute. `availableNow=True` for serverless-compatible micro-batch as a middle ground<sup>[2](#sources)</sup> |
| "How would you handle the small file problem?" | Auto Loader coalesces on ingest; OPTIMIZE compacts files; Predictive Optimization automates this; Liquid Clustering reduces fragmentation on write<sup>[16](#sources)</sup> |
| "What is your approach to data modeling in the Lakehouse?" | Medallion architecture (Bronze/Silver/Gold). Gold layer can be star schema for BI workloads or feature tables for ML. Trade-off: normalized for flexibility vs. denormalized for query performance<sup>[1](#sources)</sup><sup>[2](#sources)</sup> |

---

### 6. Sample Interview Flow (Recommended 60-Minute Structure)

Based on the official prep guide<sup>[1](#sources)</sup> and interview experiences<sup>[2](#sources)</sup><sup>[3](#sources)</sup>:

| Phase | Time | Activity |
|-------|------|----------|
| **1. Discovery** | 10-15 min | Ask 8-12 clarifying questions covering business context, current state, constraints, and NFRs. Confirm understanding. |
| **2. High-Level Architecture** | 15-20 min | Whiteboard the end-to-end flow: sources, ingestion, medallion layers, serving layer, governance overlay. Justify each choice. |
| **3. Technical Spike** | 15-20 min | Interviewer drills into 1-3 areas (e.g., "How would you handle CDC for 500 tables?" or "Design the streaming ingestion layer"). Go deep. |
| **4. Trade-offs & Failure Modes** | 5-10 min | Proactively discuss weaknesses, DR strategy, monitoring, cost optimization, what you would change with more time/budget. |

---

## Concerns/Notes
- Glassdoor and Blind content could not be scraped due to JavaScript rendering requirements. Interview experience details from those platforms are based on search result snippets only.
- The Databricks blog posts on migration strategy returned CSS/JavaScript rather than content when fetched, so migration methodology details are synthesized from search result summaries and community sources.
- The official Databricks candidate prep document<sup>[1](#sources)</sup> is the single most authoritative source and should be treated as the ground truth for what interviewers evaluate.
- Technical spike areas (DE, DW, AI/ML) should be communicated to the recruiter in advance per the prep guide. The deep-dive questions in Section 5 focus on DW, but DE and AI/ML spikes would require different preparation.

## Sources
1. Databricks Official Candidate Prep: Design & Architecture Interview - `/Users/slysik/databricks/Design & Architecture Interview_Candidate Prep.pdf`
2. Databricks System Design Interview: The Complete Guide - https://www.systemdesignhandbook.com/guides/databricks-system-design-interview/
3. Databricks Solutions Architect Interview (Glassdoor) - https://www.glassdoor.com/Interview/Databricks-Solutions-Architect-Interview-Questions-EI_IE954734.0,10_KO11,30.htm
4. Databricks Lakebridge Migration Tool & Blog - https://www.databricks.com/blog/introducing-lakebridge-free-open-data-migration-databricks-sql
5. Databricks Migration Checklist (Fission Labs) - https://www.fissionlabs.com/blog-posts/the-ultimate-checklist-for-migrating-to-databricks-lakehouse
6. Teradata to Databricks Migration (Medium) - https://medium.com/towards-data-engineering/datawarehouse-migration-jump-starting-teradata-to-databricks-migration-standardized-tools-2bed2c08a28f
7. Discovery Mistakes to Avoid (SparXiq) - https://sparxiq.com/sales-discovery-mistakes-to-avoid/
8. MEDDIC vs SPIN vs BANT Discovery Frameworks - https://secondnature.ai/meddpicc-spin-or-bant-the-right-sales-technique-for-your-organization/
9. Process Discovery: Foundation for Solution Selling (PreSales Collective) - https://www.presalescollective.com/content/part-1-process-discovery-the-foundation-for-solution-selling
10. Unity Catalog as Foundation for Data Mesh - https://community.databricks.com/t5/technical-blog/unity-catalog-as-a-foundation-for-governance-that-democratizes/ba-p/126983
11. Unity Catalog Multi-Region Best Practices - https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices
12. 3 Biggest Mistakes SEs Make in Discovery Calls - https://www.linkedin.com/pulse/3-biggest-mistakes-sales-engineers-make-discovery-calls-rew-dickinson
13. Liquid Clustering vs. Partitioning vs. Z-Order (CanadianDataGuy) - https://www.canadiandataguy.com/p/optimizing-delta-lake-tables-liquid
14. Materialized Views and Streaming Tables GA Announcement - https://www.databricks.com/blog/announcing-general-availability-materialized-views-and-streaming-tables-databricks-sql
15. Liquid Clustering Documentation (Databricks) - https://docs.databricks.com/aws/en/delta/clustering
16. Predictive Optimization Documentation (Databricks) - https://docs.databricks.com/aws/en/optimizations/predictive-optimization
