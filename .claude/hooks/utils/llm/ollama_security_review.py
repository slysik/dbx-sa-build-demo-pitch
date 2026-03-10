#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "openai",
#     "python-dotenv",
# ]
# ///

"""
Headless Ollama security review checker (local via Ollama).

Sends a plan file to a local Ollama model for security review.
Lightweight, fast, and free — catches obvious security gaps before
heavier cross-model reviews.

Usage:
    uv run ollama_security_review.py <plan-file-path> [--review-type security|architecture]
    uv run ollama_security_review.py specs/drafts/my-plan-draft-2.md --review-type security
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

REVIEW_PROMPTS = {
    "security": """You are a security engineer conducting a security review of an implementation plan.

## Your Review Focus: SECURITY VULNERABILITIES & HARDENING

Analyze the plan for security weaknesses. Even if a plan isn't security-focused, every app has an attack surface. Evaluate against these criteria:

1. **Authentication & Authorization**
   - Are API endpoints properly authenticated?
   - Is there authorization (who can do what) beyond just authentication (who are you)?
   - Are secrets (API keys, tokens) handled securely? (env vars, not hardcoded)
   - Are there endpoints that should require auth but don't?

2. **Input Validation & Injection**
   - Is user input validated and sanitized before use?
   - Are there SQL injection risks? (raw string interpolation in queries)
   - Are there XSS risks? (user content rendered without escaping)
   - Are there command injection risks? (user input in shell commands)
   - Is there path traversal risk? (user input in file paths)

3. **Data Protection**
   - Is sensitive data encrypted at rest? In transit?
   - Are there PII handling requirements not addressed?
   - Is there a data retention/deletion policy?
   - Are database connections using TLS?

4. **API Security**
   - Are rate limits in place for public-facing endpoints?
   - Are CORS headers configured correctly?
   - Is there protection against CSRF?
   - Are error messages leaking internal details? (stack traces, DB schema)

5. **Dependency & Supply Chain**
   - Are dependencies pinned to specific versions?
   - Are there known-vulnerable packages?
   - Is there a plan for dependency updates/auditing?

6. **Infrastructure & Deployment**
   - Are environment variables documented but not committed?
   - Is there a .gitignore for sensitive files?
   - Are serverless function permissions scoped minimally?
   - Is logging configured to avoid capturing secrets?

## Output Format

Respond with EXACTLY this structure:

### Critical Security Issues (MUST fix — exploitable vulnerabilities)
- [vulnerability]: [attack scenario] → [specific fix]

### Security Hardening (SHOULD fix — defense in depth)
- [weakness]: [risk level] → [hardening recommendation]

### Security Suggestions (NICE to have)
- [improvement]: [what it prevents]

### Security Strengths (Already handled well)
- [what the plan does right from a security perspective]

### Missing Security Controls
- [control not mentioned in plan]: [why it matters] → [how to add it]

### Security Risk Score: [1-10]
[1 = critical vulnerabilities, 10 = well-hardened]
[What would make it a 10?]""",

    "architecture": """You are a security-focused architect reviewing a plan for architectural security concerns.

## Your Review Focus: SECURE ARCHITECTURE

1. **Trust Boundaries** — Where does trusted code meet untrusted input?
2. **Attack Surface** — What's exposed? What should be internal-only?
3. **Failure Modes** — Do failures default to secure states?
4. **Least Privilege** — Does each component have minimal required access?

## Output Format

### Critical Issues (MUST fix before build)
- [issue]: [security implication] → [specific recommendation]

### Improvements (SHOULD fix)
- [issue]: [risk] → [recommendation]

### Suggestions (NICE to have)
- [idea]: [security benefit]""",
}


def review_plan(plan_path: str, review_type: str = "security") -> str | None:
    """
    Send a plan to local Ollama 3B model for security review.

    Args:
        plan_path: Path to the plan markdown file
        review_type: One of 'security', 'architecture'

    Returns:
        str: The review feedback, or None if error
    """
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_SECURITY_MODEL", os.getenv("OLLAMA_MODEL", "qwen3:4b"))

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

Provide your security review now. Be specific about attack vectors and reference exact sections/task IDs from the plan."""

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=f"{ollama_host}/v1",
            api_key="ollama",  # required but unused
        )

        print(f"Calling {model} via Ollama for {review_type} review...", file=sys.stderr)

        start_time = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a security engineer conducting a thorough security review of a software implementation plan. Focus on exploitable vulnerabilities, missing security controls, and hardening opportunities. Be specific and reference exact sections.",
                },
                {"role": "user", "content": full_prompt},
            ],
            max_tokens=4096,
            temperature=0.2,  # Lower temp for more focused security analysis
        )

        review_text = response.choices[0].message.content.strip()

        duration_ms = int((time.time() - start_time) * 1000)

        result = f"""## Ollama Security Review ({review_type.title()})
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
                "review_id": "0B",
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
        print(f"Error calling Ollama: {e}", file=sys.stderr)
        print(f"Ensure Ollama is running and model '{model}' is available:", file=sys.stderr)
        print("  ollama serve", file=sys.stderr)
        print(f"  ollama pull {model}", file=sys.stderr)
        return None


def main():
    """CLI interface for security review."""
    if len(sys.argv) < 2:
        print(
            "Usage: uv run ollama_security_review.py <plan-file-path> [--review-type security|architecture]"
        )
        print(
            "       uv run ollama_security_review.py specs/drafts/my-plan-draft-2.md --review-type security"
        )
        print()
        print("Environment variables:")
        print("  OLLAMA_SECURITY_MODEL — Model name (default: qwen3:4b)")
        print("  OLLAMA_HOST           — Ollama API URL (default: http://localhost:11434)")
        sys.exit(1)

    plan_path = sys.argv[1]
    review_type = "security"  # default

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
