#!/usr/bin/env python3
"""
Generate a standalone HTML version of the DW Feature Matrix.
Opens directly in any browser — no dependencies.
"""

OUT = "/Users/slysik/databricks/dw-feature-matrix.html"

# ── Colour tokens ─────────────────────────────────────────────────────────────
STRONG  = ("b7e4c7","1a5c38","●● Strong")
GOOD    = ("fff3cd","856404","● Good")
LIMITED = ("f8d7da","7b1d24","▲ Limited")
NA      = ("e9ecef","6c757d","— N/A")
DBSQL   = ("cfe2ff","0a3e85","★ Native")

S,G,L,N,D = STRONG,GOOD,LIMITED,NA,DBSQL

# ── Matrix data ───────────────────────────────────────────────────────────────
SECTIONS = [
    {
        "name": "⚡ PERFORMANCE",
        "hdr_bg": "dbeafe", "hdr_fc": "1e40af",
        "rows": [
            ("Query Engine",
             ("MapReduce\nBatch only\nNo vectorization",L),
             ("Custom MPP\nS-Blade parallel\nFPGA scan assist",S),
             ("Warp Speed\nNVMe ~80 GB/s\nColumnar scan",S),
             ("SQL Server DW\nColumnstore CCI\nGood BI perf",G),
             ("Photon (C++)\nVectorized SIMD\nBenchmark leader",D)),

            ("Data Skipping\n/ Zone Maps",
             ("None\nFull scans only",N),
             ("Zone Maps\n3 MB extents\nAuto-maintained",G),
             ("Column Stats\nBlock-level skip\nAuto-collected",G),
             ("Statistics\nRow group skip\nAuto-updated",G),
             ("Delta Data Skip\nMin/max per file\n+ Liquid Cluster",D)),

            ("Clustering /\nSort Keys",
             ("DISTRIBUTE ON\nHash only\nNo sort layer",N),
             ("CBT Sort Keys\nFixed at CREATE\nCTAS to change",L),
             ("SORT ON cols\nFixed at CREATE\nCTAS to change",L),
             ("Clustered CCI\nSome mutability\nRebuild needed",G),
             ("Liquid Clustering\nALTER TABLE · sec\nIncr OPTIMIZE",D)),

            ("Result Cache",
             ("None",N),
             ("None",N),
             ("None",N),
             ("Query cache\nDirectLake fast\nPBI optimized",G),
             ("PQE Cache\nAuto-invalidate\nZero compute",D)),

            ("Materialized\nViews",
             ("None",N),
             ("Manual summary\ntables only",L),
             ("Manual summary\ntables only",L),
             ("MVs in preview\nManual refresh\nLimited scope",G),
             ("MVs GA\nAuto-refresh\nPhoton-powered",D)),

            ("Compression",
             ("GZIP only\nRow-level\nBasic",L),
             ("AZ-64 / ZSTD\nColumn-optimized\nAdaptive",S),
             ("LZ4 / ZSTD\nHW-assisted\nColumn-level",S),
             ("Snappy/Parquet\nColumnstore CCI\nGood ratio",G),
             ("ZSTD Delta\nColumn-level\nAuto-selected",D)),
        ]
    },
    {
        "name": "🔄 FLEXIBILITY",
        "hdr_bg": "dcfce7", "hdr_fc": "14532d",
        "rows": [
            ("Key / Schema\nChanges",
             ("CTAS required\nDist key only\nHours / days",L),
             ("CTAS required\nOvernight job\nTable offline",L),
             ("CTAS required\nEven on NVMe\nHours",L),
             ("ALTER TABLE\nSome ops rebuild\nModerate cost",G),
             ("ALTER TABLE\nCLUSTER BY\nSeconds · No rebuild",D)),

            ("Auto-\nOptimization",
             ("None\nManual only",N),
             ("Manual GROOM\nManual ANALYZE\nDBA oncall",N),
             ("Auto ANALYZE\nManual VACUUM\nNo auto-cluster",L),
             ("Auto stats\nPartial vacuum\nManual indexes",G),
             ("Predictive Opt.\nAuto OPTIMIZE\nCLUSTER BY AUTO",D)),

            ("SQL Dialect /\nProc Support",
             ("HiveQL\nLimited SQL\nNo stored procs",L),
             ("Netezza SQL\nBTEQ / FastExport\nANSI + exts",G),
             ("PostgreSQL\nWire compatible\nStandard SQL",G),
             ("T-SQL full\nSQL Server procs\nRich ecosystem",S),
             ("ANSI SQL\nSQL Scripting GA\nAI functions",D)),

            ("Streaming /\nReal-time Ingest",
             ("Batch only\nNo streaming",N),
             ("Batch only\nNo streaming",N),
             ("Micro-batch\nConnectors only\nNot native",L),
             ("Eventstream\nMaturing\nNot prod-grade yet",L),
             ("Structured Stream\nLakeFlow CDC\nKafka native",D)),
        ]
    },
    {
        "name": "💰 COST MODEL",
        "hdr_bg": "fef3c7", "hdr_fc": "78350f",
        "rows": [
            ("Compute Model",
             ("Commodity HW\nFixed footprint\nCapex",L),
             ("MPP Appliance\nFixed nodes\n$8M+ / yr typical",L),
             ("Appliance or\ncloud fixed SKU\nHigh Capex/Opex",L),
             ("F-SKU Capacity\nFixed + smoothing\nOpex",G),
             ("Serverless DBU\nPer-second billing\n$0 when idle",D)),

            ("Idle Cost",
             ("Full HW cost\n24/7 always-on\nNo pause",L),
             ("Full appliance\n24/7 always-on\nNo pause",L),
             ("Always-on cost\nAppliance or\ncloud reserved",L),
             ("F-SKU consumed\nPause = still cost\nCU smoothing",G),
             ("Auto-stop 5 min\n$0 when idle\nFull elasticity",D)),

            ("Burst Handling\n(Month-end)",
             ("No elasticity\nFixed capacity\nCrash or queue",N),
             ("WLM rationing\nFixed ceiling\nQueue or fail",L),
             ("WLM pool slots\nFixed ceiling\nQueue or fail",L),
             ("24hr smoothing\nBurst capacity\nF-SKU ceiling",G),
             ("IWM auto-scale\n+cluster in 15s\nNo hard ceiling",D)),
        ]
    },
    {
        "name": "📈 SCALABILITY",
        "hdr_bg": "ede9fe", "hdr_fc": "3b0764",
        "rows": [
            ("Horizontal\nScale",
             ("Add Hadoop nodes\nSlow HW refresh\nCapex",G),
             ("Add S-Blades\nExpensive + slow\nHW refresh cycle",L),
             ("Add appliance\nnodes or resize\ncloud instance",L),
             ("Scale F-SKU tier\nAzure-managed\nElastic",G),
             ("Infinite scale\nServerless auto\nNo node ceiling",D)),

            ("Concurrency\nScaling",
             ("Low\nMapReduce queue\n~10–20 users",L),
             ("WLM pools\n100–200 users\nSlot-bounded",G),
             ("WLM pools\nSlot-bounded\n500+ w/ config",G),
             ("Capacity-based\nSmoothing helps\nPBI optimized",G),
             ("IWM auto-scale\nMulti-warehouse\n1,000s concurrent",D)),

            ("Storage-Compute\nSeparation",
             ("Early attempt\nHDFS + compute\nPartial only",G),
             ("Tightly coupled\nS-Blade = both\nNo separation",L),
             ("Appliance: coupled\nCloud: partial\nLimited flex",L),
             ("OneLake + F-SKU\nTrue separation\nAzure-native",S),
             ("Delta on ADLS/S3\nServerless compute\nFull separation",D)),
        ]
    },
    {
        "name": "🛡️ GOVERNANCE & TRUST",
        "hdr_bg": "fce7f3", "hdr_fc": "831843",
        "rows": [
            ("Access Control\n& Security",
             ("Hadoop ACLs\nNo col masks\nNo row filters",L),
             ("Row-level sec.\nColumn privs\nRole-based",G),
             ("Row security\nColumn privs\nRole-based",G),
             ("RLS + CLS\nMicrosoft Purview\nAzure AD native",G),
             ("Unity Catalog\nRow filt + ColMask\nABAC tags (PP)",D)),

            ("Data Lineage",
             ("None\nNo auto-capture",N),
             ("Manual docs\nNo auto-lineage",L),
             ("Manual docs\nNo auto-lineage",L),
             ("Purview + PBI\nManual tagging\nPartial auto",G),
             ("Unity Catalog\nAuto-captured\nColumn-level",D)),

            ("ACID / Time\nTravel / Audit",
             ("No ACID\nNo versioning\nNo audit trail",N),
             ("Snapshot ISO\nNo time travel\nLimited versioning",L),
             ("MVCC isolation\nNo time travel\nManual audit",L),
             ("ACID transact.\nDelta on OneLake\nNo time travel",G),
             ("Delta ACID full\nTime Travel 30d+\nCHANGE FEED",D)),
        ]
    },
]

