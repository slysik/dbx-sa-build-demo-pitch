---
description: Measure thrice, cut once — iterative plan refinement with 7 review cycles (2 local + 2 cross-model + 3 Claude) before build
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
            --contains '## Review History'
            --contains '## Team Orchestration'
            --contains '### Team Members'
---

# Plan With Team v3 — Measure Thrice, Cut Once

You are the **planning orchestrator**. You generate an implementation plan, then run it through **7 review cycles** — two local reviews via Kimi 2.5 and Ollama 3B (free, instant), two cross-model reviews via Codex and Gemini (headless API calls), then 3 Claude review cycles with different lenses. Each review produces actionable feedback that you incorporate before the next cycle. Only the final, battle-tested plan is saved.

**Philosophy**: The cost of 7 review passes is trivial compared to the cost of building from a bad plan. Local reviews (Kimi + Ollama) are free and fast — catch simplicity and security issues first. Cross-model reviews (Codex + Gemini) catch blind spots that same-model review misses — each LLM has different strengths. Catch architecture mistakes, missing edge cases, and weak acceptance criteria BEFORE any code is written.

## Variables

USER_PROMPT: $1
ORCHESTRATION_PROMPT: $2 - (Optional) Guidance for team assembly and execution
PLAN_OUTPUT_DIRECTORY: `specs/`
DRAFTS_DIRECTORY: `specs/drafts/`
TEAM_MEMBERS: `.claude/agents/team/*.md`
GENERAL_PURPOSE_AGENT: `general-purpose`
REVIEW_CYCLES: 7 (2 Local + 2 Cross-Model + 3 Claude)
KIMI_REVIEW_SCRIPT: `.claude/hooks/utils/llm/kimi_review.py`
OLLAMA_SECURITY_REVIEW_SCRIPT: `.claude/hooks/utils/llm/ollama_security_review.py`
CODEX_REVIEW_SCRIPT: `.claude/hooks/utils/llm/codex_review.py`
GEMINI_REVIEW_SCRIPT: `.claude/hooks/utils/llm/gemini_review.py`

## Core Principles

1. **Plan, Don't Build** — Your only output is a plan document. No code, no deployments.
2. **Local First** — Reviews 0A (Kimi simplicity) and 0B (Ollama security) run locally for free and fast. Catch obvious complexity and security gaps before spending API credits.
3. **Cross-Model Second** — Reviews 1A (Codex/GPT-5.3) and 1C (Gemini 3) provide two independent cross-model architecture reviews before Claude weighs in. Different models have different blind spots — two cross-model perspectives maximize coverage.
4. **3 Claude Reviews** — Architecture (1B), implementation feasibility (2), quality gate (3).
5. **Cumulative Refinement** — Each revision incorporates ALL prior feedback. Reviews build on each other.
6. **Preserve History** — Save each draft and review for auditability. The final plan includes a review log.
7. **Codebase-Grounded** — Explore the actual codebase directly (no sub-agents for exploration). Plans must be rooted in real file paths and patterns.

---

## Workflow

### Phase 1: Draft Plan

1. **Parse Requirements** — Understand USER_PROMPT deeply. What is actually being asked?
2. **Explore Codebase** — Use Read, Glob, Grep directly. Understand existing patterns, architecture, relevant files.
3. **Design Solution** — Architecture decisions, tech approach, implementation strategy.
4. **Define Team & Tasks** — Workers, dependencies, parallel opportunities.
5. **Write Draft** — Save to `DRAFTS_DIRECTORY/<plan-name>-draft-1.md` using the Plan Format below.

### Phase 2: Review 0A — Kimi Simplicity Review (Local)

Run the Kimi 2.5 review script via Bash to get a simplicity and ease-of-use review. This runs **locally via Ollama** — free, fast, no API credits.

```typescript
Bash({
  command: "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/utils/llm/kimi_review.py $CLAUDE_PROJECT_DIR/DRAFTS_DIRECTORY/<plan-name>-draft-1.md --review-type simplicity",
  description: "Kimi 2.5 simplicity review of draft plan"
})
```

The script calls Kimi 2.5 (via Ollama) and returns structured feedback: Critical Complexity, Simplification Opportunities, Dependency Review, Developer Experience Issues, Strengths, and a Simplicity Score.

**If the script fails** (Ollama not running, model not pulled): Log the failure and proceed to Phase 3. Local reviews are valuable but not blocking.

