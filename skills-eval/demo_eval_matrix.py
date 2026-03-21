#!/usr/bin/env python3
"""
Demo Eval Matrix Scorer — Evaluate demo quality on SA/SC/PF/TE/BP/CP axes

Implements the Sa-to-spear SA demo eval rubric:
- SA: Spec alignment (0-3)
- SC: Simplicity/clarity (0-3)
- PF: Performance (0-3)
- TE: Token efficiency (0-3)
- BP: Best practices (0-3)
- CP: Composability (0-3, optional)

FTS_matrix = 0.30*SA' + 0.25*SC' + 0.20*PF' + 0.10*TE' + 0.15*BP'
(normalized to 0-1, then multiply by 100 for 0-100 scale)

Demo is "ready" if: SA ≥ 2, SC ≥ 2, PF ≥ 2, BP ≥ 2, and FTS_matrix ≥ 0.70

Usage:
    python3 demo_eval_matrix.py databricks-bundles
    python3 demo_eval_matrix.py --skill spark-declarative-pipelines --verbose
    python3 demo_eval_matrix.py --interactive
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime

@dataclass
class DemoScore:
    skill_name: str
    sa: float  # Spec alignment (0-3)
    sc: float  # Simplicity/clarity (0-3)
    pf: float  # Performance (0-3)
    te: float  # Token efficiency (0-3)
    bp: float  # Best practices (0-3)
    cp: float = 0.0  # Composability (0-3, optional)
    
    timestamp: str = ""
    notes: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def normalize(self) -> Dict[str, float]:
        """Normalize scores to 0-1 scale."""
        return {
            "sa_norm": self.sa / 3.0,
            "sc_norm": self.sc / 3.0,
            "pf_norm": self.pf / 3.0,
            "te_norm": self.te / 3.0,
            "bp_norm": self.bp / 3.0,
            "cp_norm": self.cp / 3.0 if self.cp > 0 else 0.0,
        }
    
    def fts_matrix(self) -> float:
        """Calculate weighted FTS_matrix (0-1 scale)."""
        norm = self.normalize()
        
        # Weighted average (CP is optional, so not included in default)
        fts = (
            0.30 * norm["sa_norm"] +
            0.25 * norm["sc_norm"] +
            0.20 * norm["pf_norm"] +
            0.10 * norm["te_norm"] +
            0.15 * norm["bp_norm"]
        )
        
        return round(fts, 3)
    
    def fts_matrix_100(self) -> float:
        """FTS_matrix on 0-100 scale."""
        return round(self.fts_matrix() * 100, 1)
    
    def is_demo_ready(self) -> bool:
        """Check if demo meets thresholds: SA≥2, SC≥2, PF≥2, BP≥2, FTS≥0.70."""
        return (
            self.sa >= 2.0 and
            self.sc >= 2.0 and
            self.pf >= 2.0 and
            self.bp >= 2.0 and
            self.fts_matrix() >= 0.70
        )
    
    def format_report(self, verbose: bool = False) -> str:
        """Format as human-readable report."""
        norm = self.normalize()
        fts = self.fts_matrix_100()
        status = "✅ DEMO-READY" if self.is_demo_ready() else "⚠️ NEEDS WORK"
        
        report = f"\n{'='*70}\n"
        report += f"📊 DEMO EVAL MATRIX: {self.skill_name}\n"
        report += f"{'='*70}\n"
        report += f"Status: {status}  |  FTS_matrix: {fts}/100\n"
        report += f"Timestamp: {self.timestamp}\n"
        report += f"{'─'*70}\n\n"
        
        report += "AXIS SCORES (0-3 scale):\n"
        report += f"  SA — Spec alignment          {self._score_bar(self.sa)} {self.sa:.1f}/3\n"
        report += f"  SC — Simplicity/clarity     {self._score_bar(self.sc)} {self.sc:.1f}/3\n"
        report += f"  PF — Performance (demo)     {self._score_bar(self.pf)} {self.pf:.1f}/3\n"
        report += f"  TE — Token efficiency       {self._score_bar(self.te)} {self.te:.1f}/3\n"
        report += f"  BP — Best practices         {self._score_bar(self.bp)} {self.bp:.1f}/3\n"
        
        if self.cp > 0:
            report += f"  CP — Composability (opt)    {self._score_bar(self.cp)} {self.cp:.1f}/3\n"
        
        report += f"\n{'─'*70}\n"
        report += f"WEIGHTED FTS_MATRIX:\n"
        report += f"  Formula: 0.30*SA' + 0.25*SC' + 0.20*PF' + 0.10*TE' + 0.15*BP'\n"
        report += f"  = {self.fts_matrix():.3f} (0-1 scale) = {fts}/100\n"
        report += f"\n{'─'*70}\n"
        
        report += "DEMO-READY CHECKLIST:\n"
        report += f"  {'✅' if self.sa >= 2.0 else '❌'} SA ≥ 2.0  (Spec alignment)       {self.sa:.1f}\n"
        report += f"  {'✅' if self.sc >= 2.0 else '❌'} SC ≥ 2.0  (Simplicity)          {self.sc:.1f}\n"
        report += f"  {'✅' if self.pf >= 2.0 else '❌'} PF ≥ 2.0  (Performance)         {self.pf:.1f}\n"
        report += f"  {'✅' if self.bp >= 2.0 else '❌'} BP ≥ 2.0  (Best practices)      {self.bp:.1f}\n"
        report += f"  {'✅' if self.fts_matrix() >= 0.70 else '❌'} FTS_matrix ≥ 0.70                  {fts}/100\n"
        
        if self.is_demo_ready():
            report += f"\n✅ VERDICT: {self.skill_name.upper()} IS DEMO-READY\n"
        else:
            gaps = []
            if self.sa < 2.0: gaps.append(f"SA too low ({self.sa:.1f})")
            if self.sc < 2.0: gaps.append(f"SC too low ({self.sc:.1f})")
            if self.pf < 2.0: gaps.append(f"PF too low ({self.pf:.1f})")
            if self.bp < 2.0: gaps.append(f"BP too low ({self.bp:.1f})")
            if self.fts_matrix() < 0.70: gaps.append(f"FTS_matrix too low ({fts}/100)")
            
            report += f"\n❌ NEEDS WORK:\n"
            for gap in gaps:
                report += f"   • {gap}\n"
        
        if self.notes:
            report += f"\nNOTES: {self.notes}\n"
        
        report += f"{'='*70}\n"
        return report
    
    def _score_bar(self, score: float) -> str:
        """Visual bar for 0-3 score."""
        filled = int(score / 3.0 * 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty
    
    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization."""
        return {
            "skill": self.skill_name,
            "timestamp": self.timestamp,
            "scores": {
                "sa": self.sa,
                "sc": self.sc,
                "pf": self.pf,
                "te": self.te,
                "bp": self.bp,
                "cp": self.cp if self.cp > 0 else None,
            },
            "fts_matrix": self.fts_matrix(),
            "fts_matrix_100": self.fts_matrix_100(),
            "is_demo_ready": self.is_demo_ready(),
            "notes": self.notes,
        }


