#!/usr/bin/env python3
"""
Sync Official Skills — Fetch patterns from databricks-solutions/ai-dev-kit

Automatically detects new patterns, APIs, and gotchas from the official repo.
Compares against your local SKILL.md files.
Reports: What's new in Databricks? What are we missing?

Usage:
    python3 sync_official_skills.py                    # Full diff
    python3 sync_official_skills.py --skill databricks-bundles  # Single skill
    python3 sync_official_skills.py --download-only    # Just clone repo, don't analyze
    python3 sync_official_skills.py --update-baseline  # Save current state as baseline
"""

import json
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass
from datetime import datetime
import tempfile
import shutil

REPO_URL = "https://github.com/databricks-solutions/ai-dev-kit.git"
LOCAL_REPO = Path(__file__).parent.parent / ".ai-dev-kit-official"
BASELINE_FILE = Path(__file__).parent / "results" / "official-skills-baseline.json"

@dataclass
class SkillDiff:
    skill_name: str
    new_patterns: List[str]
    deprecated_patterns: List[str]
    clarified_patterns: List[str]  # existing but more detailed now
    new_gotchas: List[str]
    score: float  # priority: 0-100


def clone_or_update_repo():
    """Clone/update the official ai-dev-kit repo."""
    if LOCAL_REPO.exists():
        print(f"Updating repo: {LOCAL_REPO}")
        subprocess.run(["git", "pull"], cwd=LOCAL_REPO, capture_output=True)
    else:
        print(f"Cloning repo: {REPO_URL}")
        subprocess.run(["git", "clone", REPO_URL, str(LOCAL_REPO)], capture_output=True)
    
    return LOCAL_REPO


def extract_skill_keywords(skill_path: Path) -> Dict[str, Set[str]]:
    """Extract patterns, APIs, gotchas from a SKILL.md file."""
    if not skill_path.exists():
        return {}
    
    content = skill_path.read_text()
    
    keywords = {
        "apis": set(),
        "patterns": set(),
        "gotchas": set(),
        "examples": set(),
        "parameters": set(),
    }
    
    # Extract code blocks with backticks
    code_blocks = re.findall(r"`([^`]+)`", content)
    keywords["apis"].update(code_blocks)
    
    # Extract gotchas (lines with ⚠️, CRITICAL, etc.)
    gotcha_lines = [line.strip() for line in content.split("\n") 
                   if "⚠️" in line or "CRITICAL" in line or "gotcha" in line.lower()]
    keywords["gotchas"].update(gotcha_lines[:10])
    
    # Extract patterns (function/class definitions)
    patterns = re.findall(r"((?:def|class|CREATE|SELECT|@)\s+\w+[^.!?\n]*)", content)
    keywords["patterns"].update(patterns[:20])
    
    # Extract parameter names
    params = re.findall(r"(\w+):\s*(?:\w+|str|int|bool)", content)
    keywords["parameters"].update(params[:30])
    
    return keywords


def load_official_skills(repo_path: Path) -> Dict[str, Dict]:
    """Load all skills from official ai-dev-kit repo."""
    skills = {}
    skills_dir = repo_path / "skills"
    
    if not skills_dir.exists():
        print(f"⚠️  Skills directory not found: {skills_dir}")
        return {}
    
    for skill_folder in skills_dir.iterdir():
        if skill_folder.is_dir():
            skill_md = skill_folder / "SKILL.md"
            if skill_md.exists():
                skill_name = skill_folder.name
                keywords = extract_skill_keywords(skill_md)
                
                # Also get the description from frontmatter
                content = skill_md.read_text()
                description_match = re.search(r'description:\s*"([^"]+)"', content)
                description = description_match.group(1) if description_match else ""
                
                skills[skill_name] = {
                    "path": str(skill_md),
                    "description": description,
                    "keywords": keywords,
                    "content_hash": hash(content),  # For detecting updates
                }
    
    return skills


def load_local_skills(local_base: Path) -> Dict[str, Dict]:
    """Load all local skills from .agents/skills and .pi/skills."""
    skills = {}
    
    for skill_dir in [local_base / ".agents" / "skills", local_base / ".pi" / "skills"]:
        if not skill_dir.exists():
            continue
        
        for skill_folder in skill_dir.iterdir():
            if skill_folder.is_dir():
                skill_md = skill_folder / "SKILL.md"
                if skill_md.exists():
                    skill_name = skill_folder.name
                    keywords = extract_skill_keywords(skill_md)
                    
                    content = skill_md.read_text()
                    
                    skills[skill_name] = {
                        "path": str(skill_md),
                        "keywords": keywords,
                        "content_hash": hash(content),
                    }
    
    return skills


