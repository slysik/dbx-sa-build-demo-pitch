#!/usr/bin/env python3
"""
sync-skills.py — Check and sync skills from upstream repos with detailed changelog.

Upstream sources:
  - databricks-solutions/ai-dev-kit  → Databricks skills
  - mlflow/skills                    → MLflow skills
  - databricks-solutions/apx         → APX skills

Usage:
  python3 scripts/sync-skills.py                     # Interactive: check + prompt per skill
  python3 scripts/sync-skills.py --check             # Check only, print report
  python3 scripts/sync-skills.py --apply             # Apply all updates
  python3 scripts/sync-skills.py --check --markdown  # Output as Markdown (for CI)
  python3 scripts/sync-skills.py spark-declarative-pipelines databricks-bundles  # Specific skills
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Config ───────────────────────────────────────────────────────────────────

UPSTREAM_REPOS = {
    "aidevkit": {
        "url": "https://github.com/databricks-solutions/ai-dev-kit.git",
        "branch": "main",
        "skills_path": "databricks-skills",
    },
    "mlflow": {
        "url": "https://github.com/mlflow/skills.git",
        "branch": "main",
        "skills_path": ".",
    },
    "apx": {
        "url": "https://github.com/databricks-solutions/apx.git",
        "branch": "main",
        "skills_path": "skills/apx",
    },
}

# local_name → (repo_key, upstream_dir_name)
SKILL_MAP = {
    # Databricks skills (same name)
    "databricks-agent-bricks":              ("aidevkit", "databricks-agent-bricks"),
    "databricks-ai-functions":              ("aidevkit", "databricks-ai-functions"),
    "databricks-aibi-dashboards":           ("aidevkit", "databricks-aibi-dashboards"),
    "databricks-app-python":                ("aidevkit", "databricks-app-python"),
    "databricks-bundles":                   ("aidevkit", "databricks-bundles"),
    "databricks-config":                    ("aidevkit", "databricks-config"),
    "databricks-dbsql":                     ("aidevkit", "databricks-dbsql"),
    "databricks-docs":                      ("aidevkit", "databricks-docs"),
    "databricks-genie":                     ("aidevkit", "databricks-genie"),
    "databricks-iceberg":                   ("aidevkit", "databricks-iceberg"),
    "databricks-jobs":                      ("aidevkit", "databricks-jobs"),
    "databricks-lakebase-autoscale":        ("aidevkit", "databricks-lakebase-autoscale"),
    "databricks-metric-views":              ("aidevkit", "databricks-metric-views"),
    "databricks-mlflow-evaluation":         ("aidevkit", "databricks-mlflow-evaluation"),
    "databricks-python-sdk":                ("aidevkit", "databricks-python-sdk"),
    "databricks-spark-structured-streaming":("aidevkit", "databricks-spark-structured-streaming"),
    "databricks-unity-catalog":             ("aidevkit", "databricks-unity-catalog"),
    "databricks-vector-search":             ("aidevkit", "databricks-vector-search"),
    "spark-python-data-source":             ("aidevkit", "spark-python-data-source"),
    # Renamed: local name → upstream name
    "model-serving":               ("aidevkit", "databricks-model-serving"),
    "lakebase-provisioned":        ("aidevkit", "databricks-lakebase-provisioned"),
    "spark-declarative-pipelines": ("aidevkit", "databricks-spark-declarative-pipelines"),
    "synthetic-data-generation":   ("aidevkit", "databricks-synthetic-data-gen"),
    "unstructured-pdf-generation": ("aidevkit", "databricks-unstructured-pdf-generation"),
    "zerobus-ingest":              ("aidevkit", "databricks-zerobus-ingest"),
    # MLflow skills
    "agent-evaluation":                 ("mlflow", "agent-evaluation"),
    "analyze-mlflow-chat-session":      ("mlflow", "analyze-mlflow-chat-session"),
    "analyze-mlflow-trace":             ("mlflow", "analyze-mlflow-trace"),
    "instrumenting-with-mlflow-tracing":("mlflow", "instrumenting-with-mlflow-tracing"),
    "mlflow-onboarding":                ("mlflow", "mlflow-onboarding"),
    "querying-mlflow-metrics":          ("mlflow", "querying-mlflow-metrics"),
    "retrieving-mlflow-traces":         ("mlflow", "retrieving-mlflow-traces"),
    "searching-mlflow-docs":            ("mlflow", "searching-mlflow-docs"),
    # APX
    "databricks-app-apx": ("apx", "databricks-app-apx"),
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_SKILLS = PROJECT_ROOT / ".agents" / "skills"


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class FileDiff:
    path: str
    status: str  # "modified" | "added" | "deleted"
    added_lines: int = 0
    removed_lines: int = 0
    features: list = field(default_factory=list)  # extracted feature descriptions


@dataclass
class SkillDiff:
    local_name: str
    repo: str
    status: str  # "unchanged" | "updated" | "new" | "error"
    files: list = field(default_factory=list)  # List[FileDiff]
    upstream_commits: list = field(default_factory=list)  # commit messages
    description_change: str = ""  # SKILL.md description field diff
    sections_added: list = field(default_factory=list)
    sections_removed: list = field(default_factory=list)
    sections_modified: list = field(default_factory=list)


# ── Helpers ──────────────────────────────────────────────────────────────────

C = {
    "red": "\033[0;31m", "green": "\033[0;32m", "yellow": "\033[1;33m",
    "blue": "\033[0;34m", "cyan": "\033[0;36m", "dim": "\033[2m",
    "bold": "\033[1m", "nc": "\033[0m",
}

def c(color: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{C.get(color, '')}{text}{C['nc']}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clone_repo(url: str, branch: str, dest: Path) -> bool:
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", "--quiet", f"--branch={branch}", url, str(dest)],
            check=True, capture_output=True, timeout=60,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(c("yellow", f"  ⚠ Failed to clone {url}: {e}"))
        return False


def get_upstream_commits(repo_dir: Path, skills_path: str, upstream_name: str, days: int = 7) -> list:
    """Get recent commit messages touching this skill directory."""
    skill_path = f"{skills_path}/{upstream_name}" if skills_path != "." else upstream_name
    try:
        result = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--oneline",
             "--format=%h|%ad|%s", "--date=short", "--", f"{skill_path}/"],
            cwd=str(repo_dir), capture_output=True, text=True, timeout=10,
        )
        commits = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("|", 2)
                if len(parts) == 3:
                    commits.append({"sha": parts[0], "date": parts[1], "message": parts[2]})
        return commits
    except Exception:
        return []


def extract_markdown_sections(text: str) -> dict:
    """Extract ## and ### section headers and their line ranges."""
    sections = {}
    lines = text.split("\n")
    current = None
    start = 0
    for i, line in enumerate(lines):
        if re.match(r'^#{1,3}\s+', line):
            if current:
                sections[current] = (start, i)
            current = line.strip()
            start = i
    if current:
        sections[current] = (start, len(lines))
    return sections


