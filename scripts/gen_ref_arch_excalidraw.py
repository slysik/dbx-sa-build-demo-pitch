#!/usr/bin/env python3
"""
Databricks Intelligent DW Reference Architecture — Excalidraw Generator
─────────────────────────────────────────────────────────────────────────
Reads  : ref-arch-content.md  (edit text there, not here)
Writes : ref-arch-template.excalidraw   (blank whiteboard version)
         ref-arch-customer.excalidraw   (leave-behind, filled from MD)

Usage:
  python3 scripts/gen_ref_arch_excalidraw.py            # blank template
  python3 scripts/gen_ref_arch_excalidraw.py --customer # filled from ref-arch-content.md

Dynamic boxes:
  Sources  → count ### src1 … ### srcN  in MD  (default 5, max ~7)
  Outputs  → count ### out1 … ### outN  in MD  (default 5)
  All other sections: fixed structure matching Databricks ref arch
"""

import json, re, time, random, sys
from pathlib import Path

CONTENT_FILE = Path("/Users/slysik/databricks/ref-arch-content.md")
OUT_TEMPLATE = Path("/Users/slysik/databricks/ref-arch-template.excalidraw")
OUT_CUSTOMER = Path("/Users/slysik/databricks/ref-arch-customer.excalidraw")

FILL_MODE = "--customer" in sys.argv

# ─────────────────────────────────────────────────────────────────────────────
# 1. PARSE ref-arch-content.md
# ─────────────────────────────────────────────────────────────────────────────
def parse_content(path: Path) -> dict:
    """
    Returns nested dict:  section_name → {key → text_string}
    Ignores HTML comment blocks <!-- … -->
    """
    if not path.exists():
        return {}
    raw = path.read_text()
    # Strip HTML comments
    raw = re.sub(r'<!--.*?-->', '', raw, flags=re.DOTALL)

    result: dict[str, dict[str, str]] = {}
    current_section = None
    current_key     = None
    buf             = []

    for line in raw.splitlines():
        # ## SECTION header
        if re.match(r'^## ', line):
            if current_section and current_key:
                result[current_section][current_key] = '\n'.join(buf).strip()
            sec = line.lstrip('# ').strip().upper()
            current_section = sec
            current_key     = None
            buf             = []
            result.setdefault(current_section, {})

        # ### key header
        elif re.match(r'^### ', line):
            if current_section and current_key:
                result[current_section][current_key] = '\n'.join(buf).strip()
            current_key = line.lstrip('# ').strip().lower()
            buf         = []

        # content line
        elif current_section and current_key is not None:
            buf.append(line)

    # flush last block
    if current_section and current_key:
        result[current_section][current_key] = '\n'.join(buf).strip()

    return result


PARSED = parse_content(CONTENT_FILE) if FILL_MODE else {}


def txt(section: str, key: str, blank_fallback: str) -> str:
    """
    If FILL_MODE and the section/key exists in MD, return MD content.
    Otherwise return blank_fallback (template placeholder).
    """
    if not FILL_MODE:
        return blank_fallback
    val = PARSED.get(section.upper(), {}).get(key.lower(), '').strip()
    return val if val else blank_fallback


def get_list(section: str, prefix: str, blank_template: list[str]) -> list[str]:
    """
    Return list of values for keys prefix1, prefix2, … prefixN from MD.
    If not in FILL_MODE or section missing, return blank_template.
    Strips blank entries so removing a ### srcN really removes the box.
    """
    sec = PARSED.get(section.upper(), {})
    # collect all matching keys in order
    items = []
    i = 1
    while True:
        key = f"{prefix}{i}"
        if key not in sec:
            break
        val = sec[key].strip()
        if val:          # skip explicitly blanked-out entries
            items.append(val)
        i += 1
    return items if (FILL_MODE and items) else blank_template


