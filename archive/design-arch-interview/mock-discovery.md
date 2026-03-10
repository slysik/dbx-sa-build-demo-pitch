# 🎯 Mock Interview — Live Discovery Capture
*SA Interview Copilot · Steve Lysik · Fill this in during the mock session*

---

## How This Works
1. **I (copilot) ask discovery questions** as the customer/interviewer
2. **You answer in the chat** — I capture every answer here automatically
3. **Refresh `live-arch-viewer.html`** in your browser after each section
   to see the architecture diagram update in real-time
4. Run `just live-arch` or `open live-arch-viewer.html` to open the viewer

---

## Customer Context (Revealed Progressively)
| Field | Captured |
|-------|----------|
| Customer Name | ⏳ |
| Industry | ⏳ |
| Headline Pain | ⏳ |
| Current Stack | ⏳ |
| Cloud | ⏳ |
| Data Volume | ⏳ |
| Compliance | ⏳ |
| Consumers | ⏳ |
| Timeline / Urgency | ⏳ |
| Budget Sensitivity | ⏳ |

---

## Discovery Answers Log
*(Auto-populated as interview progresses)*

---
### Exchange 1

**Steve asked:**
> "Aside from the technical stack, what is the main pain point of the current IBM Db2 system
> and what would you ideally want your DW to have going forward?"

**Jamie answered:**
- 45-day regulatory reporting lag — OCC MRA specifically cited inability to produce
  consolidated risk position across 8 business lines within required window
- Consolidation done manually in Excel — no audit trail from source to submission
- BSA/AML: transaction patterns, customer profiles, and watchlist data are siloed
  across 3 separate systems — compliance team doing manual SQL correlation on weekends
- Near-miss on 30-day SAR filing deadline last quarter
- Ideal: compliance team stops being data engineers; risk analyst self-service in seconds

**Architecture signals captured:**
- ✅ Business Problem: OCC MRA + BSA/AML silo + manual Excel consolidation
- ✅ Compliance: OCC, BSA/AML, SAR filing (30-day window), audit trail required
- ⏳ Still need: cloud, volume, stack details, Fabric/EA angle, timeline hard date

---
### Exchange 2

**Steve asked:**
> "What cloud is your preference? Daily data volume?"

**Jamie answered:**
- Cloud: **Azure** — Microsoft EA, Azure-first CIO policy
- **F64 Fabric capacity already included in EA renewal (January)** — CFO asking "why buy Databricks?"
- Db2 warehouse: **120TB** (8 years history)
- Daily ingest: **80–90GB** normal, **~140GB** peak (month-end/quarter-end)
- Transaction count: **3.5M events/day**
- BSA/AML sources identified:
  - NICE Actimize (transaction monitoring — 3rd party)
  - Salesforce Financial Services Cloud (customer profiles)
  - FinCEN 314(a) + OFAC SDN watchlists (manual flat file, loaded daily)

**Architecture signals captured:**
- ✅ Cloud: Azure
- ✅ Volume: 120TB warehouse / 80–90GB daily / 3.5M txn/day
- ✅ BSA/AML sources: Actimize + Salesforce FSC + FinCEN/OFAC
- 🚨 Competitive: Fabric F64 in EA — CFO objection active
- ⏳ Still need: hard deadline date, consumer count, BI tool, data science stack

---
### Exchange 3

**Steve asked:**
> "Full current stack — Db2 version? What feeds it? BI tool?"

**Jamie answered:**
- **Db2:** Warehouse 11.5 on-prem · 3 nodes · 2017 hardware · EoES next year
- **IBM proposing Db2 on Cloud at 3x price** — same problems, different location
- **Ingest (all batch, overnight):**
  - FIS Modern Banking Platform → JDBC nightly bulk extract (4hr run)
  - Visa/MC settlement CSV files → Python script (fails ~2x/month)
  - FedACH flat files + Fedwire ISO 20022 messages (daily morning)
  - NICE Actimize → DataStage SQL export via shared drive
  - Salesforce FSC → **weekly CSV export** (customer profiles up to 7 days stale!)
  - FinCEN/OFAC → manual flat file load
- **ETL:** IBM DataStage (one key-person dependency — 14yr employee); legacy SSIS; Python scripts no one owns
- **BI:** Tableau — 240 dashboards hitting Db2 directly; 30 legacy Cognos reports
- 🚨 **TIMELINE BOMB:** OCC 6-month window — 2 months in — **4 months left**
  - Need production evidence of material progress in 4 months, NOT 18-month migration

**Architecture signals:**
- ✅ Stack fully mapped
- ✅ Hard deadline: 4 months to demonstrate progress to OCC
- 🚨 Key risk: DataStage key-person dependency
- 🚨 Key risk: Salesforce weekly export = 7-day stale customer data for BSA/AML
- 🚨 Python script failing 2x/month on card settlement = data quality gap

---
### Exchange 4 — ⚠️ DUPLICATE QUESTION

**Steve asked:**
> "Full current stack — Db2 version? What feeds it? BI tool?" ← ALREADY ASKED IN EXCHANGE 3

**Jamie response:** Called it out. Redirected to remaining open questions:
- Consumer / compliance team headcount
- Data science team size + stack
- Fabric F64 CFO scope expectation

**🚨 DEBRIEF FLAG:** Repeated question signals poor active listening.
In a real SA interview this is a credibility ding. Customer notices.
Root cause likely: asking one question at a time instead of a prepared
3-4 question volley — running out of prepared questions.