def diff_skills(official: Dict, local: Dict) -> Dict[str, SkillDiff]:
    """Compare official vs local skills."""
    diffs = {}
    
    for skill_name, official_skill in official.items():
        if skill_name not in local:
            # Entire skill is missing
            score = 85 if "high" in official_skill.get("description", "").lower() else 50
            diffs[skill_name] = SkillDiff(
                skill_name=skill_name,
                new_patterns=list(official_skill["keywords"]["patterns"])[:5],
                deprecated_patterns=[],
                clarified_patterns=[],
                new_gotchas=list(official_skill["keywords"]["gotchas"])[:3],
                score=score
            )
        else:
            # Skill exists, compare patterns
            local_skill = local[skill_name]
            official_apis = official_skill["keywords"]["apis"]
            local_apis = local_skill["keywords"]["apis"]
            
            new_apis = official_apis - local_apis
            missing_apis = local_apis - official_apis
            
            official_gotchas = official_skill["keywords"]["gotchas"]
            local_gotchas = local_skill["keywords"]["gotchas"]
            new_gotchas = [g for g in official_gotchas if g not in local_gotchas]
            
            if new_apis or new_gotchas:
                score = (len(new_apis) * 10) + (len(new_gotchas) * 5)
                score = min(score, 100)
                
                diffs[skill_name] = SkillDiff(
                    skill_name=skill_name,
                    new_patterns=list(new_apis)[:5],
                    deprecated_patterns=list(missing_apis)[:3],
                    clarified_patterns=[],
                    new_gotchas=new_gotchas[:3],
                    score=score
                )
    
    # Sort by priority
    sorted_diffs = dict(sorted(diffs.items(), key=lambda x: x[1].score, reverse=True))
    return sorted_diffs


def format_diff_report(diffs: Dict[str, SkillDiff], verbose: bool = False) -> str:
    """Format diffs as human-readable report."""
    if not diffs:
        return "✅ All local skills are in sync with official ai-dev-kit!\n"
    
    report = "\n" + "="*70 + "\n"
    report += "🔄 OFFICIAL AI-DEV-KIT DIFF REPORT\n"
    report += "="*70 + "\n"
    report += f"Found {len(diffs)} skills with updates from official repo\n"
    report += "="*70 + "\n\n"
    
    for skill_name, diff in list(diffs.items())[:15]:
        report += f"📌 {skill_name}\n"
        report += f"   Priority score: {diff.score:.0f}/100\n"
        
        if diff.new_patterns:
            report += f"   🆕 New patterns: {', '.join(diff.new_patterns[:3])}\n"
        if diff.new_gotchas:
            report += f"   ⚠️  New gotchas: {diff.new_gotchas[0][:60]}...\n"
        if diff.deprecated_patterns:
            report += f"   ❌ Deprecated: {', '.join(diff.deprecated_patterns[:2])}\n"
        
        report += "\n"
    
    if len(diffs) > 15:
        report += f"... and {len(diffs) - 15} more skills\n"
    
    return report


def generate_json_report(diffs: Dict[str, SkillDiff], output_path: Path):
    """Save diffs as JSON for programmatic access."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "total_diffs": len(diffs),
        "diffs": {
            name: {
                "score": diff.score,
                "new_patterns": diff.new_patterns,
                "new_gotchas": diff.new_gotchas,
                "deprecated": diff.deprecated_patterns,
            }
            for name, diff in diffs.items()
        }
    }
    
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2))
    print(f"✓ Saved JSON report: {output_path}")


def save_baseline(official_skills: Dict, local_skills: Dict, baseline_path: Path):
    """Save current state as baseline for future diffs."""
    baseline = {
        "timestamp": datetime.now().isoformat(),
        "official_skills": {
            name: {
                "description": skill.get("description", ""),
                "api_count": len(skill["keywords"]["apis"]),
                "gotcha_count": len(skill["keywords"]["gotchas"]),
                "pattern_count": len(skill["keywords"]["patterns"]),
            }
            for name, skill in official_skills.items()
        },
        "local_skills": {
            name: {
                "api_count": len(skill["keywords"]["apis"]),
                "gotcha_count": len(skill["keywords"]["gotchas"]),
                "pattern_count": len(skill["keywords"]["patterns"]),
            }
            for name, skill in local_skills.items()
        }
    }
    
    baseline_path.parent.mkdir(exist_ok=True)
    baseline_path.write_text(json.dumps(baseline, indent=2))
    print(f"✓ Baseline saved: {baseline_path}")


def main():
    import sys
    
    skill_name = None
    verbose = False
    download_only = False
    update_baseline = False
    
    # Parse CLI
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--skill" and i + 1 < len(sys.argv):
            skill_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--detail":
            verbose = True
            i += 1
        elif sys.argv[i] == "--download-only":
            download_only = True
            i += 1
        elif sys.argv[i] == "--update-baseline":
            update_baseline = True
            i += 1
        else:
            i += 1
    
    print("📡 Syncing with official ai-dev-kit repository...")
    repo_path = clone_or_update_repo()
    
    if download_only:
        print(f"✓ Repo ready: {repo_path}")
        return
    
    print("📚 Loading official skills...")
    official_skills = load_official_skills(repo_path)
    print(f"   Found {len(official_skills)} official skills")
    
    print("📖 Loading local skills...")
    local_skills = load_local_skills(Path(__file__).parent.parent)
    print(f"   Found {len(local_skills)} local skills")
    
    print("🔍 Computing diffs...")
    diffs = diff_skills(official_skills, local_skills)
    
    if update_baseline:
        save_baseline(official_skills, local_skills, BASELINE_FILE)
    
    # Report
    if skill_name:
        if skill_name in diffs:
            diff = diffs[skill_name]
            print(f"\n{'='*70}")
            print(f"Diff: {skill_name}")
            print(f"{'='*70}")
            print(f"Priority score: {diff.score:.0f}/100")
            print(f"New patterns: {', '.join(diff.new_patterns)}")
            print(f"New gotchas: {len(diff.new_gotchas)} found")
        else:
            print(f"✅ {skill_name} is in sync")
    else:
        print(format_diff_report(diffs, verbose=verbose))
        
        # Save JSON report
        json_report = Path(__file__).parent / "results" / "official-skills-diff.json"
        generate_json_report(diffs, json_report)


if __name__ == "__main__":
    main()
