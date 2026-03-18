# ⚠️ Persona 2: Risk Analyst / Risk Operations
## Demo Flow — "Your Entire Risk Portfolio in One View"

**Customer Role:** Risk Analyst, Fraud Operations Manager, Compliance Officer
**Their Problem:** "We get daily risk reports 24 hours late, in Excel, and we can't drill into segments without filing a data request."
**Your Goal:** Show that Databricks delivers real-time risk intelligence — filterable, drillable, shareable — without a BI team bottleneck.

---

## Opening Statement (30 seconds)

> *"I'm going to show you your portfolio risk exactly the way your risk ops team would see it every morning — live data, full drill-down, no data requests. Let me start with the executive overview and then we'll go deeper."*

---

## Step 1: Executive Overview Page (3 minutes)

**Navigate to:** Dashboard → **🏦 Executive Overview** tab

### KPI Row 1 — The "Good News" Row
Point to the three top KPIs:
- **📊 960 Total Transactions** (for the period shown)
- **💰 $167M Transaction Volume**
- **⚠️ 5.11% Portfolio Risk Rate**

> *"Five-and-a-half percent risk rate. That's your portfolio health number. Now let me show you what that means in absolute terms..."*

### KPI Row 2 — The "Action" Row
- **🚨 5,108 Flagged for Review** — *"These are the transactions your team needs to triage."*
- **✅ 85,772 Approved** — *"85% straight-through processing — your operations are healthy."*
- **🎯 45.3 Avg Risk Score** — *"Below 50 average — the bulk of your portfolio is clean."*

> *"This is the morning briefing view. Risk rate trending up? Your team sees it here before anyone calls them."*

### Dual-Line Chart — Daily Volume vs High-Risk
**Point to the chart:**
> *"This is the story I want you to see. The blue line is total transaction volume — steady, seasonal, predictable. The orange line is high-risk activity. Notice how they move independently? That's your risk signal. When they diverge — volume stable but risk spiking — that's an anomaly worth investigating."*

**Interact:** Use the date range filter. Select last 30 days.
> *"Same view, scoped to last month. Your risk team would start their day here."*

### Status Pie + Category Bar — "Where is money going?"
**Left pie:**
> *"85.8% Approved, 7.5% Pending, 4.8% Declined, 1.9% Flagged. The Flagged slice — that's your fraud queue."*

**Right bar:**
> *"Food & Dining dominates at $59M, Retail at $51M. Travel at $38M has a slightly higher risk rate — we'll explore that on the next page."*

---

## Step 2: Risk Intelligence Page (4 minutes)

**Click:** **⚠️ Risk Intelligence** tab

### Grouped Bar — Segment × Risk Tier
> *"This is the view your risk committee wants in every quarterly review. Retail customers drive the bulk of high-risk transactions in absolute numbers — that's expected, they're your largest segment. But look at Private Banking — the High risk tier there has a disproportionately high risk rate. That's where your investigation starts."*

**Use the Customer Segment filter:**
Select "Corporate" only.
> *"Corporate clients, filtered. Corporate High risk tier — 48 flagged transactions out of 1,000. That's 4.8%. Compare that to Corporate Low — 5.4%. Slightly counterintuitive — you'd investigate whether the Low tier classification is accurate."*

### Category Risk Rate Bar
> *"Healthcare has the highest risk rate at 5.34%. Travel at 5.06%. Retail and Food are close behind. The 'Other' category is anomalously clean — worth checking if that's a categorization artifact or genuine."*

### Region Pie — Geographic Risk Distribution
> *"Risk is essentially uniform across regions — West and Midwest slightly elevated at 5.22%. If you had a concentrated fraud event in one region, this pie would show it immediately."*

### Monthly Volume Trend by Category
> *"Full year view. Retail and Food & Dining are your dominant categories month-over-month. No seasonal spike in Fuel despite what you might expect — that's a data quality signal worth exploring in production."*

### Detail Table — Full Drill-Down
**Scroll to table:**
> *"This is the source-of-truth drill-down. Every segment, every risk metric, sortable. Retail has $60M volume, 1,873 high-risk transactions, 5.17% risk rate. This table replaces your weekly Excel report — and it updates with every pipeline run."*

---

## Step 3: Ask "What's Your Question?" (2 minutes — Genie transition)

> *"You've been asking questions with filters. What if your analyst could just type the question in English?"*

**Pivot to:** If Genie Space is available, demonstrate.
Otherwise, stay in dashboard and show the filter interplay:

**Apply filters:** Merchant Category = Travel + Risk Tier = High
> *"Travel transactions for High-risk customers only. How much volume is at risk? What's the avg risk score? You just built a risk report in 10 seconds."*

---

## Close (30 seconds)

> *"Everything you just saw — the KPIs, the drill-downs, the filters — this is running live against your Gold layer in Unity Catalog. When your pipeline refreshes, the dashboard updates. No Excel. No data requests. No 24-hour lag. Your risk team gets their morning briefing automatically."*

---

## Objection Handling

| Objection | Response |
|-----------|----------|
| "We already have Tableau/Power BI" | "Keep them. Connect to the same Gold MVs via JDBC/ODBC. Databricks is the data platform — BI tool is your choice." |
| "How fresh is this data?" | "Depends on pipeline schedule. With streaming tables, you can get to sub-minute latency." |
| "Can analysts build their own reports?" | "Yes — AI/BI lets analysts build dashboards without SQL. And Genie answers NL questions against the same Gold tables." |
| "Who controls what data analysts see?" | "Unity Catalog. Column-level masking, row-level security, full audit trail. All enforced at the platform layer." |