def extract_features_from_diff(old_text: str, new_text: str) -> dict:
    """Analyze a SKILL.md diff to extract feature-level changes."""
    old_sections = extract_markdown_sections(old_text)
    new_sections = extract_markdown_sections(new_text)

    old_headers = set(old_sections.keys())
    new_headers = set(new_sections.keys())

    added = sorted(new_headers - old_headers)
    removed = sorted(old_headers - new_headers)

    # For shared sections, check if content changed
    modified = []
    old_lines = old_text.split("\n")
    new_lines = new_text.split("\n")
    for header in sorted(old_headers & new_headers):
        old_start, old_end = old_sections[header]
        new_start, new_end = new_sections[header]
        old_content = "\n".join(old_lines[old_start:old_end])
        new_content = "\n".join(new_lines[new_start:new_end])
        if old_content != new_content:
            # Count meaningful line changes (not just whitespace)
            diff = list(difflib.unified_diff(
                old_content.split("\n"), new_content.split("\n"), lineterm=""
            ))
            adds = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
            dels = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
            if adds + dels > 0:
                modified.append({"header": header, "added": adds, "removed": dels})

    # Extract description field change
    desc_change = ""
    old_desc = re.search(r'description:\s*["\'](.+?)["\']', old_text, re.DOTALL)
    new_desc = re.search(r'description:\s*["\'](.+?)["\']', new_text, re.DOTALL)
    if old_desc and new_desc and old_desc.group(1) != new_desc.group(1):
        desc_change = f"Description updated"

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "description_change": desc_change,
    }


def diff_file(upstream: Path, local: Path) -> FileDiff:
    """Compute a line-level diff between two files."""
    try:
        old = local.read_text(errors="replace").split("\n")
        new = upstream.read_text(errors="replace").split("\n")
    except Exception:
        return FileDiff(path=upstream.name, status="error")

    diff = list(difflib.unified_diff(old, new, lineterm=""))
    added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    return FileDiff(
        path=upstream.name, status="modified",
        added_lines=added, removed_lines=removed,
    )