# ─────────────────────────────────────────────────────────────────────────────
# 2. DEFAULT BLANK-TEMPLATE CONTENT
#    Vendor-specific names (Power BI, Tableau, Excel…) intentionally absent.
#    Section structural labels + Databricks platform names stay.
# ─────────────────────────────────────────────────────────────────────────────
BLANK_SOURCES = [
    "🗄️ Data Warehouses\n[ legacy EDW / cloud DW ]",
    "🏢 On-Premises Systems\n[ core banking / ERP / OLTP ]",
    "☁️ SaaS Applications\n[ CRM / HR / finance apps ]",
    "⚡ Streaming / Events\n[ Kafka / Event Hubs / CDC ]",
    "📁 Files  ·  IoT  ·  APIs\n[ flat files / devices / REST ]",
]

BLANK_OUTPUTS = [
    "🖥️ External Apps",
    "🗄️ Operational\nDatabases",
    "🤝 Data Sharing\n& Collaboration",
    "👤 Business\nUsers",
    "📊 BI Reporting\n[ fill during discovery ]",
]

# Build live source/output lists (dynamic count from MD)
SOURCES = get_list("SOURCES", "src", BLANK_SOURCES)
OUTPUTS = get_list("OUTPUTS", "out", BLANK_OUTPUTS)

# Fixed section content
T_BATCH  = txt("INGESTION",        "batch",  "⏱️ Batch Ingestion\nAuto Loader\nScheduled · File-based")
T_CDC    = txt("INGESTION",        "cdc",    "🔄 CDC Ingestion\nLakeFlow Connect\nChange streams · Managed")
T_STREAM = txt("INGESTION",        "stream", "🌊 Streaming Ingestion\nStructured Streaming\nReal-time · Low-latency")

T_RAW    = txt("MEDALLION",        "raw",    "RAW ZONE\nDelta · Append-only\nSource schema as-is\nNo transforms")
T_ODS    = txt("MEDALLION",        "ods",    "ODS / SILVER\nStandardise + Cleanse\nDQ rules · PII masking\nSCD Type 2")
T_DIMS   = txt("MEDALLION",        "dims",   "Dimensions\nSCD Type 2\nLiquid Clustered")
T_FACTS  = txt("MEDALLION",        "facts",  "Facts\nLiquid Clustered\nPhoton-optimised")
T_DM     = txt("MEDALLION",        "datamarts", "Datamarts\nMaterialized Views\nBusiness aggregates")

T_DE     = txt("DATA_ENGINEERING", "de",     "Spark Declarative Pipelines\nDeclarative ETL · Lineage\nSchema evolution auto")
T_AIML   = txt("AI_ML",            "aiml",   "MLflow · Model Registry\nTrain · Score · Serve\n[ use cases ]")

T_Q5     = txt("QUERY",            "q5",     "Databricks SQL\nServerless · Photon\nIWM auto-scale\nHigh-concurrency")
T_Q6     = txt("DASHBOARDS",       "q6",     "AI/BI Dashboards\nNL → chart · AI-assisted\n[ BI tool — fill during discovery ]")
T_Q7     = txt("SERVE",            "q7",     "Delta Sharing\nDownstream apps · APIs\nNotebooks\n[ sharing targets ]")
T_Q8     = txt("NLQ",              "q8",     "Genie Space\nNL → SQL\nSelf-service · auditable\n[ use cases ]")

T_GOV    = txt("GOVERNANCE",       "gov",    "Unity Catalog\n────────────────\nAccess control · Lineage\nAuditing · Classification\nRow filters · Column masks\nABAC tag policies")
T_STORE  = txt("OPEN_STORAGE",     "store",  "Delta Lake  ·  Parquet  ·  Iceberg\n────────────────\nOpen formats · Vendor-neutral\nACID · Time Travel · Durable")

T_ORCH   = "ORCHESTRATION  —  Databricks Workflows · Jobs · Dependency Management · Error Handling · Monitoring"

# Customer meta
CNAME    = txt("CUSTOMER", "name",       "[Customer Name]")
CCLOUD   = txt("CUSTOMER", "cloud",      "On-Prem  ·  Cloud  ·  SaaS")

