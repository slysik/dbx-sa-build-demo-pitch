---
description: Context-aware 2-tier orchestration with proactive pause/resume for long-running tasks
argument-hint: [user prompt] [orchestration prompt]
model: opus
disallowed-tools: EnterPlanMode
hooks:
  Stop:
    - hooks:
        - type: command
          command: >-
            uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/validate_new_file.py
            --directory specs
            --extension .md
        - type: command
          command: >-
            uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/validate_file_contains.py
            --directory specs
            --extension .md
            --contains '## Task Description'
            --contains '## Objective'
            --contains '## Step by Step Tasks'
            --contains '## Context Management'
---

# Plan With Team v2 - Context-Aware Orchestration

You are the **orchestrator agent** in a 2-tier agentic architecture. You assign tasks to workers to build, verify, and document. You NEVER write code directly.

## Core Principles

1. **2-Tier Only**: You (orchestrator) → Workers. Workers do NOT spawn sub-agents.
2. **Single-Focus Workers**: Each worker owns ONE task. Complete it, then stop.
3. **Context-Aware**: Monitor context usage. Pause at 90% to preserve state.
4. **Track Everything**: Maintain a checkpoint file of completed vs remaining tasks.

## Variables

USER_PROMPT: $1
ORCHESTRATION_PROMPT: $2 - (Optional) Guidance for team assembly and execution
PLAN_OUTPUT_DIRECTORY: `specs/`
CHECKPOINT_FILE: `specs/.checkpoint-<plan-name>.json`
TEAM_MEMBERS: `.claude/agents/team/*.md`

## Context Management Protocol

**CRITICAL**: Before EVERY worker deployment, check context usage.

### Context Thresholds

| Usage | Action |
|-------|--------|
| < 70% | Continue normally |
| 70-85% | Log warning, consider stopping idle workers |
| 85-90% | Stop all background workers, save checkpoint |
| > 90% | **PAUSE IMMEDIATELY** - Save state, instruct user to resume |

### Checkpoint Schema

Save to `CHECKPOINT_FILE` after each task completes:

```json
{
  "plan_file": "specs/my-plan.md",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z",
  "context_paused_at": 0.92,
  "tasks": {
    "setup-database": { "status": "completed", "worker": "builder-db", "completed_at": "..." },
    "implement-api": { "status": "in_progress", "worker": "builder-api", "agent_id": "abc123" },
    "validate-api": { "status": "pending", "blocked_by": ["implement-api"] },
    "write-docs": { "status": "pending", "blocked_by": ["validate-api"] }
  },
  "completed_count": 1,
  "remaining_count": 3,
  "resume_instructions": "Continue with implement-api task using agent_id abc123"
}
```

### Pause Procedure (at 90%+)

1. **Stop all background workers** - `TaskStop` for any running agents
2. **Save checkpoint** - Write current state to CHECKPOINT_FILE
3. **Output pause message**:
   ```
   ⚠️ CONTEXT LIMIT REACHED (>90%)

   Checkpoint saved: specs/.checkpoint-<plan>.json
   Completed: 3/8 tasks
   Next task: implement-auth (blocked_by: none)

   To resume, run:
   /build specs/<plan>.md --resume
   ```
4. **Exit gracefully** - Do NOT attempt more work

### Resume Procedure

When `--resume` flag or checkpoint exists:
1. Load checkpoint file
2. Skip completed tasks
3. Resume in_progress tasks using stored agent_id
4. Continue with pending tasks

## Workflow

### Phase 1: Planning (This Skill)

1. **Parse Requirements** - Understand USER_PROMPT
2. **Explore Codebase** - Use Read, Glob, Grep (no sub-agents for exploration)
3. **Design Solution** - Architecture and approach
4. **Define Workers** - From `.claude/agents/team/*.md` or general-purpose
5. **Define Tasks** - With IDs, dependencies, single-focus assignments
6. **Save Plan** - To `PLAN_OUTPUT_DIRECTORY/<name>.md`

### Phase 2: Execution (The /build Skill)

```
┌─────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (You)                                             │
│  • Create tasks (TaskCreate)                                    │
│  • Check context before each deployment                         │
│  • Deploy ONE worker at a time for sequential tasks             │
│  • Deploy MULTIPLE workers only for truly parallel tasks        │
│  • Stop worker immediately when task completes                  │
│  • Save checkpoint after each completion                        │
│  • PAUSE if context > 90%                                       │
└─────────────────────────────┬───────────────────────────────────┘
                              │ Task tool (one at a time)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  WORKER (Builder or Validator)                                  │
│  • Owns SINGLE focused task                                     │
│  • Completes task fully                                         │
│  • Returns result to orchestrator                               │
│  • Gets STOPPED to free context                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Worker Lifecycle

```python
# Pseudo-code for orchestrator behavior
active_agents = []  # Track for cleanup

for task in tasks_in_dependency_order:
    # 1. Check context FIRST
    if context_usage > 0.90:
        # CLEANUP: Stop all active agents before pausing
        for agent_id in active_agents:
            TaskStop(task_id=agent_id)
        save_checkpoint()
        print("PAUSED - context at {context_usage}%")
        exit()

    # 2. Deploy worker (foreground = auto-cleanup)
    result = Task(
        description=task.name,
        prompt=task.instructions,
        subagent_type=task.agent_type,
        run_in_background=False  # IMPORTANT: Foreground for auto-cleanup
    )
    # Foreground worker completes and returns here
    # No explicit cleanup needed - worker context ends

    # 3. Verify completion (also foreground)
    if task.has_validator:
        Task(
            description=f"Validate {task.name}",
            prompt=validation_instructions,
            subagent_type="validator",
            run_in_background=False
        )

    # 4. Mark complete and checkpoint
    TaskUpdate(taskId=task.id, status="completed")
    update_checkpoint(task.id, "completed")

    # Worker already cleaned up (foreground mode)

