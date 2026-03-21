#!/usr/bin/env python3
"""
Renders live-arch.md → live-arch-viewer.html
Diagram is built as pure HTML/CSS matching the Databricks reference architecture
visual style (orange borders, dark-teal headers, teal step badges, medallion strip).
No Mermaid — pixel-faithful recreation of the Databricks ref arch layout.
"""
import re, time
from pathlib import Path

SRC = Path("/Users/slysik/databricks/live-arch.md")
OUT = Path("/Users/slysik/databricks/live-arch-viewer.html")

md = SRC.read_text()
ts = time.strftime("%Y-%m-%d %H:%M:%S")

# ── Parse section bullets from MD ────────────────────────────────────────────
def section_items(heading):
    """Return list of bullet strings under a ## heading (strips leading - / * / bold)."""
    pat = rf'## {re.escape(heading)}\n(.*?)(?=\n## |\Z)'
    m   = re.search(pat, md, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    lines = []
    for l in m.group(1).splitlines():
        l = l.strip()
        if l.startswith('- ') or l.startswith('* '):
            l = l[2:].strip()
        l = re.sub(r'\*\*(.*?)\*\*', r'\1', l)   # strip bold markers
        l = re.sub(r'\*(.*?)\*',     r'\1', l)    # strip italic markers
        if l and not l.startswith('|') and not l.startswith('#') \
                and not re.match(r'^[-=]{2,}$', l):
            lines.append(l)
    return lines

def si(heading, default):
    items = section_items(heading)
    return items if items else default

# ── Pull content from each section (falls back to Credit Loss defaults) ────────
title_m = re.search(r'^# (.+)', md)
TITLE   = title_m.group(1).strip() if title_m else "Reference Architecture for Credit Loss Forecasting"

SUBTITLE = ""
sub_m = re.search(r'^> (.+)', md, re.MULTILINE)
if sub_m:
    SUBTITLE = sub_m.group(1).strip()

SOURCES = si("On-Prem or Cloud Data Sources", [
    "🏢 Retail Loans",
    "🏢 Commercial Loans",
    "📋 GL Extracts <small>(For Recon)</small>",
    "📊 Market / Scenario Data",
    "🔗 External Models",
])

CONN = si("① Connectivity and Protocols", [
    "Lakeflow Connect",
    "Lakehouse Federation",
    "JDBC",
])

EXT = si("② External Data or Models", [
    "Databricks Marketplace",
    "APIs (External)",
])

DP = si("③ Design Patterns with Lakeflow Pipelines", [
    "Data Controls Production / SOR",
    "GL Reconciliation",
    "Data Correction",
    "Fit for Purpose Transformations",
    "Data Pipeline Observability",
    "Data Cataloging and Lineage",
])

BI_SQL = si("⑥ Business Intelligence with Databricks SQL", [
    "Aggregate Portfolio Data",
    "Explore Scenario Data",
    "Credit Loss Forecast with AI Functions",
])

DSML = si("④ Data Science & Machine Learning with Mosaic AI", [
    "Derive Variables",
    "Score Models",
    "Calculate Expected Credit Loss",
])

# Medallion — parse table if present, else defaults
BRONZE_DESC = "Raw files (mortgage, credit card, CRE, C&amp;I)"
SILVER_DESC = "Retail loans, commercial loans, GL recon"
GOLD_DESC   = "Credit loss forecast"
medal_m = re.search(r'\| 🥉 \*\*Bronze\*\* \| (.+?) \|', md)
if medal_m: BRONZE_DESC = medal_m.group(1).strip()
medal_m = re.search(r'\| 🥈 \*\*Silver\*\* \| (.+?) \|', md)
if medal_m: SILVER_DESC = medal_m.group(1).strip()
medal_m = re.search(r'\| 🥇 \*\*Gold\*\* \| (.+?) \|', md)
if medal_m: GOLD_DESC   = medal_m.group(1).strip()

BI_OUT = si("Business Intelligence *(right panel)*", [
    "Tableau",
    "Power BI",
    "Looker",
])
BI_SUB = "AI/BI natural language self-service dashboards &amp; conversational interface"

APPS = si("⑦ Interactive Lakehouse Apps *(right panel)*", [
    "CECL &amp; Stress Test Process &amp; Controls",
    "Scenario &amp; Attribution Analysis",
    "Adjustment Overlays",
])

SHARE = si("Secure Data Sharing with Risk & Finance Systems *(right panel)*", [
    "Regulatory &amp; Disclosure Reporting",
    "ALM",
    "FP&amp;A",
])

# ── HTML helpers ──────────────────────────────────────────────────────────────
def badge(n, size=28):
    return (f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:{size}px;height:{size}px;border-radius:50%;background:#00897B;'
            f'color:#fff;font-size:{size*0.52:.0f}px;font-weight:700;flex-shrink:0">{n}</span>')

def item_list(items, style=""):
    rows = "".join(
        f'<div style="font-size:13px;color:#334155;padding:5px 0;'
        f'border-bottom:1px solid #f1f5f9;line-height:1.4;{style}">{i}</div>'
        for i in items
    )
    return rows

def icon_grid(items, cols=3):
    cells = "".join(
        f'<div style="text-align:center;font-size:12px;color:#334155;'
        f'padding:10px 6px;line-height:1.4;background:#f8fafc;'
        f'border-radius:5px;border:1px solid #e2e8f0">{i}</div>'
        for i in items
    )
    return (f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);'
            f'gap:6px;padding:8px 6px">{cells}</div>')