DBSQL_FEATURES = [
    ("⚡ Photon Engine",       "Vectorized C++ engine\nSIMD · JIT compiled\nBenchmark 2.7× faster"),
    ("💧 Liquid Clustering",   "ALTER TABLE · seconds\nIncremental OPTIMIZE\nCLUSTER BY AUTO"),
    ("🔮 Predictive Optim.",   "Auto OPTIMIZE\nAuto VACUUM\nUnity Catalog mgmt"),
    ("📊 Materialized Views",  "GA · Auto-refresh\nPhoton-accelerated\nRWA / Basel IV calcs"),
    ("🤖 AI Functions",        "ai_query · ai_classify\nai_extract · ai_gen\nSQL-native LLM calls"),
    ("🛡️ Unity Catalog",       "Row filters · Col masks\nABAC tag policies (PP)\nAuto column lineage"),
    ("🔄 LakeFlow Connect",    "Managed CDC serverless\nSchema evolution auto\nNo Debezium to manage"),
    ("📤 Delta Sharing",       "Zero-copy data sharing\nRegulatory submissions\nECB · FRB · PRA ready"),
]

# ── HTML generation ───────────────────────────────────────────────────────────
def badge(rating):
    bg, fc, label = rating
    return f'<span style="background:#{bg};color:#{fc};padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;white-space:nowrap">{label}</span>'