def interactive_score() -> DemoScore:
    """Interactive scoring mode."""
    print("\n" + "="*70)
    print("📊 INTERACTIVE DEMO EVAL MATRIX SCORER")
    print("="*70 + "\n")
    
    skill = input("Skill name: ").strip()
    
    print("\nScore each axis 0-3 (0=missing, 1=poor, 2=good, 3=excellent)\n")
    
    sa = float(input("SA — Spec alignment (does it solve the problem?): "))
    sc = float(input("SC — Simplicity/clarity (easy to explain in 2-3 bullets?): "))
    pf = float(input("PF — Performance (demo-sized data, fast?): "))
    te = float(input("TE — Token efficiency (low waste, focused?): "))
    bp = float(input("BP — Best practices (Databricks 2026 patterns?): "))
    cp_str = input("CP — Composability (optional, reusable?): ")
    cp = float(cp_str) if cp_str.strip() else 0.0
    
    notes = input("\nNotes (optional): ").strip()
    
    return DemoScore(skill, sa, sc, pf, te, bp, cp, notes=notes)


def score_from_args(skill_name: str) -> DemoScore:
    """Pre-defined scores for known skills (demo purposes)."""
    
    # Example baselines from finserv_lakehouse
    baseline_scores = {
        "spark-declarative-pipelines": DemoScore(
            skill_name="spark-declarative-pipelines",
            sa=3.0,  # Perfectly solves medallion requirement
            sc=2.5,  # Clear SQL patterns
            pf=3.0,  # Runs in <60s serverless
            te=2.0,  # Some redundant MVs
            bp=3.0,  # Liquid Clustering, UC, Delta
            notes="Strong demo-ready skill"
        ),
        "databricks-bundles": DemoScore(
            skill_name="databricks-bundles",
            sa=2.5,  # Mostly solves deployment
            sc=2.0,  # Needs clearer structure
            pf=2.5,  # Deploy works, could be faster
            te=2.0,  # Some verbosity
            bp=2.5,  # Mostly best-practices
            notes="Good but needs tightening"
        ),
    }
    
    if skill_name in baseline_scores:
        return baseline_scores[skill_name]
    else:
        # Prompt for manual scoring
        print(f"\n⚠️ No baseline for {skill_name}. Entering interactive mode...\n")
        score = interactive_score()
        score.skill_name = skill_name
        return score


