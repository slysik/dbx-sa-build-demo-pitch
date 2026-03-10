---
description: Execute plan with context-optimized worker lifecycle, auto-refresh, and team cleanup
argument-hint: [path-to-plan] [--resume]
model: opus
---

# Build v2 - Context-Optimized Execution

Execute the plan at `PATH_TO_PLAN` using context-aware worker management. Workers self-report context bloat, get refreshed with clean context, and resume seamlessly. Team resources are cleaned up on completion.

## Variables

PATH_TO_PLAN: $ARGUMENTS
CONTEXT_REFRESH_THRESHOLD: 30%
ORCHESTRATOR_PAUSE_THRESHOLD: 90%
CHECKPOINT_FILE: `specs/.checkpoint-<plan-name>.json`

## Core Principles

1. **Lean Workers**: Workers operate with minimal context. At 30% utilization, they checkpoint and get refreshed.
2. **Lossless Refresh**: When a worker is refreshed, ALL progress and remaining work is captured and re-injected.
3. **2-Tier Only**: You (orchestrator) deploy workers. Workers do NOT spawn sub-agents.
4. **Clean Shutdown**: TeamDelete triggers full context cleanup.

---

## Workflow

- If no `PATH_TO_PLAN` is provided, STOP and ask the user (AskUserQuestion).
- Read the plan at `PATH_TO_PLAN`.
- Check for existing checkpoint at `CHECKPOINT_FILE`. If found and `--resume` flag present, resume from checkpoint.
- Create the team with `TeamCreate` using the plan name.
- Create the task backlog with `TaskCreate` for each step in the plan.
- Set dependencies with `TaskUpdate` + `addBlockedBy`.
- Execute tasks using the **Worker Lifecycle** protocol below.
- On completion, run the **Team Cleanup** protocol.
- Present the plan's `## Report` section.

---

## Worker Deployment Protocol

When deploying a worker, ALWAYS include the **Context Management Directive** in the worker's prompt. This is non-negotiable.

### Initial Deployment

```typescript
Task({
  description: "Task: <task-name>",
  prompt: `
## Your Assignment

<paste full task description from TaskGet>

## Files to Work With

<list relevant files from the plan>

## Context Management Directive

You MUST monitor your context utilization throughout this task.

**Self-Assessment Rule**: After every 5 tool operations (Read, Edit, Write, Bash, Grep, Glob),
pause and assess your context window usage. Consider:
- How many files have you read?
- How much output have you accumulated from Bash commands?
- How many edits/writes have you performed?
- How much conversation history has built up?

**If you estimate you have consumed 30% or more of your context window**, you MUST
immediately stop working and return a Context Refresh Report:

\`\`\`
CONTEXT_REFRESH_NEEDED

## Progress Summary
- [what has been completed so far, be specific about files and changes]

## Files Modified
- [file1.ts] - [exact changes made]
- [file2.ts] - [exact changes made]

## Remaining Work
- [specific actions still needed to complete the task]
- [include file paths, function names, any details needed to continue]

## Current State
- [any important state: variable values, decisions made, patterns discovered]
- [anything the next context needs to know to continue seamlessly]
\`\`\`

After outputting this report, STOP immediately. Do not continue working.

**If you are close to finishing** (less than 2-3 tool operations remaining), you may
complete the task instead of requesting a refresh. Use judgment.

## Execution

Begin working on the task now.
  `,
  subagent_type: "<agent-type-from-plan>",
  team_name: "<team-name>",
  name: "<worker-name-from-plan>",
  run_in_background: false
})
```

### Context Refresh Deployment (After Worker Reports CONTEXT_REFRESH_NEEDED)

When a worker returns a `CONTEXT_REFRESH_NEEDED` report:

1. **Capture** the full progress report from the worker's output
2. **Update checkpoint** with partial progress
3. **Do NOT resume** the old agent — start fresh for clean context
4. **Re-deploy** with the progress injected:

```typescript
Task({
  description: "Continue: <task-name> (context refresh)",
  prompt: `
## Your Assignment (Continuation)

<paste full task description from TaskGet>

## IMPORTANT: Previous Progress

A previous worker made progress on this task before needing a context refresh.
You are continuing their work. Do NOT redo completed work.

### What Was Already Completed
<paste the "Progress Summary" from the refresh report>

### Files Already Modified
<paste the "Files Modified" from the refresh report>

### What Remains To Do
<paste the "Remaining Work" from the refresh report>

### State From Previous Worker
<paste the "Current State" from the refresh report>

## Context Management Directive

<same directive as initial deployment - include it again>

## Execution

Continue the task from where the previous worker left off. Start by verifying
the previous work exists (quick file reads), then proceed with remaining items.
  `,
  subagent_type: "<agent-type-from-plan>",
  team_name: "<team-name>",
  name: "<worker-name-from-plan>",
  run_in_background: false  // Fresh agent, clean context
})
```

### Refresh Cycle

A single task may go through multiple refresh cycles:

```
Deploy Worker (fresh) → Works → Hits 30% → Reports → STOP
    ↓
