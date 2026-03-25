# Skills Conflict Resolution — Canonical Routing

**Date:** 2026-03-24 | **Status:** ACTIVE | **Scope:** Interview workflow + multi-domain scaffolding

---

## Identified Conflicts & Resolutions

### 1. **Data Generation: `spark-native-bronze` vs `databricks-synthetic-data-gen`**

#### Conflict
Both skills claim authority over synthetic data generation, but with opposing approaches:

| Aspect | spark-native-bronze | databricks-synthetic-data-gen |
|--------|---------------------|------------------------------|
| **Method** | `spark.range(N)` + Spark-native columns | Spark + Faker + Pandas UDFs |
| **Use Case** | Interview demos, medallion speed | Realistic names/addresses, client-facing |
| **Scale** | 100 → 1M by changing one param | 1K → 10M with realistic distributions |
| **Generator** | Deterministic modulo/rand | Faker library (non-deterministic) |
| **Dims** | ≤ 6 columns, lean | Dims of any size |

#### Resolution ✅
**`spark-native-bronze` is CANONICAL for all interview/demo contexts.** This is explicitly acknowledged in `databricks-synthetic-data-gen`'s own documentation:

> "When building interview demos or medallion lakehouse prototypes, use `spark.range()` + Spark-native column expressions INSTEAD of Faker + Pandas UDFs"

**Routing Decision:**
- **If** user prompt = "interview demo" OR "medallion lakehouse" OR "showcase data" → **Use `spark-native-bronze`**
- **If** user prompt = "realistic customer data" OR "Faker" OR "production test dataset" → **Use `databricks-synthetic-data-gen`**
- **If** ambiguous → **Default to `spark-native-bronze`** (interview default per CLAUDE.md)

**When to invoke each:**
- `spark-native-bronze` = INTERVIEW MODE (speed, simplicity, scale demo)
- `databricks-synthetic-data-gen` = PRODUCTION MODE (realistic names, distributions, domain patterns)

---

### 2. **Bundle Configuration: `asset-bundles` vs `databricks-bundles`**

#### Conflict
Two skills with nearly identical content, confusing naming:

| Aspect | asset-bundles | databricks-bundles |
|--------|---------------|-------------------|
| **Name** | "Asset Bundles (DABs)" | "Declarative Automation Bundles (formerly Asset Bundles)" |
| **Content** | Same YAML structure, SDP_guidance.md | Same YAML structure, SDP_guidance.md |
| **Description** | Older naming (pre-2026) | New naming (2026+) |
| **Scope** | Multi-environment deployment | Multi-environment deployment (CICD) |

#### Resolution ✅
**`databricks-bundles` is the CANONICAL, CURRENT version (2026+).**

**Reason:** The description explicitly states "Declarative Automation Bundles (formerly Asset Bundles)" — this reflects the Jan 2026 Databricks CLI rename.

**When to invoke:**
- **ALWAYS use `databricks-bundles`** for any bundle/DAB task
- **NEVER** invoke `asset-bundles` — it is **DEPRECATED** as of 2026-01-01
- If a user mentions "Asset Bundles" or "DABs," immediately map them to `databricks-bundles`

**Update recommendation:** 
- [ ] Deprecate or remove `asset-bundles` from available skills
- [ ] Update all internal references (CLAUDE.md, tutorials) to use `databricks-bundles` only

---

### 3. **Repo Scaffolding Dependencies: `repo-best-practices` → `spark-native-bronze`**

#### Relationship
These are **sequential, not conflicting:**

```
Step 1: repo-best-practices → Create skeleton (README, databricks.yml, directory structure)
Step 2: spark-native-bronze → Fill skeleton with Bronze generation code + SDP patterns
```

Both are REQUIRED for interview demos; they execute in strict order.

**Routing Decision:**
- **ALWAYS invoke `repo-best-practices` FIRST** when starting a new interview project
- **Then invoke `spark-native-bronze`** to generate Bronze + SDP patterns
- User sees one unified "interview demo" workflow, but internally it's two sequential skills

---

## Consolidated Routing Table

**Use this decision tree to route incoming prompts:**

