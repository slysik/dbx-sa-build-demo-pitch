# Extension-Heavy vs Interactive: Interview Day Decision

## TL;DR
**Interactive with ONE lean extension.** Not chains, not teams, not multi-agent.

---

## Why Every Previous Extension Was Disabled

| Extension | What It Did | Why It Failed |
|---|---|---|
| `interview-gate.ts` | Blocked all input until prompt entered | Startup friction. Dialog box before you can type = wasted seconds |
| `interview-tasks.ts` | 7-phase task tracker with timers | Rigid. Interview doesn't follow a script. Phases overlap. |
| `coding-interview-gate.ts` | Phase + vertical + narration hints | System prompt injection per phase = context bloat. Gate blocks input. |
| `coding-interview-tasks.ts` | Budget-tracked tasks with /next /done | Task management during interview = distraction. You're coding, not managing tasks. |
| `interview-focus.ts` | Clean footer, no chrome | This one was fine. Disabled because it conflicted with other extensions. |

**Pattern: every "structured discipline" extension added friction without proportional value.**

---

## What Actually Matters During the Interview

From the practice run, these are the REAL bottlenecks (not what we imagined):

| Real Problem | Impact | Solution |
|---|---|---|
| Code generation speed | 40% of time | Pre-built templates (v2 scripts) |
| Debugging mismatches | 20% of time | FK integrity by construction |
| Losing track of time | 10% of time | A simple timer (not a task manager) |
| Context window filling up | 10% of time | Lean CLAUDE.md + on-demand skills |
| Forgetting to narrate | 5% of time | Narration comments in SQL (already done) |
| Infrastructure issues | 15% of time | One-time setup (done) |

Extensions address maybe 15% of the problem. Templates address 60%.

---

## Agent Chains / Teams: Why NOT

### Agent Chain (sequential pipeline)
```
datagen → bronze SQL → silver SQL → gold SQL → validate
```
**Problem**: The interview is conversational. The interviewer might say:
- "Skip bronze, go straight to silver"
- "Show me how you'd handle late-arriving data"
- "Can you change the clustering key?"

A chain can't pivot. You'd have to kill it and restart.

### Agent Team (parallel specialists)
```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Builder  │  │ Verifier │  │ Explainer│
└──────────┘  └──────────┘  └──────────┘
```
**Problem**: The interviewer is watching both screens. Multiple subagents spawning = chaos.
It looks like you're running automated tools, not demonstrating YOUR thinking.

### Subagent Widget (/sub)
**Problem**: Background agents doing work while you talk = the interviewer questions
whether YOU understand the code, or the agent wrote it for you.

---

## What WOULD Help: The Interview Cockpit

One extension. Three features. Zero blocking.

### Feature 1: Persistent Timer (from interview-tasks, simplified)
- Elapsed time in footer, always visible
- Color shifts: green (0-30m) → yellow (30-45m) → red (45-60m)
- NO task management. Just awareness.

### Feature 2: Prompt Display (from purpose-gate, simplified)
- Capture first user message as "the prompt"
- Show in a 2-line widget above the editor
- NO blocking dialog. Auto-captures from first message.

### Feature 3: Context Meter (from tool-counter/minimal)
- Model + context % in footer
- So you know when to compact

### What It Does NOT Do:
- ❌ Block input until something is entered
- ❌ Track tasks or phases
- ❌ Inject system prompts per phase
- ❌ Spawn subagents
- ❌ Run chains
- ❌ Add any per-tool-call overhead

---

## The Recommended Stack

```
pi -e .pi/extensions/interview-cockpit.ts

Active extensions:
  1. interview-cockpit.ts  — timer + prompt widget + context meter
  2. system-select.ts      — /system to switch to databricks-code-gen if needed

Active agents (via /system):
  - databricks-code-gen    — default system prompt for code generation
  - spark-explainer        — switch to this for discussion phase
  - interview-coach        — switch to this if you need narration help

Pre-built templates (the real speed):
  - scripts/generate_retail_data_v2.py
  - pipeline/bronze.sql, silver.sql, gold_v2.sql
  - dashboard/retail_dashboard.json
  - scripts/deploy_pipeline.py
  - scripts/deploy_dashboard.py
```

---

## Decision Matrix

| Approach | Speed | Reliability | Impression | Verdict |
|---|---|---|---|---|
| No extensions, pure interactive | ★★★★ | ★★★★★ | ★★★★ | **Safe choice** |
| Interview Cockpit (1 extension) | ★★★★★ | ★★★★ | ★★★★★ | **Best choice** |
| Chain pipeline | ★★★ | ★★ | ★★ | Rigid, can't pivot |
| Agent team | ★★ | ★★ | ★ | Looks automated |
| Full extension stack (gate+tasks+focus) | ★★ | ★★ | ★★★ | Startup friction kills you |

---

## Inspiration Worth Taking from pi-vs-claude-code

| Extension | What to Steal | How to Use It |
|---|---|---|
| `tool-counter.ts` | Context %, token count, cost in footer | Merge into cockpit footer |
| `minimal.ts` | Clean 1-line footer | Fallback if cockpit has issues |
| `purpose-gate.ts` | Auto-capture first message as purpose | Widget shows interview prompt |
| `drift.ts` | "read-heavy" detection | Could warn if you're reading too much, not building |
| `tilldone.ts` | Visual progress bar | Too heavy for interview — just use the timer |
| `damage-control.ts` | Path protection | Not needed for interview |
| `subagent-widget.ts` | Live subagent dashboard | Overkill — looks like automation |

---

## Final Recommendation

**Build `interview-cockpit.ts` — 150 lines, zero blocking, three passive features.**

Then run the interview as:
```
pi -e .pi/extensions/interview-cockpit.ts -e .pi/extensions/system-select.ts
```

The extension gives you AWARENESS (time, prompt, context).
The templates give you SPEED (pre-built code to adapt).
The /system command gives you FLEXIBILITY (switch agents mid-interview).
YOUR BRAIN gives the narration.