def save_score(score: DemoScore, results_dir: Path = None):
    """Save score to JSON file."""
    if results_dir is None:
        results_dir = Path(__file__).parent / "results"
    
    results_dir.mkdir(exist_ok=True)
    
    score_file = results_dir / f"{score.skill_name}-demo-score.json"
    score_file.write_text(json.dumps(score.to_dict(), indent=2))
    
    print(f"✓ Saved: {score_file}")


def load_score(skill_name: str, results_dir: Path = None) -> DemoScore:
    """Load previous score."""
    if results_dir is None:
        results_dir = Path(__file__).parent / "results"
    
    score_file = results_dir / f"{skill_name}-demo-score.json"
    
    if not score_file.exists():
        return None
    
    data = json.loads(score_file.read_text())
    return DemoScore(
        skill_name=data["skill"],
        sa=data["scores"]["sa"],
        sc=data["scores"]["sc"],
        pf=data["scores"]["pf"],
        te=data["scores"]["te"],
        bp=data["scores"]["bp"],
        cp=data["scores"].get("cp") or 0.0,
        timestamp=data["timestamp"],
        notes=data.get("notes", ""),
    )


def compare_scores(skill_name: str, old_score: DemoScore, new_score: DemoScore) -> str:
    """Compare two evaluations."""
    report = f"\n{'='*70}\n"
    report += f"📈 COMPARISON: {skill_name}\n"
    report += f"{'='*70}\n\n"
    
    report += f"{'Axis':<15} {'Old':<10} {'New':<10} {'Change':<10}\n"
    report += f"{'-'*45}\n"
    
    for axis, attr in [("SA", "sa"), ("SC", "sc"), ("PF", "pf"), ("TE", "te"), ("BP", "bp")]:
        old_val = getattr(old_score, attr)
        new_val = getattr(new_score, attr)
        change = new_val - old_val
        symbol = "↑" if change > 0 else ("↓" if change < 0 else "=")
        
        report += f"{axis:<15} {old_val:<10.1f} {new_val:<10.1f} {symbol} {change:+.1f}\n"
    
    old_fts = old_score.fts_matrix_100()
    new_fts = new_score.fts_matrix_100()
    fts_change = new_fts - old_fts
    
    report += f"{'-'*45}\n"
    report += f"{'FTS_matrix':<15} {old_fts:<10.1f} {new_fts:<10.1f} {fts_change:+.1f}\n"
    
    report += f"\n{'VERDICT':<15}\n"
    
    if old_score.is_demo_ready() and new_score.is_demo_ready():
        report += "✅ Both demo-ready, improvement confirmed\n"
    elif not old_score.is_demo_ready() and new_score.is_demo_ready():
        report += "✅ PROMOTED to demo-ready!\n"
    elif old_score.is_demo_ready() and not new_score.is_demo_ready():
        report += "❌ REGRESSION: was demo-ready, no longer\n"
    else:
        if fts_change > 0:
            report += f"✅ Improvement (+{fts_change:.1f}/100), still needs work\n"
        else:
            report += f"❌ No improvement, needs different approach\n"
    
    report += f"{'='*70}\n"
    return report


def main():
    import sys
    
    skill_name = None
    verbose = False
    interactive = False
    compare_skill = None
    
    # Parse args
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--skill" and i + 1 < len(sys.argv):
            skill_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--verbose":
            verbose = True
            i += 1
        elif sys.argv[i] == "--interactive":
            interactive = True
            i += 1
        elif sys.argv[i] == "--compare" and i + 1 < len(sys.argv):
            compare_skill = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    if interactive or not skill_name:
        score = interactive_score()
    else:
        score = score_from_args(skill_name)
    
    # Print report
    print(score.format_report(verbose=verbose))
    
    # Save score
    save_score(score)
    
    # Compare if requested
    if compare_skill:
        old_score = load_score(compare_skill)
        if old_score:
            print(compare_scores(skill_name or score.skill_name, old_score, score))
        else:
            print(f"⚠️ No previous score found for {compare_skill}")


if __name__ == "__main__":
    main()
