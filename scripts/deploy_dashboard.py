"""Deploy retail dashboard via Lakeview API."""
import json
import subprocess
import sys

WH_ID = "b89b264d78f9d52e"
PROFILE = "slysik"
HOST = "https://adb-7405619449104571.11.azuredatabricks.net"

with open("dashboard/retail_dashboard.json") as f:
    dash = json.load(f)

payload = {
    "display_name": "Retail Performance Dashboard",
    "parent_path": "/Users/slysik@gmail.com/dashboards",
    "warehouse_id": WH_ID,
    "serialized_dashboard": json.dumps(dash),
}

r = subprocess.run(
    ["databricks", "-p", PROFILE, "api", "post", "/api/2.0/lakeview/dashboards", "--json", json.dumps(payload)],
    capture_output=True, text=True,
)

if r.returncode != 0:
    print(f"Error: {r.stderr}", file=sys.stderr)
    sys.exit(1)

d = json.loads(r.stdout)
dash_id = d.get("dashboard_id", "")
print(f"Dashboard ID: {dash_id}")
print(f"Path: {d.get('path', '')}")
print(f"URL: {HOST}/dashboardsv3/{dash_id}")