def cell_html(text, rating):
    bg, fc, _ = rating
    lines = text.strip().split("\n")
    content = "<br>".join(lines)
    b = badge(rating)
    return (f'<td style="background:#{bg};padding:6px 8px;vertical-align:top;'
            f'border:1px solid #dee2e6;min-width:110px;max-width:140px">'
            f'{b}<div style="color:#{fc};font-size:10px;margin-top:4px;'
            f'line-height:1.4">{content}</div></td>')

def feat_cell(text):
    lines = text.strip().split("\n")
    content = "<br>".join(lines)
    return (f'<td style="background:#f1f5f9;padding:6px 10px;vertical-align:middle;'
            f'border:1px solid #dee2e6;font-size:11px;font-weight:600;'
            f'color:#1e293b;min-width:120px">{content}</td>')

rows_html = []

for sec in SECTIONS:
    # Category header spanning all 6 columns
    rows_html.append(
        f'<tr><td colspan="6" style="background:#{sec["hdr_bg"]};'
        f'color:#{sec["hdr_fc"]};font-size:13px;font-weight:700;'
        f'padding:8px 12px;border:1px solid #dee2e6;letter-spacing:.3px">'
        f'{sec["name"]}</td></tr>'
    )
    for row in sec["rows"]:
        feat = row[0]
        cells = row[1:]   # (dat, net, yb, fab, dbs)
        tr = "<tr>" + feat_cell(feat)
        for (txt, rating) in cells:
            tr += cell_html(txt, rating)
        tr += "</tr>"
        rows_html.append(tr)

