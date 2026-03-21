# 🚀 Learning Path — Databricks Skills Update (Q1 2026)

## Your Gap Analysis Summary

**Total gaps detected:** 21 across 14 skills  
**High-severity gaps:** 6 (requires urgent documentation)  
**Most critical skill:** `databricks-bundles` (4 HIGH gaps)  
**Most critical domain:** Serverless compute configuration (appearing in 3 gaps)

---

## Priority Tiers (What to Learn First)

### 🔴 TIER 1: CRITICAL (This Week — 3 hours)
These gaps block real user workflows and show up repeatedly.

| # | Skill | Gap | Score | Why Now | Learning Time |
|---|-------|-----|-------|---------|----------------|
| 1 | bundles | Serverless notebooks (queue: enabled) | 90/100 | Users always ask "how do I configure a serverless job?" | 20 min |
| 2 | bundles | Workspace admin ≠ UC CREATE_SCHEMA | 90/100 | Permission errors are #1 support issue | 15 min |
| 3 | bundles | Serverless notebook tasks (no cluster) | 90/100 | Same as #1, different context | 15 min |
| 4 | spark-declarative-pipelines | Lakeflow CDC with DELETE tracking | 70/100 | New SDP feature, high-value pattern | 30 min |
| 5 | model-serving | ChatAgent/ResponsesAgent | 70/100 | Hot new feature, customers asking about it | 25 min |

**Total time: ~2 hours learning + practice**

### 🟡 TIER 2: IMPORTANT (This Month — 5 hours)
High-value additions that improve demo flexibility.

| # | Skill | Gap | Score | Why Next | Learning Time |
|---|-------|-----|-------|----------|----------------|
| 6 | bundles | Bundle variables with lookup | 60/100 | Simplifies multi-environment setup | 25 min |
| 7 | databricks-ai-functions | ai_extract_table() | 60/100 | Document parsing is popular use case | 30 min |
| 8 | databricks-aibi-dashboards | dataset_catalog/schema params | 60/100 | Makes dashboards more portable | 20 min |
| 9 | databricks-iceberg | Iceberg v3 + Uniform | 60/100 | Emerging pattern, differentiator | 40 min |
| 10 | databricks-python-sdk | Databricks Connect v2 | 60/100 | IDE-based development (emerging) | 30 min |
| 11 | databricks-spark-structured-streaming | Real-Time Mode (RTM) | 60/100 | Next-gen streaming, worth knowing | 35 min |
| 12 | databricks-vector-search | Direct index type | 60/100 | Alternative to Delta Sync | 25 min |

**Total time: ~3.5 hours learning + practice**

### 🟢 TIER 3: NICE-TO-HAVE (Q2 — 4 hours)
Fills knowledge gaps, enables edge-case discussions.

| # | Skill | Gap | Score | Why Later | Learning Time |
|---|-------|-----|-------|-----------|----------------|
| 13 | mlflow-evaluation | MLflow 3 GenAI eval + GEPA | 70/100 | Emerging, needed for advanced eval scenarios | 45 min |
| 14 | bundles | Apps resource (Dash/Streamlit) | 30/100 | Nice for demo diversification | 30 min |
| 15 | databricks-genie | Genie Spaces sampling | 30/100 | Edge case, low-frequency ask | 15 min |
| 16 | databricks-metric-views | Metric Views (YAML) | 30/100 | Governance feature, not always relevant | 25 min |
| 17 | databricks-unity-catalog | Row/column masking | 30/100 | Security feature, enterprise-specific | 30 min |

**Total time: ~2.5 hours learning + practice**

---

## How to Learn Each Gap (Method)

### Method A: Quick POC (15–30 min per gap)
**Best for:** Understanding syntax, seeing it work live

1. Read docs (5 min)
2. Create temp notebook on serverless workspace
3. Copy-paste example code from docs
4. Modify for finserv_lakehouse context
5. Execute and verify it works
6. Write 2–3 gotchas down in a temp file
7. Update SKILL.md with gotchas + example

### Method B: Deep Dive (30–60 min per gap)
**Best for:** Features that affect architecture/design

1. Read official docs + blog posts (10 min)
2. Build realistic POC from scratch (15 min)
3. Test edge cases / error conditions (10 min)
4. Compare with old pattern (why is new one better?) (5 min)
5. Document pattern + gotchas + comparison (10 min)
6. Create demo snippet in finserv_lakehouse (10 min)

### Method C: Reading Only (5–10 min per gap)
**Best for:** Low-priority, nice-to-know features

1. Skim official docs
2. Note 1-2 key gotchas
3. Add 1 paragraph to SKILL.md
4. Move on

