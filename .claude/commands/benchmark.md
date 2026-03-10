---
description: Run A/B benchmark comparing /build vs /build_v2 on a sample plan
argument-hint: [path-to-plan] [build|build_v2|report]
model: opus
---

# Benchmark: Build vs Build_v2

Compare orchestration strategies by running the same plan through `/build` and `/build_v2`, collecting metrics, and generating a comparison report.

## Variables

PATH_TO_PLAN: $1 (default: `specs/benchmark-url-shortener.md`)
MODE: $2 (one of: `build`, `build_v2`, `report`, `setup`, `reset`)

## Metrics to Capture

For each run, record these metrics in `specs/benchmark-results.json`:

### 1. Token Usage
- **Total input tokens** — from `/cost` output after run
- **Total output tokens** — from `/cost` output after run
- **Total cost** — dollar amount from `/cost`
- **Cache read tokens** — how much context was served from cache
- **Cache write tokens** — new context written to cache

### 2. Correctness (Desired vs Actual State)
- **Acceptance criteria pass rate** — X/N criteria passed
- **Per-criterion results** — pass/fail for each specific criterion
- **TypeScript compilation** — clean or errors
- **Functional tests** — each CLI command works as specified
- **Idempotency check** — shortening same URL twice gives same code

### 3. Speed & Performance
- **Wall clock time** — total seconds from start to finish
- **Task count** — total tasks created
- **Worker deployments** — total Task tool invocations
- **Context refreshes** — (v2 only) how many CONTEXT_REFRESH_NEEDED cycles
- **Validation cycles** — how many validator deployments

### 4. Context Efficiency
- **Orchestrator context at completion** — percentage of context used by end
- **Average worker context per deployment** — estimated from tool operation counts
- **Total refresh cycles** — (v2 only) sum across all workers
- **Checkpoint saves** — number of checkpoint file updates

### 5. Quality Signals
- **Files created** — count and completeness
- **Lines of code produced** — total LOC across all new files
- **Ruff/Ty validator triggers** — how many PostToolUse validations fired
- **Worker errors/retries** — count of failures that needed re-deployment
- **Code duplication** — any repeated patterns across files

## Workflow

### Mode: `setup`

Prepare the benchmark environment:

1. Ensure the plan exists at `PATH_TO_PLAN`
2. Create `specs/benchmark-results.json` with empty structure:
```json
{
  "plan": "specs/benchmark-url-shortener.md",
  "runs": {
    "build_v1": null,
    "build_v2": null
  },
  "comparison": null
}
```
3. Create a git branch `benchmark/build-comparison` from current state
4. Confirm setup is ready

### Mode: `reset`

Reset the workspace between runs:

1. Remove `apps/url-shortener/` directory if it exists
2. Remove any checkpoint files for this plan
3. Remove any team resources created during previous run
4. Git checkout to clean state on the benchmark branch
5. Confirm reset is complete

### Mode: `build`

Run the plan through `/build` (v1) and collect metrics:

1. Record start timestamp
2. Record current `/cost` output (baseline)
3. Note: The user should now run in a SEPARATE session:
   ```
   /build specs/benchmark-url-shortener.md
   ```
4. After completion, return to this session and run:
   ```
   /benchmark specs/benchmark-url-shortener.md report-v1
   ```

### Mode: `build_v2`

Run the plan through `/build_v2` and collect metrics:

1. Record start timestamp
2. Record current `/cost` output (baseline)
3. Note: The user should now run in a SEPARATE session:
   ```
   /build_v2 specs/benchmark-url-shortener.md
   ```
4. After completion, return to this session and run:
   ```
   /benchmark specs/benchmark-url-shortener.md report-v2
   ```

### Mode: `report`

Generate the comparison report:

1. Read `specs/benchmark-results.json`
2. Run all validation commands from the plan's Acceptance Criteria
3. Count files created, lines of code
4. Populate the metrics for the current run (v1 or v2 depending on which was just run)
5. If both runs are complete, generate the comparison

## Metrics Collection Script

After each build run completes, execute this collection sequence:

