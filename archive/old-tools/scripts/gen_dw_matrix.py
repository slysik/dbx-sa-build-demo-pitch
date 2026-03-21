#!/usr/bin/env python3
"""
Generate DW Performance Feature Matrix Excalidraw diagram.
Covers: Dataupia → Netezza → Yellowbrick → Fabric DW → Databricks SQL
Steve Lysik — Insider View: 20 Years Across All Five Platforms
"""
import json, random, time

# ── Colour palette ──────────────────────────────────────────────────────────
STRONG  = {"bg": "#b7e4c7", "fc": "#1a5c38"}   # green
GOOD    = {"bg": "#fff3cd", "fc": "#6d4c00"}   # amber
LIMITED = {"bg": "#f8d7da", "fc": "#7b1d24"}   # red
NA      = {"bg": "#e9ecef", "fc": "#6c757d"}   # grey
DBSQL   = {"bg": "#cfe2ff", "fc": "#0a3e85"}   # blue  ← Databricks native
FEAT    = {"bg": "#f8fafc", "fc": "#1e293b"}   # feature label col

# Column header colours
H_FEAT  = {"bg": "#1e293b", "fc": "#ffffff"}
H_DAT   = {"bg": "#4b5563", "fc": "#ffffff"}
H_NET   = {"bg": "#1d4ed8", "fc": "#ffffff"}
H_YB    = {"bg": "#b45309", "fc": "#ffffff"}
H_FAB   = {"bg": "#6d28d9", "fc": "#ffffff"}
H_DBS   = {"bg": "#ea580c", "fc": "#ffffff"}

# Category header colours
CAT_PERF  = {"bg": "#dbeafe", "fc": "#1e40af"}
CAT_FLEX  = {"bg": "#dcfce7", "fc": "#14532d"}
CAT_COST  = {"bg": "#fef3c7", "fc": "#78350f"}
CAT_SCALE = {"bg": "#ede9fe", "fc": "#3b0764"}
CAT_GOV   = {"bg": "#fce7f3", "fc": "#831843"}
CAT_DBX   = {"bg": "#fff7ed", "fc": "#7c2d12"}   # Databricks exclusive section

# ── Grid geometry ────────────────────────────────────────────────────────────
COLS = [
    {"key": "feat",  "x":  40, "w": 240},
    {"key": "dat",   "x": 280, "w": 148},
    {"key": "net",   "x": 428, "w": 148},
    {"key": "yb",    "x": 576, "w": 148},
    {"key": "fab",   "x": 724, "w": 148},
    {"key": "dbs",   "x": 872, "w": 180},
]
RIGHT_EDGE = 1052   # 872 + 180
GRID_W     = RIGHT_EDGE - 40   # 1012

ROW_H   = 44   # data rows
CAT_H   = 30   # category header rows
HEAD_H  = 65   # column header row

# ── Element builder ───────────────────────────────────────────────────────────
_id = 1000
elements = []

def _nid():
    global _id
    _id += 1
    return str(_id)

def rect(x, y, w, h, bg, stroke, roughness=0, radius=None):
    r = {
        "id": _nid(), "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h, "angle": 0,
        "strokeColor": stroke, "backgroundColor": bg,
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": roughness, "opacity": 100,
        "groupIds": [], "roundness": {"type": 3, "value": 4} if radius else None,
        "seed": random.randint(1, 99999), "version": 1, "versionNonce": random.randint(1, 99999),
        "isDeleted": False, "boundElements": None,
        "updated": int(time.time() * 1000), "link": None, "locked": False,
    }
    elements.append(r)
    return r

def text(x, y, w, h, content, fc, font_size=11, bold=False, align="center"):
    family = 2  # Helvetica
    t = {
        "id": _nid(), "type": "text",
        "x": x, "y": y, "width": w, "height": h, "angle": 0,
        "strokeColor": fc, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100,
        "groupIds": [], "roundness": None,
        "seed": random.randint(1, 99999), "version": 1, "versionNonce": random.randint(1, 99999),
        "isDeleted": False, "boundElements": None,
        "updated": int(time.time() * 1000), "link": None, "locked": False,
        "text": content, "fontSize": font_size, "fontFamily": family,
        "textAlign": align, "verticalAlign": "middle",
        "baseline": font_size, "containerId": None, "originalText": content,
        "lineHeight": 1.25,
    }
    elements.append(t)
    return t