# ─────────────────────────────────────────────────────────────────────────────
# 3. COLOUR PALETTE  (matched from official Databricks ref arch screenshot)
# ─────────────────────────────────────────────────────────────────────────────
C_ORANGE      = "#FF3621"   # Databricks orange — main border, title bar
C_TEAL_DARK   = "#1B3A4B"   # Sources sidebar, orchestration banner
C_TEAL_CIRCLE = "#00897B"   # Step-number circles
C_TEAL_LIGHT  = "#E8F5F3"   # Source icon cell background
C_GOLD        = "#D4980A"   # Datamarts / Gold
C_SILVER      = "#7B8FA1"   # ODS / Silver
C_BRONZE      = "#C0392B"   # RAW / Bronze
C_DASH_BG     = "#F8FAFB"   # Dashed-box interior
C_DASH_BD     = "#64748B"   # Dashed-box border
C_OUT_BG      = "#F1F5F9"   # Right output boxes
C_WHITE       = "#FFFFFF"
C_BLACK       = "#1E293B"

# ─────────────────────────────────────────────────────────────────────────────
# 4. ELEMENT BUILDERS
# ─────────────────────────────────────────────────────────────────────────────
_eid = 3000
elements: list[dict] = []

def _nid():
    global _eid; _eid += 1; return str(_eid)

def _ts():
    return int(time.time() * 1000)

def _base(t: str, x, y, w, h) -> dict:
    return dict(id=_nid(), type=t, x=x, y=y, width=w, height=h, angle=0,
                groupIds=[], seed=random.randint(1,99999), version=1,
                versionNonce=random.randint(1,99999), isDeleted=False,
                boundElements=None, updated=_ts(), link=None, locked=False)

def R(x, y, w, h, bg, stroke, *,
      stroke_w=1.5, dash=False, radius=True, opacity=100):
    e = _base("rectangle", x, y, w, h)
    e.update(strokeColor=stroke, backgroundColor=bg, fillStyle="solid",
             strokeWidth=stroke_w,
             strokeStyle="dashed" if dash else "solid",
             roughness=0, opacity=opacity,
             roundness={"type": 3, "value": 6} if radius else None)
    elements.append(e)

def T(x, y, w, h, text, fc=C_BLACK, fs=11, align="center"):
    e = _base("text", x, y, w, h)
    e.update(strokeColor=fc, backgroundColor="transparent",
             fillStyle="solid", strokeWidth=1, strokeStyle="solid",
             roughness=0, opacity=100, roundness=None,
             text=text, fontSize=fs, fontFamily=2,
             textAlign=align, verticalAlign="middle",
             baseline=fs, containerId=None, originalText=text,
             lineHeight=1.3)
    elements.append(e)

def E(x, y, d, bg, stroke):
    """Circle for step-number badge."""
    e = _base("ellipse", x, y, d, d)
    e.update(strokeColor=stroke, backgroundColor=bg, fillStyle="solid",
             strokeWidth=2, strokeStyle="solid", roughness=0, opacity=100,
             roundness={"type": 3, "value": 6})
    elements.append(e)

def badge(x, y, num, d=26):
    E(x, y, d, C_TEAL_CIRCLE, C_TEAL_CIRCLE)
    T(x, y, d, d, str(num), C_WHITE, fs=12, align="center")

def arrow(x1, y1, x2, y2, bidirectional=False):
    e = _base("arrow", x1, y1, x2-x1, y2-y1)
    e.update(strokeColor=C_TEAL_DARK, backgroundColor="transparent",
             fillStyle="solid", strokeWidth=1.5, strokeStyle="solid",
             roughness=0, opacity=100,
             roundness={"type": 2, "value": 16},
             points=[[0, 0], [x2-x1, y2-y1]],
             lastCommittedPoint=None,
             startBinding=None, endBinding=None,
             startArrowhead="arrow" if bidirectional else None,
             endArrowhead="arrow")
    elements.append(e)

def section_box(x, y, w, h, num, label,
                bg=C_DASH_BG, border=C_DASH_BD, dash=True):
    R(x, y, w, h, bg, border, dash=dash)
    badge(x+5, y+5, num, d=24)
    T(x+34, y+5, w-38, 20, label, C_BLACK, fs=10, align="left")