```bash
# 1. File count and LOC
find apps/url-shortener/src -name "*.ts" | wc -l
find apps/url-shortener/src -name "*.ts" -exec cat {} + | wc -l

# 2. TypeScript compilation
cd apps/url-shortener && bunx tsc --noEmit 2>&1; echo "EXIT: $?"

# 3. Functional tests
bun run --cwd apps/url-shortener start help 2>&1; echo "EXIT: $?"
bun run --cwd apps/url-shortener start shorten https://example.com 2>&1
bun run --cwd apps/url-shortener start shorten https://google.com 2>&1
bun run --cwd apps/url-shortener start list 2>&1
bun run --cwd apps/url-shortener start stats 2>&1
bun run --cwd apps/url-shortener start shorten https://example.com 2>&1  # idempotent check
bun run --cwd apps/url-shortener start resolve <shortcode-from-above> 2>&1
bun run --cwd apps/url-shortener start delete <shortcode-from-above> 2>&1

# 4. Checkpoint/refresh data (v2 only)
cat specs/.checkpoint-benchmark-url-shortener.json 2>/dev/null || echo "No checkpoint"

# 5. Hook logs (count PostToolUse validator triggers)
cat logs/post_tool_use.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
validators = [e for e in data if 'validator' in str(e.get('tool_name', ''))]
print(f'Validator triggers: {len(validators)}')
" 2>/dev/null || echo "No hook logs"
```

## Comparison Report Format

```markdown
# Benchmark Report: /build vs /build_v2

**Plan**: specs/benchmark-url-shortener.md
**Date**: [date]

## Summary

| Metric | /build (v1) | /build_v2 | Delta | Winner |
|--------|-------------|-----------|-------|--------|
| Total Cost | $X.XX | $X.XX | -X% | v1/v2 |
| Wall Clock Time | Xs | Xs | -X% | v1/v2 |
| Acceptance Criteria | X/12 | X/12 | +/-N | v1/v2 |
| TypeScript Clean | Yes/No | Yes/No | - | v1/v2 |
| Worker Deployments | N | N | +/-N | v1/v2 |
| Context Refreshes | 0 | N | +N | - |
| Files Created | N | N | +/-N | v1/v2 |
| Total LOC | N | N | +/-N | v1/v2 |
| Worker Errors | N | N | +/-N | v1/v2 |

## Token Usage

| Metric | /build (v1) | /build_v2 | Delta |
|--------|-------------|-----------|-------|
| Input Tokens | N | N | +/-N% |
| Output Tokens | N | N | +/-N% |
| Cache Read | N | N | +/-N% |
| Total Cost | $X.XX | $X.XX | +/-N% |

## Correctness Detail

| Criterion | /build (v1) | /build_v2 |
|-----------|-------------|-----------|
| package.json exists | pass/fail | pass/fail |
| tsconfig.json strict | pass/fail | pass/fail |
| All 14 files exist | pass/fail | pass/fail |
| shorten command | pass/fail | pass/fail |
| resolve command | pass/fail | pass/fail |
| list command | pass/fail | pass/fail |
| delete command | pass/fail | pass/fail |
| stats command | pass/fail | pass/fail |
| help command | pass/fail | pass/fail |
| TSC --noEmit clean | pass/fail | pass/fail |
| Error handling | pass/fail | pass/fail |
| Idempotent shorten | pass/fail | pass/fail |

## Context Efficiency (v2 only)

| Worker | Refresh Cycles | Total Deployments | Notes |
|--------|---------------|-------------------|-------|
| builder-foundation | N | N | ... |
| builder-core | N | N | ... |
| builder-integration | N | N | ... |
| validator-final | 0 | 1 | Read-only, no refresh |

## Analysis

### Where v2 Helps
- [observations about context freshness impact on code quality]
- [observations about worker focus and task completion]

### Where v2 Costs More
- [additional API calls from refresh cycles]
- [overhead of progress capture and re-injection]

### Recommendation
[Which version to prefer and under what conditions]
```

## Running the Full Benchmark

### Step-by-step Protocol

```
# 1. Setup
/benchmark specs/benchmark-url-shortener.md setup

# 2. Run v1
#    Open NEW session (or /clear first)
/build specs/benchmark-url-shortener.md
#    After completion, record /cost output
#    Return to benchmark session:
/benchmark specs/benchmark-url-shortener.md report-v1

# 3. Reset
/benchmark specs/benchmark-url-shortener.md reset

# 4. Run v2
#    Open NEW session (or /clear first)
/build_v2 specs/benchmark-url-shortener.md
#    After completion, record /cost output
#    Return to benchmark session:
/benchmark specs/benchmark-url-shortener.md report-v2

# 5. Compare
/benchmark specs/benchmark-url-shortener.md report
```

### Important: Isolation

- Each build run MUST happen in a **separate session** to avoid cross-contamination
- Use `/clear` or start a new Claude Code session between runs
- The benchmark session (this command) is for setup, reset, and reporting only
- Do NOT run builds in the same session as the benchmark coordinator

## Notes

- The benchmark plan is intentionally medium-complexity (5 tasks, 14 files, ~300-400 LOC expected)
- v1 is expected to be faster (fewer API calls) but may produce lower quality at scale
- v2 is expected to produce more consistent quality due to fresh context per cycle
- The real value of v2 shows on LARGER plans — this benchmark provides a baseline
- For a more demanding test, duplicate the plan with 2x-3x the tasks
