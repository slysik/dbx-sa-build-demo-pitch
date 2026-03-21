#!/usr/bin/env python3
"""
seed_data.py — Populate skills-eval/results/*.tsv with realistic synthetic history.

Simulates 3 weeks of optimization experiments across 5 skills.
Run once to get a populated dashboard. Real eval runs will append to these files.

Usage:
    python skills-eval/seed_data.py
    python skills-eval/seed_data.py --reset   # overwrite existing data
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

START_DATE = datetime(2026, 3, 1, 9, 0, 0)

# ── Synthetic experiment histories ─────────────────────────────────────────────
# Format: (commit, fts, skill_tokens, status, description)
EXPERIMENTS = {
    "spark-declarative-pipelines": [
        ("a1b2c3d", 5.00, 8200, "keep",    "baseline — upstream SKILL.md"),
        ("b2c3d4e", 5.80, 8450, "keep",    "added ai_summarize non-determinism gotcha"),
        ("c3d4e5f", 5.40, 9100, "discard", "added too much prose — noise > signal"),
        ("d4e5f60", 6.20, 8500, "keep",    "restructured checklist, added FK column note"),
        ("e5f6071", 6.80, 8650, "keep",    "added pipelines list-pipelines correction"),
        ("f607182", 7.20, 8700, "keep",    "added serverless poll cadence (15-20s)"),
        ("0718293", 7.20, 9200, "discard", "added streaming patterns — off-topic for interview"),
        ("1829304", 7.60, 8250, "keep",    "removed duplicate content, tightened language"),
        ("2930415", 7.80, 8400, "keep",    "added CDC auto_cdc_flow pattern"),
        ("3041526", 8.20, 8450, "keep",    "refined quick start + multi-source gold pattern"),
    ],
    "databricks-aibi-dashboards": [
        ("a2b3c4d", 4.50, 2200, "keep",    "baseline — upstream SKILL.md"),
        ("b3c4d5e", 5.20, 2400, "keep",    "added widget version number table"),
        ("c4d5e6f", 6.00, 2550, "keep",    "added filter page type documentation"),
        ("d5e6f70", 7.00, 2650, "keep",    "added embed_credentials: false gotcha"),
        ("e6f7081", 7.60, 2700, "keep",    "added parent_path pre-creation requirement"),
        ("f708192", 7.40, 3300, "discard", "added 8 more examples — too verbose"),
        ("0819203", 7.80, 2750, "keep",    "added troubleshooting guide reference"),
        ("1920314", 7.60, 3500, "discard", "tried to embed full widget JSON — broke routing"),
        ("2031425", 8.40, 2600, "keep",    "trim + restructure → clean index file"),
        ("3142536", 8.60, 2700, "keep",    "added widget name vs frame.title gotcha"),
    ],
    "synthetic-data-generation": [
        ("a3b4c5d", 5.50, 2800, "keep",    "baseline — upstream SKILL.md"),
        ("b4c5d6e", 6.40, 3000, "keep",    "added spark.range() override for interview context"),
        ("c5d6e7f", 7.00, 3100, "keep",    "added ingest_ts/source_system/batch_id requirement"),
        ("d6e7f80", 7.40, 3200, "keep",    "added broadcast join pattern for dim tables"),
        ("e7f8091", 7.20, 4000, "discard", "added domain examples — too long, wrong skill"),
        ("f809102", 7.60, 3300, "keep",    "added dim ≤6 columns rule"),
        ("0910213", 7.80, 3500, "discard", "added Faker examples — contradicts spark.range() rule"),
        ("1021324", 8.20, 3200, "keep",    "simplified + column naming gotcha"),
    ],
    "databricks-genie": [
        ("a4b5c6d", 4.20, 1200, "keep",    "baseline — upstream SKILL.md"),
        ("b5c6d7e", 5.60, 1400, "keep",    "added serialized_space proto3 JSON format"),
        ("c6d7e8f", 6.40, 1500, "keep",    "added table alphabetical sort requirement"),
        ("d7e8f90", 7.00, 1600, "keep",    "added permissions gotcha (data-rooms NOT valid)"),
        ("e8f9001", 7.40, 1700, "keep",    "added sample_questions 32hex id + list format"),
        ("f900112", 7.20, 2200, "discard", "added full API examples — too verbose for index"),
        ("0011223", 7.80, 1750, "keep",    "trim + refocus on proto3 rules"),
        ("1122334", 8.20, 1850, "keep",    "added ask_genie conversation pattern"),
    ],
    "databricks-bundles": [
        ("a5b6c7d", 5.80, 2500, "keep",    "baseline — upstream SKILL.md"),
        ("b6c7d8e", 6.20, 2600, "keep",    "added --only flag (not --task) correction"),
        ("c7d8e9f", 6.80, 2700, "keep",    "added stale tfstate recovery steps"),
        ("d8e9f00", 7.20, 2800, "keep",    "added serverless notebook task pattern"),
        ("e9f0011", 0.00, 2800, "crash",   "tried client:1 env spec — crashes workspace"),
        ("f001122", 7.60, 2900, "keep",    "added multi-workspace backup target pattern"),
        ("0112233", 7.80, 3000, "keep",    "added variable override per target"),
        ("1223344", 8.00, 2850, "keep",    "simplified examples, removed redundant prose"),
    ],
}

# Synthetic per-criterion scores that match the FTS trajectory
CRITERION_PROFILES = {
    "spark-declarative-pipelines": [
        {"correct_imports": 1.0, "no_antipatterns": 1.5, "pattern_adherence": 1.2, "completeness": 0.8, "first_try_runnable": 0.5},
        {"correct_imports": 1.0, "no_antipatterns": 1.8, "pattern_adherence": 1.5, "completeness": 1.0, "first_try_runnable": 0.5},
        {"correct_imports": 1.0, "no_antipatterns": 1.5, "pattern_adherence": 1.2, "completeness": 0.8, "first_try_runnable": 0.9},
        {"correct_imports": 1.0, "no_antipatterns": 1.8, "pattern_adherence": 1.8, "completeness": 1.2, "first_try_runnable": 1.4},
        {"correct_imports": 1.0, "no_antipatterns": 2.0, "pattern_adherence": 2.1, "completeness": 1.4, "first_try_runnable": 1.3},
        {"correct_imports": 1.0, "no_antipatterns": 2.0, "pattern_adherence": 2.2, "completeness": 1.6, "first_try_runnable": 1.4},
        {"correct_imports": 1.0, "no_antipatterns": 2.0, "pattern_adherence": 2.2, "completeness": 1.5, "first_try_runnable": 1.5},
        {"correct_imports": 1.0, "no_antipatterns": 2.0, "pattern_adherence": 2.4, "completeness": 1.6, "first_try_runnable": 1.6},
        {"correct_imports": 1.0, "no_antipatterns": 2.0, "pattern_adherence": 2.5, "completeness": 1.7, "first_try_runnable": 1.6},
        {"correct_imports": 1.0, "no_antipatterns": 2.0, "pattern_adherence": 2.8, "completeness": 1.8, "first_try_runnable": 1.6},
    ],
}


def write_tsv(skill: str, experiments: list, overwrite: bool = False) -> None:
    path = RESULTS_DIR / f"{skill}.tsv"
    if path.exists() and not overwrite:
        existing = path.read_text().strip().split("\n")
        if len(existing) > 1:  # has data rows
            print(f"  SKIP {skill}.tsv (already has data — use --reset to overwrite)")
            return

    header = "commit\tFTS\tskill_tokens\tstatus\tdescription\n"
    rows = []
    for commit, fts, tokens, status, desc in experiments:
        rows.append(f"{commit}\t{fts:.2f}\t{tokens}\t{status}\t{desc}")

    path.write_text(header + "\n".join(rows) + "\n")
    print(f"  ✓ {skill}.tsv  ({len(experiments)} experiments)")


def write_last_run(skill: str, experiments: list) -> None:
    """Write a synthetic last-run JSON for the most recent experiment."""
    last = experiments[-1]
    commit, fts, tokens, status, desc = last

    # Generate per-prompt scores that sum to approximately the FTS
    prompt_titles = {
        "spark-declarative-pipelines": [
            "Silver transform with data quality",
            "New pipeline project initialization",
            "ai_summarize in pipeline vs notebook",
            "Auto CDC for streaming ingestion",
            "Multi-source Gold aggregation",
        ],
        "databricks-aibi-dashboards": [
            "Create a counter widget",
            "Deploy dashboard with correct publish settings",
            "Bar chart widget for revenue by category",
            "Debug no selected fields error",
            "Multi-page dashboard with global filter",
        ],
        "synthetic-data-generation": [
            "Scalable Bronze fact table",
            "Bronze metadata columns",
            "Dimension table design constraints",
            "Non-uniform category distribution",
            "Direct Delta write pattern",
        ],
        "databricks-genie": [
            "Create a Genie Space via API",
            "serialized_space format",
            "Table sort order requirement",
            "Ask a question via Genie API",
            "Genie permissions model",
        ],
        "databricks-bundles": [
            "Multi-target bundle for two workspaces",
            "Run a single task in a job",
            "Stale tfstate recovery",
            "Serverless notebook task",
            "Bundle variables with defaults",
        ],
    }.get(skill, [f"Prompt {i+1}" for i in range(5)])

    # Distribute fts across 5 prompts with slight variance
    import random
    random.seed(42)
    prompt_ftss = []
    for i in range(5):
        variance = random.uniform(-0.5, 0.5)
        p_fts = max(0, min(10, fts + variance))
        prompt_ftss.append(round(p_fts, 2))
    # Adjust so mean ≈ fts
    adj = fts - sum(prompt_ftss) / 5
    prompt_ftss = [round(min(10, max(0, p + adj)), 2) for p in prompt_ftss]

    prompts = []
    for i, title in enumerate(prompt_titles):
        p_fts = prompt_ftss[i]
        prompts.append({
            "prompt": title,
            "fts": p_fts,
            "scores": {
                "correct_imports":     round(min(1.0, p_fts / 10), 2),
                "no_antipatterns":     round(min(2.0, p_fts / 5), 2),
                "pattern_adherence":   round(min(3.0, p_fts * 0.3), 2),
                "completeness":        round(min(2.0, p_fts / 5), 2),
                "first_try_runnable":  round(min(2.0, p_fts / 5), 2),
            }
        })

    data = {
        "skill": skill,
        "timestamp": datetime.now().isoformat(),
        "fts": fts,
        "skill_tokens": tokens,
        "prompts": prompts,
    }

    path = RESULTS_DIR / f"{skill}-last-run.json"
    path.write_text(json.dumps(data, indent=2))
    print(f"  ✓ {skill}-last-run.json")


def main():
    overwrite = "--reset" in sys.argv
    print(f"Seeding skills-eval/results/ {'(reset mode)' if overwrite else '(skip existing)'}")
    print()
    for skill, experiments in EXPERIMENTS.items():
        write_tsv(skill, experiments, overwrite=overwrite)
        write_last_run(skill, experiments)

    print()
    print("Done. Run the dashboard:")
    print("  python skills-eval/dashboard.py")


if __name__ == "__main__":
    main()
