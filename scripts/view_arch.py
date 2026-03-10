#!/usr/bin/env python3
"""
view_arch.py — Renders live-arch.md as a pixel-faithful HTML replica of
dbx_ref_arch.excalidraw (7-column zone layout, dark governance bar).

Usage:
    python3 scripts/view_arch.py           # render + open browser
    python3 scripts/view_arch.py --watch   # render + open + auto-reload on save
"""
import re, sys, time, subprocess
from pathlib import Path

SRC   = Path("/Users/slysik/databricks/live-arch.md")
OUT   = Path("/Users/slysik/databricks/live-arch-viewer.html")
WATCH = "--watch" in sys.argv

# ── Zone palette (matches dbx_ref_arch.excalidraw exactly) ─────────────────
ZONES = {
    "Z1": dict(
        label="DATA SOURCES",
        bg="#dbe4ff", border="#4a9eed", header="#2563eb",
        node_bg="#a5d8ff", node_border="#4a9eed", node_color="#1e3a5f",
    ),
    "Z2": dict(
        label="INGESTION",
        bg="#fff3e0", border="#f59e0b", header="#b45309",
        node_bg="#ffd8a8", node_border="#f59e0b", node_color="#7c4a00",
    ),
    "Z3": dict(
        label="MEDALLION ARCHITECTURE",
        bg="#dcfce7", border="#22c55e", header="#15803d",
        node_bg=None, node_border=None, node_color=None,  # handled specially
        wide=True,
    ),
    "Z4": dict(
        label="COMPUTE",
        bg="#ede9fe", border="#8b5cf6", header="#6d28d9",
        node_bg="#d0bfff", node_border="#8b5cf6", node_color="#3b0764",
    ),
    "Z5": dict(
        label="AI / ML",
        bg="#fdf2f8", border="#ec4899", header="#9d174d",
        node_bg="#eebefa", node_border="#ec4899", node_color="#6b21a8",
        wide=True,
    ),
    "Z6": dict(
        label="CONSUMPTION",
        bg="#e0fdf4", border="#06b6d4", header="#0e7490",
        node_bg="#c3fae8", node_border="#06b6d4", node_color="#0e4f5c",
    ),
    "Z7": dict(
        label="DATA MESH",
        bg="#fefce8", border="#f59e0b", header="#b45309",
        node_bg="#fff3bf", node_border="#f59e0b", node_color="#78350f",
    ),
}

MEDALLION_LAYERS = {
    "bronze": dict(bg="#ffd8a8", border="#b45309", color="#7c2d12", label="🥉 BRONZE"),
    "silver": dict(bg="#e8e8e8", border="#757575", color="#374151", label="🥈 SILVER"),
    "gold":   dict(bg="#fff3bf", border="#b45309", color="#78350f", label="🥇 GOLD"),
}
DL_BAR = dict(bg="#c3fae8", border="#06b6d4", color="#0e4f5c")
UC_BAR = dict(bg="#d0bfff", border="#8b5cf6", color="#3b0764")
GENIE  = dict(bg="#ffc9c9", border="#ef4444", color="#7f1d1d")
GOV_BAR = dict(bg="#1e1e2e", border="#555555", color="#a0a0a0")
DBX_RED = "#FF3621"


# ── Mermaid parser ──────────────────────────────────────────────────────────

def extract_mermaid(md: str) -> str:
    m = re.search(r'```mermaid\n(.*?)```', md, re.DOTALL)
    return m.group(1) if m else ""


def parse_zone(mermaid, zone_id):
    """Extract node labels from a subgraph block by zone ID."""
    pat = rf'subgraph {zone_id}\["[^"]*"\](.*?)(?=\n  subgraph |\n  subgraph|\nsubgraph |(?<=end)\n|\Z)'
    block_m = re.search(
        rf'subgraph {zone_id}\[.*?\](.*?)(?=\n\s*subgraph |\n\s*%%|\n  Z\d|\n  ds|\n  ig|\n  mg|\n  ms|\n  mb|\n  cp|\n  co|\n  dm|\n  g\d|\n\s*end\b)',
        mermaid, re.DOTALL
    )
    # Simpler: find the subgraph block between the header and next subgraph/end
    pat2 = rf'subgraph {zone_id}\[".*?"\]\n(.*?)(?=\n  end\b|\n  subgraph |\Z)'
    m2 = re.search(pat2, mermaid, re.DOTALL)
    if not m2:
        # Try without quotes
        pat3 = rf'subgraph {zone_id}\[.*?\]\n(.*?)(?=\n  end|\nend)'
        m2 = re.search(pat3, mermaid, re.DOTALL)
    if not m2:
        return []

    block = m2.group(1)
    labels = []
    # Match nodeId["label"] or nodeId['label']
    for m in re.finditer(r'^\s*\w+\["(.*?)"\]', block, re.MULTILINE):
        raw = m.group(1)
        # Convert \n to <br>, strip HTML-unsafe chars
        label = raw.replace(r'\n', '<br>').replace('\n', '<br>')
        labels.append(label)
    return labels


