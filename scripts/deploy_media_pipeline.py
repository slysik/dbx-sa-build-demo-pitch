"""Deploy Media SDP: upload Silver + Gold SQL → create/update pipeline → run → validate."""
import json, subprocess, sys, time

PROFILE = "slysik"
HOST = "https://adb-7405619449104571.11.azuredatabricks.net"
WH_ID = "b89b264d78f9d52e"
CATALOG = "interview"
SCHEMA = "media"
PIPELINE_NAME = "media_medallion"
USER = "slysik@gmail.com"

SQL_FILES = {
    "media_silver.sql": "pipeline/media_silver.sql",
    "media_gold.sql":   "pipeline/media_gold.sql",
}

def cli(*args) -> str:
    r = subprocess.run(["databricks", "-p", PROFILE] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: {r.stderr}", file=sys.stderr)
    return r.stdout

def api_post(path, payload):
    return json.loads(cli("api", "post", path, "--json", json.dumps(payload)))

def api_get(path):
    return json.loads(cli("api", "get", path))

def api_put(path, payload):
    return json.loads(cli("api", "put", path, "--json", json.dumps(payload)))

# ── 1. Upload SQL ──
print("1/4 Uploading SDP SQL...")
for target_name, local_path in SQL_FILES.items():
    target = f"/Users/{USER}/media_pipeline/{target_name}"
    cli("workspace", "mkdirs", f"/Users/{USER}/media_pipeline")
    cli("workspace", "import", target, "--file", local_path,
        "--format", "SOURCE", "--language", "SQL", "--overwrite")
    print(f"  ✓ {local_path} → {target}")

# ── 2. Find or create pipeline ──
print("2/4 Finding/creating pipeline...")
pipelines = api_get(f"/api/2.0/pipelines?filter=name%20LIKE%20%27{PIPELINE_NAME}%27")
existing = [p for p in pipelines.get("statuses", []) if p.get("name") == PIPELINE_NAME]

pipeline_spec = {
    "name": PIPELINE_NAME,
    "catalog": CATALOG,
    "target": SCHEMA,
    "channel": "CURRENT",
    "serverless": True,
    "continuous": False,
    "libraries": [
        {"notebook": {"path": f"/Users/{USER}/media_pipeline/media_silver.sql"}},
        {"notebook": {"path": f"/Users/{USER}/media_pipeline/media_gold.sql"}},
    ],
}

if existing:
    pipeline_id = existing[0]["pipeline_id"]
    api_put(f"/api/2.0/pipelines/{pipeline_id}", pipeline_spec)
    print(f"  ✓ Updated: {pipeline_id}")
else:
    result = api_post("/api/2.0/pipelines", pipeline_spec)
    pipeline_id = result["pipeline_id"]
    print(f"  ✓ Created: {pipeline_id}")

# ── 3. Trigger run ──
full_refresh = "--full-refresh" in sys.argv
print(f"3/4 Running ({'full refresh' if full_refresh else 'incremental'})...")
api_post(f"/api/2.0/pipelines/{pipeline_id}/updates", {"full_refresh": full_refresh})

for _ in range(60):
    info = api_get(f"/api/2.0/pipelines/{pipeline_id}")
    updates = info.get("latest_updates", [])
    state = updates[0].get("state", "") if updates else ""
    print(f"  [{time.strftime('%H:%M:%S')}] {state}")
    if state in ("COMPLETED", "FAILED", "CANCELED"):
        break
    time.sleep(10)

if state != "COMPLETED":
    print(f"\n❌ Pipeline {state}: {HOST}/pipelines/{pipeline_id}")
    sys.exit(1)

# ── 4. Validate ──
print("4/4 Validating...")
tables = [
    "bronze_content", "bronze_subscribers", "bronze_stream_events",
    "silver_content", "silver_subscribers", "silver_stream_events",
    "gold_daily_streaming", "gold_content_popularity", "gold_plan_engagement",
]
unions = " UNION ALL ".join(
    f"SELECT '{t}' AS tbl, COUNT(*) AS rows FROM {CATALOG}.{SCHEMA}.{t}" for t in tables
)
result = api_post("/api/2.0/sql/statements", {
    "warehouse_id": WH_ID, "statement": unions, "wait_timeout": "50s",
})

print(f"\n{'Table':<35} {'Rows':>10}")
print("-" * 48)
for r in sorted(result.get("result", {}).get("data_array", []), key=lambda x: x[0]):
    cnt = int(float(r[1]))
    print(f"  {r[0]:<33} {cnt:>10,}  {'✓' if cnt > 0 else '✗ EMPTY'}")

print(f"\n✅ Pipeline: {HOST}/pipelines/{pipeline_id}")