Capture Progress → Update Checkpoint
    ↓
Deploy Worker (fresh) → Injected with progress → Continues → Hits 30% → Reports → STOP
    ↓
Capture Progress → Update Checkpoint
    ↓
Deploy Worker (fresh) → Injected with progress → Finishes → Task Complete
```

**There is no limit** on refresh cycles. Large tasks may refresh 3-5 times. This is normal and expected — each cycle has clean, efficient context.

---

## Orchestrator Execution Loop

```
for each task in dependency_order:

    1. Check orchestrator context (ORCHESTRATOR_PAUSE_THRESHOLD)
       → If > 90%: save checkpoint, pause, instruct user to /build --resume

    2. Deploy worker with Context Management Directive

    3. Read worker output:
       a. If output contains "CONTEXT_REFRESH_NEEDED":
          → Extract progress report
          → Update checkpoint with partial progress
          → Re-deploy with fresh context + progress (go to step 2)

       b. If output contains "Task Complete" or similar:
          → TaskUpdate(taskId, status: "completed")
          → Update checkpoint
          → Continue to next task

       c. If output contains errors/blockers:
          → Log the issue
          → Attempt re-deploy with error context
          → If 3 failures: skip task, note in checkpoint, continue

    4. If task has a validator in the plan:
       → Deploy validator (validators are lightweight, no refresh needed)
       → If validator reports FAIL: re-deploy builder with failure details

    5. Save checkpoint after each task completion
```

---

## Checkpoint Schema

Save to `CHECKPOINT_FILE` after every task completion or refresh:

```json
{
  "plan_file": "specs/my-plan.md",
  "team_name": "my-plan-team",
  "created_at": "2026-02-09T10:30:00Z",
  "updated_at": "2026-02-09T11:45:00Z",
  "orchestrator_context_usage": 0.45,
  "tasks": {
    "setup-database": {
      "status": "completed",
      "worker": "builder-db",
      "refresh_count": 0,
      "completed_at": "2026-02-09T10:35:00Z"
    },
    "implement-api": {
      "status": "in_progress",
      "worker": "builder-api",
      "refresh_count": 2,
      "last_progress": "Completed GET/POST endpoints. PUT/DELETE remaining.",
      "last_refresh_report": { "...full report..." }
    },
    "validate-api": {
      "status": "pending",
      "blocked_by": ["implement-api"]
    }
  },
  "completed_count": 1,
  "total_count": 3,
  "total_refresh_cycles": 2
}
```

---

## Orchestrator Pause Protocol (90%+)

When the orchestrator's own context approaches 90%:

1. **Stop all background workers** (if any running)
2. **Save checkpoint** with full state
3. **Output pause message**:

```
CONTEXT LIMIT REACHED (orchestrator > 90%)