def parse_all_zones(mermaid):
    """Parse all 7 zones + GOV from Mermaid block."""
    result = {}
    for zid in ["Z1", "Z2", "Z4", "Z5", "Z6", "Z7"]:
        result[zid] = parse_zone(mermaid, zid)

    # Zone 3 — parse medallion layers (mb, ms, mg) + dl + uc
    result["Z3"] = parse_medallion(mermaid)

    # GOV bar
    result["GOV"] = parse_gov(mermaid)
    return result


def parse_medallion(mermaid: str) -> dict:
    """Extract bronze/silver/gold labels + dl/uc bars."""
    def node_label(nid):
        m = re.search(rf'\b{nid}\["(.*?)"\]', mermaid, re.DOTALL)
        if not m:
            return None
        return m.group(1).replace(r'\n', '<br>').replace('\n', '<br>')

    return {
        "bronze": node_label("mb"),
        "silver": node_label("ms"),
        "gold":   node_label("mg"),
        "dl":     node_label("dl"),
        "uc":     node_label("uc"),
        "genie":  node_label("gn"),
    }


def parse_gov(mermaid: str) -> list[str]:
    labels = []
    for i in range(1, 8):
        m = re.search(rf'\bg{i}\["(.*?)"\]', mermaid, re.DOTALL)
        if m:
            labels.append(m.group(1).replace(r'\n', '<br>').replace('\n', '<br>'))
    return labels


# ── HTML builders ───────────────────────────────────────────────────────────

def node_card(label: str, bg: str, border: str, color: str,
              extra_style: str = "", width: str = "100%") -> str:
    return f"""
      <div style="
        background:{bg};
        border:2px solid {border};
        border-radius:8px;
        padding:8px 10px;
        font-size:12px;
        font-weight:600;
        color:{color};
        text-align:center;
        line-height:1.4;
        width:{width};
        {extra_style}
      ">{label}</div>"""


def zone_column(zone_id: str, nodes: list[str], extra_style: str = "") -> str:
    z = ZONES[zone_id]
    cards = "\n".join(
        node_card(lbl, z["node_bg"], z["node_border"], z["node_color"],
                  extra_style="margin-bottom:6px")
        for lbl in nodes
    ) if nodes else '<div style="color:#94a3b8;font-size:11px;text-align:center">⏳ pending</div>'

    return f"""
    <div style="
      background:{z['bg']};
      border:1.5px solid {z['border']};
      border-radius:10px;
      padding:10px 8px 12px;
      display:flex;
      flex-direction:column;
      gap:0;
      flex:{'2' if z.get('wide') else '1'};
      min-width:0;
      {extra_style}
    ">
      <div style="
        font-size:11px;font-weight:700;
        color:{z['header']};
        text-transform:uppercase;
        letter-spacing:.07em;
        text-align:center;
        margin-bottom:10px;
        padding-bottom:6px;
        border-bottom:1.5px solid {z['border']};
      ">{z['label']}</div>
      {cards}
    </div>"""