---

## Tier 1 Detailed Learning Plan (This Week)

### Gap 1: Serverless Notebooks in Jobs (queue: enabled)

**What you need to know:**
```yaml
# OLD (cluster-based)
tasks:
  - task_key: my_task
    notebook_task:
      notebook_path: /path/to/notebook
    existing_cluster_id: cluster-abc123    # ← NO

# NEW (serverless)
tasks:
  - task_key: my_task
    notebook_task:
      notebook_path: /path/to/notebook
      source: WORKSPACE                     # ← required
    queue:
      enabled: true                         # ← serverless compute
```

**Gotchas to document:**
- `source: WORKSPACE` is required (tells job where notebook lives)
- `queue: enabled` means serverless (no cluster needed)
- Don't use `existing_cluster_id` with serverless
- Don't use `new_cluster` with serverless
- Faster startup, perfect for orchestration

**POC Task (20 min):**
1. Open finserv_lakehouse/databricks.yml
2. Find job definition with notebook task
3. Add `source: WORKSPACE` to notebook_task
4. Add `queue: { enabled: true }` below notebook_task
5. Run: `databricks bundle deploy`
6. Check: Job runs on serverless ✅

**Add to SKILL.md:**
Location: `### Jobs Resources` section, update example to show serverless pattern

---

### Gap 2: Workspace Admin ≠ UC CREATE_SCHEMA

**What you need to know:**
- Workspace admin = admin inside the workspace (UI, jobs, notebooks)
- UC admin = permissions on catalogs/schemas (data governance)
- These are **different permissions**
- Workspace admin does NOT automatically get UC permissions

**Why it matters:**
When you add SP to workspace admins and it can't create schema:
```
ERROR: PERMISSION_DENIED on CREATE_SCHEMA
```
The fix: Someone with UC catalog ownership must explicitly grant:
```sql
GRANT ALL PRIVILEGES ON CATALOG finserv TO `your-sp-client-id`
```

**Gotchas:**
- Grant command must come from **catalog owner** (original creator)
- Use `client_id` not SP display name
- Must happen BEFORE bundle deploy
- Applies to every new service principal

**POC Task (15 min):**
1. Read: https://docs.databricks.com/en/admin/workspace-administration/manage-users.html (2 min)
2. Read: https://docs.databricks.com/en/data-governance/access-control/workspace-acl.html (3 min)
3. Note down: "Workspace admin ≠ UC access, need explicit grant" (10 min)

**Add to SKILL.md:**
New section: `## UC Permissions for Service Principals`
Include: Step-by-step grant commands + when to run them

---

### Gap 3: Serverless Notebook Tasks (Queue vs Cluster Config)

**This is similar to Gap 1, but in Jobs context. Combined.**

**Add to SKILL.md:**
Update Jobs section with complete example showing:
- No `existing_cluster_id`
- No `new_cluster`
- Serverless notebook task config with source + queue

---

### Gap 4: Lakeflow CDC with DELETE Tracking

**What you need to know:**
```sql
-- Pattern: Auto CDC for SCD Type 2 with DELETE tracking
CREATE OR REFRESH STREAMING TABLE silver_orders_scd2 AS
SELECT * FROM (
  APPLY CHANGES INTO silver_orders_scd2
    FROM catalog.source.orders_cdc
    KEYS (order_id)
    SEQUENCE BY version
    COLUMNS * EXCEPT (_change_type)
    APPLY AS DELETE WHEN _change_type = 'delete'
    TRACK HISTORY
)
```

**Key patterns:**
- `APPLY AS DELETE WHEN` for handling deletes
- `SEQUENCE BY` for ordering changes
- `TRACK HISTORY` for SCD Type 2
- Works on `create_auto_cdc_flow()` in Python

**Gotchas:**
- Order matters: `APPLY AS DELETE` comes before `SEQUENCE BY`
- Can't use reserved columns like `_rescued_data`
- If tracking history, table grows (expected)
- Streaming table, not materialized view

**POC Task (30 min):**
1. Read: https://docs.databricks.com/ldp/cdc (10 min)
2. Create test streaming table in finserv workspace (10 min)
3. Test: Add + delete rows, verify CDC works (10 min)

**Add to SKILL.md:**
Update 9-auto_cdc.md with DELETE tracking example + gotchas

---

### Gap 5: Model Serving ChatAgent/ResponsesAgent

**What you need to know:**
- New agent types in Model Serving (Q1 2026)
- ChatAgent: Multi-turn conversation endpoint
- ResponsesAgent: Function-calling agent (tools)
- Both serve LLM agents, not just models