Checkpoint saved: specs/.checkpoint-<plan>.json
Team: <team-name>
Completed: <N>/<total> tasks
Total worker refreshes: <count>
Next task: <task-name> (status: <pending|in_progress>)

To resume:
/build_v2 specs/<plan>.md --resume
```

4. **Do NOT run TeamDelete** — the team persists for resume
5. Exit gracefully

---

## Resume Protocol

When `--resume` flag is present or checkpoint file exists:

1. **Read checkpoint** from `CHECKPOINT_FILE`
2. **Skip completed tasks** — do not re-execute
3. **For in_progress tasks**: Re-deploy with the `last_refresh_report` from checkpoint as progress context
4. **For pending tasks**: Execute normally
5. **Continue** the execution loop from where it left off

---

## Team Cleanup Protocol

When ALL tasks are completed successfully:

1. **Final validation**: Deploy the validator for the final acceptance criteria check
2. **Log completion**: Update checkpoint with `"status": "all_complete"`
3. **Delete the team**:

```typescript
// Clean up team resources
TeamDelete()
```

4. **Instruct context clear**: Output to user:

```
All tasks complete. Team resources cleaned up.

To free orchestrator context, run:
/clear

Then review the completed work at:
<list of modified files>
```

The `TeamDelete` call removes:
- Team config at `~/.claude/teams/<team-name>/`
- Task list at `~/.claude/tasks/<team-name>/`

The `/clear` recommendation frees the orchestrator's accumulated context from the build session. The checkpoint file is preserved at `CHECKPOINT_FILE` as a record of the completed work.

---

## Worker Prompt Templates

### Builder Worker Template

```
## Your Assignment

[task description]

## Relevant Context

Plan: [plan file path]
Task ID: [task-id]
Dependencies completed: [list of completed prerequisite tasks and their outcomes]

## Files to Work With

[relevant files from plan]

## Context Management Directive

[full directive as specified in Worker Deployment Protocol above]

## Acceptance Criteria for This Task

[specific criteria from the plan for this task]

## Execution

Begin working. Remember: monitor your context, report if you hit 30%.
```

### Validator Worker Template

```
## Your Assignment

Validate that task "[task-name]" was completed correctly.

## What Was Built

[summary from builder's completion report or refresh reports]

## Files to Inspect

[files that were modified]

## Acceptance Criteria

[criteria to verify]

## Validation Commands

[specific commands from the plan]

## Execution

Inspect the work. Run validation commands. Report pass/fail.
Validators are lightweight — no context refresh needed.
```

### Continuation Worker Template (Post-Refresh)

```
## Your Assignment (Continuation)

[full task description]

## Previous Progress — DO NOT REDO

[progress summary from refresh report]

### Files Already Modified
[files list from refresh report]

### Remaining Work
[remaining items from refresh report]

### Important State
[current state from refresh report]

## Context Management Directive

[full directive — yes, include it again every time]

## Execution

Verify previous work exists (quick checks), then continue with remaining items.
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Worker crashes mid-task | Re-deploy with last checkpoint state |
| Worker reports blocker | Log it, attempt workaround, escalate after 3 failures |
| Validator reports FAIL | Re-deploy builder with failure details as context |
| Refresh report is incomplete | Re-deploy and ask worker to assess current file state |
| Checkpoint file corrupted | Fall back to plan file, re-check file system for completed work |
| TeamCreate fails | Proceed without team (fall back to Task-only orchestration) |

---

## Report

After all tasks complete and cleanup finishes:

```
Build Complete

Plan: <plan-file>
Tasks: <completed>/<total>
Worker Refreshes: <total refresh cycles across all workers>
Team: <team-name> (cleaned up)

Files Changed:
- [file list from all worker reports]

Validation: [PASS/FAIL]

Checkpoint: <checkpoint-file> (preserved as record)

Recommended: Run /clear to free orchestrator context.
```