def medallion_column(data: dict) -> str:
    z = ZONES["Z3"]

    # Bronze / Silver / Gold side-by-side row
    def layer(key):
        cfg = MEDALLION_LAYERS[key]
        lbl = data.get(key) or cfg["label"]
        return f"""
        <div style="
          flex:1;
          background:{cfg['bg']};
          border:2px solid {cfg['border']};
          border-radius:8px;
          padding:10px 8px;
          font-size:11px;
          font-weight:700;
          color:{cfg['color']};
          text-align:center;
          line-height:1.5;
        ">{lbl}</div>"""

    bronze_html = layer("bronze")
    silver_html = layer("silver")
    gold_html   = layer("gold")

    # Delta Lake bar
    dl_lbl = data.get("dl") or "Delta Lake — ACID · Time Travel · Liquid Clustering"
    dl_html = f"""
    <div style="
      background:{DL_BAR['bg']};
      border:2px solid {DL_BAR['border']};
      border-radius:7px;
      padding:7px 12px;
      font-size:11px;
      font-weight:700;
      color:{DL_BAR['color']};
      text-align:center;
      margin-top:8px;
    ">{dl_lbl}</div>"""

    # Unity Catalog bar
    uc_lbl = data.get("uc") or "Unity Catalog — Lineage · Row Filters · Column Masks"
    uc_html = f"""
    <div style="
      background:{UC_BAR['bg']};
      border:2px solid {UC_BAR['border']};
      border-radius:7px;
      padding:7px 12px;
      font-size:11px;
      font-weight:700;
      color:{UC_BAR['color']};
      text-align:center;
      margin-top:6px;
    ">{uc_lbl}</div>"""

    return f"""
    <div style="
      background:{z['bg']};
      border:1.5px solid {z['border']};
      border-radius:10px;
      padding:10px 8px 12px;
      display:flex;
      flex-direction:column;
      flex:2.2;
      min-width:0;
    ">
      <div style="
        font-size:11px;font-weight:700;
        color:{z['header']};
        text-transform:uppercase;
        letter-spacing:.07em;
        text-align:center;
        margin-bottom:10px;
        padding-bottom:6px;
        border-bottom:1.5px solid {z['border']};
      ">{z['label']}</div>
      <div style="display:flex;gap:6px;flex:1">{bronze_html}{silver_html}{gold_html}</div>
      {dl_html}
      {uc_html}
    </div>"""


def ai_column(nodes, genie_label):
    z = ZONES["Z5"]
    genie_html = ""
    if genie_label:
        genie_html = f"""
      <div style="
        background:{GENIE['bg']};
        border:3px solid {GENIE['border']};
        border-radius:8px;
        padding:8px 10px;
        font-size:12px;
        font-weight:700;
        color:{GENIE['color']};
        text-align:center;
        line-height:1.4;
        margin-top:6px;
      ">{genie_label}</div>"""

    # Filter out genie from main nodes (it's handled separately)
    main_nodes = [n for n in nodes if 'genie' not in n.lower() and 'nl' not in n.lower()]
    cards_html = "\n".join(
        node_card(lbl, z["node_bg"], z["node_border"], z["node_color"],
                  extra_style="margin-bottom:6px")
        for lbl in main_nodes
    )

    return f"""
    <div style="
      background:{z['bg']};
      border:1.5px solid {z['border']};
      border-radius:10px;
      padding:10px 8px 12px;
      display:flex;
      flex-direction:column;
      flex:1.8;
      min-width:0;
    ">
      <div style="
        font-size:11px;font-weight:700;
        color:{z['header']};
        text-transform:uppercase;
        letter-spacing:.07em;
        text-align:center;
        margin-bottom:10px;
        padding-bottom:6px;
        border-bottom:1.5px solid {z['border']};
      ">{z['label']}</div>
      {cards_html}
      {genie_html}
    </div>"""


def gov_bar_html(nodes: list[str]) -> str:
    pills = ""
    for lbl in nodes:
        pills += f"""
      <div style="
        background:#2d2d4e;
        border:1px solid #4a4a7a;
        border-radius:6px;
        padding:7px 14px;
        font-size:12px;
        font-weight:600;
        color:#c4c4d8;
        text-align:center;
        line-height:1.4;
        flex:1;
        min-width:0;
      ">{lbl}</div>"""

    return f"""
  <div style="
    background:{GOV_BAR['bg']};
    border:1px solid {GOV_BAR['border']};
    border-radius:10px;
    padding:12px 14px;
    margin-top:10px;
  ">
    <div style="
      font-size:10px;
      font-weight:700;
      color:#6b6b9a;
      text-transform:uppercase;
      letter-spacing:.1em;
      text-align:center;
      margin-bottom:10px;
    ">🛡️ PLATFORM GOVERNANCE &amp; OPERATIONS</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">{pills}</div>
  </div>"""


