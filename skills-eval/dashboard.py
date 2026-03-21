#!/usr/bin/env python3
"""
Skills Eval Dashboard — Live visualization of Databricks skill optimization.

Reads results/*.tsv and results/*-last-run.json, serves at http://localhost:8502.
Auto-refreshes every 15s. No dependencies beyond stdlib.

Usage:
    python skills-eval/dashboard.py
    python skills-eval/dashboard.py --port 8502
"""

import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR   = Path(__file__).parent / "results"
SKILLS_DIR = Path(__file__).parent.parent / ".agents" / "skills"

SKILL_META = {
    "spark-declarative-pipelines": {"short": "SDP",          "color": "#c0784a"},
    "databricks-aibi-dashboards":  {"short": "AI/BI Dash",   "color": "#2980b9"},
    "synthetic-data-generation":   {"short": "Synth Data",   "color": "#27ae60"},
    "databricks-genie":            {"short": "Genie",         "color": "#8e44ad"},
    "databricks-bundles":          {"short": "Bundles",       "color": "#d35400"},
}

# ── HTML ───────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skills Eval — Databricks Coding Agent</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #faf9f7; color: #2d2a26; padding: 32px;
         max-width: 1280px; margin: 0 auto; }

  /* ── Header ── */
  .header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 28px; }
  .header h1 { font-size: 26px; font-weight: 700; }
  .header-right { text-align: right; }
  .badge { display: inline-block; background: #c0784a; color: white; font-size: 11px;
           font-weight: 700; padding: 3px 10px; border-radius: 4px; letter-spacing: 1px; }
  .subtitle { color: #8a8580; font-size: 13px; margin-top: 6px; }

  /* ── Summary stats ── */
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }
  .stat-card { background: white; border-radius: 12px; padding: 18px 22px;
               box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  .stat-label { font-size: 11px; font-weight: 600; text-transform: uppercase;
                letter-spacing: 1px; color: #8a8580; margin-bottom: 6px; }
  .stat-value { font-size: 34px; font-weight: 700; }
  .orange { color: #c0784a; } .green { color: #27ae60; }
  .blue { color: #2980b9; } .neutral { color: #2d2a26; }

  /* ── Skill cards ── */
  .skill-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 24px; }
  .skill-card { background: white; border-radius: 12px; padding: 16px 18px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                border-top: 3px solid var(--accent); }
  .skill-name { font-size: 11px; font-weight: 600; text-transform: uppercase;
                letter-spacing: 1px; color: #8a8580; margin-bottom: 8px; }
  .skill-fts  { font-size: 30px; font-weight: 700; color: var(--accent); line-height: 1; }
  .skill-fts-label { font-size: 11px; color: #8a8580; margin-top: 2px; }
  .skill-delta { font-size: 13px; font-weight: 600; margin-top: 6px; }
  .skill-tokens { font-size: 11px; color: #8a8580; margin-top: 4px; }
  .progress-bg { background: #f0efed; border-radius: 4px; height: 4px; margin-top: 10px; }
  .progress-fill { height: 4px; border-radius: 4px; background: var(--accent);
                   transition: width 0.6s ease; }

  /* ── Charts ── */
  .chart-row { display: grid; grid-template-columns: 2fr 1fr; gap: 14px; margin-bottom: 24px; }
  .panel { background: white; border-radius: 12px; padding: 22px 24px;
           box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  .panel h3 { font-size: 11px; font-weight: 600; text-transform: uppercase;
              letter-spacing: 1px; color: #8a8580; margin-bottom: 16px; }
  .panel canvas { width: 100% !important; }
  .tall { height: 280px; }
  .medium { height: 200px; }

  /* ── Criteria breakdown ── */
  .criteria-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 24px; }
  .criteria-card { background: white; border-radius: 12px; padding: 16px 18px;
                   box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  .criteria-card h4 { font-size: 11px; font-weight: 600; text-transform: uppercase;
                      letter-spacing: 1px; color: #8a8580; margin-bottom: 10px; }
  .criteria-card canvas { width: 100% !important; height: 100px !important; }
  .crit-row { display: flex; justify-content: space-between; align-items: center;
              padding: 4px 0; border-bottom: 1px solid #f5f4f2; font-size: 12px; }
  .crit-row:last-child { border-bottom: none; }
  .crit-name { color: #4a4540; }
  .crit-score { font-weight: 600; }
  .crit-bar-wrap { flex: 1; margin: 0 8px; background: #f0efed; border-radius: 3px; height: 4px; }
  .crit-bar { height: 4px; border-radius: 3px; }

  /* ── Table ── */
  .table-panel { background: white; border-radius: 12px; padding: 22px 24px;
                 box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  .table-panel h3 { font-size: 11px; font-weight: 600; text-transform: uppercase;
                    letter-spacing: 1px; color: #8a8580; margin-bottom: 14px; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase;
       letter-spacing: 1px; color: #8a8580; padding: 7px 10px; border-bottom: 1px solid #eee; }
  td { padding: 9px 10px; border-bottom: 1px solid #f5f4f2; font-size: 13px; }
  .status-keep    { color: #27ae60; font-weight: 600; font-size: 11px; }
  .status-discard { color: #8a8580; font-size: 11px; }
  .status-crash   { color: #e74c3c; font-weight: 600; font-size: 11px; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 10px;
          font-size: 11px; font-weight: 600; }
  .pill-sdp  { background: rgba(192,120,74,.12); color: #c0784a; }
  .pill-aibi { background: rgba(41,128,185,.12); color: #2980b9; }
  .pill-syn  { background: rgba(39,174,96,.12);  color: #27ae60; }
  .pill-genie{ background: rgba(142,68,173,.12); color: #8e44ad; }
  .pill-bun  { background: rgba(211,84,0,.12);   color: #d35400; }
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Skills Eval Tracker</h1>
    <div class="subtitle">Databricks Coding Agent — Karpathy autoresearch pattern</div>
  </div>
  <div class="header-right">
    <span class="badge" id="live-badge">LIVE</span>
    <div class="subtitle" id="last-updated">—</div>
  </div>
</div>

<!-- Summary stats -->
<div class="stats">
  <div class="stat-card">
    <div class="stat-label">Avg Best FTS</div>
    <div class="stat-value orange" id="stat-avg">—</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Total Experiments</div>
    <div class="stat-value neutral" id="stat-total">—</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Kept</div>
    <div class="stat-value green" id="stat-kept">—</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Discarded / Crashed</div>
    <div class="stat-value neutral" id="stat-disc">—</div>
  </div>
</div>

<!-- Skill leaderboard cards -->
<div class="skill-cards" id="skill-cards"></div>

<!-- Main trend chart + token efficiency -->
<div class="chart-row">
  <div class="panel">
    <h3>FTS Trend by Skill</h3>
    <canvas id="trendChart" class="tall"></canvas>
  </div>
  <div class="panel">
    <h3>Token Efficiency</h3>
    <canvas id="tokenChart" class="tall"></canvas>
  </div>
</div>

<!-- Per-skill last-run criteria breakdown -->
<div style="margin-bottom:8px">
  <span style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#8a8580">
    Last Run — Per-Prompt Criteria (most recent eval)
  </span>
</div>
<div class="criteria-row" id="criteria-row"></div>

<!-- Experiment log -->
<div class="table-panel">
  <h3>Experiment Log</h3>
  <table>
    <thead>
      <tr>
        <th>Skill</th><th>Commit</th><th>FTS</th>
        <th>Tokens</th><th>Status</th><th>Description</th>
      </tr>
    </thead>
    <tbody id="exp-table"></tbody>
  </table>
</div>

<script>
const SKILL_META = __SKILL_META__;
const CRIT_MAX   = { correct_imports: 1, no_antipatterns: 2, pattern_adherence: 3, completeness: 2, first_try_runnable: 2 };
const CRIT_LABEL = { correct_imports: "Imports", no_antipatterns: "No Anti-patterns", pattern_adherence: "Pattern", completeness: "Complete", first_try_runnable: "Runnable" };
const PILL_CLASS = {
  "spark-declarative-pipelines": "pill-sdp",
  "databricks-aibi-dashboards":  "pill-aibi",
  "synthetic-data-generation":   "pill-syn",
  "databricks-genie":            "pill-genie",
  "databricks-bundles":          "pill-bun",
};

let trendChart, tokenChart;

function hex(color, a) {
  const r = parseInt(color.slice(1,3),16), g = parseInt(color.slice(3,5),16), b = parseInt(color.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

function initCharts() {
  const trendCtx = document.getElementById('trendChart').getContext('2d');
  trendChart = new Chart(trendCtx, {
    type: 'line',
    data: { datasets: [] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, boxWidth: 12 } } },
      scales: {
        x: { type: 'linear', title: { display: true, text: 'Experiment #', font: { size: 11 }, color: '#8a8580' },
             grid: { display: false }, ticks: { font: { size: 11 }, color: '#8a8580' } },
        y: { min: 0, max: 10, title: { display: true, text: 'FTS (0–10)', font: { size: 11 }, color: '#8a8580' },
             grid: { color: '#f0efed' }, ticks: { font: { size: 11 }, color: '#8a8580', stepSize: 2 } }
      }
    }
  });

  const tokCtx = document.getElementById('tokenChart').getContext('2d');
  tokenChart = new Chart(tokCtx, {
    type: 'scatter',
    data: { datasets: [] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, boxWidth: 12 } } },
      scales: {
        x: { title: { display: true, text: 'Skill Tokens', font: { size: 11 }, color: '#8a8580' },
             grid: { color: '#f0efed' }, ticks: { font: { size: 11 }, color: '#8a8580' } },
        y: { min: 0, max: 10, title: { display: true, text: 'FTS', font: { size: 11 }, color: '#8a8580' },
             grid: { color: '#f0efed' }, ticks: { font: { size: 11 }, color: '#8a8580', stepSize: 2 } }
      }
    }
  });
}

function updateSkillCards(skills) {
  const container = document.getElementById('skill-cards');
  container.innerHTML = '';
  for (const [skill, d] of Object.entries(skills)) {
    const meta  = SKILL_META[skill] || { short: skill, color: '#888' };
    const best  = d.current_fts ?? 0;
    const base  = d.baseline_fts ?? 0;
    const delta = (best - base).toFixed(1);
    const pct   = Math.round((best / 10) * 100);
    container.innerHTML += `
      <div class="skill-card" style="--accent:${meta.color}">
        <div class="skill-name">${meta.short}</div>
        <div class="skill-fts">${best.toFixed(1)}</div>
        <div class="skill-fts-label">/ 10 FTS</div>
        <div class="skill-delta" style="color:${delta >= 0 ? '#27ae60' : '#e74c3c'}">
          ${delta >= 0 ? '▲' : '▼'} ${Math.abs(delta)} from baseline
        </div>
        <div class="skill-tokens">${(d.skill_tokens||0).toLocaleString()} tokens</div>
        <div class="progress-bg"><div class="progress-fill" style="width:${pct}%"></div></div>
      </div>`;
  }
}

function updateTrendChart(skills) {
  const datasets = [];
  for (const [skill, d] of Object.entries(skills)) {
    const meta = SKILL_META[skill] || { short: skill, color: '#888' };
    const kept = (d.experiments||[]).filter(e => e.status !== 'crash');
    if (!kept.length) continue;
    datasets.push({
      label: meta.short,
      data: kept.map((e, i) => ({ x: i + 1, y: e.fts })),
      borderColor: meta.color,
      backgroundColor: hex(meta.color, 0.08),
      fill: false, tension: 0.3,
      pointRadius: 5, pointBackgroundColor: meta.color,
      borderWidth: 2,
    });
  }
  trendChart.data.datasets = datasets;
  trendChart.update('none');
}

function updateTokenChart(skills) {
  const datasets = [];
  for (const [skill, d] of Object.entries(skills)) {
    const meta = SKILL_META[skill] || { short: skill, color: '#888' };
    const kept = (d.experiments||[]).filter(e => e.status === 'keep');
    if (!kept.length) continue;
    datasets.push({
      label: meta.short,
      data: kept.map(e => ({ x: e.skill_tokens, y: e.fts })),
      backgroundColor: hex(meta.color, 0.7),
      borderColor: meta.color,
      pointRadius: 6, pointHoverRadius: 8,
    });
  }
  tokenChart.data.datasets = datasets;
  tokenChart.update('none');
}

function updateCriteria(last_runs) {
  const container = document.getElementById('criteria-row');
  container.innerHTML = '';
  for (const [skill, run] of Object.entries(last_runs)) {
    const meta = SKILL_META[skill] || { short: skill, color: '#888' };
    if (!run || !run.prompts) continue;
    // Average criteria across prompts
    const avg = {};
    for (const crit of Object.keys(CRIT_MAX)) avg[crit] = 0;
    run.prompts.forEach(p => {
      for (const [c, v] of Object.entries(p.scores || {})) {
        if (c in avg) avg[c] += v;
      }
    });
    const n = run.prompts.length || 1;
    for (const c in avg) avg[c] = avg[c] / n;

    let rows = '';
    for (const [crit, label] of Object.entries(CRIT_LABEL)) {
      const score = avg[crit] || 0;
      const max   = CRIT_MAX[crit];
      const pct   = Math.round((score / max) * 100);
      const color = pct >= 80 ? '#27ae60' : pct >= 50 ? meta.color : '#e74c3c';
      rows += `<div class="crit-row">
        <span class="crit-name">${label}</span>
        <div class="crit-bar-wrap"><div class="crit-bar" style="width:${pct}%;background:${color}"></div></div>
        <span class="crit-score" style="color:${color}">${score.toFixed(1)}/${max}</span>
      </div>`;
    }
    container.innerHTML += `
      <div class="criteria-card">
        <h4 style="color:${meta.color}">${meta.short}</h4>
        ${rows}
        <div style="margin-top:8px;font-size:11px;color:#8a8580">
          FTS ${(run.fts||0).toFixed(2)} · ${(run.skill_tokens||0).toLocaleString()} tok
        </div>
      </div>`;
  }
}

function updateTable(all_experiments) {
  const tbody = document.getElementById('exp-table');
  const rows  = [...all_experiments].reverse().slice(0, 60);
  tbody.innerHTML = rows.map(e => {
    const meta = SKILL_META[e.skill] || { short: e.skill, color: '#888' };
    const pill = PILL_CLASS[e.skill] || '';
    const stClass = `status-${e.status}`;
    const stLabel = e.status.toUpperCase();
    return `<tr>
      <td><span class="pill ${pill}">${meta.short}</span></td>
      <td style="font-family:monospace;font-size:12px;color:#8a8580">${e.commit}</td>
      <td><strong>${(e.fts||0).toFixed(2)}</strong></td>
      <td style="color:#8a8580">${(e.skill_tokens||0).toLocaleString()}</td>
      <td><span class="${stClass}">${stLabel}</span></td>
      <td style="color:#4a4540;max-width:340px">${e.description}</td>
    </tr>`;
  }).join('');
}

function updateSummary(data) {
  const skills = data.skills || {};
  let total = 0, kept = 0, disc = 0, crash = 0, bestSum = 0, skillCount = 0;
  for (const d of Object.values(skills)) {
    (d.experiments||[]).forEach(e => {
      total++;
      if (e.status === 'keep')    kept++;
      else if (e.status === 'discard') disc++;
      else if (e.status === 'crash')   crash++;
    });
    if (d.current_fts != null) { bestSum += d.current_fts; skillCount++; }
  }
  document.getElementById('stat-avg').textContent   = skillCount ? (bestSum / skillCount).toFixed(1) + '/10' : '—';
  document.getElementById('stat-total').textContent  = total || '—';
  document.getElementById('stat-kept').textContent   = kept || '—';
  document.getElementById('stat-disc').textContent   = `${disc} / ${crash}`;

  const now = new Date();
  document.getElementById('last-updated').textContent =
    `Updated ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
}

async function refresh() {
  try {
    const res  = await fetch('/api/data');
    const data = await res.json();
    updateSummary(data);
    updateSkillCards(data.skills || {});
    updateTrendChart(data.skills || {});
    updateTokenChart(data.skills || {});
    updateCriteria(data.last_runs || {});
    updateTable(data.all_experiments || []);
  } catch(e) {
    console.error('Fetch error:', e);
  }
}

initCharts();
refresh();
setInterval(refresh, 15000);
</script>
</body>
</html>"""


# ── Data loading ───────────────────────────────────────────────────────────────
def parse_tsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text().strip().split("\n")
    if len(lines) < 2:
        return []
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < len(header):
            continue
        row = dict(zip(header, parts))
        try:
            row["FTS"]          = float(row["FTS"])
            row["skill_tokens"] = int(row["skill_tokens"])
        except (ValueError, KeyError):
            pass
        rows.append(row)
    return rows


def load_data() -> dict:
    skills: dict = {}
    all_experiments: list = []

    for skill, meta in SKILL_META.items():
        rows = parse_tsv(BASE_DIR / f"{skill}.tsv")
        kept_rows = [r for r in rows if r.get("status") == "keep"]
        current_fts  = max((r["FTS"] for r in kept_rows), default=None)
        baseline_fts = rows[0]["FTS"] if rows else None
        skill_tokens = kept_rows[-1]["skill_tokens"] if kept_rows else 0

        # Real SKILL.md token count
        skill_md = SKILLS_DIR / skill / "SKILL.md"
        if skill_md.exists():
            skill_tokens = len(skill_md.read_bytes()) // 4

        skills[skill] = {
            "short":        meta["short"],
            "color":        meta["color"],
            "current_fts":  current_fts,
            "baseline_fts": baseline_fts,
            "skill_tokens": skill_tokens,
            "experiments":  [
                {
                    "commit":       r.get("commit", ""),
                    "fts":          r.get("FTS", 0),
                    "skill_tokens": r.get("skill_tokens", 0),
                    "status":       r.get("status", ""),
                    "description":  r.get("description", ""),
                }
                for r in rows
            ],
        }
        for r in rows:
            all_experiments.append({
                "skill":       skill,
                "commit":      r.get("commit", ""),
                "fts":         r.get("FTS", 0),
                "skill_tokens":r.get("skill_tokens", 0),
                "status":      r.get("status", ""),
                "description": r.get("description", ""),
            })

    # Last-run JSONs
    last_runs: dict = {}
    for skill in SKILL_META:
        p = BASE_DIR / f"{skill}-last-run.json"
        if p.exists():
            try:
                last_runs[skill] = json.loads(p.read_text())
            except json.JSONDecodeError:
                pass

    return {
        "skills":          skills,
        "last_runs":       last_runs,
        "all_experiments": all_experiments,
    }


# ── HTTP server ────────────────────────────────────────────────────────────────
def build_html() -> str:
    meta_js = json.dumps(
        {k: {"short": v["short"], "color": v["color"]} for k, v in SKILL_META.items()}
    )
    return HTML.replace("__SKILL_META__", meta_js)


class Handler(SimpleHTTPRequestHandler):
    _html = build_html()

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            body = self._html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/data":
            body = json.dumps(load_data()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8502)
    args = ap.parse_args()

    print(f"Skills Eval Dashboard → http://localhost:{args.port}")
    print(f"Reading from:  {BASE_DIR}")
    print(f"Skills dir:    {SKILLS_DIR}")
    print(f"Auto-refreshes every 15s. Ctrl-C to stop.\n")

    try:
        HTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
