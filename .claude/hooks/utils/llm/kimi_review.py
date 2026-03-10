#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "openai",
#     "python-dotenv",
# ]
# ///

"""
Headless plan reviewer (local via Ollama).

Sends a plan file to a local Ollama model for simplicity and ease-of-use
review. Returns structured feedback without requiring an interactive session.

Prerequisites:
    ollama pull qwen3:4b       # Or set KIMI_MODEL env var to your model name

Usage:
    uv run kimi_review.py <plan-file-path> [--review-type simplicity|architecture|implementation|quality]
    uv run kimi_review.py specs/drafts/my-plan-draft-1.md --review-type simplicity
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

REVIEW_PROMPTS = {
    "simplicity": """You are a senior developer advocate conducting a simplicity and ease-of-use review of an implementation plan.

## Your Review Focus: SIMPLICITY & EASE OF USE

Your mission is to find unnecessary complexity. Every line in a plan should earn its place. Evaluate against these criteria:

1. **Over-Engineering**
   - Are there abstractions that don't yet need to exist? (YAGNI violations)
   - Are there patterns introduced for "future flexibility" that add complexity now?
   - Could any component be replaced with a simpler stdlib/built-in alternative?
   - Are there unnecessary wrapper layers, facades, or indirection?

2. **Developer Experience**
   - How many steps to go from clone to running? (Fewer = better)
   - How many env vars / config values are required vs optional?
   - Could a junior developer follow this plan without external help?
   - Are error messages clear enough to self-diagnose issues?

3. **Dependency Minimalism**
   - Is every dependency justified? Could any be eliminated?
   - Are there lightweight alternatives to heavy libraries?
   - Could any functionality be implemented in <20 lines instead of adding a dep?

4. **API Surface Simplicity**
   - Are there too many exported functions/types? (Minimal public API = easier to use)
   - Could any interfaces be combined or simplified?
   - Are naming conventions consistent and self-documenting?

5. **Configuration Complexity**
   - Are there too many config files? Could any be merged or eliminated?
   - Are defaults sensible so most users need zero configuration?
   - Is the distinction between required and optional config clear?

## Output Format

Respond with EXACTLY this structure:

### Critical Complexity (MUST simplify before build)
- [what's over-engineered]: [why it's too complex] → [simpler alternative]

### Simplification Opportunities (SHOULD simplify)
- [current approach]: [complexity cost] → [simpler approach]

### Dependency Review
- [dependency]: [KEEP — justified because...] or [REMOVE — replace with...]

### Developer Experience Issues
- [pain point]: [impact on developers] → [how to improve]

### Strengths (Already Simple — DO NOT complicate)
- [what's appropriately simple in the current plan]

### Simplicity Score: [1-10]
[1 = over-engineered nightmare, 10 = elegantly minimal]
[What would make it a 10?]""",

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
}


def review_plan(plan_path: str, review_type: str = "simplicity") -> str | None:
    """
    Send a plan to Kimi 2.5 (via Ollama) for review.

    Args:
        plan_path: Path to the plan markdown file
        review_type: One of 'simplicity', 'architecture'

    Returns:
        str: The review feedback, or None if error
    """
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("KIMI_MODEL", "qwen3:4b")

    if not os.path.exists(plan_path):
        print(f"Error: Plan file not found: {plan_path}", file=sys.stderr)
        return None

    with open(plan_path, "r", encoding="utf-8") as f:
        plan_content = f.read()

    review_prompt = REVIEW_PROMPTS.get(review_type)
    if not review_prompt:
        print(f"Error: Unknown review type: {review_type}", file=sys.stderr)
        print(f"Available types: {', '.join(REVIEW_PROMPTS.keys())}", file=sys.stderr)
        return None

    full_prompt = f"""{review_prompt}

## The Plan to Review

{plan_content}

---

Provide your review now. Be specific, actionable, and reference exact sections/task IDs from the plan."""

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=f"{ollama_host}/v1",
            api_key="ollama",  # required but unused
        )

        print(f"Calling Kimi 2.5 ({model}) via Ollama for {review_type} review...", file=sys.stderr)

        start_time = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior software engineer conducting a thorough plan review focused on simplicity and developer experience. Be specific, actionable, and critical. Reference exact sections and task IDs. Prefer the simplest solution that works.",
                },
                {"role": "user", "content": full_prompt},
            ],
            max_tokens=4096,
            temperature=0.3,
        )

        review_text = response.choices[0].message.content.strip()

        duration_ms = int((time.time() - start_time) * 1000)

        result = f"""## Kimi Review ({review_type.title()})
**Model**: {model} (local via Ollama)
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
                "review_id": "0A",
                "model_name": model,
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
        print(f"Error calling Kimi via Ollama: {e}", file=sys.stderr)
        print(f"Ensure Ollama is running and model '{model}' is available:", file=sys.stderr)
        print("  ollama serve", file=sys.stderr)
        print(f"  ollama pull {model}", file=sys.stderr)
        return None


def main():
    """CLI interface for plan review."""
    if len(sys.argv) < 2:
        print(
            "Usage: uv run kimi_review.py <plan-file-path> [--review-type simplicity|architecture]"
        )
        print(
            "       uv run kimi_review.py specs/drafts/my-plan-draft-1.md --review-type simplicity"
        )
        print()
        print("Environment variables:")
        print("  KIMI_MODEL    — Ollama model name (default: qwen3:4b)")
        print("  OLLAMA_HOST   — Ollama API URL (default: http://localhost:11434)")
        sys.exit(1)

    plan_path = sys.argv[1]
    review_type = "simplicity"  # default

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