def cell(x, y, w, h, content, col_style, font_size=10, fc_override=None):
    fc = fc_override or col_style["fc"]
    bg = col_style["bg"]
    stroke = fc
    rect(x, y, w, h, bg, stroke)
    text(x+2, y, w-4, h, content, fc, font_size=font_size, align="center")

def header_cell(col, y, h, content, style, font_size=12):
    cell(col["x"], y, col["w"], h, content, style, font_size=font_size)

def cat_row(y, label, style):
    rect(40, y, GRID_W, CAT_H, style["bg"], style["fc"], roughness=0)
    text(40, y, GRID_W, CAT_H, label, style["fc"], font_size=13, bold=True)

def data_row(y, feature_label, cells_dict):
    """
    cells_dict: {key: (content, style)} for dat/net/yb/fab/dbs
    feature col uses FEAT style
    """
    col_map = {c["key"]: c for c in COLS}
    # feature cell
    fc_col = col_map["feat"]
    cell(fc_col["x"], y, fc_col["w"], ROW_H, feature_label, FEAT, font_size=10)
    # data cells
    for key, (content, style) in cells_dict.items():
        c = col_map[key]
        cell(c["x"], y, c["w"], ROW_H, content, style, font_size=10)

# ── BUILD DIAGRAM ─────────────────────────────────────────────────────────────

# ── TITLE ────────────────────────────────────────────────────────────────────
rect(40, 10, GRID_W, 52, "#ea580c", "#ea580c", radius=True)
text(40, 10, GRID_W, 52,
     "DW Performance Feature Matrix: Dataupia  →  Netezza  →  Yellowbrick  →  Fabric DW  →  Databricks SQL",
     "#ffffff", font_size=18, bold=True)

rect(40, 65, GRID_W, 28, "#1e293b", "#1e293b")
text(40, 65, GRID_W, 28,
     "Steve Lysik — Insider View: 20 Years Across All Five Platforms  |  Performance · Flexibility · Cost · Scalability · Governance",
     "#94a3b8", font_size=11)

# ── GENERATION TIMELINE ───────────────────────────────────────────────────────
TL_Y = 98
tl_cols = [
    (40,  230, "🏭  Era 1: Hadoop Offload\n2006–2011",               "#6b7280", "#f9fafb"),
    (278, 292, "🔵  Era 2: MPP Appliance Peak\n2000–2018",           "#1d4ed8", "#eff6ff"),
    (578, 146, "⚡  Era 3: NVMe Flash MPP\n2016–present",            "#b45309", "#fffbeb"),
    (732, 146, "🪟  Era 4: Cloud-Native DW\n2023–present",           "#6d28d9", "#f5f3ff"),
    (886, 168, "🔶  Era 5: Unified Lakehouse\nToday + Future",       "#ea580c", "#fff7ed"),
]
for tx, tw, label, stroke, bg in tl_cols:
    rect(tx, TL_Y, tw, 70, bg, stroke, roughness=0, radius=True)
    text(tx+4, TL_Y, tw-8, 70, label, stroke, font_size=10)

# ── COLUMN HEADERS ────────────────────────────────────────────────────────────
HEAD_Y = 175
for col, style, label in [
    (COLS[0], H_FEAT,  "FEATURE"),
    (COLS[1], H_DAT,   "🏭 Dataupia\n2006–2011\nHadoop-era offload"),
    (COLS[2], H_NET,   "🔵 Netezza (IBM)\nMPP Appliance\nNPS / S-Blade"),
    (COLS[3], H_YB,    "⚡ Yellowbrick\nNVMe Flash MPP\nAppliance + Cloud"),
    (COLS[4], H_FAB,   "🪟 Microsoft\nFabric DW\nOneLake + T-SQL"),
    (COLS[5], H_DBS,   "🔶 Databricks SQL\nServerless · Photon\nDelta Lake"),
]:
    header_cell(col, HEAD_Y, HEAD_H, label, style, font_size=12)

