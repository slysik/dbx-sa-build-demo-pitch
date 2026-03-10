#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "google-genai",
#     "python-dotenv",
# ]
# ///

"""
Headless Gemini plan reviewer.

Sends a plan file to Gemini 3 for senior architecture review.
Returns structured feedback without requiring an interactive session.

Usage:
    uv run gemini_review.py <plan-file-path> [--review-type architecture|implementation|quality]
    uv run gemini_review.py specs/drafts/my-plan-draft-2.md --review-type architecture
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

REVIEW_PROMPTS = {
    "architecture": """You are a senior software architect conducting an architecture review of an implementation plan.

## Your Review Focus: ARCHITECTURE & COMPLETENESS

Evaluate the plan against these criteria:

1. **Solution Approach** — Does the architecture make sense? Are there simpler approaches overlooked? Will this scale?
2. **Component Design** — Are responsibilities cleanly separated? Missing components or layers? Do interfaces make sense?
3. **Technology Choices** — Is the tech stack appropriate? Unnecessary dependencies? Better-suited tools?
4. **Completeness** — Missing scenarios? What happens when things go wrong? Security considerations?

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
If you could rewrite the Task Description, Objective, or Solution Approach sections, what would you change? Be specific.""",

    "implementation": """You are a senior engineer conducting an implementation feasibility review.

## Your Review Focus: IMPLEMENTATION FEASIBILITY & EDGE CASES

Evaluate whether this plan can actually be BUILT successfully:

1. **Task Decomposition** — Right size? Can each worker complete independently? Hidden dependencies?
2. **Step-by-Step Accuracy** — Could a developer follow these steps? File paths correct? Signatures specified?
3. **Edge Cases** — What inputs could break this? Concurrent access? Empty state? Corrupt data?
4. **Worker Context** — Does each worker have enough context? Implicit assumptions?
5. **Parallel Opportunities** — Sequential tasks that could be parallel? Parallel tasks with hidden deps?

## Output Format

### Critical Issues (MUST fix)
- [task ID]: [issue] → [specific fix]

### Implementation Gaps
- [gap]: [what's missing] → [what to add]

### Edge Cases to Handle
- [scenario]: [what happens] → [how to handle it]

### Task Adjustments
- [task ID]: [current problem] → [revised approach]""",

    "quality": """You are a QA lead conducting a final quality gate review.

## Your Review Focus: IS THIS PLAN BUILD-READY?

1. **Acceptance Criteria** — Specific and measurable? Verifiable with a single command? Missing criteria?
2. **Validation Commands** — Will each command work? Cover all criteria? Any gaps?
3. **Team Orchestration** — Optimal assignments? Correct dependency graph? Better parallelization?
4. **Clarity** — Could a developer with no context follow this? Ambiguous instructions?
5. **Risk** — Most likely failure point? What causes restart? Mitigation strategies?

## Output Format

### VERDICT: PASS / CONDITIONAL PASS / FAIL

### Blocking Issues (if FAIL or CONDITIONAL)
- [issue]: [why it blocks] → [fix required]

### Risk Register
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|

### Confidence Score: [1-10]
[Explanation]"""
}


def review_plan(plan_path: str, review_type: str = "architecture") -> str | None:
    """
    Send a plan to Gemini 3 for review.

    Args:
        plan_path: Path to the plan markdown file
        review_type: One of 'architecture', 'implementation', 'quality'

    Returns:
        str: The review feedback, or None if error
    """
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY or GEMINI_API_KEY not set", file=sys.stderr)
        return None

    if not os.path.exists(plan_path):
        print(f"Error: Plan file not found: {plan_path}", file=sys.stderr)
        return None

    with open(plan_path, "r", encoding="utf-8") as f:
        plan_content = f.read()

    review_prompt = REVIEW_PROMPTS.get(review_type)
    if not review_prompt:
        print(f"Error: Unknown review type: {review_type}", file=sys.stderr)
        return None

    full_prompt = f"""{review_prompt}

## The Plan to Review

{plan_content}

---

Provide your review now. Be specific, actionable, and reference exact sections/task IDs from the plan."""

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        start_time = time.time()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction="You are a senior software engineer conducting a thorough plan review. Be specific, actionable, and critical. Reference exact sections and task IDs.",
                max_output_tokens=16384,
                temperature=0.3,
            ),
        )

        review_text = response.text.strip()

        duration_ms = int((time.time() - start_time) * 1000)

        # Include metadata
        result = f"""## Gemini Review ({review_type.title()})
**Model**: gemini-2.5-flash
**Review Type**: {review_type}
**Plan File**: {plan_path}

---

{review_text}"""

        # Log telemetry
        try:
            project_dir = os.getenv("CLAUDE_PROJECT_DIR", ".")
            telemetry_path = os.path.join(project_dir, "logs", "review_telemetry.jsonl")
            os.makedirs(os.path.dirname(telemetry_path), exist_ok=True)
            telemetry_entry = {
                "plan_id": os.path.basename(plan_path).replace(".md", ""),
                "review_id": "1C",
                "model_name": "gemini-2.5-flash",
                "review_type": review_type,
                "duration_ms": duration_ms,
                "raw_markdown": review_text,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            with open(telemetry_path, "a", encoding="utf-8") as tf:
                tf.write(json.dumps(telemetry_entry) + "\n")
        except Exception as te:
            print(f"Warning: Failed to write telemetry: {te}", file=sys.stderr)

        return result

    except Exception as e:
        print(f"Error calling Gemini API: {e}", file=sys.stderr)
        return None


def main():
    """CLI interface for plan review."""
    if len(sys.argv) < 2:
        print(
            "Usage: uv run gemini_review.py <plan-file-path> [--review-type architecture|implementation|quality]"
        )
        print(
            "       uv run gemini_review.py specs/drafts/my-plan-draft-2.md --review-type architecture"
        )
        sys.exit(1)

    plan_path = sys.argv[1]
    review_type = "architecture"  # default

    if "--review-type" in sys.argv:
        idx = sys.argv.index("--review-type")
        if idx + 1 < len(sys.argv):
            review_type = sys.argv[idx + 1]

    result = review_plan(plan_path, review_type)
    if result:
        print(result)
    else:
        print("Review failed. Check stderr for details.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