---
### Exchange 5

**Steve asked:**
> "please provide the team size, data science stack, and the Fabric CFO scope?"

**🚨 DEBRIEF FLAG #2:** Phrasing "please provide" = service desk ticket language.
Good discovery sounds like human curiosity, not a form.
Better: "Walk me through your team structure — compliance, analytics, DS?
And on Fabric — what specifically is your CFO expecting it to replace?"
Content was right. Delivery was stilted.

**Jamie answered:**
- Compliance: 12 total — 4 BSA/AML analysts · 3 reg reporting · 2 audit · 3 compliance ops
- Analytics: ~180 Tableau users across 8 LOBs · ~20 can write SQL
- Data engineering: 8 people · 7 know Db2/SQL · 1 DataStage expert (key-person risk)
- Data science: 5 people · Python/pandas/scikit-learn · Azure ML Compute · no MLflow · no registry
  - One fragile rule-based SAR scoring model on top of Actimize
  - Can't build proper ML model — can't get clean joined data across 3 systems
- Fabric / CFO:
  - Microsoft account team told CFO: "Fabric replaces Db2 + Tableau, it's already in your EA"
  - CFO's mental model: Fabric = free solution, Db2 gone, Tableau gone
  - Nobody on the team has hands-on Fabric experience
  - Data engineers are Db2/SQL · Data scientists are Python — NOT T-SQL proc writers
  - 🎯 CFO conversation needs a partner to help navigate it

**Architecture signals:**
- ✅ ALL discovery complete
- 🎯 Whiteboard moment: Jamie just asked "What's your architecture?"

---
### Exchange 6 — Whiteboard Answer

**Steve proposed:**
> "6 data sources fed into python scripts governed by Unity Catalog, replacing DataStage
> + IBM Quality Stage. Medallion layer: Silver DQ+PII, Gold star schema with Liquid
> Clustering + MVs. Consumption: self-service analytics, dashboards, MLflow for DS,
> Delta Sharing for audit compliance."

**What landed ✅:**
- Medallion architecture correctly named
- Unity Catalog for governance ✅
- Silver DQ + PII masking ✅
- Gold star schema + Liquid Clustering + MVs ✅
- MLflow for DS team ✅
- Delta Sharing for audit/compliance ✅
- DataStage displacement angle ✅

**What was missing / weak 🚨:**
1. Said "Python scripts" for ingestion — Python scripts ARE the problem. Should be:
   LakeFlow Connect (FIS/Actimize CDC) + Auto Loader (FinCEN/OFAC) +
   Structured Streaming (Visa/MC card files)
2. NO phasing — Jamie has 4-month OCC deadline. Complete arch ≠ 4-month MVP answer.
   Should have led with: "Here's what's live in 4 months: [BSA/AML layer + audit trail]"
3. NO Fabric answer — Most dangerous omission. CFO will kill the deal in procurement
   if this isn't addressed. Steve is a former GBB — this was his strongest card.
4. No BSA/AML specific answer — Generic medallion, didn't call out the specific
   SAR correlation problem or how unified Silver layer solves it.
5. No Lakehouse Federation mention — 120TB Db2 doesn't migrate in 4 months.
   Federation-first is the right MVP approach.

**Jamie's pushback — 3 challenges:**
1. "Python scripts" — what specifically replaces them?
2. What does the OCC examiner see in month 4?
3. You never mentioned Fabric — what do I tell my CFO?

---
### Exchange 7 — Recovery Attempt

**Steve answered:**
> "LakeFlow connectors with structured streaming (delta live tables) feeding autoloader
> for high speed load into bronze. Fabric leveraged for Power BI reporting off managed
> gold delta tables."

**What landed ✅:**
- Corrected ingestion: LakeFlow + Structured Streaming + Auto Loader ✅
- Fabric addressed: Power BI on Gold delta tables = EA utilization bridge ✅

**What was still missing 🚨:**
1. ❌ 4-month OCC MVP — STILL not answered. Most critical question. Skipped twice.
2. ⚠️ Said "delta live tables" — old product name. Current: Spark Declarative Pipelines
   (also called Lakeflow Pipelines). Naming matters in a technical eval.
3. ⚠️ Fabric answer was passive ("can be leveraged") vs. confident GBB positioning.
   Should have said: "I spent 5 years as a Microsoft GBB selling Fabric — let me
   give you the honest version your CFO needs to hear."
4. ❌ Never addressed: DS team is Python (not T-SQL) — why Fabric Warehouse
   doesn't solve the SAR ML problem even if CFO wants it.
5. ❌ Never mentioned Lakehouse Federation — 120TB Db2 doesn't migrate in 4 months.

**Jamie's final challenge:**
"What is live and in production at Meridian Bank in four months?
What does the OCC examiner actually see?"

---
### Exchange 8 — MVP Answer (STRONG RECOVERY)

**Steve delivered:**
1. Lakehouse Federation on top of Db2 — zero migration risk, zero disruption ✅
2. LakeFlow Connect CDC: FIS + Actimize + Salesforce ✅
3. Bronze landing zone for 6 sources ✅
4. Silver unified BSA/AML entity layer ✅
5. Unity Catalog lineage: source → Bronze → Silver → OCC report ✅
6. SAR candidate dashboard: <10s, no weekend SQL ✅

**Jamie's verdict:** "That's the answer I needed thirty minutes ago."
"We should set up a deeper technical session."

**Session outcome: DEAL ADVANCED ✅**