# ── SECTION: PERFORMANCE ─────────────────────────────────────────────────────
y = HEAD_Y + HEAD_H  # 240

cat_row(y, "⚡  PERFORMANCE", CAT_PERF);  y += CAT_H  # 270

data_row(y, "Query Engine", {
    "dat": ("MapReduce\nBatch only\nNo vectorization",           LIMITED),
    "net": ("Custom MPP\nS-Blade parallel\nFPGA scan assist",   STRONG),
    "yb":  ("Warp Speed\nNVMe ~80GB/s\nColumnar scan",          STRONG),
    "fab": ("SQL Server DW\nColumnstore CCI\nGood BI perf",     GOOD),
    "dbs": ("Photon (C++)\nVectorized SIMD\nBenchmark leader",  DBSQL),
}); y += ROW_H  # 314

data_row(y, "Data Skipping\n/ Zone Maps", {
    "dat": ("None\nFull scans only\n—",                             NA),
    "net": ("Zone Maps\n3MB extents\nAuto-maintained",             GOOD),
    "yb":  ("Column Stats\nBlock-level skip\nAuto-collected",      GOOD),
    "fab": ("Statistics\nRow group skip\nAuto-updated",            GOOD),
    "dbs": ("Delta Data Skip\nMin/max per file\n+ Liquid Cluster", DBSQL),
}); y += ROW_H  # 358

data_row(y, "Clustering /\nSort Keys", {
    "dat": ("DISTRIBUTE ON\nHash only\nNo sort layer",          NA),
    "net": ("CBT Sort Keys\nFixed at CREATE\nCTAS to change",  LIMITED),
    "yb":  ("SORT ON cols\nFixed at CREATE\nCTAS to change",   LIMITED),
    "fab": ("Clustered CCI\nSome mutability\nRebuild needed",   GOOD),
    "dbs": ("Liquid Clustering\nALTER TABLE · sec\nIncr OPTIMIZE", DBSQL),
}); y += ROW_H  # 402

data_row(y, "Result Cache", {
    "dat": ("None\n—\n—",                                      NA),
    "net": ("None\n—\n—",                                      NA),
    "yb":  ("None\n—\n—",                                      NA),
    "fab": ("Query cache\nDirectLake fast\nPBI optimized",     GOOD),
    "dbs": ("PQE Cache\nAuto-invalidate\nZero compute cost",   DBSQL),
}); y += ROW_H  # 446

data_row(y, "Materialized\nViews", {
    "dat": ("None\n—\n—",                                         NA),
    "net": ("Manual summary\ntables only\nNo auto-refresh",       LIMITED),
    "yb":  ("Manual summary\ntables only\nNo auto-refresh",       LIMITED),
    "fab": ("MVs in preview\nManual refresh\nLimited scope",      GOOD),
    "dbs": ("MVs GA\nAuto-refresh\nPhoton-powered",               DBSQL),
}); y += ROW_H  # 490

data_row(y, "Compression", {
    "dat": ("GZIP only\nRow-level\nBasic",                        LIMITED),
    "net": ("AZ-64 / ZSTD\nColumn-optimized\nAdaptive",          STRONG),
    "yb":  ("LZ4 / ZSTD\nHW-assisted\nColumn-level",             STRONG),
    "fab": ("Snappy/Parquet\nColumnstore CCI\nGood ratio",        GOOD),
    "dbs": ("ZSTD Delta\nColumn-level\nAuto-selected",            DBSQL),
}); y += ROW_H  # 534

# ── SECTION: FLEXIBILITY ──────────────────────────────────────────────────────
cat_row(y, "🔄  FLEXIBILITY", CAT_FLEX);  y += CAT_H  # 564