def dp_grid(items):
    cells = "".join(
        f'<div style="text-align:center;font-size:12px;color:#334155;'
        f'padding:10px 6px;line-height:1.4;border:1px solid #e2e8f0;'
        f'border-radius:5px;background:#fff">{i}</div>'
        for i in items
    )
    return (f'<div style="display:grid;grid-template-columns:1fr 1fr;'
            f'gap:7px;padding:10px">{cells}</div>')

# ── Build the diagram HTML ────────────────────────────────────────────────────
def arch_html():
    src_items  = "\n".join(
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;'
        f'padding:8px 6px;text-align:center;font-size:12px;color:#334155;'
        f'line-height:1.4">{s}</div>'
        for s in SOURCES
    )

    conn_items = item_list(CONN, "border-bottom:1px solid #f1f5f9")
    ext_items  = item_list(EXT,  "border-bottom:1px solid #f1f5f9")
    dp_items   = dp_grid(DP)
    bi_items   = icon_grid(BI_SQL, cols=3)
    ds_items   = icon_grid(DSML,   cols=3)
    app_items  = icon_grid(APPS,   cols=3)
    bi_out_row = "  ·  ".join(BI_OUT)
    share_row  = "  ·  ".join(SHARE)

    # All sizes designed at 1400px width; JS scales to viewport
    return f"""
<div id="arch-scaler" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#fff;width:1400px;transform-origin:top left;padding:20px 16px 16px">

  <!-- TITLE -->
  <div style="font-size:22px;font-weight:700;color:#0f172a;margin-bottom:6px">{TITLE}</div>
  {'<div style="font-size:13px;color:#475569;margin-bottom:20px;max-width:860px;line-height:1.5">' + SUBTITLE + '</div>' if SUBTITLE else '<div style="margin-bottom:16px"></div>'}

  <!-- DIAGRAM ROW — fixed proportions at 1400px -->
  <div style="display:flex;align-items:stretch;gap:0;height:560px">

    <!-- ── COL 1: Sources (130px) ── -->
    <div style="width:130px;flex-shrink:0;border:1.5px solid #94a3b8;border-radius:8px;
                padding:10px 8px;background:#f8fafc;display:flex;flex-direction:column">
      <div style="font-size:11px;font-weight:700;color:#475569;text-align:center;
                  margin-bottom:10px;line-height:1.4">On-Prem or Cloud<br>Data Sources</div>
      <div style="flex:1;display:flex;flex-direction:column;gap:6px;justify-content:space-evenly">
        {src_items}
      </div>
    </div>

    <!-- ── STEP BADGES ①② + arrows ── -->
    <div style="width:58px;flex-shrink:0;display:flex;flex-direction:column;
                justify-content:space-around;align-items:center;padding:20px 0">
      <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
        {badge(1,30)}
        <div style="font-size:20px;color:#64748b;line-height:1">→</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;gap:4px">
        {badge(2,30)}
        <div style="font-size:20px;color:#64748b;line-height:1">→</div>
      </div>
    </div>

    <!-- ── COL 2: Connectivity + External (148px) ── -->
    <div style="width:148px;flex-shrink:0;display:flex;flex-direction:column;gap:10px">

      <div style="flex:1;border:2.5px solid #FF3621;border-radius:8px;padding:10px">
        <div style="font-size:12px;font-weight:700;color:#FF3621;text-align:center;
                    margin-bottom:10px;line-height:1.4">Connectivity and<br>Protocols</div>
        {conn_items}
      </div>

      <div style="flex:1;border:2.5px solid #FF3621;border-radius:8px;padding:10px">
        <div style="font-size:12px;font-weight:700;color:#FF3621;text-align:center;
                    margin-bottom:10px;line-height:1.4">External Data or<br>Models</div>
        {ext_items}
      </div>

    </div>

    <!-- ── ARROW → platform ── -->
    <div style="width:28px;flex-shrink:0;display:flex;align-items:center;
                justify-content:center;font-size:22px;color:#64748b">→</div>

    <!-- ── COL 3: Data Intelligence Platform (flex:1 = ~870px) ── -->
    <div style="flex:1;border:3px solid #FF3621;border-radius:10px;
                overflow:hidden;display:flex;flex-direction:column">

      <!-- Platform title bar -->
      <div style="background:#FF3621;color:#fff;text-align:center;padding:9px 14px;
                  font-size:16px;font-weight:700;letter-spacing:.4px;flex-shrink:0">
        ⬡ &nbsp; Data Intelligence Platform &nbsp; ⬡
      </div>

      <div style="padding:10px;flex:1;display:flex;flex-direction:column;gap:8px">

        <!-- ⑤ Lakeflow Jobs -->
        <div style="background:#1B3A4B;color:#fff;border-radius:5px;
                    padding:9px 14px;display:flex;align-items:center;gap:10px;flex-shrink:0">
          {badge(5,30)}
          <span style="font-size:14px;font-weight:700">Lakeflow Jobs</span>
          <span style="font-size:12px;font-style:italic;opacity:.8">Orchestrate Model Execution</span>
        </div>

        <!-- ③ Design Patterns (left) + ⑥ BI / ④ DS/ML (right) -->
        <div style="display:flex;gap:10px;flex:1;min-height:0">

          <!-- ③ Design Patterns -->
          <div style="flex:0 0 42%;border:2px dashed #64748b;border-radius:8px;
                      overflow:hidden;display:flex;flex-direction:column">
            <div style="background:#1B3A4B;color:#fff;padding:8px 12px;
                        display:flex;align-items:center;gap:8px;flex-shrink:0">
              {badge(3,28)}
              <span style="font-size:13px;font-weight:700;line-height:1.3">
                Design Patterns with<br>Lakeflow Pipelines
              </span>
            </div>
            <div style="flex:1;overflow:auto">{dp_items}</div>
          </div>

          <!-- ⑥ BI + ④ DS/ML stacked -->
          <div style="flex:1;display:flex;flex-direction:column;gap:8px">

            <div style="flex:1;border:1.5px solid #e2e8f0;border-radius:8px;
                        overflow:hidden;display:flex;flex-direction:column">
              <div style="background:#1B3A4B;color:#fff;padding:8px 12px;
                          display:flex;align-items:center;gap:8px;flex-shrink:0">
                {badge(6,28)}
                <span style="font-size:13px;font-weight:700;line-height:1.3">
                  Business Intelligence with<br>Databricks SQL
                </span>
              </div>
              <div style="flex:1">{bi_items}</div>
            </div>

            <div style="flex:1;border:1.5px solid #e2e8f0;border-radius:8px;
                        overflow:hidden;display:flex;flex-direction:column">
              <div style="background:#1B3A4B;color:#fff;padding:8px 12px;
                          display:flex;align-items:center;gap:8px;flex-shrink:0">
                {badge(4,28)}
                <span style="font-size:13px;font-weight:700;line-height:1.3">
                  Data Science &amp; Machine Learning<br>with Mosaic AI
                </span>
              </div>
              <div style="flex:1">{ds_items}</div>
            </div>

          </div>
        </div>

        <!-- Medallion strip -->
        <div style="flex-shrink:0">
          <div style="background:#1B3A4B;color:#fff;border-radius:5px 5px 0 0;
                      padding:8px 14px;font-size:13px;font-weight:700;text-align:center">
            Portfolio Data &nbsp;–&nbsp; Market Data &nbsp;–&nbsp; Reg Reporting Data
          </div>
          <div style="display:flex;align-items:center;border:1.5px solid #e2e8f0;
                      border-top:none;border-radius:0 0 5px 5px;background:#fafafa;
                      padding:12px 10px;gap:4px">
            <div style="flex:1;text-align:center">
              <div style="width:52px;height:52px;border-radius:50%;background:#FDECEA;
                          border:3px solid #C0392B;margin:0 auto 6px;
                          display:flex;align-items:center;justify-content:center;
                          font-size:11px;font-weight:700;color:#C0392B">Bronze</div>
              <div style="font-size:11px;color:#64748b;line-height:1.4">{BRONZE_DESC}</div>
            </div>
            <div style="font-size:22px;color:#94a3b8;padding:0 8px">→</div>
            <div style="flex:1;text-align:center">
              <div style="width:52px;height:52px;border-radius:50%;background:#F1F5F9;
                          border:3px solid #7B8FA1;margin:0 auto 6px;
                          display:flex;align-items:center;justify-content:center;
                          font-size:11px;font-weight:700;color:#7B8FA1">Silver</div>
              <div style="font-size:11px;color:#64748b;line-height:1.4">{SILVER_DESC}</div>
            </div>
            <div style="font-size:22px;color:#94a3b8;padding:0 8px">→</div>
            <div style="flex:1;text-align:center">
              <div style="width:52px;height:52px;border-radius:50%;background:#FFFBEB;
                          border:3px solid #D4980A;margin:0 auto 6px;
                          display:flex;align-items:center;justify-content:center;
                          font-size:11px;font-weight:700;color:#D4980A">Gold</div>
              <div style="font-size:11px;color:#64748b;line-height:1.4">{GOLD_DESC}</div>
            </div>
          </div>
        </div>

        <!-- Foundation row -->
        <div style="display:flex;gap:8px;flex-shrink:0">
          <div style="flex:1;border:2.5px solid #FF3621;border-radius:6px;padding:10px;
                      text-align:center;font-size:13px;font-weight:700;color:#1B3A4B">
            △ &nbsp; DELTA LAKE
          </div>
          <div style="flex:1;border:2.5px solid #FF3621;border-radius:6px;padding:10px;
                      text-align:center;font-size:13px;font-weight:700;color:#1B3A4B">
            ✦ &nbsp; Apache Spark + Photon
          </div>
          <div style="flex:1;border:2.5px solid #FF3621;border-radius:6px;padding:10px;
                      text-align:center;font-size:13px;font-weight:700;color:#1B3A4B">
            ◉ &nbsp; Unity Catalog
          </div>
        </div>

      </div>
    </div>

    <!-- ── ARROW → outputs ── -->
    <div style="width:28px;flex-shrink:0;display:flex;align-items:center;
                justify-content:center;font-size:22px;color:#64748b">→</div>

    <!-- ── COL 4: Right panels (178px) ── -->
    <div style="width:178px;flex-shrink:0;display:flex;flex-direction:column;gap:10px">

      <div style="border:1.5px solid #94a3b8;border-radius:8px;padding:12px;
                  background:#f8fafc">
        <div style="font-size:12px;font-weight:700;color:#475569;margin-bottom:8px;
                    text-align:center">Business Intelligence</div>
        <div style="font-size:12px;color:#334155;text-align:center;margin-bottom:6px;
                    font-weight:600">{bi_out_row}</div>
        <div style="font-size:11px;color:#64748b;text-align:center;line-height:1.4">{BI_SUB}</div>
      </div>

      <div style="border:2.5px solid #FF3621;border-radius:8px;overflow:hidden;flex:1">
        <div style="background:#FF3621;color:#fff;padding:8px 10px;
                    display:flex;align-items:center;gap:8px">
          {badge(7,28)}
          <span style="font-size:12px;font-weight:700;line-height:1.3">
            Interactive<br>Lakehouse Apps
          </span>
        </div>
        <div>{app_items}</div>
      </div>

      <div style="border:1.5px solid #94a3b8;border-radius:8px;padding:12px;
                  background:#f8fafc">
        <div style="font-size:11px;font-weight:700;color:#475569;margin-bottom:8px;
                    text-align:center;line-height:1.4">
          Secure Data Sharing with<br>Risk &amp; Finance Systems
        </div>
        <div style="font-size:12px;color:#334155;text-align:center;line-height:1.8">{share_row}</div>
      </div>

    </div>
  </div>
</div>

<script>
  (function() {{
    var el    = document.getElementById('arch-scaler');
    var avail = document.getElementById('arch-wrapper').clientWidth - 8;
    var scale = Math.min(1, avail / 1400);
    el.style.transform = 'scale(' + scale + ')';
    el.style.height    = (620 * scale) + 'px';   /* collapse whitespace below */
    document.getElementById('arch-wrapper').style.height = (620 * scale + 32) + 'px';
  }})();
</script>
"""

