#!/usr/bin/env python3
"""
Master rebuild — run after editing ref-arch-content.md
Regenerates: blank template Excalidraw
             customer-filled Excalidraw
             live-arch-viewer.html

Usage:
  python3 scripts/rebuild_arch.py           # rebuild everything
  python3 scripts/rebuild_arch.py --open    # rebuild + open browser + Excalidraw
"""
import subprocess, sys, time
from pathlib import Path

BASE    = Path("/Users/slysik/databricks")
SCRIPTS = BASE / "scripts"
OPEN    = "--open" in sys.argv

def run(cmd, label):
    t0 = time.time()
    r  = subprocess.run(cmd, capture_output=True, text=True)
    ok = r.returncode == 0
    elapsed = time.time() - t0
    icon = "✅" if ok else "❌"
    print(f"  {icon}  {label:<44} {elapsed:.1f}s")
    if not ok:
        print(f"     {r.stderr.strip()[:120]}")
    return ok

print()
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  🔶  Databricks Arch Rebuild                          ")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print()

results = []

# 1. Blank template Excalidraw
results.append(run(
    ["python3", str(SCRIPTS/"gen_ref_arch_excalidraw.py")],
    "Blank template  → ref-arch-template.excalidraw"
))

# 2. Customer-filled Excalidraw (reads ref-arch-content.md)
results.append(run(
    ["python3", str(SCRIPTS/"gen_ref_arch_excalidraw.py"), "--customer"],
    "Customer-filled → ref-arch-customer.excalidraw"
))

# 3. Live HTML viewer (reads live-arch.md)
results.append(run(
    ["python3", str(SCRIPTS/"render_arch.py")],
    "HTML viewer     → live-arch-viewer.html"
))

# 4. DW feature matrix HTML
results.append(run(
    ["python3", str(SCRIPTS/"gen_dw_matrix_html.py")],
    "Feature matrix  → dw-feature-matrix.html"
))

print()
passed = sum(results)
print(f"  {'All good ✅' if passed == len(results) else f'{passed}/{len(results)} succeeded'}")
print()
print("  Files ready:")
for f in [
    "ref-arch-template.excalidraw  ← blank whiteboard  (open in Excalidraw)",
    "ref-arch-customer.excalidraw  ← leave-behind       (open in Excalidraw)",
    "live-arch-viewer.html         ← browser viewer     (⌘R to refresh)",
    "dw-feature-matrix.html        ← competitive matrix (browser)",
]:
    print(f"    📄  {f}")

print()
print("  Edit workflow:")
print("    1.  Edit ref-arch-content.md   (sources, BI tool, etc.)")
print("    2.  python3 scripts/rebuild_arch.py --open")
print("    3.  Excalidraw + browser open automatically")
print()

if OPEN and all(results):
    import subprocess
    subprocess.Popen(["open", str(BASE/"ref-arch-customer.excalidraw")])
    subprocess.Popen(["open", str(BASE/"live-arch-viewer.html")])
    print("  🚀  Opened Excalidraw + browser")
