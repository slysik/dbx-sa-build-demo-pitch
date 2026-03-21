#!/usr/bin/env python3
"""
Experiment Loop with Multi-Model Consistency Gates

Controls the keep/discard decision using rules:
- Improvement must be consistent across ≥2 models
- Discard fragile improvements (only 1 model improves)
- Track multi-model consensus

Usage:
    python experiment_loop.py spark-declarative-pipelines --baseline
    python experiment_loop.py databricks-bundles --test-improvement
"""

import json
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict

RESULTS_DIR = Path(__file__).parent / "results"
SKILLS_DIR = Path(__file__).parent.parent / ".agents" / "skills"

# Model tier configuration
MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}

# Consistency gate rules
RULES = {
    "min_models_improve": 2,  # At least 2 of 3 models must improve
    "min_improvement": 0.1,   # At least 0.1 point improvement
    "direction_consistency": True,  # All improving models go same direction
}


def run_eval_all_models(skill_name: str, verbose: bool = True) -> Dict[str, float]:
    """
    Run evaluation against all three model tiers.
    Returns {model_name: fts_score}
    """
    results = {}
    
    for tier, model_id in MODELS.items():
        if verbose:
            print(f"\n  [{tier}] {model_id}...", end=" ", flush=True)
        
        env = os.environ.copy()
        env["EVAL_MODEL"] = model_id
        
        try:
            result = subprocess.run(
                ["python3", "eval_harness.py", skill_name],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
            
            # Extract FTS from output
            for line in result.stdout.split("\n"):
                if "FTS:" in line and "/10" in line:
                    fts_str = line.split("FTS:")[1].split("/10")[0].strip()
                    fts = float(fts_str)
                    results[tier] = fts
                    if verbose:
                        print(f"FTS={fts:.2f}")
                    break
        except subprocess.TimeoutExpired:
            results[tier] = 0.0
            if verbose:
                print("TIMEOUT")
        except Exception as e:
            results[tier] = 0.0
            if verbose:
                print(f"ERROR: {e}")
    
    return results


def compare_baselines(skill_name: str, baseline_results: Dict[str, float],
                     new_results: Dict[str, float]) -> Tuple[bool, str]:
    """
    Apply consistency gates: decide KEEP or DISCARD.
    
    Returns (keep_decision: bool, explanation: str)
    """
    improvements = {}
    for model_tier in baseline_results:
        old_fts = baseline_results[model_tier]
        new_fts = new_results[model_tier]
        improvement = new_fts - old_fts
        improvements[model_tier] = improvement
    
    # Count how many models improved
    improved_count = sum(1 for imp in improvements.values() if imp >= RULES["min_improvement"])
    
    # Get improvement directions
    directions = {k: "↑" if v > 0 else "↓" for k, v in improvements.items()}
    
    # Decision logic
    if improved_count >= RULES["min_models_improve"]:
        # Check consistency: are improvements all same direction?
        directions_set = set(directions.values())
        if len(directions_set) == 1 or "↑" not in directions.values():
            explanation = (
                f"✅ KEEP — {improved_count}/{len(improvements)} models improved consistently\n"
                f"   haiku:  {baseline_results['haiku']:.2f} → {new_results['haiku']:.2f} "
                f"({improvements['haiku']:+.2f}) {directions['haiku']}\n"
                f"   sonnet: {baseline_results['sonnet']:.2f} → {new_results['sonnet']:.2f} "
                f"({improvements['sonnet']:+.2f}) {directions['sonnet']}\n"
                f"   opus:   {baseline_results['opus']:.2f} → {new_results['opus']:.2f} "
                f"({improvements['opus']:+.2f}) {directions['opus']}"
            )
            return True, explanation
        else:
            explanation = (
                f"⚠️  FRAGILE — improvements in conflicting directions\n"
                f"   haiku:  {baseline_results['haiku']:.2f} → {new_results['haiku']:.2f} "
                f"({improvements['haiku']:+.2f}) {directions['haiku']}\n"
                f"   sonnet: {baseline_results['sonnet']:.2f} → {new_results['sonnet']:.2f} "
                f"({improvements['sonnet']:+.2f}) {directions['sonnet']}\n"
                f"   opus:   {baseline_results['opus']:.2f} → {new_results['opus']:.2f} "
                f"({improvements['opus']:+.2f}) {directions['opus']}\n"
                f"   DISCARD — model disagreement signals unclear skill guidance"
            )
            return False, explanation
    else:
        explanation = (
            f"❌ DISCARD — only {improved_count}/{len(improvements)} models improved "
            f"(need ≥{RULES['min_models_improve']})\n"
            f"   haiku:  {baseline_results['haiku']:.2f} → {new_results['haiku']:.2f} "
            f"({improvements['haiku']:+.2f}) {directions['haiku']}\n"
            f"   sonnet: {baseline_results['sonnet']:.2f} → {new_results['sonnet']:.2f} "
            f"({improvements['sonnet']:+.2f}) {directions['sonnet']}\n"
            f"   opus:   {baseline_results['opus']:.2f} → {new_results['opus']:.2f} "
            f"({improvements['opus']:+.2f}) {directions['opus']}\n"
            f"   Single-model improvements are fragile — skill explanation is ambiguous"
        )
        return False, explanation


def get_baseline(skill_name: str) -> Dict[str, float]:
    """Get current baseline FTS for all models."""
    baseline_file = RESULTS_DIR / f"{skill_name}-baseline.json"
    
    if baseline_file.exists():
        return json.loads(baseline_file.read_text())
    
    # If no baseline, run one
    print(f"\n📊 Computing baseline for {skill_name}...")
    baseline = run_eval_all_models(skill_name, verbose=True)
    
    baseline_file.write_text(json.dumps(baseline, indent=2))
    print(f"\n✓ Baseline saved: {baseline_file}")
    
    return baseline


def log_experiment(skill_name: str, baseline: Dict[str, float], 
                  new_scores: Dict[str, float], decision: str, 
                  description: str) -> None:
    """Log experiment to TSV."""
    tsv_path = RESULTS_DIR / f"{skill_name}-multimodel.tsv"
    
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    ).stdout.strip()
    
    header = "commit\tdecision\tdescription\thaiku_before\thaiku_after\tsonnet_before\tsonnet_after\topus_before\topus_after\n"
    
    row = (
        f"{commit}\t{decision}\t{description}\t"
        f"{baseline['haiku']:.2f}\t{new_scores['haiku']:.2f}\t"
        f"{baseline['sonnet']:.2f}\t{new_scores['sonnet']:.2f}\t"
        f"{baseline['opus']:.2f}\t{new_scores['opus']:.2f}\n"
    )
    
    if not tsv_path.exists():
        tsv_path.write_text(header + row)
    else:
        tsv_path.write_text(tsv_path.read_text() + row)
    
    print(f"\n✓ Logged to {tsv_path.name}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python experiment_loop.py <skill> --baseline")
        print("  python experiment_loop.py <skill> --test <description>")
        print("\nExample:")
        print("  python experiment_loop.py databricks-bundles --baseline")
        print("  python experiment_loop.py databricks-bundles --test 'added --only flag'")
        sys.exit(1)
    
    skill_name = sys.argv[1]
    
    if sys.argv[2] == "--baseline":
        print(f"\n{'='*60}")
        print(f"ESTABLISHING BASELINE: {skill_name}")
        print(f"{'='*60}")
        
        baseline = run_eval_all_models(skill_name, verbose=True)
        
        baseline_file = RESULTS_DIR / f"{skill_name}-baseline.json"
        baseline_file.write_text(json.dumps(baseline, indent=2))
        
        print(f"\n{'─'*60}")
        print(f"✅ Baseline established:")
        for model, fts in baseline.items():
            print(f"   {model:10s}: {fts:.2f}/10")
        print(f"{'─'*60}")
    
    elif sys.argv[2] == "--test":
        description = sys.argv[3] if len(sys.argv) > 3 else "experimental change"
        
        print(f"\n{'='*60}")
        print(f"TESTING CHANGE: {skill_name}")
        print(f"Description: {description}")
        print(f"{'='*60}")
        
        baseline = get_baseline(skill_name)
        
        print(f"\n📊 Evaluating new version...")
        new_scores = run_eval_all_models(skill_name, verbose=True)
        
        keep_it, explanation = compare_baselines(skill_name, baseline, new_scores)
        
        print(f"\n{'─'*60}")
        print(explanation)
        print(f"{'─'*60}")
        
        decision = "KEEP" if keep_it else "DISCARD"
        log_experiment(skill_name, baseline, new_scores, decision, description)
        
        if keep_it:
            # Update baseline
            baseline_file = RESULTS_DIR / f"{skill_name}-baseline.json"
            baseline_file.write_text(json.dumps(new_scores, indent=2))
            print(f"\n✅ Baseline updated: {new_scores}")
        else:
            print(f"\n↩️  Baseline unchanged — revert changes and try different approach")
        
        return 0 if keep_it else 1


if __name__ == "__main__":
    sys.exit(main())
