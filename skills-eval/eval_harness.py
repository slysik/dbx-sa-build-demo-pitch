#!/usr/bin/env python3
"""
skills-eval/eval_harness.py — FIXED. Do not modify.

Analogous to prepare.py in karpathy/autoresearch.
Scores a Databricks skill's SKILL.md against fixed test prompts.
Metric: FTS (First-Try Score, 0–10 per prompt, mean across 5 prompts).

Usage:
    python skills-eval/eval_harness.py <skill-name>
    python skills-eval/eval_harness.py --baseline-all
    python skills-eval/eval_harness.py spark-declarative-pipelines
"""

import sys
import json
import subprocess
import os
import re
import time
from pathlib import Path
from datetime import datetime

# ── Fixed paths (never change) ─────────────────────────────────────────────────
ROOT         = Path(__file__).parent.parent
SKILLS_DIR   = ROOT / ".agents" / "skills"
PI_SKILLS    = ROOT / ".pi" / "skills"
PROMPTS_DIR  = Path(__file__).parent / "prompts"
RESULTS_DIR  = Path(__file__).parent / "results"

# ── Fixed scoring rubric (never change) ────────────────────────────────────────
RUBRIC = {
    "correct_imports": {
        "points": 1,
        "desc": "Uses the correct imports for the domain (pyspark.sql.functions, etc.)"
    },
    "no_antipatterns": {
        "points": 2,
        "desc": "Avoids: collect() on large data, SELECT *, Faker/Pandas loops for scale, hardcoded secrets, schema inference in Silver/Gold"
    },
    "pattern_adherence": {
        "points": 3,
        "desc": "Uses the core pattern the skill teaches (e.g. spark.range() for Bronze, CREATE MATERIALIZED VIEW for SDP, widget version numbers for Dashboard)"
    },
    "completeness": {
        "points": 2,
        "desc": "Covers all aspects of the prompt — doesn't silently skip required elements"
    },
    "first_try_runnable": {
        "points": 2,
        "desc": "Code would execute without modification — correct syntax, no undefined variables, UC 3-level namespace used"
    },
}
MAX_SCORE = sum(v["points"] for v in RUBRIC.values())  # 10

# ── Anti-pattern signatures (auto-deducted from no_antipatterns) ───────────────
ANTIPATTERNS = [
    (r"\.collect\(\)",              "uses .collect() — forbidden on non-trivial data"),
    (r"SELECT \*",                  "uses SELECT * — forbidden in Silver/Gold"),
    (r"from faker import",          "imports Faker — use spark.range() for scale generation"),
    (r"os\.environ\.get\([^)]+,\s*['\"][^'\"]{4,}", "hardcoded secret fallback in os.environ.get()"),
    (r"toPandas\(\)",               "uses toPandas() on potentially large data"),
    (r"\.repartition\(\d+\)",       "uses repartition() to reduce — use coalesce()"),
]

# ── Skill → expected patterns (for pattern_adherence scoring) ──────────────────
REQUIRED_PATTERNS = {
    "spark-declarative-pipelines": [
        r"CREATE OR REFRESH (STREAMING TABLE|MATERIALIZED VIEW)",
        r"serverless.*true|serverless: true",
        r"EXPECT|WHERE \w+ IS NOT NULL",
    ],
    "databricks-aibi-dashboards": [
        r'"version":\s*[23]',
        r'embed_credentials.*false|embed_credentials: false',
        r"parent_path",
    ],
    "synthetic-data-generation": [
        r"spark\.range\(|RANGE\(",
        r"withColumn|F\.",
        r"saveAsTable|write\.format",
    ],
    "databricks-genie": [
        r"serialized_space|genie/spaces",
        r"table_identifiers",
        r"sample_questions",
    ],
    "databricks-bundles": [
        r"databricks\.yml|bundle:",
        r"targets:",
        r"pipelines:|jobs:",
    ],
    "spark-native-bronze": [
        r"spark\.range\(",
        r"F\.broadcast\(|broadcast\(",
        r"ingest_ts|source_system|batch_id",
    ],
    "model-serving": [
        r"mlflow\.pyfunc|ChatAgent|ResponsesAgent",
        r"served_entities|served_models",
        r"endpoint_name|serving_endpoint",
    ],
    "databricks-vector-search": [
        r"VectorSearchClient|vector_search",
        r"create_delta_sync_index|create_direct_vector_access_index",
        r"similarity_search",
    ],
}


def load_skill(skill_name: str) -> tuple[str, int]:
    """Load SKILL.md content. Returns (content, byte_count)."""
    # Try .agents/skills first, then .pi/skills
    candidates = [
        SKILLS_DIR / skill_name / "SKILL.md",
        PI_SKILLS / skill_name / "SKILL.md",
    ]
    for path in candidates:
        if path.exists():
            content = path.read_text()
            return content, len(content.encode())
    raise FileNotFoundError(f"SKILL.md not found for: {skill_name}")