# ─────────────────────────────────────────────────────────────────────────────
# 5. LAYOUT — all measurements in pixels
# ─────────────────────────────────────────────────────────────────────────────
N_SRC = len(SOURCES)   # dynamic
N_OUT = len(OUTPUTS)   # dynamic

# Canvas title bar
TITLE_Y   = 10
TITLE_H   = 36

# Sources sidebar
SRC_X = 20;  SRC_Y = TITLE_Y + TITLE_H + 10
SRC_W = 152

# Main platform box
PLT_X = SRC_X + SRC_W + 14;  PLT_Y = SRC_Y
PLT_W = 1390;                  PLT_H = 0  # computed below

# Inside platform
PI = 10   # inner padding

# Orchestration banner
ORC_H = 38

# Ingestion column
ING_W = 196

# Medallion area
MED_W = 516

# Serve column
SRV_W = PLT_W - ING_W - MED_W - PI*4  # remaining width

# Output column (right of platform)
OUT_X  = PLT_X + PLT_W + 16
OUT_W  = 168
OUT_Y  = PLT_Y   # same top as platform — computed here so serve arrows can reference it

# Foundation height
FOUND_H = 120

# Derive working area height from source count
# At minimum: 560px working area; grows with more sources
WORK_H  = max(560, N_SRC * 118 + 20)
PLT_H   = ORC_H + WORK_H + FOUND_H + PI*5  # total platform height
SRC_H   = PLT_H   # sidebar matches platform
out_bh  = (PLT_H - 20) // N_OUT - 6        # output box height (computed once)

# Interior Y references (inside platform box)
ORC_Y   = PLT_Y + 44 + PI
WORK_Y  = ORC_Y + ORC_H + PI   # where ingestion/medallion/serve start
WORK_BOT= WORK_Y + WORK_H      # bottom of working area
FOUND_Y = WORK_BOT + PI

# Ingestion box
ING_X = PLT_X + PI;    ING_Y = WORK_Y;   ING_H = WORK_H

# Medallion box
MED_X = ING_X + ING_W + PI;  MED_Y = WORK_Y;  MED_H = WORK_H

# Data Engineering + AI/ML strip (top of medallion area)
DE_STRIP_H = 95
DE_W  = (MED_W - 20) // 2 - 5
ML_W  = DE_W
DE_X  = MED_X + 8;                DE_Y = MED_Y + 28
ML_X  = DE_X + DE_W + 6;          ML_Y = DE_Y

# Cylinder storage (below DE strip)
CYL_Y  = DE_Y + DE_STRIP_H + 12
CYL_H  = 100
RAW_W  = 82;   RAW_X  = MED_X + 10
ODS_W  = 82;   ODS_X  = RAW_X + RAW_W + 12
DIMS_W = 76;   DIMS_X = ODS_X + ODS_W + 12;  DIMS_Y = CYL_Y - 24
FACTS_W= 76;   FACTS_X= DIMS_X;               FACTS_Y= DIMS_Y + CYL_H//2 + 14 + 24
DM_W   = 82;   DM_X   = DIMS_X + DIMS_W + 12; DM_Y   = CYL_Y - 12;  DM_H = CYL_H + 30

# Serve column  (4 equal boxes stacked)
SRV_X  = MED_X + MED_W + PI;   SRV_Y = WORK_Y;   SRV_H = WORK_H
SRV_BH = (SRV_H - 6) // 4 - 4   # each serve-box height

# ─────────────────────────────────────────────────────────────────────────────
# 6. DRAW
# ─────────────────────────────────────────────────────────────────────────────

# ── Canvas title bar ──────────────────────────────────────────────────────────
total_w = OUT_X + OUT_W + 10
R(SRC_X, TITLE_Y, total_w - SRC_X, TITLE_H,
  C_TEAL_DARK, C_TEAL_DARK, radius=True)
