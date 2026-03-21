# skills-eval — Autoresearch for Databricks Skills

Adapted from [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

Karpathy's system optimizes `val_bpb` on a language model by letting an AI agent
modify `train.py` in a keep/discard loop. We do the same for SKILL.md files:
optimize **First-Try Score (FTS)** — does the agent produce correct, runnable
Databricks code on the first attempt using only the skill as guidance?

---

## Analogy

| autoresearch | skills-eval |
|---|---|
| `train.py` | `SKILL.md` + reference sub-files |
| `prepare.py` (fixed eval) | `eval_harness.py` (fixed, never modify) |
| `val_bpb` | **FTS** (First-Try Score, 0–10) |
| 5-min time budget | 5 fixed prompts per eval run |
| `program.md` | `program.md` (agent loop instructions) |
| `results.tsv` | `results/<skill>.tsv` |

---

## Files

```
skills-eval/
├── program.md          ← Agent loop instructions (READ THIS FIRST)
├── eval_harness.py     ← Fixed scorer — never modify
├── README.md           ← This file
├── prompts/            ← Fixed test prompts per skill (validation data — never modify)
│   ├── spark-declarative-pipelines.md
│   ├── databricks-aibi-dashboards.md
│   ├── synthetic-data-generation.md
│   ├── databricks-genie.md
│   └── databricks-bundles.md
└── results/            ← Experiment logs per skill (git-untracked, like results.tsv)
    ├── spark-declarative-pipelines.tsv
    ├── databricks-aibi-dashboards.tsv
    ├── synthetic-data-generation.tsv
    ├── databricks-genie.tsv
    └── databricks-bundles.tsv
```

---

## Quick Start

```bash
# Automated (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-ant-api03-...
python skills-eval/eval_harness.py spark-declarative-pipelines

# Run baseline for all 5 skills
python skills-eval/eval_harness.py --baseline-all

# Manual (agent generates code, pastes in terminal)
python skills-eval/eval_harness.py databricks-aibi-dashboards

# Log a result after manual eval
python skills-eval/eval_harness.py --log databricks-aibi-dashboards 7.40 keep "added embed_credentials gotcha"
```

---

## Scoring Rubric (fixed)

| Criterion | Points | What |
|---|---|---|
| Correct imports | 1 | Right libraries for the domain |
| No anti-patterns | 2 | No `collect()`, `SELECT *`, Faker loops at scale, hardcoded secrets |
| Pattern adherence | 3 | Uses core patterns the skill teaches |
| Completeness | 2 | Covers all prompt requirements |
| First-try runnable | 2 | UC 3-level namespace, no placeholders, no error traces |
| **Total** | **10** | |

---

## Current skill gaps (already patched)

| Skill | Gap | Fix |
|---|---|---|
| `spark-declarative-pipelines` | `ai_summarize` non-deterministic | Added ⚠️ gotcha block |
| `spark-declarative-pipelines` | `pipelines list-pipelines` not `list` | Added ⚠️ gotcha block |
| `databricks-aibi-dashboards` | `embed_credentials: false` required | Added ⚠️ deployment gotchas |
| `databricks-aibi-dashboards` | `parent_path` must be pre-created dir | Added ⚠️ deployment gotchas |
| `synthetic-data-generation` | `spark.range()` vs Faker conflict | Added ⚠️ interview override block |
| `synthetic-data-generation` | Missing `ingest_ts/source_system/batch_id` | Added ⚠️ interview override block |

---

## Simplicity criterion

> All else being equal, fewer tokens = better.
> Same FTS with 20% fewer tokens → always keep the reduction.
> Ideal SKILL.md: ≤1500 token index file routing to sub-files.
> Sub-files: as deep as needed, loaded on demand.

---

## Adding new skills to the eval

1. Create `prompts/<skill-name>.md` with 5 prompts in the format shown
2. Add `REQUIRED_PATTERNS["<skill-name>"]` to `eval_harness.py` (rubric patterns)
3. Create `results/<skill-name>.tsv` with header row
4. Run baseline: `python skills-eval/eval_harness.py <skill-name>`