# Databricks exclusive feature tiles
tiles = []
for title, body in DBSQL_FEATURES:
    lines = body.strip().split("\n")
    body_html = "<br>".join(lines)
    tiles.append(
        f'<div style="background:#cfe2ff;border:1.5px solid #0a3e85;border-radius:8px;'
        f'padding:10px 12px;min-width:130px;flex:1">'
        f'<div style="color:#0a3e85;font-size:12px;font-weight:700;margin-bottom:6px">{title}</div>'
        f'<div style="color:#1e3a5f;font-size:10px;line-height:1.5">{body_html}</div>'
        f'</div>'
    )
tiles_html = '<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:10px">' + "".join(tiles) + '</div>'

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DW Feature Matrix — Steve Lysik</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         margin: 0; padding: 20px; background: #f8fafc; color: #1e293b; }}
  .wrap {{ max-width: 1120px; margin: 0 auto; }}
  .title-bar {{ background: #ea580c; color: #fff; padding: 16px 24px;
                border-radius: 10px 10px 0 0; }}
  .title-bar h1 {{ margin:0; font-size:18px; line-height:1.3 }}
  .title-bar p  {{ margin:4px 0 0; font-size:12px; opacity:.85 }}
  .era-row {{ display:flex; gap:6px; margin: 10px 0; }}
  .era {{ border-radius:6px; padding:8px 10px; flex:1; font-size:10px;
          font-weight:600; line-height:1.5; }}
  table {{ border-collapse:collapse; width:100%; background:#fff;
           box-shadow:0 2px 8px rgba(0,0,0,.08); }}
  thead th {{ padding:10px 8px; font-size:12px; font-weight:700;
              border:1px solid #dee2e6; text-align:center; }}
  .legend {{ display:flex; gap:12px; margin:14px 0; flex-wrap:wrap; align-items:center }}
  .leg {{ display:flex; align-items:center; gap:5px; font-size:11px }}
  .leg-dot {{ width:14px; height:14px; border-radius:3px }}
  .dbx-section {{ margin-top:18px; background:#fff7ed;
                  border:2px solid #ea580c; border-radius:8px; padding:14px 18px }}
  .dbx-section h3 {{ margin:0 0 2px; font-size:14px; color:#ea580c }}
  .dbx-section p {{ margin:0 0 8px; font-size:11px; color:#78350f }}
  .footer {{ margin-top:14px; background:#1e293b; color:#94a3b8;
             font-size:10px; padding:10px 14px; border-radius:6px; }}
  @media print {{ body{{ padding:0 }} .wrap{{ max-width:100% }} }}
</style>
</head>
<body>
<div class="wrap">

  <!-- TITLE -->
  <div class="title-bar">
    <h1>DW Performance Feature Matrix<br>
        Dataupia &nbsp;→&nbsp; Netezza &nbsp;→&nbsp; Yellowbrick &nbsp;→&nbsp;
        Microsoft Fabric DW &nbsp;→&nbsp; Databricks SQL</h1>
    <p>Steve Lysik — Insider View: 20 Years Across All Five Platforms &nbsp;|&nbsp;
       Performance · Flexibility · Cost · Scalability · Governance</p>
  </div>

  <!-- ERA TIMELINE -->
  <div class="era-row">
    <div class="era" style="background:#f1f5f9;border:1.5px solid #6b7280;color:#374151">
      🏭 <strong>Era 1</strong><br>Hadoop-era Offload<br>2006–2011</div>
    <div class="era" style="background:#eff6ff;border:1.5px solid #1d4ed8;color:#1d4ed8">
      🔵 <strong>Era 2</strong><br>MPP Appliance Peak<br>2000–2018</div>
    <div class="era" style="background:#fffbeb;border:1.5px solid #b45309;color:#b45309">
      ⚡ <strong>Era 3</strong><br>NVMe Flash MPP<br>2016–present</div>
    <div class="era" style="background:#f5f3ff;border:1.5px solid #6d28d9;color:#6d28d9">
      🪟 <strong>Era 4</strong><br>Cloud-Native DW<br>2023–present</div>
    <div class="era" style="background:#fff7ed;border:1.5px solid #ea580c;color:#ea580c">
      🔶 <strong>Era 5</strong><br>Unified Lakehouse<br>Today + Future</div>
  </div>

  <!-- LEGEND -->
  <div class="legend">
    <strong style="font-size:11px">LEGEND:</strong>
    <div class="leg"><div class="leg-dot" style="background:#b7e4c7;border:1px solid #1a5c38"></div>●● Strong</div>
    <div class="leg"><div class="leg-dot" style="background:#fff3cd;border:1px solid #856404"></div>● Good</div>
    <div class="leg"><div class="leg-dot" style="background:#f8d7da;border:1px solid #7b1d24"></div>▲ Limited</div>
    <div class="leg"><div class="leg-dot" style="background:#e9ecef;border:1px solid #6c757d"></div>— N/A</div>
    <div class="leg"><div class="leg-dot" style="background:#cfe2ff;border:1px solid #0a3e85"></div>★ Databricks Native</div>
  </div>

  <!-- MATRIX TABLE -->
  <table>
    <thead>
      <tr>
        <th style="background:#1e293b;color:#fff;min-width:120px">FEATURE</th>
        <th style="background:#4b5563;color:#fff">🏭 Dataupia<br><span style="font-weight:400;font-size:10px">2006–2011<br>Hadoop-era offload</span></th>
        <th style="background:#1d4ed8;color:#fff">🔵 Netezza (IBM)<br><span style="font-weight:400;font-size:10px">MPP Appliance<br>NPS / S-Blade</span></th>
        <th style="background:#b45309;color:#fff">⚡ Yellowbrick<br><span style="font-weight:400;font-size:10px">NVMe Flash MPP<br>Appliance + Cloud</span></th>
        <th style="background:#6d28d9;color:#fff">🪟 Microsoft Fabric DW<br><span style="font-weight:400;font-size:10px">OneLake + T-SQL</span></th>
        <th style="background:#ea580c;color:#fff">🔶 Databricks SQL<br><span style="font-weight:400;font-size:10px">Serverless · Photon<br>Delta Lake</span></th>
      </tr>
    </thead>
    <tbody>
      {"".join(rows_html)}
    </tbody>
  </table>

  <!-- DATABRICKS EXCLUSIVE -->
  <div class="dbx-section">
    <h3>🔶 Databricks SQL — Exclusive Features</h3>
    <p>Not available in any legacy platform above</p>
    {tiles_html}
  </div>

  <!-- FOOTER -->
  <div class="footer">
    Steve Lysik — SE: IBM / Netezza (8 yr) &nbsp;·&nbsp;
    Dataupia w/ Foster Hinshaw (4 yr, first customer RIMM/BlackBerry) &nbsp;·&nbsp;
    Yellowbrick Data (2 yr) &nbsp;·&nbsp;
    Microsoft Global Black Belt / Fabric SME (5 yr) &nbsp;·&nbsp;
    Databricks Solutions Architect
  </div>

</div>
</body>
</html>
"""

with open(OUT, "w") as f:
    f.write(html)

print(f"✅  Written → {OUT}")
print(f"    Sections : {len(SECTIONS)}")
print(f"    Data rows: {sum(len(s['rows']) for s in SECTIONS)}")
print(f"    Platforms: Dataupia · Netezza · Yellowbrick · Fabric DW · Databricks SQL")
print(f"    Excl. features: {len(DBSQL_FEATURES)}")
print(f"    File size: {len(html):,} chars")