title_str = (f"INTELLIGENT DATA WAREHOUSING ON DATABRICKS"
             + (f"  —  {CNAME}" if FILL_MODE else "  —  BLANK TEMPLATE"))
T(SRC_X, TITLE_Y, total_w - SRC_X, TITLE_H,
  title_str, C_WHITE, fs=13, align="center")

# ── Platform outer box ────────────────────────────────────────────────────────
R(PLT_X, PLT_Y, PLT_W, PLT_H, C_WHITE, C_ORANGE, stroke_w=3, radius=True)
# Title strip
R(PLT_X, PLT_Y, PLT_W, 42, C_ORANGE, C_ORANGE, radius=True)
T(PLT_X, PLT_Y, PLT_W, 42,
  "🔶  DATA INTELLIGENCE PLATFORM"
  + (f"  ·  {CCLOUD}" if FILL_MODE else ""),
  C_WHITE, fs=14, align="center")

# ── Orchestration banner ───────────────────────────────────────────────────────
R(PLT_X+PI, ORC_Y, PLT_W-PI*2, ORC_H, C_TEAL_DARK, C_TEAL_DARK, radius=False)
T(PLT_X+PI, ORC_Y, PLT_W-PI*2, ORC_H, T_ORCH, C_WHITE, fs=9, align="center")

# ── ① Sources sidebar  (dynamic N_SRC boxes) ─────────────────────────────────
R(SRC_X, SRC_Y, SRC_W, SRC_H, C_TEAL_DARK, C_TEAL_DARK, radius=True)
badge(SRC_X+5, SRC_Y+6, "①", d=24)
T(SRC_X, SRC_Y+6, SRC_W, 22, "DATA SOURCES", C_WHITE, fs=11, align="center")
T(SRC_X, SRC_Y+26, SRC_W, 16, CCLOUD if FILL_MODE else "On-Prem  ·  Cloud  ·  SaaS",
  "#94D3CC", fs=8, align="center")

# Dynamic source boxes — auto-spaced
src_pad   = 6
src_start = SRC_Y + 50
src_avail = SRC_H - 56
src_bh    = (src_avail - src_pad*(N_SRC-1)) // N_SRC

for i, label in enumerate(SOURCES):
    sy = src_start + i * (src_bh + src_pad)
    R(SRC_X+6, sy, SRC_W-12, src_bh, C_TEAL_LIGHT, C_TEAL_CIRCLE, radius=True, stroke_w=1)
    T(SRC_X+6, sy, SRC_W-12, src_bh, label, C_TEAL_DARK, fs=9, align="center")
    # Arrow → platform
    arrow(SRC_X+SRC_W, sy + src_bh//2,
          PLT_X-2,     WORK_Y + (i+0.5)*(WORK_H/N_SRC))

# ── ② Ingestion  (3 fixed boxes: Batch / CDC / Streaming) ────────────────────
section_box(ING_X, ING_Y, ING_W, ING_H, "②", "INGESTION")

ing_items = [
    (T_BATCH,  "#EFF9F7", C_TEAL_CIRCLE),
    (T_CDC,    "#F0FDF4", "#16A34A"),
    (T_STREAM, "#EFF6FF", "#2563EB"),
]
ing_bh = (ING_H - 36) // 3 - 6
for i, (label, bg, col) in enumerate(ing_items):
    iy = ING_Y + 32 + i*(ing_bh + 8)
    R(ING_X+6, iy, ING_W-12, ing_bh, bg, col, radius=True, stroke_w=1.2, dash=False)
    T(ING_X+6, iy, ING_W-12, ing_bh, label, C_BLACK, fs=9, align="center")