```
┌─ User prompt mentions "interview" / "demo" / "medallion" / "showcase"?
│  YES → Go to Table A (Interview Mode)
│  NO  → Go to Table B (Production Mode)
│
└─ Table A: INTERVIEW MODE (Speed Focus)
   ├─ "Create new project" / "scaffold"?
   │  └─ invoke: repo-best-practices THEN spark-native-bronze
   ├─ "Generate data" / "create Bronze"?
   │  └─ invoke: spark-native-bronze
   ├─ "SDP pipeline" / "Silver" / "Gold"?
   │  └─ invoke: spark-declarative-pipelines (referenced in spark-native-bronze)
   ├─ "Dashboard" / "AI/BI"?
   │  └─ invoke: databricks-aibi-dashboards
   ├─ "Deploy" / "bundle"?
   │  └─ invoke: databricks-bundles
   └─ "Genie" / "natural language SQL"?
      └─ invoke: databricks-genie

└─ Table B: PRODUCTION MODE (Realism Focus)
   ├─ "Realistic synthetic data" / "Faker" / "names & addresses"?
   │  └─ invoke: databricks-synthetic-data-gen
   ├─ "DBSQL features" / "stored procedures" / "geospatial"?
   │  └─ invoke: databricks-dbsql
   ├─ "Streaming pipeline" / "Kafka" / "CDC"?
   │  └─ invoke: databricks-spark-structured-streaming
   ├─ "Vector Search" / "RAG"?
   │  └─ invoke: databricks-vector-search
   ├─ "Model Serving" / "LLM endpoint"?
   │  └─ invoke: databricks-model-serving
   ├─ "MLflow tracing" / "observability"?
   │  └─ invoke: instrumenting-with-mlflow-tracing
   └─ "Agent / Knowledge Assistant"?
      └─ invoke: databricks-agent-bricks
```

---

## Priority Rules

### Rule 1: Context > Function Name
- If a skill's description conflicts with its name, **the context (interview vs production) wins**
- `spark-native-bronze` + `repo-best-practices` together = **INTERVIEW CANONICAL**
- `databricks-synthetic-data-gen` = **PRODUCTION CANONICAL**

### Rule 2: Newest Version Wins
- `databricks-bundles` (2026+) > `asset-bundles` (pre-2026)
- When in doubt, prefer the skill with the latest year/version number

### Rule 3: Explicit Override in Prompt
- If user explicitly says "use Faker" → use `databricks-synthetic-data-gen` even if context is interview
- If user explicitly says "use spark.range()" → use `spark-native-bronze`
- Explicit > Implicit

### Rule 4: Interview = Default for Ambiguous Prompts
- If the prompt doesn't clearly signal "production" or "realistic data" → assume **interview mode**
- Invoke `spark-native-bronze` + `repo-best-practices` by default
- This matches CLAUDE.md's "Interview workflow" principle

---

## CLAUDE.md Updates Needed

Update the **SKILL ROUTING** section in CLAUDE.md with:

```markdown
### Data Generation (CONFLICT RESOLVED — 2026-03-24)
- **Interview mode** (default) → `.pi/skills/spark-native-bronze/SKILL.md` ONLY
- **Production mode** (realistic data) → `.agents/skills/synthetic-data-generation/SKILL.md`
- `.agents/skills/asset-bundles/SKILL.md` is DEPRECATED — use `databricks-bundles` instead

### Bundle Configuration (CONFLICT RESOLVED — 2026-03-24)
- **Use only:** `.agents/skills/databricks-bundles/SKILL.md`
- **Never use:** `.agents/skills/asset-bundles/SKILL.md` (pre-2026 naming, DEPRECATED)
```

---

## Summary

| Conflict | Resolution | Winner | Action |
|----------|-----------|--------|--------|
| Data generation | Interview vs Production | `spark-native-bronze` (interview default) | Routing by context |
| Bundle naming | `asset-bundles` vs `databricks-bundles` | `databricks-bundles` (2026+) | Deprecate `asset-bundles` |
| Repo scaffold | `repo-best-practices` + `spark-native-bronze` | Both (sequential) | Always invoke in order |

---

## Approval Checklist

- [x] Conflicts identified and documented
- [x] Routing decision provided for each conflict
- [x] Canonical skills identified
- [x] Context-based routing rules defined
- [x] CLAUDE.md update location noted
- [ ] User approval requested
- [ ] CLAUDE.md updated (ACTION ITEM)
- [ ] `asset-bundles` removed or hidden (FUTURE)

---

## Questions for User

1. **Should I deprecate `asset-bundles` from the available skills list?** (Recommended: YES)
2. **Should interview prompts ALWAYS prefer `spark-native-bronze` over `databricks-synthetic-data-gen`?** (Recommended: YES)
3. **Should I update CLAUDE.md now with this routing table?** (Recommended: YES)

