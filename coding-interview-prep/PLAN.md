# Databricks Sr. Solutions Architect — Coding Interview Prep Plan

**Interview Date**: Wednesday, March 10, 2026
**Format**: 60-min collaborative pair programming on Databricks Free Edition
**Tools**: Claude Code + Pi (terminal, shared screen) → Databricks UI (shared screen)

---

## Your Strategy: The "AI Pilot" Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  SHARED SCREEN 1: Ghostty Terminal                              │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │  Claude Code          │  │  Pi (coding agent)    │            │
│  │  - Generate code      │  │  - Databricks skills  │            │
│  │  - Debug/iterate      │  │  - Upload notebooks   │            │
│  └──────────────────────┘  └──────────────────────┘            │
│                                                                 │
│  SHARED SCREEN 2: Databricks UI                                 │
│  - Run notebooks, show results, explain pipelines               │
└─────────────────────────────────────────────────────────────────┘
```

### The 60-Minute Interview Flow You'll Practice

| Phase | Time | What You Do |
|-------|------|-------------|
| **Discovery** | 0–10 min | Hear prompt → ask clarifying questions → define scope |
| **Generate Dataset** | 10–20 min | Prompt AI → generate Python (Faker) synthetic data → review & fix |
| **Build Pipeline** | 20–45 min | Build medallion or analytical solution → SQL transforms → explain |
| **Discuss & Scale** | 45–60 min | Explain execution, how it scales, trade-offs |

### "Think Out Loud" — Your Narration Template

At every step, narrate using this pattern:
1. **WHAT** I'm about to do and **WHY**
2. **PROMPT** the AI tool
3. **AUDIT** the output — call out what's good, what needs fixing
4. **EXPLAIN** to the interviewer what the code does (as if they're a customer)

Example script:
> "I need to generate a realistic transactions dataset. I'll use Faker for customer names and 
> IDs, and numpy for amounts — real transaction amounts aren't uniform, they cluster around 
> small purchases with occasional large ones. Let me prompt Claude for this...
> 
> *[reviews output]*
> 
> OK, Claude gave me a good start but the fraud labels are 50/50 — in reality fraud is maybe 
> 1-2% of transactions. Let me fix that distribution. Also I want to add a timestamp column 
> with realistic time patterns..."

---

## Day-by-Day Practice Schedule

### Day 1 (Thursday Mar 4): Foundation — Environment + Faker + PySpark Basics
**Goal**: Eliminate UI friction, get comfortable generating data

- [ ] Sign up for Databricks Free Edition (backup to Azure workspace)
- [ ] Spin up a cluster, run a hello-world notebook
- [ ] **Practice Problem 1**: Generate a synthetic dataset (see `practice/01-synthetic-data/`)
- [ ] Learn the `just nb-upload` workflow to push notebooks from terminal → Databricks
- [ ] Read: `Faker` basics, `PySpark DataFrame` creation from Python lists/dicts

**Key Concepts to Nail**:
- `from faker import Faker` — names, addresses, dates, credit cards
- `spark.createDataFrame(data, schema)` — Python list → Spark DataFrame
- `df.write.format("delta").saveAsTable("catalog.schema.table")` — persist to Delta

---

### Day 2 (Friday Mar 5): Pipeline Building — Bronze/Silver/Gold in SQL
**Goal**: Build a full medallion pipeline, narrating as you go

- [ ] **Practice Problem 2**: End-to-end medallion pipeline (see `practice/02-medallion-pipeline/`)
- [ ] Practice the "Think Out Loud" narration — record yourself if possible
- [ ] Focus on SQL transforms (your strength): window functions, aggregations, CASE/WHEN
- [ ] Understand what happens under the hood: Delta log, Z-ordering, partitioning

**Key Concepts to Nail**:
- Bronze: raw ingestion (COPY INTO or Auto Loader)
- Silver: data quality (constraints, dedup, type casting, null handling)
- Gold: business aggregations, feature engineering, star schema patterns
- Delta Lake: ACID transactions, time travel, OPTIMIZE, VACUUM

---

### Day 3 (Saturday Mar 6): Distributed Reasoning — How Spark Executes
**Goal**: Be able to explain ANY code's execution at the Spark level

- [ ] **Practice Problem 3**: Explain the execution (see `practice/03-spark-execution/`)
- [ ] Study: Spark UI, DAG, stages, tasks, shuffle, broadcast joins
- [ ] Practice explaining: "When I run this GROUP BY, Spark will..."
- [ ] Know the difference: narrow vs wide transformations, partition count impact

**Key Talking Points** (memorize these patterns):
- "This JOIN will cause a shuffle because both tables are large — in production I'd consider broadcast hint if the dimension table is small"
- "The GROUP BY creates a new stage — Spark hashes the key and redistributes across partitions"  
- "This window function partitions by customer_id, so all rows for a customer land on the same executor"
- "With Delta, this write is ACID — if it fails halfway, the transaction rolls back cleanly"

---

### Day 4 (Sunday Mar 7): Debugging & Resilience
**Goal**: Practice hitting errors and recovering gracefully

- [ ] **Practice Problem 4**: Intentionally broken code (see `practice/04-debugging/`)
- [ ] Common PySpark errors: column name typos, schema mismatches, null handling
- [ ] Practice the "bail out" — know when to say "I'm stuck on syntax, can we move on?"
- [ ] Practice narrating through bugs: "Hmm, I got a AnalysisException — that usually means..."

**Common Errors to Recognize Instantly**:
- `AnalysisException: cannot resolve column` → typo or wrong table alias
- `Py4JJavaError` → usually a serialization issue or OOM
- `DELTA_MISSING_COLUMN` → schema evolution needed
- `ParseException` → SQL syntax error

---

### Day 5 (Monday Mar 8): Full Mock Interview #1
**Goal**: Simulate the full 60-minute interview end-to-end

- [ ] **Mock Problem 5**: Timed 60-minute simulation (see `practice/05-mock-interview-1/`)
- [ ] Set a timer. Follow the Discovery → Build → Discuss flow
- [ ] Use Claude/Pi to generate all code, but NARRATE everything
- [ ] Upload to Databricks, run it, explain it
- [ ] Review: What went well? Where did you get stuck? What took too long?

---

### Day 6 (Tuesday Mar 9): Full Mock Interview #2 + Polish
**Goal**: Second full simulation with different scenario, polish weak spots

- [ ] **Mock Problem 6**: Different domain scenario (see `practice/06-mock-interview-2/`)
- [ ] Focus on whatever was weakest in Mock #1
- [ ] Practice your opening: "Let me start by asking a few clarifying questions..."
- [ ] Practice your closing: walk through the Databricks UI showing what you built
- [ ] Prepare 2-3 "smart questions" to ask the interviewers about their team

---

### Day 7 (Wednesday Mar 10): Interview Day
- [ ] Light review only — skim this plan, review your narration notes
- [ ] Log into Databricks Free Edition, confirm cluster starts
- [ ] Have Ghostty open with Claude Code + Pi ready
- [ ] **Relax. Be curious. You've practiced this.**

---

## Quick Reference: Things to Say

### Discovery Phase Clarifying Questions
- "What's the business use case — are we doing analytics, ML features, or reporting?"
- "How many records should the dataset have? Thousands? Millions?"
- "Are there specific columns or data types you'd like to see?"
- "Should I include any data quality issues to handle in the pipeline?"
- "Will this be batch or streaming?"

### While Generating Code
- "I'm prompting Claude to generate a Faker-based dataset with [X columns]..."
- "Let me review this — I want to make sure the data types and distributions are realistic"
- "I see the AI used [X], but I'd prefer [Y] because..."
- "Good, but I need to add [edge case] to make this production-realistic"

### While Explaining Code
- "This Bronze layer is doing raw ingestion — no transforms, just landing the data as-is"
- "In Silver, I'm deduplicating on [key] and casting types — this is where data quality lives"
- "The Gold layer aggregates by [dimension] — this is what the business analyst would query"
- "Under the hood, this GROUP BY triggers a shuffle across partitions..."

### When Stuck
- "I'm hitting a syntax issue with [X] — mind if I look that up quickly?"
- "I know the logic I want but I'm fighting the API — can I describe my intent and move on?"
- "Let me step back — the approach should be [describe], even if my syntax isn't perfect"

---

## Evaluation Criteria Mapped to Practice

| Criteria | What They're Looking For | How You Demonstrate It |
|----------|-------------------------|----------------------|
| **Computational Thinking** | Break problem into logical steps | Discovery questions → clear pipeline stages |
| **Code Stewardship** | Explain what code does under the hood | Narrate every AI output, catch errors |
| **Resilience** | Handle bugs gracefully | Narrate the debug process, use "bail out" wisely |

---

## Files in This Directory

```
coding-interview-prep/
├── PLAN.md                          ← This file
├── cheat-sheets/
│   ├── pyspark-essentials.md        ← PySpark syntax you'll need
│   ├── faker-patterns.md            ← Faker recipes for synthetic data
│   ├── sql-transforms.md            ← SQL patterns for Silver/Gold
│   ├── spark-execution.md           ← How to explain Spark internals
│   └── narration-scripts.md         ← "Think out loud" scripts
├── practice/
│   ├── 01-synthetic-data/           ← Day 1: Generate data with Faker
│   ├── 02-medallion-pipeline/       ← Day 2: Full Bronze→Silver→Gold
│   ├── 03-spark-execution/          ← Day 3: Explain what Spark does
│   ├── 04-debugging/                ← Day 4: Fix broken code
│   ├── 05-mock-interview-1/         ← Day 5: Full 60-min simulation
│   └── 06-mock-interview-2/         ← Day 6: Second simulation
└── sample-prompts/
    └── interviewer-prompts.md       ← Likely prompts they might give you
```