data_row(y, "Key / Schema\nChanges", {
    "dat": ("CTAS required\nDist key only\nHours/days",               LIMITED),
    "net": ("CTAS required\nOvernight job\nTable offline",            LIMITED),
    "yb":  ("CTAS required\nEven on NVMe\nHours",                    LIMITED),
    "fab": ("ALTER TABLE\nSome ops rebuild\nModerate cost",           GOOD),
    "dbs": ("ALTER TABLE\nCLUSTER BY\nSeconds · No rebuild",         DBSQL),
}); y += ROW_H  # 608

data_row(y, "Auto-\nOptimization", {
    "dat": ("None\nManual only\n—",                                   NA),
    "net": ("Manual GROOM\nManual ANALYZE\nDBA oncall",               NA),
    "yb":  ("Auto ANALYZE\nManual VACUUM\nNo auto-cluster",           LIMITED),
    "fab": ("Auto stats\nPartial vacuum\nManual indexes",             GOOD),
    "dbs": ("Predictive Opt.\nAuto OPTIMIZE\nCLUSTER BY AUTO",        DBSQL),
}); y += ROW_H  # 652

data_row(y, "SQL Dialect /\nProc Support", {
    "dat": ("HiveQL\nLimited SQL\nNo stored procs",                   LIMITED),
    "net": ("Netezza SQL\nBTEQ/FastExport\nANSI + exts",             GOOD),
    "yb":  ("PostgreSQL\nWire compatible\nStandard SQL",              GOOD),
    "fab": ("T-SQL full\nSQL Server procs\nRich ecosystem",           STRONG),
    "dbs": ("ANSI SQL\nSQL Scripting GA\nAI functions",               DBSQL),
}); y += ROW_H  # 696

data_row(y, "Streaming /\nReal-time Ingest", {
    "dat": ("Batch only\nNo streaming\n—",                            NA),
    "net": ("Batch only\nNo streaming\n—",                            NA),
    "yb":  ("Micro-batch\nConnectors only\nNot native",               LIMITED),
    "fab": ("Eventstream\nMaturing\nNot prod-grade yet",              LIMITED),
    "dbs": ("Structured Stream\nLakeFlow CDC\nKafka native",          DBSQL),
}); y += ROW_H  # 740

# ── SECTION: COST MODEL ───────────────────────────────────────────────────────
cat_row(y, "💰  COST MODEL", CAT_COST);  y += CAT_H  # 770

data_row(y, "Compute Model", {
    "dat": ("Commodity HW\nFixed footprint\nCapex",                   LIMITED),
    "net": ("MPP Appliance\nFixed nodes\n$8M+ / yr typical",          LIMITED),
    "yb":  ("Appliance or\ncloud fixed SKU\nHigh Capex/Opex",         LIMITED),
    "fab": ("F-SKU Capacity\nFixed + smoothing\nOpex",                GOOD),
    "dbs": ("Serverless DBU\nPer-second billing\n$0 when idle",       DBSQL),
}); y += ROW_H  # 814

data_row(y, "Idle Cost", {
    "dat": ("Full HW cost\n24/7 always-on\nNo pause",                 LIMITED),
    "net": ("Full appliance\n24/7 always-on\nNo pause",               LIMITED),
    "yb":  ("Always-on cost\nAppliance or\ncloud reserved",           LIMITED),
    "fab": ("F-SKU consumed\nPause = still cost\nCU smoothing",       GOOD),
    "dbs": ("Auto-stop 5 min\n$0 when idle\nFull elasticity",         DBSQL),
}); y += ROW_H  # 858

data_row(y, "Burst Handling\n(Month-end)", {
    "dat": ("No elasticity\nFixed capacity\nCrash or queue",          NA),
    "net": ("WLM rationing\nFixed ceiling\nQueue or fail",            LIMITED),
    "yb":  ("WLM pool slots\nFixed ceiling\nQueue or fail",           LIMITED),
    "fab": ("24hr smoothing\nBurst capacity\nF-SKU ceiling",          GOOD),
    "dbs": ("IWM auto-scale\n+cluster in 15s\nNo hard ceiling",       DBSQL),
}); y += ROW_H  # 902

# ── SECTION: SCALABILITY ──────────────────────────────────────────────────────
cat_row(y, "📈  SCALABILITY", CAT_SCALE);  y += CAT_H  # 932

