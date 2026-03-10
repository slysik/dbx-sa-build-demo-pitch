---
description: Save current session state to disk files for /clear recovery. Updates SCRATCHPAD.md, specs/state.md, and specs/decisions.md.
---

You are performing a **context checkpoint** — saving the current session state to disk so the user can `/clear` without losing context.

## Steps

### 1. Update SCRATCHPAD.md

Read the current `SCRATCHPAD.md` file, then rewrite it with:

- **Current Task**: What you're actively working on right now
- **Context Needed**: Key facts, file paths, architectural constraints relevant to current work
- **What's Been Done This Session**: List of completed items from this session
- **What Remains**: Uncompleted items, next steps
- **Key Details Not Yet In Files**: Any decisions or details discussed but not written to source code
- **Resume Instructions**: Specific instructions for Claude after `/clear` — which files to read first, which task to pick up, any gotchas

### 2. Update specs/state.md

Read the current `specs/state.md` file. Check `TaskList` for current task status. Update:

- **Desired State**: The full plan (from spec files or conversation)
- **Actual State**: What's actually built and working
- **Delta**: What remains, with blockers and priority

### 3. Update specs/decisions.md

Read the current `specs/decisions.md` file. If any architectural or design decisions were made during this session that aren't already recorded, append them using the template format in the file.

### 4. Confirm to User

After updating all files, tell the user:

```
Checkpoint saved:
- SCRATCHPAD.md — session state and resume instructions
- specs/state.md — plan vs reality alignment
- specs/decisions.md — decision log

Ready for /clear. To resume: "Read SCRATCHPAD.md and continue"
```

## Important

- Be thorough — this is the user's safety net before wiping context
- Include specific file paths and line numbers where relevant
- The resume instructions should be detailed enough that a fresh Claude instance with zero context can pick up immediately
- Don't be generic — reference actual code, actual decisions, actual state