**After Review 0A**: Read the Kimi feedback. Revise the plan to eliminate unnecessary complexity, simplify over-engineered patterns, and remove unjustified dependencies. Save as `DRAFTS_DIRECTORY/<plan-name>-draft-2.md`.

### Phase 3: Review 0B — Ollama Security Review (Local)

Run the Ollama 3B security review script via Bash. Like Review 0A, this runs **locally via Ollama** — free, fast, catches obvious security gaps early.

```typescript
Bash({
  command: "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/utils/llm/ollama_security_review.py $CLAUDE_PROJECT_DIR/DRAFTS_DIRECTORY/<plan-name>-draft-2.md --review-type security",
  description: "Ollama 3B security review of simplicity-revised draft"
})
```

The script calls llama3.2:3b (via Ollama) and returns structured feedback: Critical Security Issues, Security Hardening, Suggestions, Strengths, Missing Security Controls, and a Security Risk Score.

**If the script fails** (Ollama not running, model not available): Log the failure and proceed to Phase 4. Local reviews are valuable but not blocking.

**After Review 0B**: Read the security feedback. Revise the plan to address critical security vulnerabilities, add missing security controls, and harden the design. Save as `DRAFTS_DIRECTORY/<plan-name>-draft-3.md`.

### Phase 4: Review 1A — Codex Architecture Review (Headless)

Run the Codex review script via Bash to get cross-model architecture feedback. This is a **headless API call** — no sub-agent, no interactive session.

```typescript
Bash({
  command: "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/utils/llm/codex_review.py $CLAUDE_PROJECT_DIR/DRAFTS_DIRECTORY/<plan-name>-draft-3.md --review-type architecture",
  description: "Codex architecture review of locally-reviewed draft"
})
```

The script calls GPT-5.3-codex and returns structured feedback: Critical Issues, Improvements, Suggestions, Strengths, and Revised Recommendations.

**If the script fails** (missing API key, network error): Log the failure and proceed to Phase 5. Cross-model reviews are valuable but not blocking — the 3 Claude reviews still provide thorough coverage.

**After Review 1A**: Read the Codex feedback. Revise the plan to address ALL critical issues and incorporate practical improvements. Save as `DRAFTS_DIRECTORY/<plan-name>-draft-4.md`.

### Phase 5: Review 1C — Gemini Architecture Review (Headless)

Run the Gemini review script via Bash to get a second cross-model architecture perspective. Like Review 1A, this is a **headless API call**.

```typescript
Bash({
  command: "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/utils/llm/gemini_review.py $CLAUDE_PROJECT_DIR/DRAFTS_DIRECTORY/<plan-name>-draft-4.md --review-type architecture",
  description: "Gemini architecture review of Codex-revised draft"
})
```

The script calls Gemini 3 and returns the same structured feedback format as the Codex review. Having two different cross-model perspectives (Codex + Gemini) before the Claude reviews maximizes blind spot coverage.

**If the script fails** (missing API key, network error): Log the failure and proceed to Phase 6. Cross-model reviews are valuable but not blocking.

**After Review 1C**: Read the Gemini feedback. Revise the plan to incorporate findings not already addressed by previous reviews. Save as `DRAFTS_DIRECTORY/<plan-name>-draft-5.md`.

### Phase 6: Review 1B — Claude Architecture Review

Deploy a Claude reviewer agent to critique the multi-reviewed draft. This reviewer sees the revised plan AND all prior review outputs, providing a same-model architecture perspective:

```typescript
Task({
  description: "Review #1B: Claude architecture review",
  prompt: `
You are a senior software architect conducting an architecture review of an implementation plan.

## The Plan (Revision 5 — already revised after Kimi simplicity, Ollama security, Codex + Gemini architecture reviews)
<paste full contents of draft-5.md>

## Previous Reviews
### Review 0A (Kimi Simplicity): <paste Kimi review output from Phase 2>
### Review 0B (Ollama Security): <paste Ollama security review output from Phase 3>
### Review 1A (Codex): <paste Codex review output from Phase 4>
### Review 1C (Gemini): <paste Gemini review output from Phase 5>

## Your Review Focus: ARCHITECTURE & COMPLETENESS

Evaluate the plan against these criteria:

1. **Solution Approach**
   - Does the architecture make sense for the problem?
   - Are there simpler approaches that were overlooked?
   - Will this scale if requirements grow?

2. **Component Design**
   - Are responsibilities cleanly separated?
   - Are there missing components or layers?
   - Do the interfaces between components make sense?

