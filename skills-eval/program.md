# skills-eval — Autoresearch for Databricks Skills

Adapted from Karpathy's autoresearch pattern. Instead of optimizing `val_bpb` on an LLM,
we optimize **First-Try Score (FTS)** — does the agent produce correct, runnable Databricks
code on the first attempt, using only the skill as guidance?

---

## Analogy to autoresearch

| autoresearch | skills-eval |
|---|---|
| `train.py` | `SKILL.md` (+ reference sub-files) — the thing being modified |
| `prepare.py` | `eval_harness.py` — fixed eval, never modified |
| `val_bpb` | **FTS** (First-Try Score, 0–10) — higher is better |
| 5-min time budget | Fixed N=5 prompts per eval run |
| `program.md` | This file |
| `results.tsv` | `results/{skill}.tsv` — one row per experiment |

---

## Setup (one-time)

1. **Agree on a skill to optimize** — pick from `results/*.tsv` (lowest baseline FTS first)
2. **Create a branch**: `git checkout -b skills-eval/<skill>/<tag>` (e.g. `skills-eval/sdp/mar20`)
3. **Read the in-scope files**:
   - `eval_harness.py` — the fixed scorer. Do not modify.
   - `prompts/<skill>.md` — the test prompts. Do not modify.
   - `.agents/skills/<skill>/SKILL.md` — the file you edit.
   - `.agents/skills/<skill>/` sub-files — also editable.
4. **Run baseline**: `python skills-eval/eval_harness.py <skill>` to establish the starting FTS.
5. **Initialize results**: baseline row is written automatically.

---

## Experimentation Loop

**LOOP FOREVER:**

1. Read `results/<skill>.tsv` — understand what's been tried, current best FTS.
2. Look at the **lowest-scoring prompts** from the last eval run (logged to `results/<skill>-last-run.json`).
3. Identify the root cause: what pattern is missing or unclear in `SKILL.md`?
4. Edit `SKILL.md` (or a reference sub-file) to address the gap. One hypothesis per experiment.
5. `git commit -am "skills-eval: <skill> — <what you changed>"`
6. Run the eval: `python skills-eval/eval_harness.py <skill> > run.log 2>&1`
7. Read results: `grep "^FTS:" run.log`
8. If FTS improved → advance (keep commit). If same or worse → `git reset HEAD~1`.
9. Log to `results/<skill>.tsv`.

**What you CAN change:**
- `SKILL.md` content — add patterns, fix gotchas, restructure, clarify
- Reference sub-files — expand, split, add new files
- The `description:` frontmatter — affects which prompts trigger this skill

**What you CANNOT change:**
- `eval_harness.py` — the eval is fixed
- `prompts/<skill>.md` — the test questions are fixed validation data
- The scoring rubric in `eval_harness.py`

---

## Simplicity criterion (from autoresearch)

> All else being equal, fewer tokens is better. A 0.5 FTS improvement from adding
> 2KB of dense prose? Probably not worth it — add structure instead.
> Removing 500 tokens and getting equal FTS? Always keep.

The ideal SKILL.md is a **lean index file** (≤1500 tokens) that routes to sub-files.
Sub-files can be as detailed as needed — they're loaded on demand, not always in context.

---

## Scoring

FTS is scored 0–10 per prompt. See `eval_harness.py` for the full rubric. Summary:

| Criterion | Points | What it checks |
|---|---|---|
| Correct imports | 1 | Right libraries for the domain |
| No anti-patterns | 2 | No `collect()`, `SELECT *`, Faker loops, hardcoded secrets |
| Pattern adherence | 3 | Uses the key pattern the skill teaches |
| Completeness | 2 | Covers all aspects of the prompt |
| First-try runnable | 2 | Code would execute without modification |

**Total: 10 points per prompt. FTS = mean across all 5 prompts.**

---

## Results TSV format

`results/<skill>.tsv` — tab-separated, one row per experiment:

```
commit	FTS	skill_tokens	status	description
```

- `commit` — 7-char git hash
- `FTS` — mean First-Try Score (0.0–10.0, 2 decimal places)
- `skill_tokens` — byte count of SKILL.md ÷ 4 (token proxy)
- `status` — `keep`, `discard`, or `crash`
- `description` — what this experiment changed

Example:
```
commit	FTS	skill_tokens	status	description
a1b2c3d	6.20	2240	keep	baseline
b2c3d4e	7.40	2480	keep	added embed_credentials gotcha + parent_path rules
c3d4e5f	7.20	2700	discard	added too much prose — noise > signal
d4e5f6g	8.10	2360	keep	restructured as index → sub-file, cut prose
```

---

## Priority queue (lowest baseline FTS = highest priority)

Run `python skills-eval/eval_harness.py --baseline-all` to populate this table.

| Skill | Est. FTS | Known gaps |
|---|---|---|
| `spark-declarative-pipelines` | TBD | `ai_summarize` non-determinism, `pipelines list-pipelines` |
| `databricks-aibi-dashboards` | TBD | `embed_credentials: false`, `parent_path` |
| `synthetic-data-generation` | TBD | Conflicts with `spark.range()` preference in CLAUDE.md |
| `databricks-genie` | TBD | `serialized_space` proto3 format, table sort order |
| `databricks-bundles` | TBD | `--only` flag (not `--task`), stale tfstate recovery |

---

## NEVER STOP

Once the loop begins, do not pause to ask if you should continue. Run until manually interrupted.
If FTS plateaus (no improvement in 3 experiments), switch to a different skill.