data_row(y, "Horizontal\nScale", {
    "dat": ("Add Hadoop nodes\nSlow HW refresh\nCapex",               GOOD),
    "net": ("Add S-Blades\nExpensive + slow\nHW refresh cycle",       LIMITED),
    "yb":  ("Add appliance nodes\nor cloud resize\nModerate",         LIMITED),
    "fab": ("Scale F-SKU tier\nAzure-managed\nElastic",               GOOD),
    "dbs": ("Infinite scale\nServerless auto\nNo node ceiling",       DBSQL),
}); y += ROW_H  # 976

data_row(y, "Concurrency\nScaling", {
    "dat": ("Low\nMapReduce queue\n~10–20 users",                     LIMITED),
    "net": ("WLM pools\n100–200 users\nSlot-bounded",                 GOOD),
    "yb":  ("WLM pools\nSlot-bounded\n500+ w/ config",                GOOD),
    "fab": ("Capacity-based\nSmoothing helps\nPBI optimized",         GOOD),
    "dbs": ("IWM auto-scale\nMulti-warehouse\n1,000s concurrent",     DBSQL),
}); y += ROW_H  # 1020

data_row(y, "Storage-Compute\nSeparation", {
    "dat": ("Early attempt\nHDFS + compute\nPartial only",            GOOD),
    "net": ("Tightly coupled\nS-Blade = both\nNo separation",         LIMITED),
    "yb":  ("Appliance: coupled\nCloud: partial\nLimited flex",       LIMITED),
    "fab": ("OneLake + F-SKU\nTrue separation\nAzure-native",         STRONG),
    "dbs": ("Delta on ADLS/S3\nServerless compute\nFull separation",  DBSQL),
}); y += ROW_H  # 1064

# ── SECTION: GOVERNANCE ───────────────────────────────────────────────────────
cat_row(y, "🛡️  GOVERNANCE & TRUST", CAT_GOV);  y += CAT_H  # 1094

data_row(y, "Access Control\n& Security", {
    "dat": ("Hadoop ACLs\nNo col masks\nNo row filters",              LIMITED),
    "net": ("Row-level sec.\nColumn privs\nRole-based",               GOOD),
    "yb":  ("Row security\nColumn privs\nRole-based",                 GOOD),
    "fab": ("RLS + CLS\nMicrosoft Purview\nAzure AD native",          GOOD),
    "dbs": ("Unity Catalog\nRow filt + ColMask\nABAC tags (PP)",      DBSQL),
}); y += ROW_H  # 1138

data_row(y, "Data Lineage", {
    "dat": ("None\nNo auto-capture\n—",                               NA),
    "net": ("Manual docs\nNo auto-lineage\n—",                        LIMITED),
    "yb":  ("Manual docs\nNo auto-lineage\n—",                        LIMITED),
    "fab": ("Purview + PBI\nManual tagging\nPartial auto",            GOOD),
    "dbs": ("Unity Catalog\nAuto-captured\nColumn-level",             DBSQL),
}); y += ROW_H  # 1182

data_row(y, "ACID / Time\nTravel / Audit", {
    "dat": ("No ACID\nNo versioning\nNo audit trail",                 NA),
    "net": ("Snapshot ISO\nNo time travel\nLimited versioning",       LIMITED),
    "yb":  ("MVCC isolation\nNo time travel\nManual audit",           LIMITED),
    "fab": ("ACID transact.\nDelta on OneLake\nNo time travel",       GOOD),
    "dbs": ("Delta ACID full\nTime Travel 30d+\nCHANGE FEED",         DBSQL),
}); y += ROW_H  # 1226

MATRIX_BOTTOM = y   # 1226

# ── DATABRICKS EXCLUSIVE FEATURES CALLOUT ────────────────────────────────────
DBX_Y = MATRIX_BOTTOM + 28   # 1254

rect(40, DBX_Y, GRID_W, 34, "#fff7ed", "#ea580c", roughness=0)
text(40, DBX_Y, GRID_W, 34,
     "🔶  DATABRICKS SQL — EXCLUSIVE FEATURES  (not available in any legacy platform above)",
     "#ea580c", font_size=14, bold=True)