def arrow_sep() -> str:
    return """
    <div style="
      display:flex;
      align-items:center;
      justify-content:center;
      font-size:20px;
      color:#94a3b8;
      flex-shrink:0;
      padding:0 2px;
      margin-top:28px;
    ">→</div>"""


# ── Metadata panels ─────────────────────────────────────────────────────────

def discovery_panel(md: str) -> str:
    m = re.search(r'## Discovery Status\n(.+?)(?=\n##|\Z)', md, re.DOTALL)
    if not m:
        return ""
    rows_html = ""
    for line in m.group(1).strip().splitlines():
        if line.startswith('|') and '---' not in line and 'Category' not in line:
            cells = [c.strip() for c in line.strip('|').split('|')]
            if len(cells) >= 3:
                s = cells[1]
                c = "#22c55e" if "✅" in s else "#f59e0b" if "⏳" in s else "#94a3b8"
                rows_html += f"""
                <tr>
                  <td style="padding:5px 10px;font-weight:600;font-size:12px;border-bottom:1px solid #f1f5f9;white-space:nowrap">{cells[0]}</td>
                  <td style="padding:5px 10px;border-bottom:1px solid #f1f5f9">
                    <span style="color:{c};font-weight:700;font-size:13px">{s}</span>
                  </td>
                  <td style="padding:5px 10px;border-bottom:1px solid #f1f5f9;color:#475569;font-size:12px">{cells[2]}</td>
                </tr>"""
    if not rows_html:
        return ""
    return f"""
    <div class="panel">
      <div class="panel-title">📋 Discovery Status</div>
      <table style="width:100%;border-collapse:collapse">
        <thead><tr style="background:#f8fafc">
          <th style="text-align:left;padding:5px 10px;color:#64748b;font-size:10px;text-transform:uppercase;border-bottom:2px solid #e2e8f0">Category</th>
          <th style="text-align:left;padding:5px 10px;color:#64748b;font-size:10px;text-transform:uppercase;border-bottom:2px solid #e2e8f0">Status</th>
          <th style="text-align:left;padding:5px 10px;color:#64748b;font-size:10px;text-transform:uppercase;border-bottom:2px solid #e2e8f0">Key Facts</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>"""


def decisions_panel(md: str) -> str:
    m = re.search(r'## Key Architecture Decisions\n(.+?)(?=\n##|\Z)', md, re.DOTALL)
    if not m:
        return ""
    rows_html = ""
    for line in m.group(1).strip().splitlines():
        if line.startswith('|') and '---' not in line and 'Decision' not in line:
            cells = [c.strip() for c in line.strip('|').split('|')]
            if len(cells) >= 4 and 'pending' not in cells[0]:
                rows_html += f"""
                <tr>
                  <td style="padding:6px 10px;font-weight:600;font-size:12px;border-bottom:1px solid #f1f5f9">{cells[0]}</td>
                  <td style="padding:6px 10px;border-bottom:1px solid #f1f5f9">
                    <span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;white-space:nowrap">{cells[1]}</span>
                  </td>
                  <td style="padding:6px 10px;color:#374151;font-size:12px;border-bottom:1px solid #f1f5f9">{cells[2]}</td>
                  <td style="padding:6px 10px;color:#6b7280;font-size:11px;font-style:italic;border-bottom:1px solid #f1f5f9">{cells[3]}</td>
                </tr>"""
    if not rows_html:
        return ""
    return f"""
    <div class="panel">
      <div class="panel-title">🏛️ Key Architecture Decisions</div>
      <table style="width:100%;border-collapse:collapse">
        <thead><tr style="background:#f8fafc">
          <th style="text-align:left;padding:5px 10px;color:#64748b;font-size:10px;text-transform:uppercase;border-bottom:2px solid #e2e8f0">Decision</th>
          <th style="text-align:left;padding:5px 10px;color:#64748b;font-size:10px;text-transform:uppercase;border-bottom:2px solid #e2e8f0">Choice</th>
          <th style="text-align:left;padding:5px 10px;color:#64748b;font-size:10px;text-transform:uppercase;border-bottom:2px solid #e2e8f0">Rationale</th>
          <th style="text-align:left;padding:5px 10px;color:#64748b;font-size:10px;text-transform:uppercase;border-bottom:2px solid #e2e8f0">Trade-off</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>"""


