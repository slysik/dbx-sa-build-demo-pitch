# Demo Narrative — 60-Minute SA Interview

## The Core Story (Memorize This)

> "You're a bank losing **$12M/year** to fraud your batch system catches 24 hours too late.
> In the next 60 minutes, I'm going to show you exactly how we'd fix that — live, on real infrastructure."

**Adapt the numbers to the prompt.** If the prompt is credit risk → swap fraud for delinquency rate.
If it's regulatory reporting → swap fraud for T+5 → T+1 report delivery.

---

## How to Open (Critical — Say This First 60 Seconds)

> "Before I show the solution, I want to be transparent about how I built it —
> because the *way* I built it is part of what I'm demoing.
>
> I used **PI coding agent** to scaffold the project: notebooks, SQL transforms, bundle config, README.
> Then I iterated with AI assistance to refine the risk scoring logic, tune the schema, and build
> the presentation layer. The whole end-to-end solution — Bronze ingestion, Silver transforms,
> Gold aggregations, this dashboard, and the Genie Space — was built in under 4 hours.
>
> That's not a party trick. That's what your data team looks like when Databricks AI tooling
> is part of their workflow. Let me walk you through it."

**Why this works:** The recruiter explicitly told candidates the winning workflow is PI → iterate → deploy.
You're the candidate who actually did it. Open by naming it.

---

## Panel Personas & How to Play Them

| Persona | What They Care About | How to Win Them |
|---|---|---|
| **Business Leader / VP** | ROI, risk reduction, time-to-value | Lead with dollar impact. "This moves fraud detection from T+24h to near-real-time. At your transaction volume that's ~$12M in recoverable losses annually." |
| **Head of Data / CDO** | Architecture, governance, team burden | Show Unity Catalog lineage. "One platform — ingestion, transformation, governance, BI, and ML. No stitching together 5 tools." |
| **Data Engineer / Architect** | Scalability, code quality, operability | Show `spark.range()`, explain broadcast joins, walk through the SDP declarative SQL. "Same code runs at 100 rows or 10M — I just change one parameter." |
| **CISO / Risk** | Security, compliance, audit trail | Show column masks, row filters, Delta history. "Every access is logged. GDPR data residency is enforced by catalog policy, not application code." |

---

## Clock Management (60 min)

```
00:00 – 02:00  HOW I BUILT IT      → "I used PI coding agent to scaffold this in 4 hours — 
                                       that workflow IS the demo" (recruiter signal: say this)
02:00 – 06:00  Business context    → State the problem, quantify the pain ($12M fraud gap)
06:00 – 10:00  Architecture walk   → Git folder → Mermaid diagram → 3-layer medallion
10:00 – 20:00  Live walkthrough    → Bronze notebook (talk through code) → SDP pipeline → Gold
20:00 – 32:00  Dashboard           → KPIs hook Business Leader → channel/segment charts for CDO
32:00 – 42:00  Genie Space         → Live NL demo ("ask it anything") → biggest CDO wow moment
42:00 – 50:00  Unity Catalog depth → Lineage, column masks, row filters for VP Engineering
50:00 – 57:00  Interruption buffer → Handle questions (stay in SA mode, not engineer mode)
57:00 – 60:00  Next steps          → "90-day PoV plan — here's what week 1 looks like"
```

**The Genie demo is your CDO moment.** Have a question ready that the CDO will want to ask.
Suggest: *"What if you could let your analysts ask that question themselves, right now?"* → type it live.

**Critical:** Start the Bronze notebook AND the SDP pipeline in the first 5 minutes.
By the time you finish the architecture walk, the data is already flowing.

---

## Opening (Business Leader hook — first 90 seconds)

> "Before I show you any code, let me make sure I understand what you're trying to solve.
> You're processing [X] transactions per day. Your current fraud detection runs in batch —
> by the time you catch a fraudulent pattern, the money is already gone.
> What I'm going to build today is the data foundation that changes that.
> It ingests raw transactions, scores every one of them in near-real-time,
> and surfaces the highest-risk ones to your analysts instantly.
> Let me show you — and I'll explain every decision as we go."

---

## Architecture Walk Talking Points (5 min)

Point to each layer as you speak:

1. **Bronze** — "Raw data lands here, exactly as it came from the source. No transformation, no business logic. This is our audit trail — regulators can always see original data."

2. **Silver** — "Here we apply business logic in SQL — enrich with customer and merchant data, score every transaction deterministically. Same score every time, fully auditable."

3. **Gold** — "Consumption-ready aggregations. Pre-computed daily metrics, segment breakdowns, merchant exposure. Dashboard queries hit this layer — sub-second response at any scale."

4. **Compute** — "No clusters to manage. Everything runs on Databricks Serverless — it provisions in seconds and scales automatically. You pay for compute you use, not compute you provision."

5. **Governance** — "Unity Catalog sits across all layers. Data lineage is automatic — from the raw CSV all the way to the dashboard widget. Column masks, row filters, fine-grained access — all enforced at the catalog level."

---

## Bronze Narration (while notebook runs)

