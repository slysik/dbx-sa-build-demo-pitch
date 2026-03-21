"""Execute a Python file on a Databricks cluster via the Command API."""
import json
import subprocess
import sys
import time

PROFILE = "slysik"
CLUSTER_ID = "0310-193517-r0u8giyo"

def dbx_api(method, path, payload=None):
    cmd = ["databricks", "-p", PROFILE, "api", method, path]
    if payload:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: {r.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(r.stdout)

# Create context
ctx = dbx_api("post", "/api/1.2/contexts/create", {"clusterId": CLUSTER_ID, "language": "python"})
context_id = ctx["id"]
print(f"Context: {context_id}")

# Read the script
script_path = sys.argv[1] if len(sys.argv) > 1 else "scripts/generate_retail_data.py"
with open(script_path) as f:
    code = f.read()

# Execute
result = dbx_api("post", "/api/1.2/commands/execute", {
    "clusterId": CLUSTER_ID,
    "contextId": context_id,
    "language": "python",
    "command": code,
})
cmd_id = result["id"]
print(f"Command: {cmd_id} — running...")

# Poll
while True:
    status = dbx_api("get", f"/api/1.2/commands/status?clusterId={CLUSTER_ID}&contextId={context_id}&commandId={cmd_id}")
    state = status["status"]
    if state in ("Finished", "Error", "Cancelled"):
        results = status.get("results", {})
        print(f"\nState: {state}")
        print(f"Type: {results.get('resultType', '')}")
        data = results.get("data", "")
        if data:
            print(data)
        cause = results.get("cause", "")
        if cause:
            print(f"ERROR:\n{cause}")
        break
    print(".", end="", flush=True)
    time.sleep(5)