def load_prompts(skill_name: str) -> list[dict]:
    """Load test prompts for a skill."""
    prompts_file = PROMPTS_DIR / f"{skill_name}.md"
    if not prompts_file.exists():
        raise FileNotFoundError(f"No prompts file: {prompts_file}")

    content = prompts_file.read_text()
    prompts = []
    # Parse ## Prompt N: <title> blocks
    blocks = re.split(r"^## Prompt \d+", content, flags=re.MULTILINE)
    for block in blocks[1:]:  # skip header
        lines = block.strip().split("\n")
        title = lines[0].strip(": \t") if lines else "untitled"
        # Extract the question (lines after the title, before EXPECT:)
        question_lines = []
        expect_lines = []
        in_expect = False
        for line in lines[1:]:
            if line.startswith("**EXPECT:**"):
                in_expect = True
                continue
            if in_expect:
                expect_lines.append(line)
            else:
                question_lines.append(line)
        prompts.append({
            "title": title,
            "question": "\n".join(question_lines).strip(),
            "expect": "\n".join(expect_lines).strip(),
        })
    return prompts


def score_output(output: str, skill_name: str, expect: str) -> dict[str, float]:
    """
    Score generated code output against the fixed rubric.
    Returns dict of {criterion: score} and total.
    This function is the eval harness equivalent of evaluate_bpb() in autoresearch.
    NEVER MODIFY THIS FUNCTION.
    """
    scores = {}

    # 1. correct_imports (1 pt) — heuristic: code has at least one import
    has_import = bool(re.search(r"^import |^from ", output, re.MULTILINE))
    has_code   = bool(re.search(r"def |CREATE |SELECT |spark\.", output, re.IGNORECASE))
    scores["correct_imports"] = 1.0 if (has_import or has_code) else 0.0

    # 2. no_antipatterns (2 pts) — deduct per violation, min 0
    violations = []
    for pattern, label in ANTIPATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            violations.append(label)
    deduction = min(2.0, len(violations) * 0.67)
    scores["no_antipatterns"] = max(0.0, 2.0 - deduction)

    # 3. pattern_adherence (3 pts) — skill-specific required patterns
    required = REQUIRED_PATTERNS.get(skill_name, [])
    if required:
        matches = sum(1 for p in required if re.search(p, output, re.IGNORECASE))
        scores["pattern_adherence"] = round(3.0 * (matches / len(required)), 2)
    else:
        scores["pattern_adherence"] = 1.5  # neutral if no patterns defined for skill

    # 4. completeness (2 pts) — does output address all EXPECT: keywords?
    expect_keywords = [w.strip().lower() for w in expect.split(",") if w.strip()]
    if expect_keywords:
        matched = sum(1 for kw in expect_keywords if kw.lower() in output.lower())
        scores["completeness"] = round(2.0 * (matched / len(expect_keywords)), 2)
    else:
        scores["completeness"] = 1.0  # neutral if no expect keywords defined

    # 5. first_try_runnable (2 pts) — structural checks
    runnable_checks = [
        bool(re.search(r"\w+\.\w+\.\w+", output)),           # UC 3-level namespace
        not bool(re.search(r"<your_\w+>|TODO|FIXME|YOUR_", output, re.IGNORECASE)),  # no placeholders
        not bool(re.search(r"SyntaxError|NameError|ModuleNotFoundError", output)),   # no error traces
    ]
    scores["first_try_runnable"] = round(2.0 * (sum(runnable_checks) / len(runnable_checks)), 2)

    total = sum(scores.values())
    scores["total"] = round(total, 2)
    scores["violations"] = violations
    return scores