def open_questions_panel(md: str) -> str:
    m = re.search(r'## Open Questions.*?\n(.*?)(?=\n##|\Z)', md, re.DOTALL)
    if not m:
        return ""
    items = [
        re.sub(r'^- \[.\] ?', '', l.strip()).strip()
        for l in m.group(1).splitlines()
        if re.match(r'^\s*- \[', l)
    ]
    if not items:
        return ""
    lis = "".join(f'<li style="padding:4px 0;font-size:12px;color:#374151;border-bottom:1px solid #f8fafc">❓ {i}</li>' for i in items)
    return f"""
    <div class="panel">
      <div class="panel-title">🔍 Open Questions</div>
      <ul style="list-style:none;padding:0;margin:0">{lis}</ul>
    </div>"""


def talking_points_panel(md: str) -> str:
    m = re.search(r"## Steve's Talking Points.*?\n(.*?)(?=\n##|\Z)", md, re.DOTALL)
    if not m:
        return ""
    content = m.group(1)

    def extract_quote(heading):
        hm = re.search(rf'### {re.escape(heading)}\n> (.+?)(?=\n###|\n##|\Z)', content, re.DOTALL)
        return hm.group(1).strip().replace('\n', ' ') if hm else None

    lead  = extract_quote("🎯 Lead With")
    proof = extract_quote("📌 Proof Point")

    # Watch out bullets
    wm = re.search(r'### ⚠️ Watch Out For\n(.*?)(?=\n###|\n##|\Z)', content, re.DOTALL)
    watch_items = []
    if wm:
        watch_items = [
            re.sub(r'^- \*\*.*?\*\* ?→? ?', '→ ', l.strip()).lstrip('- ').strip()
            for l in wm.group(1).splitlines()
            if l.strip().startswith('- ')
        ]

    cards = ""
    if lead:
        cards += f"""
        <div style="background:#f0fdf4;border-left:4px solid #22c55e;border-radius:0 8px 8px 0;padding:12px 14px">
          <div style="font-size:10px;font-weight:700;color:#15803d;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px">🎯 Lead With</div>
          <blockquote style="font-size:12px;color:#374151;line-height:1.6;font-style:italic;margin:0">"{lead}"</blockquote>
        </div>"""
    if proof:
        cards += f"""
        <div style="background:#eff6ff;border-left:4px solid #3b82f6;border-radius:0 8px 8px 0;padding:12px 14px">
          <div style="font-size:10px;font-weight:700;color:#1d4ed8;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px">📌 Proof Point</div>
          <blockquote style="font-size:12px;color:#374151;line-height:1.6;font-style:italic;margin:0">"{proof}"</blockquote>
        </div>"""
    if watch_items:
        lis = "".join(f'<li style="padding:3px 0;font-size:12px;color:#92400e">⚠️ {i}</li>' for i in watch_items)
        cards += f"""
        <div style="background:#fff7ed;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;padding:12px 14px">
          <div style="font-size:10px;font-weight:700;color:#b45309;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px">⚠️ Watch Out For</div>
          <ul style="list-style:none;padding:0;margin:0">{lis}</ul>
        </div>"""

    if not cards:
        return ""
    return f"""
    <div class="panel">
      <div class="panel-title">🎤 Steve's Talking Points</div>
      <div style="display:flex;flex-direction:column;gap:10px">{cards}</div>
    </div>"""


# ── Main render ─────────────────────────────────────────────────────────────

