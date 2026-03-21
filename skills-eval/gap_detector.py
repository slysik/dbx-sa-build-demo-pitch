#!/usr/bin/env python3
"""
Gap Detector — Identifies skill documentation gaps against current Databricks features

Compares:
- Current SKILL.md files (what you've documented)
- Latest Databricks features (what's available)
- Outputs: ranked list of gaps (missing patterns, outdated syntax, new APIs)

Usage:
    python3 gap_detector.py                          # analyze all skills
    python3 gap_detector.py --skill databricks-bundles  # single skill
    python3 gap_detector.py --skill databricks-bundles --detail  # verbose
    python3 gap_detector.py --report html > report.html  # generate report
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Set
from datetime import datetime
import subprocess

SKILLS_DIR = Path(__file__).parent.parent / ".agents" / "skills"
PI_SKILLS_DIR = Path(__file__).parent.parent / ".pi" / "skills"

@dataclass
class Feature:
    """Represents a Databricks feature/API"""
    name: str
    keywords: List[str]
    api_endpoint: str = ""
    docs_link: str = ""
    released: str = "2026-Q1"  # Approximate quarter
    severity: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    category: str = "feature"  # feature, bug-fix, deprecation, parameter
    skill_domain: str = ""  # which skill should cover this

@dataclass
class Gap:
    """Represents a gap in skill coverage"""
    feature: Feature
    gap_type: str  # "missing", "outdated", "unclear"
    skill_name: str
    current_coverage: str  # quote from SKILL.md if found
    recommendation: str
    score: float  # 0-100, higher = more important to fix


# ── Curated Feature List (Updated 2026-Q1) ─────────────────────────────────
# This is your source of truth for "what's new in Databricks"
# Update this quarterly when new features drop

DATABRICKS_FEATURES = [
    # ── NEW IN 2026-Q1 ──────────────────────────────────────────────────────
    Feature(
        name="Lakeflow CDC with DELETE tracking",
        keywords=["apply_as_delete", "create_auto_cdc_flow", "TRACK HISTORY", "sequence_by"],
        api_endpoint="/api/2.0/pipelines",
        docs_link="https://docs.databricks.com/ldp/cdc",
        released="2026-Q1",
        severity="HIGH",
        skill_domain="spark-declarative-pipelines"
    ),
    Feature(
        name="ai_extract_table() for document parsing",
        keywords=["ai_extract_table", "extract structured data", "tables from documents"],
        docs_link="https://docs.databricks.com/en/ai/foundation-models/ai-functions",
        released="2026-Q1",
        severity="MEDIUM",
        skill_domain="databricks-ai-functions"
    ),
    Feature(
        name="Genie Spaces sampling parameter",
        keywords=["sampling", "Genie Spaces", "sample_size", "data sampling"],
        docs_link="https://docs.databricks.com/genie/admin/sampling",
        released="2026-Q1",
        severity="LOW",
        skill_domain="databricks-genie"
    ),
    Feature(
        name="Bundle variables with lookup (warehouse/cluster auto-resolution)",
        keywords=["lookup:", "warehouse lookup", "cluster lookup", "resolve", "auto-resolve"],
        docs_link="https://docs.databricks.com/dev-tools/bundles/settings",
        released="2026-Q1",
        severity="MEDIUM",
        skill_domain="databricks-bundles"
    ),
    Feature(
        name="Lakebase Autoscale (managed PostgreSQL)",
        keywords=["Lakebase Autoscale", "managed postgresql", "database branching", "scale-to-zero"],
        docs_link="https://docs.databricks.com/lakebase/autoscale/overview",
        released="2026-Q1",
        severity="MEDIUM",
        skill_domain="databricks-lakebase-autoscale"
    ),
    Feature(
        name="Liquid Clustering on Materialized Views",
        keywords=["CLUSTER BY", "liquid clustering", "materialized view clustering"],
        docs_link="https://docs.databricks.com/en/lakehouse/data-organization",
        released="2026-Q1",
        severity="LOW",
        skill_domain="spark-declarative-pipelines"
    ),
    Feature(
        name="AI/BI Dashboard: dataset_catalog / dataset_schema parameters",
        keywords=["dataset_catalog", "dataset_schema", "default catalog", "default schema", "dashboard variables"],
        docs_link="https://docs.databricks.com/en/dashboards/dev-tools/bundles",
        released="2026-01",
        severity="MEDIUM",
        skill_domain="databricks-aibi-dashboards"
    ),
    Feature(
        name="Apps resource in Bundles (Dash, Streamlit, Reflex)",
        keywords=["apps:", "app.yaml", "source_code_path", "app deployment"],
        docs_link="https://docs.databricks.com/dev-tools/bundles/resources",
        released="2026-01",
        severity="MEDIUM",
        skill_domain="databricks-bundles"
    ),
    Feature(
        name="Model Serving: ChatAgent and ResponsesAgent",
        keywords=["ChatAgent", "ResponsesAgent", "agent_tools", "model serving agents"],
        docs_link="https://docs.databricks.com/en/generative-ai/agents/deploy-agents",
        released="2026-Q1",
        severity="HIGH",
        skill_domain="model-serving"
    ),
    Feature(
        name="Serverless notebooks in Jobs (queue: enabled)",
        keywords=["queue: enabled", "serverless notebook", "serverless compute", "queue.enabled"],
        docs_link="https://docs.databricks.com/api/workspace/jobs/submit",
        released="2025-Q4",
        severity="HIGH",
        skill_domain="databricks-bundles"
    ),
    Feature(
        name="Databricks Connect v2 (Python, Java, Go, Rust)",
        keywords=["Databricks Connect", "remote execution", "local IDE"],
        docs_link="https://docs.databricks.com/dev-tools/databricks-connect",
        released="2025-Q4",
        severity="MEDIUM",
        skill_domain="databricks-python-sdk"
    ),
    Feature(
        name="Unity Catalog: Row-level and column-level masking",
        keywords=["row masking", "column masking", "data masking", "UC security"],
        docs_link="https://docs.databricks.com/en/data-governance/access-control/column-level-security",
        released="2025-Q4",
        severity="LOW",
        skill_domain="databricks-unity-catalog"
    ),
    Feature(
        name="MLflow 3: GenAI evaluation and GEPA optimization",
        keywords=["mlflow.genai.evaluate", "GEPA", "prompt optimization", "evaluator", "@scorer"],
        docs_link="https://docs.databricks.com/en/mlflow/genai-eval",
        released="2026-Q1",
        severity="HIGH",
        skill_domain="databricks-mlflow-evaluation"
    ),
    Feature(
        name="Vector Search: Direct index type (no Delta Sync requirement)",
        keywords=["direct_access_index", "direct index", "vector search", "no delta sync"],
        docs_link="https://docs.databricks.com/en/vector-search/index",
        released="2025-Q4",
        severity="MEDIUM",
        skill_domain="databricks-vector-search"
    ),
    Feature(
        name="Iceberg v3 + External Iceberg Reads (Uniform)",
        keywords=["Iceberg v3", "External Iceberg Reads", "Uniform", "compatibility mode"],
        docs_link="https://docs.databricks.com/en/data-engineering/iceberg/iceberg-overview",
        released="2025-Q4",
        severity="MEDIUM",
        skill_domain="databricks-iceberg"
    ),
    Feature(
        name="Metric Views (governed business metrics in YAML)",
        keywords=["metric view", "business metrics", "governed metrics", "@metric"],
        docs_link="https://docs.databricks.com/en/lakehouse/data-governance/metrics",
        released="2026-Q1",
        severity="LOW",
        skill_domain="databricks-metric-views"
    ),
    Feature(
        name="Real-Time Mode (RTM) for Structured Streaming",
        keywords=["Real-Time Mode", "RTM", "streaming", "micro-batching"],
        docs_link="https://docs.databricks.com/en/structured-streaming/real-time-mode",
        released="2025-Q4",
        severity="MEDIUM",
        skill_domain="databricks-spark-structured-streaming"
    ),
    Feature(
        name="Zerobus Ingest (gRPC producer for Delta)",
        keywords=["Zerobus Ingest", "gRPC", "near real-time", "ingest producer"],
        docs_link="https://docs.databricks.com/en/developer-tools/zerobus/overview",
        released="2026-Q1",
        severity="LOW",
        skill_domain="databricks-zerobus-ingest"
    ),
    
    # ── KEEP CURRENT (Important gotchas, still relevant) ──────────────────
    Feature(
        name="Workspace admin ≠ UC CREATE_SCHEMA (explicit grant required)",
        keywords=["workspace admin", "CREATE_SCHEMA", "UC access", "GRANT ALL PRIVILEGES"],
        released="2025-Q3",
        severity="HIGH",
        skill_domain="databricks-bundles"
    ),
    Feature(
        name="--only flag (not --task) for running single job tasks",
        keywords=["--only", "bundle run", "task_key", "not --task"],
        released="2025-Q3",
        severity="HIGH",
        skill_domain="databricks-bundles"
    ),
    Feature(
        name="ai_summarize is non-deterministic (invalid in Materialized Views)",
        keywords=["ai_summarize", "non-deterministic", "materialized view", "notebook"],
        released="2025-Q2",
        severity="HIGH",
        skill_domain="spark-declarative-pipelines"
    ),
    Feature(
        name="Serverless notebook tasks: no existing_cluster_id, queue: enabled",
        keywords=["serverless", "queue: enabled", "notebook_task", "source: WORKSPACE"],
        released="2025-Q4",
        severity="HIGH",
        skill_domain="databricks-bundles"
    ),
]


def load_skill(skill_name: str) -> tuple[str, Path]:
    """Load SKILL.md content. Returns (content, file_path)."""
    candidates = [
        SKILLS_DIR / skill_name / "SKILL.md",
        PI_SKILLS_DIR / skill_name / "SKILL.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(), path
    raise FileNotFoundError(f"SKILL.md not found for: {skill_name}")


def extract_skill_coverage(skill_content: str) -> Dict[str, List[str]]:
    """Extract keywords and patterns from skill documentation."""
    coverage = {
        "explicit_keywords": [],
        "api_patterns": [],
        "gotcha_patterns": [],
        "example_code": [],
    }
    
    # Find explicitly documented features
    for line in skill_content.split("\n"):
        # Look for code patterns
        if re.search(r"`\w+\(`", line) or re.search(r"CREATE OR REFRESH", line):
            coverage["api_patterns"].append(line.strip())
        # Look for gotchas
        if "⚠️" in line or "gotcha" in line.lower():
            coverage["gotcha_patterns"].append(line.strip())
        # Extract quoted keywords
        matches = re.findall(r"`([^`]+)`", line)
        coverage["explicit_keywords"].extend(matches)
    
    return coverage


def detect_gaps(skill_name: str, skill_content: str) -> List[Gap]:
    """Compare skill coverage against feature list."""
    gaps = []
    coverage = extract_skill_coverage(skill_content)
    all_keywords = coverage["explicit_keywords"] + coverage["api_patterns"] + coverage["gotcha_patterns"]
    all_keywords_lower = [k.lower() for k in all_keywords]
    
    for feature in DATABRICKS_FEATURES:
        if feature.skill_domain and feature.skill_domain != skill_name:
            continue  # Not relevant to this skill
        
        # Check if feature keywords appear in skill
        keyword_matches = sum(1 for kw in feature.keywords 
                            if any(kw.lower() in ak for ak in all_keywords_lower))
        
        coverage_percentage = keyword_matches / len(feature.keywords) * 100
        
        # Determine gap type
        if coverage_percentage == 0:
            gap_type = "missing"
            score = feature.severity == "HIGH" and 90 or (feature.severity == "MEDIUM" and 60 or 30)
        elif coverage_percentage < 50:
            gap_type = "unclear"
            score = feature.severity == "HIGH" and 70 or (feature.severity == "MEDIUM" and 45 or 20)
        elif coverage_percentage < 100:
            gap_type = "outdated"
            score = feature.severity == "HIGH" and 50 or (feature.severity == "MEDIUM" and 30 or 10)
        else:
            continue  # Feature is fully covered
        
        # Find what coverage exists
        current_coverage = " | ".join([k for k in all_keywords 
                                     if any(fw.lower() in k.lower() for fw in feature.keywords)][:3])
        if not current_coverage:
            current_coverage = "(not found)"
        
        gap = Gap(
            feature=feature,
            gap_type=gap_type,
            skill_name=skill_name,
            current_coverage=current_coverage,
            recommendation=f"Add/clarify: {feature.name}",
            score=score
        )
        gaps.append(gap)
    
    # Sort by score (highest = most important)
    return sorted(gaps, key=lambda g: g.score, reverse=True)


def format_gap_report(gaps: List[Gap], skill_name: str, verbose: bool = False) -> str:
    """Format gaps as human-readable report."""
    if not gaps:
        return f"✅ {skill_name}: No gaps detected! All features covered."
    
    report = f"\n{'='*70}\n"
    report += f"📊 GAP REPORT: {skill_name}\n"
    report += f"{'='*70}\n"
    report += f"Total gaps: {len(gaps)} | High severity: {sum(1 for g in gaps if g.feature.severity == 'HIGH')}\n"
    report += f"{'─'*70}\n\n"
    
    for i, gap in enumerate(gaps[:10], 1):  # Top 10 gaps
        report += f"{i}. {gap.feature.name}\n"
        report += f"   Status: {gap.gap_type.upper()}\n"
        report += f"   Severity: {gap.feature.severity} | Priority score: {gap.score:.0f}/100\n"
        report += f"   Category: {gap.feature.category}\n"
        report += f"   Released: {gap.feature.released}\n"
        
        if verbose:
            report += f"   Current coverage: {gap.current_coverage}\n"
            report += f"   Keywords to cover: {', '.join(gap.feature.keywords[:3])}\n"
        
        report += f"   📝 Action: {gap.recommendation}\n"
        report += f"   🔗 Docs: {gap.feature.docs_link}\n\n"
    
    if len(gaps) > 10:
        report += f"... and {len(gaps) - 10} more gaps (use --detail to see all)\n"
    
    return report


def generate_html_report(all_skills_gaps: Dict[str, List[Gap]]) -> str:
    """Generate an HTML dashboard of gaps across all skills."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Databricks Skills Gap Report</title>
    <style>
        body { font-family: -apple-system, system-ui; margin: 20px; background: #f5f5f5; }
        h1 { color: #1f77b4; }
        .skill-section { background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .gap { background: #fafafa; padding: 12px; margin: 10px 0; border-left: 4px solid #ff7f0e; }
        .gap.high { border-left-color: #d62728; }
        .gap.medium { border-left-color: #ff7f0e; }
        .gap.low { border-left-color: #2ca02c; }
        .feature-name { font-weight: bold; font-size: 14px; }
        .score { display: inline-block; background: #1f77b4; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 10px; }
        .timestamp { color: #888; font-size: 12px; }
    </style>
</head>
<body>
    <h1>🎯 Databricks Skills Gap Report</h1>
    <p class="timestamp">Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
"""
    
    # Summary
    total_gaps = sum(len(gaps) for gaps in all_skills_gaps.values())
    high_gaps = sum(1 for gaps in all_skills_gaps.values() for g in gaps if g.feature.severity == "HIGH")
    
    html += f"""
    <div style="background: #e8f4f8; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <h3>Summary</h3>
        <p><strong>Total gaps:</strong> {total_gaps} | <strong>High severity:</strong> {high_gaps}</p>
    </div>
"""
    
    # Per-skill details
    for skill_name in sorted(all_skills_gaps.keys()):
        gaps = all_skills_gaps[skill_name]
        high_count = sum(1 for g in gaps if g.feature.severity == "HIGH")
        
        html += f"""
    <div class="skill-section">
        <h2>{skill_name}</h2>
        <p>Gaps: {len(gaps)} ({high_count} high priority)</p>
"""
        
        for gap in gaps[:5]:  # Top 5 per skill
            html += f"""
        <div class="gap {gap.feature.severity.lower()}">
            <div class="feature-name">{gap.feature.name} <span class="score">{gap.score:.0f}</span></div>
            <p>{gap.gap_type.upper()}: {gap.recommendation}</p>
            <small><a href="{gap.feature.docs_link}" target="_blank">📖 Docs</a></small>
        </div>
"""
        
        if len(gaps) > 5:
            html += f"<p><em>... and {len(gaps) - 5} more</em></p>"
        
        html += "</div>\n"
    
    html += "</body></html>"
    return html


def main():
    import sys
    
    skill_name = None
    verbose = False
    report_format = "text"
    
    # Parse CLI args
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--skill" and i + 1 < len(sys.argv):
            skill_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--detail":
            verbose = True
            i += 1
        elif sys.argv[i] == "--report" and i + 1 < len(sys.argv):
            report_format = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # Run gap detection
    if skill_name:
        # Single skill
        skill_content, skill_path = load_skill(skill_name)
        gaps = detect_gaps(skill_name, skill_content)
        print(format_gap_report(gaps, skill_name, verbose=verbose))
    else:
        # All skills
        all_skills_gaps = {}
        skill_dirs = [SKILLS_DIR, PI_SKILLS_DIR]
        
        for skill_dir in skill_dirs:
            if not skill_dir.exists():
                continue
            for skill_path in skill_dir.iterdir():
                if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                    sname = skill_path.name
                    try:
                        skill_content, _ = load_skill(sname)
                        gaps = detect_gaps(sname, skill_content)
                        if gaps:  # Only include skills with gaps
                            all_skills_gaps[sname] = gaps
                    except:
                        pass
        
        if report_format == "html":
            print(generate_html_report(all_skills_gaps))
        else:
            # Text report
            print("\n" + "="*70)
            print("🎯 DATABRICKS SKILLS GAP DETECTOR")
            print("="*70)
            print(f"Analyzed: {len(all_skills_gaps)} skills with gaps")
            print(f"Total gaps: {sum(len(g) for g in all_skills_gaps.values())}")
            print("="*70)
            
            for skill_name in sorted(all_skills_gaps.keys()):
                gaps = all_skills_gaps[skill_name]
                print(format_gap_report(gaps, skill_name, verbose=verbose))


if __name__ == "__main__":
    main()