3. **Technology Choices**
   - Is the tech stack appropriate?
   - Are there unnecessary dependencies?
   - Are there better-suited tools or patterns?

4. **Completeness**
   - What scenarios are missing?
   - What happens when things go wrong?
   - Are there security considerations not addressed?

## Output Format

Respond with EXACTLY this structure:

### Critical Issues (MUST fix before build)
- [issue]: [why it matters] → [specific recommendation]

### Improvements (SHOULD fix)
- [issue]: [impact] → [recommendation]

### Suggestions (NICE to have)
- [idea]: [benefit]

### Strengths (DO NOT change)
- [what's good about the current plan]

### Revised Recommendations
If you could rewrite the Task Description, Objective, or Solution Approach sections, what would you change? Be specific.
  `,
  subagent_type: "general-purpose",
  model: "opus",
  run_in_background: false
})
```

**After Review 1B**: Read the feedback. Revise the plan to address ALL critical issues and as many improvements as practical. Save as `DRAFTS_DIRECTORY/<plan-name>-draft-6.md`.

### Phase 7: Review Cycle 2 — Implementation Feasibility Review

Deploy a second reviewer with the revised draft + all prior review feedback:

```typescript
Task({
  description: "Review #2: Implementation feasibility",
  prompt: `
You are a senior engineer conducting an implementation feasibility review.

## The Plan (Revision 6 — already revised after Kimi simplicity, Ollama security, Codex, Gemini, and Claude architecture reviews)
<paste full contents of draft-6.md>

## Previous Review Feedback
### Review #0A (Kimi Simplicity): <paste Kimi review output>
### Review #0B (Ollama Security): <paste Ollama security review output>
### Review #1A (Codex Architecture): <paste Codex review output>
### Review #1C (Gemini Architecture): <paste Gemini review output>
### Review #1B (Claude Architecture): <paste Review 1B output>

## Your Review Focus: IMPLEMENTATION FEASIBILITY & EDGE CASES

Evaluate whether this plan can actually be BUILT successfully:

1. **Task Decomposition**
   - Is each task the right size? (Not too big, not too small)
   - Can a single worker complete each task without needing context from other tasks?
   - Are there hidden dependencies not captured in "Depends On"?

2. **Step-by-Step Accuracy**
   - For each task: could a developer follow these steps and produce working code?
   - Are file paths correct and consistent?
   - Are function signatures, type definitions, and interfaces specified clearly enough?

3. **Edge Cases & Error Handling**
   - What inputs could break this?
   - What happens during concurrent access, empty state, or corrupt data?
   - Are error messages user-friendly?

4. **Worker Context**
   - Does each worker have enough context in their task description to work independently?
   - Are there implicit assumptions that should be explicit?
   - Would a worker need to read files not listed in their task?

5. **Parallel Opportunities**
   - Are there tasks marked sequential that could safely run in parallel?
   - Are there tasks marked parallel that actually have hidden dependencies?

## Output Format

### Critical Issues (MUST fix)
- [task ID]: [issue] → [specific fix]

### Implementation Gaps
- [gap]: [what's missing] → [what to add]

### Edge Cases to Handle
- [scenario]: [what happens] → [how to handle it]

### Task Adjustments
- [task ID]: [current problem] → [revised approach]

### Parallel Optimization
- [which tasks could be parallelized or must be sequential]
  `,
  subagent_type: "general-purpose",
  model: "opus",
  run_in_background: false
})
```

**After Review 2**: Read the feedback. Revise to address critical issues, fill implementation gaps, add missing edge cases. Save as `DRAFTS_DIRECTORY/<plan-name>-draft-7.md`.

### Phase 8: Review Cycle 3 — Quality Gate

Deploy a final reviewer with the polished draft + all prior feedback:

```typescript
Task({
  description: "Review #3: Quality gate",
  prompt: `
You are a QA lead conducting a final quality gate review before this plan goes to build.

## The Plan (Revision 7 — already passed Kimi simplicity, Ollama security, Codex, Gemini, Claude architecture, and implementation reviews)
<paste full contents of draft-7.md>

## Previous Reviews
### Review #0A (Kimi Simplicity): <paste summary of Kimi review findings>
### Review #0B (Ollama Security): <paste summary of Ollama security review findings>
### Review #1A (Codex Architecture): <paste summary of Codex review findings>
### Review #1C (Gemini Architecture): <paste summary of Gemini review findings>
### Review #1B (Claude Architecture): <paste summary of Review 1B findings>
### Review #2 (Implementation): <paste summary of Review 2 findings>

## Your Review Focus: QUALITY GATE — IS THIS PLAN BUILD-READY?

This is the FINAL check. Be ruthless. If this plan ships with problems, real time and money are wasted.

1. **Acceptance Criteria Quality**
   - Is every criterion specific and measurable? (No vague "works correctly")
   - Can each criterion be verified with a single command or check?
   - Are there missing criteria that should exist?
   - Could someone unfamiliar with the project verify these?

2. **Validation Commands**
   - Will each command actually work? (correct paths, flags, syntax)
   - Do the commands cover ALL acceptance criteria?
   - Are there validation gaps — criteria without corresponding commands?

3. **Team Orchestration**
   - Are worker assignments optimal? (right agent type for each task)
   - Is the dependency graph correct? (no cycles, no missing edges)
   - Could the build complete in fewer steps with better parallelization?

4. **Plan Clarity**
   - Could a developer with NO context follow this plan end-to-end?
   - Are there ambiguous instructions that could be interpreted multiple ways?
   - Is anything assumed but not stated?

5. **Risk Assessment**
   - What is the single most likely failure point?
   - What would cause a build to fail at step N and need to restart?
   - Are there mitigation strategies for the top risks?

## Output Format

### VERDICT: PASS / CONDITIONAL PASS / FAIL

### Blocking Issues (if FAIL or CONDITIONAL)
- [issue]: [why it blocks] → [fix required]

### Final Adjustments (for CONDITIONAL PASS)
- [adjustment needed]

### Risk Register
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ... | High/Med/Low | High/Med/Low | ... |

### Confidence Score: [1-10]
[Explanation of score — what would make it a 10?]
  `,
  subagent_type: "general-purpose",
  model: "opus",
  run_in_background: false
})
```

**After Review 3**: Incorporate final adjustments. If FAIL verdict, address all blocking issues and consider re-running the quality gate. Save final plan to `PLAN_OUTPUT_DIRECTORY/<plan-name>.md`.

### Phase 9: Finalize

1. Incorporate Review 3 feedback into the final plan
2. Add the `## Review History` section (see Plan Format below)
3. Save final plan to `PLAN_OUTPUT_DIRECTORY/<plan-name>.md`
4. Present the Report

---

## Plan Format

Follow this EXACT format. Replace `<requested content>` with actual content. Everything NOT in angle brackets should be written exactly as shown.

```md
# Plan: <task name>

## Task Description
<describe the task in detail based on the prompt>

## Objective
<clearly state what will be accomplished when this plan is complete>

<if task_type is feature or complexity is medium/complex:>
## Problem Statement
<clearly define the specific problem or opportunity>

## Solution Approach
<describe the proposed solution and how it addresses the objective>
</if>

## Relevant Files
Use these files to complete the task:

<list files with bullet points explaining why. Include new files under an h3 'New Files' section if needed>

<if complexity is medium/complex:>
## Implementation Phases
### Phase 1: Foundation
<foundational work needed>

### Phase 2: Core Implementation
<main implementation work>

### Phase 3: Integration & Polish
<integration, testing, final touches>
</if>

## Team Orchestration

- You operate as the team lead and orchestrate the team to execute the plan.
- You NEVER operate directly on the codebase. You use Task and Task* tools.

### Team Members
<list each team member with Name, Role, Agent Type, Resume fields>

## Step by Step Tasks

<list tasks as h3 headers with Task ID, Depends On, Assigned To, Agent Type, Parallel, and specific actions>

### N. Final Validation
- **Task ID**: validate-all
- **Depends On**: <all previous Task IDs>
- **Assigned To**: <validator team member>
- **Agent Type**: validator
- **Parallel**: false
- Run all validation commands
- Verify acceptance criteria met

## Acceptance Criteria
<specific, measurable criteria — each must be verifiable with a single command or check>

## Validation Commands
<specific commands to validate the work>

## Review History

This plan was refined through 7 review cycles (2 local + 2 cross-model + 3 Claude) before finalization.

### Review #0A: Kimi Simplicity Review (Local)
- **Model**: Kimi 2.5 (local via Ollama)
- **Reviewer Focus**: Simplicity, ease of use, over-engineering, dependency minimalism
- **Critical Complexity Found**: <count>
- **Key Changes Made**: <brief summary of what was simplified>

### Review #0B: Ollama Security Review (Local)
- **Model**: llama3.2:3b (local via Ollama)
- **Reviewer Focus**: Security vulnerabilities, auth, input validation, data protection
- **Critical Security Issues Found**: <count>
- **Key Changes Made**: <brief summary of security hardening>

### Review #1A: Codex Architecture Review (Cross-Model)
- **Model**: GPT-5.3-codex (codex-mini-latest)
- **Reviewer Focus**: Architecture blind spots, solution approach, completeness
- **Critical Issues Found**: <count>
- **Key Changes Made**: <brief summary of what was revised>

### Review #1C: Gemini Architecture Review (Cross-Model)
- **Model**: gemini-3.0-flash
- **Reviewer Focus**: Architecture blind spots, second cross-model perspective
- **Critical Issues Found**: <count>
- **Key Changes Made**: <brief summary of what was revised>

### Review #1B: Claude Architecture Review
- **Reviewer Focus**: Solution approach, component design, technology choices
- **Critical Issues Found**: <count>
- **Key Changes Made**: <brief summary of what was revised>

### Review #2: Implementation Feasibility
- **Reviewer Focus**: Task decomposition, edge cases, worker context
- **Critical Issues Found**: <count>
- **Key Changes Made**: <brief summary>

### Review #3: Quality Gate
- **Verdict**: <PASS / CONDITIONAL PASS>
- **Confidence Score**: <1-10>
- **Final Adjustments**: <brief summary>
- **Top Risk**: <single biggest risk and its mitigation>

### Draft History
- Draft 1: `specs/drafts/<name>-draft-1.md` (initial)
- Draft 2: `specs/drafts/<name>-draft-2.md` (post Kimi simplicity review)
- Draft 3: `specs/drafts/<name>-draft-3.md` (post Ollama security review)
- Draft 4: `specs/drafts/<name>-draft-4.md` (post Codex review)
- Draft 5: `specs/drafts/<name>-draft-5.md` (post Gemini review)
- Draft 6: `specs/drafts/<name>-draft-6.md` (post Claude architecture review)
- Draft 7: `specs/drafts/<name>-draft-7.md` (post implementation review)
- Final: `specs/<name>.md` (post quality gate)

## Notes
<optional additional context, dependencies, or considerations>
```

---

## Instructions

- **PLANNING ONLY**: Do NOT build, write code, or deploy builders. Your only output is a plan document.
- If no `USER_PROMPT` is provided, stop and ask the user.
- If `ORCHESTRATION_PROMPT` is provided, use it to guide team composition and task structure.
- Explore the codebase DIRECTLY (Read, Glob, Grep) — no sub-agents for exploration.
- Run ALL 7 review cycles (0A Kimi + 0B Ollama + 1A Codex + 1C Gemini + 1B/2/3 Claude). Do not skip reviews even if the plan "looks good."
- Reviews 0A (Kimi) and 0B (Ollama) run via Bash as local Ollama calls. Reviews 1A (Codex) and 1C (Gemini) run via Bash as headless API calls. Reviews 1B, 2, and 3 are SEPARATE Task deployments (fresh context, no carry-over bias).
- If a local or cross-model review script fails (Ollama not running, missing API key, network error), log the failure and proceed to the next phase. Local and cross-model reviews are valuable but not blocking — the 3 Claude reviews still provide thorough coverage.
- Preserve all 7 drafts in `DRAFTS_DIRECTORY` for auditability.
- The final plan must include the `## Review History` section.
- Generate a descriptive, kebab-case filename for the plan.

---

## Report

After creating and saving the final plan:

```
Plan Created (7x Reviewed — 2 Local + 2 Cross-Model + 3 Claude)

File: specs/<filename>.md
Drafts: specs/drafts/<name>-draft-{1,2,3,4,5,6,7}.md

Review Summary:
- Review 0A (Kimi Simplicity): <N> complexity issues found and simplified
- Review 0B (Ollama Security): <N> security issues found and hardened
- Review 1A (Codex Architecture): <N> critical issues found and resolved
- Review 1C (Gemini Architecture): <N> critical issues found and resolved
- Review 1B (Claude Architecture): <N> critical issues found and resolved
- Review 2 (Implementation): <N> critical issues, <N> edge cases added
- Review 3 (Quality Gate): <VERDICT>, confidence <X>/10

Tasks: <N> total
<list tasks and owners>

Team: <list members and roles>

When ready to build:
/build specs/<filename>.md
```