dbx_features = [
    ("⚡ Photon Engine",        "Vectorized C++ engine\nSIMD · JIT compiled\nBenchmark 2.7× faster"),
    ("💧 Liquid Clustering",    "ALTER TABLE · seconds\nIncremental OPTIMIZE\nCLUSTER BY AUTO"),
    ("🔮 Predictive Optim.",    "Auto OPTIMIZE\nAuto VACUUM\nUnity Catalog managed"),
    ("📊 Materialized Views",   "GA · Auto-refresh\nPhoton-accelerated\nRWA / Basel IV calcs"),
    ("🤖 AI Functions",         "ai_query · ai_classify\nai_extract · ai_gen\nSQL-native LLM calls"),
    ("🛡️ Unity Catalog",        "Row filters · Col masks\nABAC tag policies (PP)\nAuto column lineage"),
    ("🔄 LakeFlow Connect",     "Managed CDC serverless\nSchema evolution auto\nNo Debezium to manage"),
    ("📤 Delta Sharing",        "Zero-copy data sharing\nRegulatory submissions\nECB · FRB · PRA ready"),
]

FEAT_BOX_W = 118
FEAT_BOX_H = 72
FEAT_GAP   = 10
FEAT_Y     = DBX_Y + 44
start_x    = 40

for i, (title, body) in enumerate(dbx_features):
    fx = start_x + i * (FEAT_BOX_W + FEAT_GAP)
    rect(fx, FEAT_Y, FEAT_BOX_W, FEAT_BOX_H, "#cfe2ff", "#0a3e85", radius=True)
    text(fx+2, FEAT_Y+2,    FEAT_BOX_W-4, 20, title, "#0a3e85", font_size=11, bold=True)
    text(fx+2, FEAT_Y+22,   FEAT_BOX_W-4, FEAT_BOX_H-22, body, "#1e3a5f", font_size=9)

# ── LEGEND ────────────────────────────────────────────────────────────────────
LEG_Y = FEAT_Y + FEAT_BOX_H + 20  # ~1390

rect(40, LEG_Y, GRID_W, 28, "#f8fafc", "#94a3b8")
text(40, LEG_Y, GRID_W, 28,
     "LEGEND:   🟢 STRONG = industry-leading capability    🟡 GOOD = solid, production-grade    "
     "🔴 LIMITED = real constraints / pain    ⬜ N/A = not available    🔵 DATABRICKS NATIVE = exclusive or best-in-class",
     "#475569", font_size=10)

# ── STEVE'S BACKGROUND FOOTER ────────────────────────────────────────────────
FTR_Y = LEG_Y + 34
rect(40, FTR_Y, GRID_W, 24, "#1e293b", "#1e293b")
text(40, FTR_Y, GRID_W, 24,
     "Steve Lysik — SE: IBM/Netezza (8yr) · Dataupia w/ Foster Hinshaw (4yr, first customer RIMM/BlackBerry) · "
     "Yellowbrick (2yr) · Microsoft GBB / Fabric SME (5yr) · Databricks SA",
     "#94a3b8", font_size=9)

# ── OUTPUT ────────────────────────────────────────────────────────────────────
doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {
        "gridSize": None,
        "viewBackgroundColor": "#ffffff",
        "zoom": {"value": 0.75},
        "scrollX": 0,
        "scrollY": 0,
    },
    "files": {},
}

out_path = "/Users/slysik/databricks/dw-feature-matrix.excalidraw"
with open(out_path, "w") as f:
    json.dump(doc, f, indent=2)

print(f"✅  Written {len(elements)} elements → {out_path}")
print(f"    Matrix rows  : 19 data rows + 5 category headers")
print(f"    Platforms    : Dataupia · Netezza · Yellowbrick · Fabric DW · Databricks SQL")
print(f"    Sections     : Performance · Flexibility · Cost · Scalability · Governance")
print(f"    Exclusive box: 8 Databricks-native features")
print(f"    Total height : ~{FTR_Y + 24}px")