def render():
    md      = SRC.read_text()
    mermaid = extract_mermaid(md)
    zones   = parse_all_zones(mermaid)
    ts      = time.strftime("%Y-%m-%d %H:%M:%S")

    title_m = re.search(r'^# (.+)', md)
    title   = title_m.group(1).strip() if title_m else "Live Architecture"
    # Strip markdown italic asterisks from subtitle
    subtitle_m = re.search(r'^\*(.+?)\*$', md, re.MULTILINE)
    subtitle = subtitle_m.group(1).strip() if subtitle_m else ""

    # Build 7-column diagram
    z1 = zone_column("Z1", zones["Z1"])
    z2 = zone_column("Z2", zones["Z2"])
    z3 = medallion_column(zones["Z3"])
    z4 = zone_column("Z4", zones["Z4"])
    z5 = ai_column(zones["Z5"], zones["Z3"].get("genie"))
    z6 = zone_column("Z6", zones["Z6"])
    z7 = zone_column("Z7", zones["Z7"])
    gov = gov_bar_html(zones["GOV"])

    arr = arrow_sep()

    refresh_tag = '<meta http-equiv="refresh" content="8">' if WATCH else ""
    watch_badge = '<span style="background:#f59e0b;color:#fff;font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;margin-left:8px">⟳ WATCH</span>' if WATCH else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  {refresh_tag}
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0 }}
    body {{ font-family:"Nunito",sans-serif;
            background:#f1f5f9; color:#1e293b }}
    .topbar {{ background:{DBX_RED}; color:#fff; padding:10px 20px;
               display:flex; align-items:center; justify-content:space-between;
               position:sticky; top:0; z-index:100; box-shadow:0 2px 8px rgba(0,0,0,.25) }}
    .topbar h1 {{ font-size:15px; font-weight:700 }}
    .topbar .meta {{ font-size:11px; opacity:.9; text-align:right; line-height:1.6 }}
    .live-badge {{ background:#22c55e; color:#fff; font-size:10px; font-weight:700;
                   padding:3px 10px; border-radius:20px; margin-left:8px }}
    .wrap {{ padding:16px 18px; max-width:1800px; margin:0 auto }}
    .subtitle {{ font-size:12px; color:#64748b; margin-bottom:12px; font-style:italic }}
    .diagram-wrap {{ background:#fff; border-radius:12px; padding:16px;
                     box-shadow:0 1px 6px rgba(0,0,0,.1); margin-bottom:14px; overflow-x:auto }}
    .diagram-inner {{ display:flex; align-items:stretch; gap:4px; min-width:1100px }}
    .panel {{ background:#fff; border-radius:10px; padding:16px 18px;
              box-shadow:0 1px 4px rgba(0,0,0,.08); margin-bottom:14px; overflow-x:auto }}
    .panel-title {{ font-size:13px; font-weight:700; color:#0f172a; margin-bottom:12px;
                    padding-bottom:8px; border-bottom:2px solid #f1f5f9 }}
    .bottom-panels {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px }}
    @media(max-width:1200px) {{ .bottom-panels {{ grid-template-columns:1fr 1fr }} }}
  </style>
</head>
<body>

<div class="topbar">
  <h1>
    🔶 &nbsp; Databricks Data Intelligence Platform
    <span class="live-badge">LIVE</span>{watch_badge}
  </h1>
  <div class="meta">
    {title}<br>
    {ts} &nbsp;·&nbsp; source: live-arch.md
  </div>
</div>

<div class="wrap">
  {f'<div class="subtitle">{subtitle}</div>' if subtitle else ''}

  <!-- ── Main Architecture Diagram ────────────────────────────────────────── -->
  <div class="diagram-wrap">
    <div style="font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;
                letter-spacing:.08em;margin-bottom:10px">Architecture Diagram</div>
    <div class="diagram-inner">
      {z1}{arr}{z2}{arr}{z3}{arr}{z4}{arr}{z5}{arr}{z6}{arr}{z7}
    </div>
    {gov}
  </div>

  <!-- ── Discovery + Decisions ─────────────────────────────────────────────── -->
  {discovery_panel(md)}
  {decisions_panel(md)}

  <!-- ── Bottom 3-up ──────────────────────────────────────────────────────── -->
  <div class="bottom-panels">
    {open_questions_panel(md)}
    {talking_points_panel(md)}
  </div>

</div>
</body>
</html>"""

    OUT.write_text(html)
    print(f"✅  Rendered → {OUT}  [{ts}]")


if __name__ == "__main__":
    render()
    subprocess.run(["open", str(OUT)])

    if WATCH:
        print("👁️  Watch mode active — browser auto-refreshes every 8s on file change")
        last = SRC.stat().st_mtime
        while True:
            time.sleep(3)
            cur = SRC.stat().st_mtime
            if cur != last:
                last = cur
                render()
                print(f"🔄  Reloaded [{time.strftime('%H:%M:%S')}]")