def compare_skill(
    local_name: str, upstream_dir: Path, local_dir: Path, repo_key: str,
    repo_dir: Path, repo_cfg: dict
) -> SkillDiff:
    """Full comparison of one skill."""
    result = SkillDiff(local_name=local_name, repo=repo_key, status="unchanged")

    if not local_dir.exists():
        result.status = "new"
        result.files = [
            FileDiff(path=f.name, status="added")
            for f in upstream_dir.rglob("*") if f.is_file()
        ]
        return result

    # Compare all files
    upstream_files = {f.relative_to(upstream_dir): f for f in upstream_dir.rglob("*") if f.is_file()}
    local_files = {f.relative_to(local_dir): f for f in local_dir.rglob("*") if f.is_file()}

    for rel, uf in sorted(upstream_files.items()):
        lf = local_dir / rel
        if not lf.exists():
            result.files.append(FileDiff(path=str(rel), status="added"))
        elif sha256(uf) != sha256(lf):
            fd = diff_file(uf, lf)
            fd.path = str(rel)
            result.files.append(fd)

    for rel in sorted(local_files.keys()):
        if rel not in upstream_files:
            result.files.append(FileDiff(path=str(rel), status="deleted"))

    if result.files:
        result.status = "updated"

    # Feature-level analysis on SKILL.md
    upstream_skill = upstream_dir / "SKILL.md"
    local_skill = local_dir / "SKILL.md"
    if upstream_skill.exists() and local_skill.exists():
        if sha256(upstream_skill) != sha256(local_skill):
            features = extract_features_from_diff(
                local_skill.read_text(errors="replace"),
                upstream_skill.read_text(errors="replace"),
            )
            result.sections_added = features["added"]
            result.sections_removed = features["removed"]
            result.sections_modified = features["modified"]
            result.description_change = features["description_change"]

    # Get upstream commits
    upstream_name = SKILL_MAP[local_name][1]
    result.upstream_commits = get_upstream_commits(
        repo_dir, repo_cfg["skills_path"], upstream_name, days=30
    )

    return result


# ── Report formatters ────────────────────────────────────────────────────────

def format_terminal(results: list, show_unchanged: bool = False) -> str:
    """Rich terminal output."""
    lines = []
    updated = [r for r in results if r.status == "updated"]
    new = [r for r in results if r.status == "new"]
    unchanged = [r for r in results if r.status == "unchanged"]

    lines.append(c("cyan", f"\n{'━' * 70}"))
    lines.append(c("bold", f"  Skills Update Report — {len(results)} checked"))
    lines.append(c("cyan", f"{'━' * 70}\n"))

    if not updated and not new:
        lines.append(c("green", "  ✅ All skills are up to date.\n"))
        return "\n".join(lines)

    # Updated skills (detailed)
    if updated:
        lines.append(c("yellow", f"  🔄 {len(updated)} skill(s) with updates:\n"))
        for r in sorted(updated, key=lambda x: x.local_name):
            mod = [f for f in r.files if f.status == "modified"]
            add = [f for f in r.files if f.status == "added"]
            rem = [f for f in r.files if f.status == "deleted"]
            lines.append(c("yellow", f"  ┌─ {r.local_name}") + c("dim", f"  ({r.repo})"))

            # File-level changes
            for f in mod:
                lines.append(c("dim", f"  │  Δ {f.path}") +
                             c("green", f" +{f.added_lines}") +
                             c("red", f" -{f.removed_lines}"))
            for f in add:
                lines.append(c("green", f"  │  + {f.path} (new file)"))
            for f in rem:
                lines.append(c("red", f"  │  - {f.path} (removed)"))

            # Feature-level changes (SKILL.md sections)
            if r.description_change:
                lines.append(c("cyan", f"  │  📝 {r.description_change}"))
            if r.sections_added:
                for s in r.sections_added:
                    lines.append(c("green", f"  │  ✨ New section: {s}"))
            if r.sections_removed:
                for s in r.sections_removed:
                    lines.append(c("red", f"  │  🗑  Removed section: {s}"))
            if r.sections_modified:
                for s in r.sections_modified:
                    lines.append(c("yellow", f"  │  📝 Modified: {s['header']}") +
                                 c("green", f" +{s['added']}") +
                                 c("red", f" -{s['removed']}"))

            # Upstream commits
            if r.upstream_commits:
                lines.append(c("dim", f"  │  Recent commits:"))
                for cm in r.upstream_commits[:5]:
                    lines.append(c("dim", f"  │    {cm['sha']} {cm['date']} {cm['message'][:65]}"))

            lines.append(c("dim", "  └─"))
            lines.append("")

    # New skills
    if new:
        lines.append(c("green", f"\n  🆕 {len(new)} new skill(s) available:\n"))
        for r in sorted(new, key=lambda x: x.local_name):
            nfiles = len(r.files)
            lines.append(c("green", f"    + {r.local_name}") +
                         c("dim", f"  ({r.repo}, {nfiles} files)"))

    # Summary
    lines.append(c("cyan", f"\n{'━' * 70}"))
    lines.append(f"  Unchanged: {len(unchanged)}  |  "
                 + c("yellow", f"Updated: {len(updated)}") + "  |  "
                 + c("green", f"New: {len(new)}"))
    lines.append(c("cyan", f"{'━' * 70}\n"))

    return "\n".join(lines)


