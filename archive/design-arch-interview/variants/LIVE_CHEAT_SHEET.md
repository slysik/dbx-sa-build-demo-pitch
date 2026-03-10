# Live Interview Cheat Sheet

## BEFORE THE INTERVIEW
1. Open the closest variant in excalidraw.com (File → Open)
2. Update the title with the scenario name
3. Keep this cheat sheet visible on a second monitor or half-screen

---

## PICK YOUR VARIANT

| If the scenario sounds like... | Open this file |
|---|---|
| Retail bank, deposits, loans, branches | `retail_banking.excalidraw` |
| Trading, securities, portfolio, hedge fund | `capital_markets.excalidraw` |
| P&C or Life insurance, claims, policies | `insurance.excalidraw` |
| Payment processor, card issuer, ACH/wires | `payments.excalidraw` |

---

## DISCOVERY FLOW (First 15-20 min)

Ask in this order — each question maps to diagram columns:

| # | Ask This | Maps To | Listen For |
|---|---|---|---|
| 1 | "What does success look like? Top 2-3 reports that can't miss SLA?" | Domain Products, Gold | Use cases, KPIs, regulatory pressure |
| 2 | "What are the refresh targets for each?" | Ingestion, Compute | EOD vs intraday vs streaming |
| 3 | "Which 2-3 metrics does the CFO/CRO actually look at?" | Gold | Metric names, source of truth, ownership |
| 4 | "If we had 90 days, which subject area first?" | Gold, Domain Products | Thin slice scope |
| 5 | "Walk me through your top 5 source systems" | Sources | System names, vendors, cadence |
| 6 | "What batch tools and load windows today?" | Ingestion (card 1) | Informatica, ADF, mainframe windows |
| 7 | "Any sources needing near-RT or CDC?" | Ingestion (cards 2-3) | Latency, replay, Kafka/Debezium |
| 8 | "How do you validate data? Recon controls?" | Silver | DQ, GL tie-outs, quarantine |
| 9 | "Who consumes this? What BI tools?" | Serve, Compute | Power BI, Tableau, personas |
| 10 | "Regulatory guardrails? PII masking? Audit?" | Guardrails | SOX, GDPR, PCI, RBAC |

---

## QUICK EDITS DURING WHITEBOARDING

When you pivot to the diagram (~20 min mark), these are the ONLY cards worth editing live:

### Must-edit (takes 30 seconds each):
- **Title**: Scenario name + date
- **Sources cards**: Rename to the actual systems they mentioned
- **Gold card 1**: Rename facts/dims to their domain (e.g., Fact_Claim vs Fact_Trade)
- **Domain Products**: Rename to their actual business units

### Edit if time (nice-to-have):
- **Ingestion cards**: Swap tools if they mentioned specific ones
- **Serve card 2**: Swap BI tool name

### DON'T bother editing live:
- Bronze, Silver (patterns are universal)
- Compute (always Workflows + SDP + DBSQL)
- Platform Guardrails (always the same 6)

---

## TALKING POINTS PER COLUMN (What to say as you walk through)

### Sources (30 sec)
"Here are the systems you mentioned. I've categorized them by batch vs streaming ingestion pattern."

### Ingestion (1 min)
"For [batch sources], we use Autoloader with schema evolution — it handles late files, retries, exactly-once. For [streaming sources], Kafka into structured streaming with checkpoint recovery. Key point: we land everything into Bronze with full replay capability."

### Bronze (30 sec)
"Bronze is our immutable audit layer. Append-only Delta tables, partitioned by ingestion date. PII/PCI gets tagged here via Unity Catalog — we don't mask yet, just classify, so we preserve the raw signal for reprocessing."

### Silver (1.5 min)
"Silver is where we do the heavy lifting. Deduplication using your golden keys — [customer ID / trade ID / policy ID]. Data quality gates quarantine bad records rather than silently dropping them. And critically for FinServ — reconciliation controls. Your GL tie-outs, balance checks — they run as DQ expectations with alerting if they break."

### Gold – DW SPIKE (2-3 min) ⭐
"This is the data warehousing layer and where I want to go deeper. Star schema design — [Fact_Transaction / Fact_Trade / Fact_Claim] as the grain, with conformed dimensions from Silver. Key design decisions:
- **Why star over vault**: For your BI-heavy consumption pattern, star schema gives you the fastest query performance on DBSQL. Kimball facts scan efficiently with liquid clustering.
- **Materialized views vs tables**: For your regulatory extracts, I'd use materialized views — they auto-refresh incrementally and DBSQL optimizes them. For ad-hoc aggregates, standard Gold tables.
- **Metrics layer**: Single definition of [their KPIs] — owned by the business, enforced in the platform.
- **DBSQL performance**: Liquid clustering on your high-cardinality columns, predictive I/O, and result caching for repeat dashboard queries."

### Compute (30 sec)
"Databricks Workflows orchestrates the DAG — Bronze to Silver to Gold with SLA monitoring. Lakeflow SDP pipelines handle the streaming tables. DBSQL Pro warehouses serve the Gold layer — auto-scaling, so you're not paying for peak capacity 24/7."

### Serve (1 min)
"[Power BI / Tableau] connects directly to DBSQL via the native connector. Analysts get the drill path — start at the KPI, drill to transaction, drill to raw source for audit evidence. For external sharing — Delta Sharing to regulators or downstream systems, no data copying."

### Domain Products (30 sec)
"Each of these becomes a data product in Unity Catalog — discoverable, governed, with lineage. [Risk / Finance / Customer / Payments] — each has an owner, SLAs, and quality contracts."

### Platform Guardrails (1 min)
"Underpinning everything: Unity Catalog for RBAC and column masking — your PII stays protected. Full lineage and audit trail for your examiners. CI/CD with dev/test/prod isolation. And cost controls with chargeback per business unit."

---

## DATA WAREHOUSING SPIKE — DEEP DIVE PREP

If they push deeper on your DW spike, be ready for:

### Dimensional Modeling
- Star schema: Fact tables at transaction grain, conformed dimensions
- Why not Data Vault: overkill for their consumption pattern, adds latency
- SCD Type 2: handled in Silver via SDP `APPLY CHANGES`, surfaced in Gold dims
- Late-arriving facts: Bronze replay + Silver reprocessing handles this

### DBSQL Performance
- Liquid clustering > Z-ORDER (adaptive, no manual tuning)
- Predictive I/O: skips irrelevant data files
- Result caching: automatic for repeat BI queries
- Photon engine: vectorized execution for analytical queries

### Materialized Views vs Tables
- MVs: auto-incremental refresh, great for regulatory extracts + dashboards
- Tables: full control, better for complex multi-hop transforms
- Trade-off: MVs save compute but have refresh latency

### Cost Optimization
- DBSQL Serverless: auto-scale to zero, pay per query
- Warehouse T-shirt sizing: Small for dev, Medium for analysts, Large for batch refresh
- Query routing: tag queries by team for chargeback

### Semantic / Metrics Layer
- Databricks Metrics Layer or dbt metrics
- Business owns definition, platform enforces calculation
- Prevents "which number is right" arguments