# ── Build full HTML page ──────────────────────────────────────────────────────
diagram = arch_html()

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="15">
<title>{TITLE}</title>
<style>
  * {{ box-sizing:border-box;margin:0;padding:0 }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
          background:#f1f5f9;color:#1e293b;overflow-x:hidden }}
  .topbar {{ background:#FF3621;color:#fff;padding:9px 18px;
             display:flex;align-items:center;justify-content:space-between }}
  .topbar h1 {{ font-size:14px;font-weight:700 }}
  .meta  {{ font-size:10px;opacity:.85;text-align:right;line-height:1.5 }}
  .pill  {{ background:#22c55e;color:#fff;font-size:10px;font-weight:700;
            padding:3px 10px;border-radius:20px }}
  .wrap  {{ padding:12px }}
  .card  {{ background:#fff;border-radius:8px;
            box-shadow:0 1px 4px rgba(0,0,0,.1);overflow:hidden }}
</style>
</head>
<body>

<div class="topbar">
  <h1>🔶 &nbsp; {TITLE}</h1>
  <div style="display:flex;align-items:center;gap:10px">
    <span class="pill">TEMPLATE</span>
    <div class="meta">Edit live-arch.md → python3 scripts/render_arch.py<br>
                      Auto-refresh 15s &nbsp;·&nbsp; {ts}</div>
  </div>
</div>

<div class="wrap">
  <div class="card">
    <div id="arch-wrapper" style="padding:4px;overflow:hidden">
      {diagram}
    </div>
  </div>
</div>

</body>
</html>
"""

OUT.write_text(html)
print(f"✅  Rendered → {OUT.name}  [{ts}]")
print(f"    Sources   : {len(SOURCES)} items")
print(f"    Design Px : {len(DP)} items")
print(f"    BI SQL    : {len(BI_SQL)} items")
print(f"    DS/ML     : {len(DSML)} items")
print(f"    Apps      : {len(APPS)} items")
