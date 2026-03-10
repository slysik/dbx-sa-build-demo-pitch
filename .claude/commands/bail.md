---
description: Rescue when stuck — diagnose the issue, suggest fixes, and get back on track
argument-hint: [optional: error message or description of what's stuck]
---

# Bail

Emergency rescue command for when you're stuck during a live interview. Diagnoses the problem, suggests fixes, and gets you moving again fast.

## Variables

CONTEXT: $ARGUMENTS

## Instructions

- Speed is everything — this is a live interview rescue, not a deep investigation.
- Diagnose fast, fix fast, narrate the fix as a teaching moment.
- If the fix involves SQL, test it via `execute_sql` before suggesting.
- Frame errors positively: "Good — this is actually a common pattern I see with customers..."
- Check `tasks/lessons.md` and MEMORY.md for known gotchas before investigating from scratch.

## Workflow

1. **Assess the situation:**
   - If `CONTEXT` provided, analyze the error/stuck point
   - If no `CONTEXT`, check recent tool outputs and conversation for the last error or blocker

2. **Diagnose** — check these in order:
   - Is it a known gotcha? (Check lessons learned: INTERVAL syntax, rand() seed, TEMP VIEW, DECIMAL, etc.)
   - Is it a syntax error? (Missing backticks on reserved words, wrong function name, etc.)
   - Is it a runtime error? (Table not found, permission denied, type mismatch, etc.)
   - Is it a logic error? (Wrong join, missing filter, bad aggregation, etc.)
   - Is it an environment issue? (Cluster down, warehouse not running, MCP disconnected?)

3. **Provide the fix** with interview-safe narration:
   ```
   ISSUE: [one-line diagnosis]
   ROOT CAUSE: [why it happened]
   FIX: [exact code/SQL to run]
   TALK TRACK: [what to say to the interviewer]
   ```

4. **If the fix is non-trivial**, offer two paths:
   - **Quick fix:** Get past it and move on (simpler approach)
   - **Proper fix:** Do it right (if time permits)

5. **Capture the lesson** — add to `tasks/lessons.md` if it's a new gotcha.

## Talk Tracks for Common Situations

- **Syntax error:** "Let me fix that — this is actually a common gotcha with [feature]. In production, I'd catch this in CI."
- **Permission error:** "This is a governance control working as designed. Let me adjust the approach."
- **Type mismatch:** "Good catch — Delta's schema enforcement is protecting us. Let me cast explicitly."
- **Logic error:** "Let me validate the intermediate result... ah, I see the issue. The join predicate needs adjustment."
- **Stuck on approach:** "Let me step back and think about this differently. The simpler path here is..."

## Report

```
Rescued. [one-line summary of what was fixed]
Continue building.
```
