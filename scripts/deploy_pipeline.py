"""Upload SDP SQL (Silver + Gold) + create/trigger pipeline + monitor + validate.

Architecture:
  - Bronze: managed Delta tables written by generate_retail_data_v2.py
  - Silver + Gold: SDP materialized views reading from bronze Delta tables

Usage: python3 scripts/deploy_pipeline.py [--full-refresh]
"""
import json
import subprocess
import sys
import time

PROFILE = "slysik"
HOST = "https://adb-7405619449104571.11.azuredatabricks.net"
WH_ID = "b89b264d78f9d52e"
CATALOG = "interview"
SCHEMA = "retail"
PIPELINE_NAME = "retail_medallion"
USER = "slysik@gmail.com"

# SDP only handles Silver + Gold (Bronze is pre-written as Delta tables)
SQL_FILES = {
    "silver.sql": "pipeline/silver.sql",
    "gold.sql":   "pipeline/gold_v2.sql",
}

def cli(*args) -> str:
    r = subprocess.run(["databricks", "-p", PROFILE] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: {r.stderr}", file=sys.stderr)
    return r.stdout

def api_post(path: str, payload: dict) -> dict:
    return json.loads(cli("api", "post", path, "--json", json.dumps(payload)))

def api_get(path: str) -> dict:
    return json.loads(cli("api", "get", path))


# ═══════════════════════════════════════════════════════════════
# 1. Upload SQL files
# ═══════════════════════════════════════════════════════════════
print("1/4 Uploading SDP SQL (Silver + Gold)...")
for target_name, local_path in SQL_FILES.items():
    target = f"/Users/{USER}/pipeline/{target_name}"
    cli("workspace", "import", target, "--file", local_path,
        "--format", "SOURCE", "--language", "SQL", "--overwrite")
    print(f"  ✓ {local_path} → {target}")


# ═══════════════════════════════════════════════════════════════
# 2. Find or create pipeline
# ═══════════════════════════════════════════════════════════════
print("2/4 Finding/creating pipeline...")
pipelines = api_get(f"/api/2.0/pipelines?filter=name%20LIKE%20%27{PIPELINE_NAME}%27")
existing = [p for p in pipelines.get("statuses", []) if p.get("name") == PIPELINE_NAME]

if existing:
    pipeline_id = existing[0]["pipeline_id"]
    print(f"  ✓ Found existing pipeline: {pipeline_id}")

    # Update pipeline to point to Silver + Gold only (drop bronze.sql)
    api_post(f"/api/2.0/pipelines/{pipeline_id}", {
        "name": PIPELINE_NAME,
        "catalog": CATALOG,
        "target": SCHEMA,
        "channel": "CURRENT",
        "serverless": True,
        "continuous": False,
        "libraries": [
            {"notebook": {"path": f"/Users/{USER}/pipeline/silver.sql"}},
            {"notebook": {"path": f"/Users/{USER}/pipeline/gold.sql"}},
        ],
    })
    print(f"  ✓ Updated pipeline libraries (Silver + Gold only)")
else:
    result = api_post("/api/2.0/pipelines", {
        "name": PIPELINE_NAME,
        "catalog": CATALOG,
        "target": SCHEMA,
        "channel": "CURRENT",
        "serverless": True,
        "continuous": False,
        "libraries": [
            {"notebook": {"path": f"/Users/{USER}/pipeline/silver.sql"}},
            {"notebook": {"path": f"/Users/{USER}/pipeline/gold.sql"}},
        ],
    })
    pipeline_id = result["pipeline_id"]
    print(f"  ✓ Created pipeline: {pipeline_id}")


# ═══════════════════════════════════════════════════════════════
# 3. Trigger full refresh
# ═══════════════════════════════════════════════════════════════
full_refresh = "--full-refresh" in sys.argv
print(f"3/4 Triggering pipeline ({'full refresh' if full_refresh else 'incremental'})...")
update = api_post(f"/api/2.0/pipelines/{pipeline_id}/updates",
                  {"full_refresh": full_refresh})
update_id = update.get("update_id", "")
print(f"  ✓ Update ID: {update_id}")

# Monitor
for i in range(60):
    info = api_get(f"/api/2.0/pipelines/{pipeline_id}")
    state = info.get("state", "")
    updates = info.get("latest_updates", [])
    update_state = updates[0].get("state", "") if updates else ""
    print(f"  [{time.strftime('%H:%M:%S')}] {state} | {update_state}")
    if update_state in ("COMPLETED", "FAILED", "CANCELED"):
        break
    time.sleep(10)

if update_state != "COMPLETED":
    print(f"\n❌ Pipeline {update_state}. Check UI: {HOST}/pipelines/{pipeline_id}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# 4. Validate row counts (all 12 tables: 4 bronze + 4 silver + 4 gold)
# ═══════════════════════════════════════════════════════════════
print("4/4 Validating row counts...")

tables = [
    "bronze_customers", "bronze_products", "bronze_orders", "bronze_order_items",
    "silver_customers", "silver_products", "silver_orders", "silver_order_items",
    "gold_daily_sales", "gold_product_performance", "gold_customer_ltv", "gold_regional_summary",
]
unions = " UNION ALL ".join(
    f"SELECT '{t}' AS tbl, COUNT(*) AS rows FROM {CATALOG}.{SCHEMA}.{t}"
    for t in tables
)

result = api_post("/api/2.0/sql/statements", {
    "warehouse_id": WH_ID,
    "statement": unions,
    "wait_timeout": "50s",
})

rows = result.get("result", {}).get("data_array", [])
all_ok = True
print(f"\n{'Table':<35} {'Rows':>12}")
print("-" * 50)
for r in sorted(rows, key=lambda x: x[0]):
    cnt = int(float(r[1]))
    marker = "✓" if cnt > 0 else "✗ EMPTY"
    print(f"  {r[0]:<33} {cnt:>12,}  {marker}")
    if cnt == 0:
        all_ok = False

if all_ok:
    print(f"\n✅ All {len(tables)} tables populated.")
    print(f"   Bronze: managed Delta tables (notebook-written)")
    print(f"   Silver + Gold: SDP materialized views")
    print(f"   Pipeline: {HOST}/pipelines/{pipeline_id}")
else:
    print(f"\n❌ Some tables are empty! Check pipeline: {HOST}/pipelines/{pipeline_id}")
    sys.exit(1)