**Pattern:**
```python
# Deploy a ChatAgent endpoint
from databricks.agents import ChatAgent

agent = ChatAgent(
    model="claude-opus-4",
    system_prompt="You are a helpful Databricks expert",
    tools=[vector_search_tool, sql_query_tool]
)

serving_endpoint = agent.deploy(
    endpoint_name="databricks-expert",
    compute="serverless"
)
```

**Gotchas:**
- Endpoints have different types now (classical ML vs agent)
- Agent endpoints support tool calling
- Latency higher than classical model serving (expected)
- Configuration is different from traditional serving

**POC Task (25 min):**
1. Read: https://docs.databricks.com/en/generative-ai/agents/deploy-agents (10 min)
2. Skim: Agent Bricks documentation (5 min)
3. Note: Key differences vs classical model serving (10 min)

**Add to SKILL.md:**
New section in model-serving skill: "Agent Endpoints"
Include: ChatAgent vs ResponsesAgent, when to use each, deployment pattern

---

## Post-Learning Checklist

### For Each Gap You Fill:

- [ ] Read documentation (bookmark the URL)
- [ ] Do POC on finserv workspace
- [ ] Update relevant SKILL.md
- [ ] Run gap detector again: `python3 skills-eval/gap_detector.py --skill <name>`
- [ ] Verify gap is now marked "COVERED" or "OUTDATED" (improvement)
- [ ] Run FTS eval: `python3 skills-eval/experiment_loop.py <skill> --test "added <feature>"`
- [ ] Confirm FTS didn't drop

---

## Timeline (Recommended)

```
WEEK 1 (15 hours available → allocate 2-3 hours to learning)
├─ Mon: Gap 1 + 2 (Serverless notebooks + UC permissions)
├─ Wed: Gap 3 (Serverless notebook tasks)
└─ Fri: Gap 4 (Lakeflow CDC)

WEEK 2 (if time)
├─ Tue: Gap 5 (ChatAgent/ResponsesAgent)
└─ Thu: Review + consolidate

WEEK 3-4 (Tier 2 gaps, 1 per day)
├─ Mon: Bundles lookup variables
├─ Tue: ai_extract_table()
├─ Wed: Dashboard dataset_catalog
├─ Thu: Iceberg v3
└─ Fri: Connect v2

Then ongoing maintenance:
├─ Weekly: Run gap detector (10 min)
├─ Monthly: Tier 3 gaps as time allows
└─ As features drop: Update SKILL.md within 2 weeks
```

---

## How Gap Detector Helps You Stay Ahead

**Every week you:**
1. Run: `python3 skills-eval/gap_detector.py` (1 min)
2. Review new gaps (5 min)
3. Decide which to learn (5 min)
4. Do POC + update SKILL.md (20 min if urgent, skip if low priority)
5. Validate with FTS (2 min)

**Every month:**
- Feature stream monitor will detect new Databricks releases
- Gap detector will surface which skills need updates
- You pick top 3-5 to learn
- Repeat

**By end of Q2:**
- You'll have learned 20+ new features
- All skills will be 0.75+ on the matrix
- Your demos will use cutting-edge patterns
- You'll be the tip-of-the-spear SA

---

## Resources Bookmarks

**Add these to your browser:**
- Databricks Release Notes: https://docs.databricks.com/release-notes/
- API Docs: https://docs.databricks.com/api/
- SDK Changelog: https://github.com/databricks/databricks-sdk-py/releases
- Your gap detector output: `python3 skills-eval/gap_detector.py --report html > gaps.html`

**In your shell:**
```bash
# Quick check any time
python3 skills-eval/gap_detector.py --skill databricks-bundles --detail

# See all gaps (ranked)
python3 skills-eval/gap_detector.py

# Generate HTML report for sharing with team
python3 skills-eval/gap_detector.py --report html > gaps.html
open gaps.html
```

---

## Questions to Ask Yourself (Weekly Reflection)

1. "What's the newest Databricks feature I learned this week?"
2. "Did I test it on the workspace?"
3. "Did I add it to my SKILL.md?"
4. "Did my FTS improve?"
5. "Could I use this in my next demo?"

If you answer YES to all 5 → you're staying sharp.

---

## Next Steps

1. **This hour:** Pick 1 gap from Tier 1 and do the POC
2. **By end of week:** Complete all Tier 1 (2-3 hours total)
3. **By end of month:** Start Tier 2, keep running gap detector weekly
4. **By end of Q2:** All Tier 1 + 2 completed, system is self-sustaining

**Ready to pick your first gap to close?**