def run_eval(skill_name: str, verbose: bool = True) -> dict:
    """
    Main eval function. Loads skill + prompts, generates output via LLM judge,
    scores each output, returns aggregate FTS.

    NOTE: In the current implementation, output generation is done by reading
    the skill and having the agent self-evaluate against each prompt using the
    LLM judge approach (Databricks ai_query or Claude API).
    For automated runs: set ANTHROPIC_API_KEY and this will call Claude directly.
    For manual runs: the agent reads the prompt, generates code, pastes it here.
    """
    skill_content, skill_bytes = load_skill(skill_name)
    prompts = load_prompts(skill_name)
    skill_tokens = skill_bytes // 4

    if verbose:
        model = os.environ.get("EVAL_MODEL", "claude-sonnet-4-6")
        print(f"\n{'='*60}")
        print(f"Evaluating: {skill_name}")
        print(f"Model: {model}")
        print(f"SKILL.md: {skill_bytes:,} bytes (~{skill_tokens:,} tokens)")
        print(f"Prompts: {len(prompts)}")
        print(f"{'='*60}")

    results = []
    for i, prompt in enumerate(prompts, 1):
        if verbose:
            print(f"\n[{i}/{len(prompts)}] {prompt['title']}")
            print(f"  Question: {prompt['question'][:100]}...")

        # ── Generation: use Claude API if key available, else prompt for manual input ──
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key:
            output = _generate_via_claude(skill_content, prompt["question"], api_key)
        else:
            print(f"\n  MANUAL MODE: Paste the generated code for this prompt, then press Enter twice:")
            lines = []
            while True:
                line = input()
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
            output = "\n".join(lines[:-1])  # drop trailing blank

        scores = score_output(output, skill_name, prompt["expect"])
        results.append({
            "prompt": prompt["title"],
            "scores": scores,
            "fts": scores["total"],
        })

        if verbose:
            print(f"  FTS: {scores['total']:.2f}/10")
            if scores["violations"]:
                print(f"  Anti-patterns: {', '.join(scores['violations'])}")

    fts_mean = round(sum(r["fts"] for r in results) / len(results), 2)
    model = os.environ.get("EVAL_MODEL", "claude-sonnet-4-6")

    if verbose:
        print(f"\n{'─'*40}")
        print(f"FTS: {fts_mean:.2f}/10  (mean across {len(results)} prompts)")
        print(f"Skill tokens: ~{skill_tokens:,}")
        print(f"Model: {model}")

    # Write last-run detail for the experiment loop
    last_run_path = RESULTS_DIR / f"{skill_name}-last-run.json"
    last_run_path.write_text(json.dumps({
        "skill": skill_name,
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "fts": fts_mean,
        "skill_tokens": skill_tokens,
        "prompts": results,
    }, indent=2))

    return {
        "fts": fts_mean,
        "skill_tokens": skill_tokens,
        "results": results,
    }


def _generate_via_claude(skill_content: str, question: str, api_key: str) -> str:
    """Call Claude API with skill as system context, question as user message.
    Model selection: EVAL_MODEL env var (default: claude-sonnet-4-6)
    """
    import urllib.request, urllib.error

    model = os.environ.get("EVAL_MODEL", "claude-sonnet-4-6")

    payload = json.dumps({
        "model": model,
        "max_tokens": 2048,
        "system": f"You are a Databricks expert. Use ONLY the following skill guidance to answer:\n\n{skill_content}",
        "messages": [{"role": "user", "content": question}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
            return data["content"][0]["text"]
    except Exception as e:
        print(f"  Claude API error: {e}")
        return ""


def log_result(skill_name: str, fts: float, skill_tokens: int,
               status: str, description: str) -> None:
    """Append a result row to the skill's TSV file."""
    tsv_path = RESULTS_DIR / f"{skill_name}.tsv"
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()

    header = "commit\tFTS\tskill_tokens\tstatus\tdescription\n"
    row = f"{commit}\t{fts:.2f}\t{skill_tokens}\t{status}\t{description}\n"

    if not tsv_path.exists():
        tsv_path.write_text(header + row)
    else:
        tsv_path.write_text(tsv_path.read_text() + row)

    print(f"\nLogged → {tsv_path.name}: {commit}  FTS={fts:.2f}  {status}  {description}")


def baseline_all() -> None:
    """Run baseline eval for all skills that have prompts defined."""
    print("Running baseline for all skills with prompts...")
    for prompts_file in sorted(PROMPTS_DIR.glob("*.md")):
        skill_name = prompts_file.stem
        try:
            result = run_eval(skill_name, verbose=False)
            log_result(skill_name, result["fts"], result["skill_tokens"],
                      "keep", "baseline")
            print(f"  {skill_name:<45} FTS={result['fts']:.2f}  tokens={result['skill_tokens']:,}")
        except Exception as e:
            print(f"  {skill_name:<45} ERROR: {e}")


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    RESULTS_DIR.mkdir(exist_ok=True)

    if len(sys.argv) < 2:
        print("Usage: python eval_harness.py <skill-name>")
        print("       python eval_harness.py --baseline-all")
        print("       python eval_harness.py --log <skill> <fts> <status> <description>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "--baseline-all":
        baseline_all()

    elif cmd == "--log":
        # python eval_harness.py --log spark-declarative-pipelines 7.40 keep "added ai_summarize gotcha"
        skill_name  = sys.argv[2]
        fts         = float(sys.argv[3])
        status      = sys.argv[4]
        description = sys.argv[5] if len(sys.argv) > 5 else "manual log"
        skill_content, skill_bytes = load_skill(skill_name)
        log_result(skill_name, fts, skill_bytes // 4, status, description)

    else:
        skill_name = cmd
        result = run_eval(skill_name, verbose=True)
        # Auto-log if this is a baseline (no existing TSV)
        tsv_path = RESULTS_DIR / f"{skill_name}.tsv"
        if not tsv_path.exists():
            log_result(skill_name, result["fts"], result["skill_tokens"],
                      "keep", "baseline")
        else:
            print(f"\nFTS: {result['fts']:.2f}  — run --log to record this result")
            print(f"  python skills-eval/eval_harness.py --log {skill_name} {result['fts']:.2f} keep|discard \"<description>\"")