> "I'm using `spark.range()` to generate 100,000 transactions distributed across the cluster.
> No Python loops, no Pandas — this scales from 100 rows to 10 million by changing one number.
> [point to broadcast join] The customer and merchant dimensions are tiny — 500 and 200 rows —
> so I'm broadcasting them to every executor. Zero shuffle, zero skew."

> "Direct to Delta Bronze — no intermediate files. Bronze is append-only, source-shaped.
> Three metadata columns: ingest timestamp, source system, batch ID.
> These are what your compliance team needs for audit trails."

---

## SDP Pipeline Narration (while pipeline runs)

> "The SDP pipeline is declarative SQL — I define *what* I want, Databricks figures out *how*.
> Silver joins all three Bronze tables and applies a deterministic risk score.
> [point to CASE statement] Not ML yet — pure business rules. Auditable, explainable,
> compliant with model risk management requirements. We'd layer ML on top of this."

> "Gold is three materialized views — daily metrics, customer segment breakdown, merchant exposure.
> The dashboard hits Gold. Pre-aggregated, 5-second refresh, sub-second query response."

---

## Dashboard Talking Points

> "This is what your risk team sees in real time. [point to fraud rate KPI]
> 3.2% high-risk transaction rate — that's normal. [point to spike]
> But this spike on the 15th? That's a pattern your current system would catch tomorrow.
> Databricks catches it now."

> "And for your business leader — [point to amount at risk]
> $340,000 in high-risk transaction volume in the last 7 days.
> That's the number that moves the conversation from IT project to business priority."

---

## Genie Demo (NL → SQL live)

Ask live during the demo — pick one of these based on the prompt scenario:

- "How much did high-risk Online transactions increase week-over-week?"
- "Which customer segment has the highest fraud rate?"
- "Show me the top 5 merchants by amount of high-risk transactions this quarter"
- "What percentage of Wealth segment customers triggered a high risk score?"

> "This is Genie — natural language to SQL, built directly on our Gold tables.
> No BI tool configuration, no cube definitions. Your analysts ask questions in plain English
> and get answers from the same governed data your engineers built."

---

## Governance Talking Points (for CTO / CISO)

> "Unity Catalog gives you one control plane across all your data assets.
> Column masks: your analysts see `CUST-XXXXX` where the real ID is.
> Row filters: EU customers' data never leaves the EU region — enforced at the catalog, not the app.
> Delta history: I can show you exactly who accessed what, when, and what the data looked like
> at any point in time. GDPR right-to-erasure? `VACUUM` + `REPLACE WHERE` — fully supported."

---

## Closing (earn the next step)

> "What you've just seen is a working prototype — built in [X] hours on real Databricks infrastructure.
> This isn't a slide deck. You can query this data right now."
>
> "The path from here: in 30 days we'd connect your actual core banking feed via Auto Loader.
> In 60 days we'd replace the rule-based risk scoring with an ML model trained on your history.
> In 90 days your compliance team has the regulatory reporting dashboard they've been asking for."
>
> "The question I'd ask you is: what's the cost of waiting another 90 days with the system you have today?"

---

## Objection Handling

| Objection | Response |
|---|---|
| "We're already using Snowflake" | "Snowflake is excellent for SQL analytics. Where it gets expensive is when you add ML, streaming, and governance as separate tools. Databricks unifies all of that — one platform, one cost center, one governance model." |
| "This is too complex for our team" | "The Silver and Gold layers are pure SQL. Your team already knows this. The PySpark Bronze notebook is 50 lines and I'd walk your team through it in an afternoon." |
| "How does this handle PCI-DSS?" | "Delta Lake's immutable history + Unity Catalog audit logs = complete access trail. Column masks for card numbers, row filters for data residency, automated VACUUM for data retention policies." |
| "What about our existing Teradata investment?" | "Lakebridge — free Databricks tooling — auto-converts 80% of your Teradata SQL. We run both in parallel with Lakehouse Federation. Zero-risk migration." |
| "The timeline is too aggressive" | "We're not asking you to migrate. We're asking you to run a 90-day POV in parallel with your existing system. When it proves value, you migrate on your timeline." |

---

## 4-Hour Build Window — Day-Of Checklist

When you receive the scenario prompt:

1. **Read the prompt → identify the exact pain point** (fraud / credit risk / regulatory / customer 360)
2. **Adapt the story** — swap numbers and framing in `demo_narrative.md`
3. **Adapt the schema name** — rename `finance` to match the scenario if needed
4. **Check the Bronze notebook** — are the column names right for the scenario? (usually yes)
5. **Run the pipeline** — `just upload-project finance_lakehouse` → trigger Bronze → trigger SDP
6. **Build the dashboard** — query Gold tables, build 4-5 widgets, deploy via `dbx_deploy_dashboard`
7. **Test Genie** — prepare 3 NL questions relevant to the scenario
8. **`just open`** → confirm everything is live

**Total time: 90 minutes if scaffold is already built (which it is).**
Remaining 2.5 hours: rehearse the narrative, prepare for panel questions.