def format_markdown(results: list) -> str:
    """Markdown output for GitHub Issues / CI."""
    lines = []
    updated = [r for r in results if r.status == "updated"]
    new = [r for r in results if r.status == "new"]
    unchanged = [r for r in results if r.status == "unchanged"]

    from datetime import date
    today = date.today().isoformat()

    lines.append(f"## 🔍 Skills Update Report — {today}\n")
    lines.append(f"**Checked:** {len(results)} skills | "
                 f"**Updated:** {len(updated)} | **New:** {len(new)} | "
                 f"**Unchanged:** {len(unchanged)}\n")

    if not updated and not new:
        lines.append("✅ All skills are up to date.\n")
        return "\n".join(lines)

    # Detailed table
    if updated:
        lines.append("### 🔄 Updated Skills\n")
        for r in sorted(updated, key=lambda x: x.local_name):
            mod = [f for f in r.files if f.status == "modified"]
            add = [f for f in r.files if f.status == "added"]
            rem = [f for f in r.files if f.status == "deleted"]

            lines.append(f"#### `{r.local_name}` ({r.repo})\n")

            # Files table
            lines.append("| File | Status | Changes |")
            lines.append("|------|--------|---------|")
            for f in mod:
                lines.append(f"| `{f.path}` | Modified | +{f.added_lines} / -{f.removed_lines} |")
            for f in add:
                lines.append(f"| `{f.path}` | ✨ New | — |")
            for f in rem:
                lines.append(f"| `{f.path}` | 🗑 Removed | — |")
            lines.append("")

            # Features
            features = []
            if r.description_change:
                features.append(f"- 📝 {r.description_change}")
            for s in r.sections_added:
                features.append(f"- ✨ **New section:** {s}")
            for s in r.sections_removed:
                features.append(f"- 🗑 **Removed section:** {s}")
            for s in r.sections_modified:
                features.append(f"- 📝 **Modified:** {s['header']} (+{s['added']}/-{s['removed']})")
            if features:
                lines.append("**Feature changes (SKILL.md):**\n")
                lines.extend(features)
                lines.append("")

            # Commits
            if r.upstream_commits:
                lines.append("<details><summary>Recent upstream commits</summary>\n")
                for cm in r.upstream_commits[:10]:
                    lines.append(f"- `{cm['sha']}` ({cm['date']}) {cm['message']}")
                lines.append("\n</details>\n")

    if new:
        lines.append("### 🆕 New Skills Available\n")
        lines.append("| Skill | Source | Files |")
        lines.append("|-------|--------|-------|")
        for r in sorted(new, key=lambda x: x.local_name):
            lines.append(f"| `{r.local_name}` | {r.repo} | {len(r.files)} |")
        lines.append("")

    # Update instructions
    lines.append("### 🔧 How to update\n")
    lines.append("```bash")
    lines.append("# Interactive (prompts per skill):")
    lines.append("just skills-sync")
    lines.append("")
    lines.append("# Apply all updates:")
    lines.append("just skills-update")
    lines.append("")
    lines.append("# Specific skills only:")
    if updated:
        names = " ".join(r.local_name for r in updated[:3])
        lines.append(f"just skills-sync-one {names}")
    lines.append("```\n")

    return "\n".join(lines)


def format_json(results: list) -> str:
    """JSON output for programmatic consumption."""
    from datetime import date
    updated = [r for r in results if r.status != "unchanged"]
    output = {
        "date": date.today().isoformat(),
        "total_checked": len(results),
        "updated_count": sum(1 for r in results if r.status == "updated"),
        "new_count": sum(1 for r in results if r.status == "new"),
        "skills": [],
    }
    for r in sorted(updated, key=lambda x: x.local_name):
        skill = {
            "name": r.local_name,
            "source": r.repo,
            "status": r.status,
            "files": [
                {"path": f.path, "status": f.status, "added": f.added_lines, "removed": f.removed_lines}
                for f in r.files
            ],
            "features": {
                "description_changed": bool(r.description_change),
                "sections_added": r.sections_added,
                "sections_removed": r.sections_removed,
                "sections_modified": [s["header"] for s in r.sections_modified],
            },
            "commits": r.upstream_commits[:5],
        }
        output["skills"].append(skill)
    return json.dumps(output, indent=2)