arrow(ING_X+ING_W, ING_Y+ING_H//2, MED_X-2, MED_Y+MED_H//2)

# ── ③ Medallion area + ④ DE / AI/ML ──────────────────────────────────────────
section_box(MED_X, MED_Y, MED_W, MED_H, "③", "MEDALLION STORAGE")

# DE box
R(DE_X, DE_Y, DE_W, DE_STRIP_H, "#F0FDF4", C_TEAL_CIRCLE, dash=True, radius=True, stroke_w=1.5)
badge(DE_X+4, DE_Y+4, "④", d=22)
T(DE_X+30, DE_Y+4, DE_W-34, 18, "DATA ENGINEERING", C_TEAL_DARK, fs=9, align="left")
T(DE_X+4, DE_Y+24, DE_W-8, DE_STRIP_H-28, T_DE, "#1B4332", fs=8, align="center")

# AI/ML box
R(ML_X, ML_Y, ML_W, DE_STRIP_H, "#FFF7ED", C_ORANGE, dash=True, radius=True, stroke_w=1.5)
badge(ML_X+4, ML_Y+4, "④", d=22)
T(ML_X+30, ML_Y+4, ML_W-34, 18, "AI / ML", "#92400E", fs=9, align="left")
T(ML_X+4, ML_Y+24, ML_W-8, DE_STRIP_H-28, T_AIML, "#7C2D12", fs=8, align="center")

arrow(DE_X+DE_W, DE_Y+DE_STRIP_H//2, ML_X, ML_Y+DE_STRIP_H//2, bidirectional=True)

# Storage cylinders
for (rx,ry,rw,rh,label,body,bg,col) in [
    (RAW_X,  CYL_Y,  RAW_W,  CYL_H,  "🥉 RAW",   T_RAW,   "#FDECEA", C_BRONZE),
    (ODS_X,  CYL_Y,  ODS_W,  CYL_H,  "🥈 ODS",   T_ODS,   "#F1F5F9", C_SILVER),
    (DIMS_X, DIMS_Y, DIMS_W, CYL_H//2+8, "🥇 Dims", T_DIMS, "#FFFBEB", C_GOLD),
    (FACTS_X,FACTS_Y,FACTS_W,CYL_H//2+8,"🥇 Facts",T_FACTS,"#FFFBEB", C_GOLD),
    (DM_X,   DM_Y,   DM_W,   DM_H,   "📊 Marts",T_DM,    "#FEF3C7", "#B45309"),
]:
    R(rx, ry, rw, rh, bg, col, radius=True, stroke_w=1.5)
    T(rx, ry,   rw, 18, label, col,    fs=9,  align="center")
    T(rx, ry+18, rw, rh-20, body, C_BLACK, fs=8, align="center")

mid_y = CYL_Y + CYL_H//2
arrow(RAW_X+RAW_W,   mid_y,          ODS_X,          mid_y)
arrow(ODS_X+ODS_W,   CYL_Y+CYL_H//3,DIMS_X,          DIMS_Y+CYL_H//4+4)
arrow(ODS_X+ODS_W,   CYL_Y+CYL_H*2//3,FACTS_X,       FACTS_Y+CYL_H//4+4)
arrow(DIMS_X+DIMS_W, DIMS_Y+CYL_H//4+4, DM_X,        DM_Y+DM_H//3)
arrow(FACTS_X+FACTS_W,FACTS_Y+CYL_H//4+4,DM_X,       DM_Y+DM_H*2//3)

arrow(MED_X+MED_W,   MED_Y+MED_H//2, SRV_X-2,        SRV_Y+SRV_H//2)

# ── ⑤⑥⑦⑧ Serve / Consume  (4 fixed boxes) ────────────────────────────────────
R(SRV_X, SRV_Y, SRV_W, SRV_H, C_DASH_BG, C_DASH_BD, dash=True)

serve_items = [
    ("⑤", "QUERY",               T_Q5,  "#EFF9F7", C_TEAL_CIRCLE),
    ("⑥", "DASHBOARDS",          T_Q6,  "#FFF7ED", C_ORANGE),
    ("⑦", "SERVE",               T_Q7,  "#F0FDF4", "#16A34A"),
    ("⑧", "NATURAL LANGUAGE QUERY", T_Q8, "#F5F3FF", "#7C3AED"),
]
for i, (num, title, body, bg, col) in enumerate(serve_items):
    bx = SRV_X+6;  by = SRV_Y+6 + i*(SRV_BH+6)
    bw = SRV_W-12
    R(bx, by, bw, SRV_BH, bg, col, radius=True, dash=False, stroke_w=1.5)
    badge(bx+4, by+4, num, d=22)
    T(bx+30, by+4, bw-34, 18, title, col, fs=9, align="left")
    T(bx+4,  by+24, bw-8, SRV_BH-28, body, C_BLACK, fs=8, align="center")
    # Arrow → nearest output box
    target_i = min(i, N_OUT-1)
    oy = OUT_Y + 10 + target_i*(out_bh+8) + out_bh//2
    arrow(bx+bw, by+SRV_BH//2, OUT_X-2, oy)

# ── Foundation strip ──────────────────────────────────────────────────────────
R(PLT_X+PI, FOUND_Y, PLT_W-PI*2, FOUND_H, C_TEAL_DARK, C_ORANGE,
  stroke_w=2, radius=True)
T(PLT_X+PI, FOUND_Y, PLT_W-PI*2, 20,
  "UNIFIED  ·  OPEN  ·  SCALABLE  LAKEHOUSE  ARCHITECTURE",
  C_WHITE, fs=10, align="center")
# Gov + Storage side by side
hw = (PLT_W - PI*4) // 2
R(PLT_X+PI,    FOUND_Y+22, hw,   FOUND_H-28, "#1B3A4B", C_TEAL_CIRCLE, radius=True)
T(PLT_X+PI,    FOUND_Y+22, hw,   18, "🛡️  GOVERNANCE", "#94D3CC", fs=10, align="center")
T(PLT_X+PI,    FOUND_Y+40, hw,   FOUND_H-46, T_GOV, C_WHITE, fs=8, align="center")

R(PLT_X+PI*2+hw, FOUND_Y+22, hw, FOUND_H-28, "#1B3A4B", C_ORANGE, radius=True)
T(PLT_X+PI*2+hw, FOUND_Y+22, hw, 18, "📦  OPEN STORAGE", "#FCA5A5", fs=10, align="center")
T(PLT_X+PI*2+hw, FOUND_Y+40, hw, FOUND_H-46, T_STORE, C_WHITE, fs=8, align="center")

# ── Right output boxes  (dynamic N_OUT boxes) ─────────────────────────────────
OUT_Y   = PLT_Y
out_bh  = (PLT_H - 20) // N_OUT - 6   # dynamic height per box

for i, label in enumerate(OUTPUTS):
    oy = OUT_Y + 10 + i*(out_bh+8)
    R(OUT_X, oy, OUT_W, out_bh, C_OUT_BG, C_TEAL_DARK, radius=True, stroke_w=1.5)
    T(OUT_X, oy, OUT_W, out_bh, label, C_TEAL_DARK, fs=10, align="center")

# ─────────────────────────────────────────────────────────────────────────────
# 7. WRITE OUTPUT
# ─────────────────────────────────────────────────────────────────────────────
out_path = OUT_CUSTOMER if FILL_MODE else OUT_TEMPLATE

doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {
        "gridSize": None,
        "viewBackgroundColor": "#F8FAFC",
        "zoom": {"value": 0.65},
        "scrollX": 0,
        "scrollY": 30,
    },
    "files": {},
}

out_path.write_text(json.dumps(doc, indent=2))

print(f"✅  Written → {out_path.name}")
print(f"    Mode          : {'customer-filled' if FILL_MODE else 'blank template'}")
print(f"    Source boxes  : {N_SRC}  (edit ## SOURCES in ref-arch-content.md to add/remove)")
print(f"    Output boxes  : {N_OUT}  (edit ## OUTPUTS in ref-arch-content.md to add/remove)")
print(f"    Total elements: {len(elements)}")
print(f"    Canvas        : ~{OUT_X+OUT_W}w × {PLT_Y+PLT_H+60}h px")
print()
print("  Next steps:")
print("  1. Open in Excalidraw:  open", out_path.name)
print("  2. Rebuild everything:  python3 scripts/rebuild_arch.py")