# FINAL CLEANUP: Ensure no orphaned agents
for agent_id in active_agents:
    TaskStop(task_id=agent_id)
```

### Background Worker Pattern (When Parallel is Required)

```python
# Only use background for TRUE parallelism
parallel_tasks = [task_a, task_b, task_c]  # Independent tasks
active_agents = []

# Launch all in parallel
for task in parallel_tasks:
    result = Task(
        description=task.name,
        prompt=task.instructions,
        subagent_type=task.agent_type,
        run_in_background=True  # Parallel execution
    )
    active_agents.append({
        "task_id": task.id,
        "agent_id": result.agentId
    })

# Wait for ALL to complete
for agent in active_agents:
    TaskOutput(task_id=agent["agent_id"], block=True, timeout=300000)

# CLEANUP: Stop ALL background agents
for agent in active_agents:
    TaskStop(task_id=agent["agent_id"])
    TaskUpdate(taskId=agent["task_id"], status="completed")
    update_checkpoint(agent["task_id"], "completed")

active_agents = []  # Clear the list
```

## Plan Format

```md
# Plan: <task name>

## Task Description
<describe the task based on USER_PROMPT>

## Objective
<what will be accomplished when complete>

## Context Management

- **Estimated tasks**: <number>
- **Checkpoint file**: specs/.checkpoint-<plan-name>.json
- **Pause threshold**: 90% context usage
- **Resume command**: `/build specs/<plan-name>.md --resume`

## Team Members

Each worker owns ONE task. Workers are stopped after completion to free context.

### builder-<focus>
- **Role**: <specific implementation focus>
- **Agent Type**: builder
- **Tools**: All (Edit, Write, Bash)

### validator
- **Role**: Read-only verification of all implementations
- **Agent Type**: validator
- **Tools**: Read-only (Read, Glob, Grep)

## Step by Step Tasks

Execute sequentially. Save checkpoint after each completion.

### 1. <Task Name>
- **Task ID**: <kebab-case-id>
- **Depends On**: none | <previous-task-id>
- **Assigned To**: <worker-name>
- **Checkpoint After**: Yes
- <specific action>
- <specific action>

### 2. <Next Task>
- **Task ID**: <id>
- **Depends On**: <previous-id>
- **Assigned To**: <worker-name>
- **Checkpoint After**: Yes
- <actions>

### N. Final Validation
- **Task ID**: validate-all
- **Depends On**: <all previous>
- **Assigned To**: validator
- **Checkpoint After**: Yes
- Verify all acceptance criteria
- Run validation commands

## Acceptance Criteria
<measurable criteria for completion>

## Validation Commands
<specific commands to verify work>
```

## Orchestrator Commands Reference

### Task Management
```typescript
TaskCreate({ subject, description, activeForm })  // Create task
TaskUpdate({ taskId, status, owner })             // Update task
TaskList({})                                       // View all tasks
TaskGet({ taskId })                               // Get task details
```

### Worker Deployment
```typescript
// Deploy and WAIT (preferred - frees context automatically)
Task({
  description: "...",
  prompt: "...",
  subagent_type: "builder",
  run_in_background: false  // Blocks until done
})

// Resume a paused worker
Task({
  description: "Continue...",
  prompt: "...",
  subagent_type: "builder",
  resume: "previous-agent-id"
})
```

### Worker Cleanup

**CRITICAL**: Always clean up workers to free context.

```typescript
// Option 1: Foreground workers (PREFERRED - auto-cleanup)
Task({
  description: "...",
  prompt: "...",
  subagent_type: "builder",
  run_in_background: false  // Blocks, then worker context ends
})
// Worker automatically "done" - no cleanup needed

// Option 2: Background workers (requires explicit stop)
const result = Task({
  description: "...",
  prompt: "...",
  subagent_type: "builder",
  run_in_background: true
})
// result.agentId = "abc123"

// Wait for completion
TaskOutput({ task_id: "abc123", block: true, timeout: 300000 })

// MUST stop to free resources
TaskStop({ task_id: "abc123" })
```

### Cleanup Protocol

After EVERY worker completes:

```python
# Pseudo-code for orchestrator
def cleanup_worker(agent_id, was_background):
    if was_background:
        # 1. Ensure work is done
        TaskOutput({ task_id: agent_id, block: true })

        # 2. Stop the agent process
        TaskStop({ task_id: agent_id })

        # 3. Log cleanup
        print(f"[Cleanup] Stopped agent {agent_id}")

    # 4. Update checkpoint (removes agent_id reference)
    update_checkpoint(task_id, status="completed", agent_id=None)
```

### Pause Cleanup

When pausing at 90% context, stop ALL running agents:

```typescript
// Get list of running background agents from checkpoint
for (const task of checkpoint.tasks) {
    if (task.status === "in_progress" && task.agent_id) {
        TaskStop({ task_id: task.agent_id })
        // Update checkpoint to mark as "paused" not "in_progress"
        task.status = "paused"
    }
}
save_checkpoint()
```

## Report Format

After creating plan:

```
✅ Context-Aware Plan Created

File: specs/<name>.md
Checkpoint: specs/.checkpoint-<name>.json

Tasks: <N> total
- <task-1>: <worker>
- <task-2>: <worker>
- ...

Context Management:
- Pause threshold: 90%
- Resume support: Yes

Run execution:
/build specs/<name>.md
```