# ── Apply ────────────────────────────────────────────────────────────────────

def apply_skill(local_name: str, repo_dirs: dict):
    """Copy upstream skill to local directory."""
    repo_key, upstream_name = SKILL_MAP[local_name]
    repo_cfg = UPSTREAM_REPOS[repo_key]
    repo_dir = repo_dirs[repo_key]
    skills_base = repo_dir / repo_cfg["skills_path"]
    upstream_dir = skills_base / upstream_name
    local_dir = LOCAL_SKILLS / local_name

    if not upstream_dir.exists():
        print(c("red", f"  ✗ {local_name}: upstream not found"))
        return

    # Remove local and copy fresh
    if local_dir.exists():
        shutil.rmtree(local_dir)
    shutil.copytree(upstream_dir, local_dir)
    print(c("green", f"  ✓ {local_name} updated"))


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Check and sync Databricks skills from upstream")
    parser.add_argument("skills", nargs="*", help="Specific skill names to check (local names)")
    parser.add_argument("--check", action="store_true", help="Check only, no changes")
    parser.add_argument("--apply", action="store_true", help="Apply all updates without prompting")
    parser.add_argument("--markdown", action="store_true", help="Output as Markdown")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--report", type=str, help="Write report to file")
    args = parser.parse_args()

    # Clone upstream repos
    tmpdir = Path(tempfile.mkdtemp())
    repo_dirs = {}

    try:
        quiet = args.json  # suppress progress for machine-readable output
        if not quiet:
            print(c("blue", "Fetching upstream repos..."))
        for key, cfg in UPSTREAM_REPOS.items():
            dest = tmpdir / key
            ok = clone_repo(cfg["url"], cfg["branch"], dest)
            if ok:
                repo_dirs[key] = dest
            elif not quiet:
                print(c("yellow", f"  ⚠ Skipping {key} (clone failed)"))

        if not repo_dirs:
            print(c("red", "No upstream repos available. Exiting."))
            sys.exit(1)

        # Determine skills to check
        if args.skills:
            skills_to_check = args.skills
        else:
            skills_to_check = sorted(SKILL_MAP.keys())

        # Compare each skill
        results = []
        for local_name in skills_to_check:
            if local_name not in SKILL_MAP:
                if not quiet:
                    print(c("yellow", f"  ⚠ {local_name}: no upstream mapping (local-only)"))
                continue

            repo_key, upstream_name = SKILL_MAP[local_name]
            if repo_key not in repo_dirs:
                continue

            repo_cfg = UPSTREAM_REPOS[repo_key]
            repo_dir = repo_dirs[repo_key]
            skills_base = repo_dir / repo_cfg["skills_path"]
            upstream_dir = skills_base / upstream_name

            if not upstream_dir.exists():
                continue

            local_dir = LOCAL_SKILLS / local_name
            result = compare_skill(
                local_name, upstream_dir, local_dir, repo_key, repo_dir, repo_cfg
            )
            results.append(result)

        # Format output
        if args.json:
            report = format_json(results)
        elif args.markdown:
            report = format_markdown(results)
        else:
            report = format_terminal(results)

        print(report)

        # Write report file if requested
        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            # Always write markdown to file
            report_path.write_text(format_markdown(results))
            print(c("dim", f"  Report written to {report_path}"))

        # Apply mode
        updated = [r for r in results if r.status in ("updated", "new")]
        if not updated:
            return

        if args.check:
            if not args.json and not args.markdown:
                print(c("blue", "Run with --apply to update, or without flags for interactive.\n"))
            return

        if args.apply:
            print(c("blue", "\nApplying all updates..."))
            for r in updated:
                apply_skill(r.local_name, repo_dirs)
            print(c("green", f"\nDone. Run 'git diff .agents/skills/' to review.\n"))
            return

        # Interactive mode
        print()
        for r in updated:
            answer = input(f"  Apply update for {c('yellow', r.local_name)}? [y/N] ").strip()
            if answer.lower() in ("y", "yes"):
                apply_skill(r.local_name, repo_dirs)
            else:
                print(c("dim", f"  ⏭  Skipped {r.local_name}"))

        print(c("green", f"\nDone. Run 'git diff .agents/skills/' to review.\n"))

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
