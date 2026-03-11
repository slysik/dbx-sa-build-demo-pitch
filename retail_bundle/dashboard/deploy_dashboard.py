"""Deploy + publish retail dashboard via Lakeview REST API.

SA: Dashboard reads from Gold tables — pre-aggregated, stable contracts.
    embed_credentials=false because personal MS account flakes with embedded auth.
    Viewer's browser session handles auth instead.

Usage: python dashboard/deploy_dashboard.py
"""
import json
import subprocess
import sys

PROFILE = "slysik"
HOST = "https://adb-7405619449104571.11.azuredatabricks.net"
WH_ID = "b89b264d78f9d52e"
USER = "slysik@gmail.com"
DASH_DIR = "retail_bundle/dashboard"


def api(method: str, path: str, payload: dict) -> dict:
    cmd = ["databricks", "-p", PROFILE, "api", method, path, "--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(r.stdout) if r.stdout.strip() else {}


# Load dashboard JSON
with open(f"{DASH_DIR}/retail_dashboard.json") as f:
    dash = json.load(f)

# Create dashboard
print("Creating dashboard...")
result = api("post", "/api/2.0/lakeview/dashboards", {
    "display_name": "Retail Performance Dashboard",
    "parent_path": f"/Users/{USER}/dashboards",
    "warehouse_id": WH_ID,
    "serialized_dashboard": json.dumps(dash),
})

dash_id = result.get("dashboard_id", "")
print(f"  Dashboard ID: {dash_id}")

# Publish — ALWAYS embed_credentials=false on this workspace
print("Publishing (embed_credentials=false)...")
api("post", f"/api/2.0/lakeview/dashboards/{dash_id}/published", {
    "embed_credentials": False,
    "warehouse_id": WH_ID,
})

url = f"{HOST}/dashboardsv3/{dash_id}"
print(f"\n✅ Dashboard live: {url}")
