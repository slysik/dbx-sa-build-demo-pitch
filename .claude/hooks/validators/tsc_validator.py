#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
TypeScript Type Checker Validator for Claude Code PostToolUse Hook

Runs `npx tsc --noEmit` on TypeScript files after Write/Edit operations.

Outputs JSON decision for Claude Code PostToolUse hook:
- {"decision": "block", "reason": "..."} to block and prompt Claude to fix
- {} to allow completion
"""
import json
import logging
import subprocess
import sys
from pathlib import Path

# Logging setup - log file next to this script
SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "tsc_validator.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, mode='a')]
)
logger = logging.getLogger(__name__)


def find_tsconfig(start_path: str) -> Path | None:
    """Walk up from file to find nearest tsconfig.json."""
    current = Path(start_path).parent
    while current != current.parent:
        tsconfig = current / "tsconfig.json"
        if tsconfig.exists():
            return tsconfig
        current = current.parent
    return None


def detect_package_manager(project_dir: Path) -> str:
    """Detect which package manager to use for running tsc."""
    # Check for lockfiles to determine package manager
    if (project_dir / "bun.lockb").exists() or (project_dir / "bun.lock").exists():
        return "bun"
    elif (project_dir / "pnpm-lock.yaml").exists():
        return "pnpm"
    elif (project_dir / "yarn.lock").exists():
        return "yarn"
    else:
        return "npm"


def get_tsc_command(project_dir: Path) -> list[str]:
    """Get the appropriate tsc command based on package manager."""
    pm = detect_package_manager(project_dir)

    # Check if typescript is installed locally
    node_modules_tsc = project_dir / "node_modules" / ".bin" / "tsc"
    if node_modules_tsc.exists():
        return [str(node_modules_tsc), "--noEmit"]

    # Use package manager's runner
    if pm == "bun":
        return ["bunx", "tsc", "--noEmit"]
    elif pm == "pnpm":
        return ["pnpm", "exec", "tsc", "--noEmit"]
    elif pm == "yarn":
        return ["yarn", "tsc", "--noEmit"]
    else:
        return ["npx", "tsc", "--noEmit"]


def main():
    logger.info("=" * 50)
    logger.info("TSC VALIDATOR POSTTOOLUSE HOOK TRIGGERED")

    # Read hook input from stdin (Claude Code passes JSON)
    try:
        stdin_data = sys.stdin.read()
        if stdin_data.strip():
            hook_input = json.loads(stdin_data)
            logger.info(f"hook_input keys: {list(hook_input.keys())}")
        else:
            hook_input = {}
    except json.JSONDecodeError:
        hook_input = {}

    # Extract file_path from PostToolUse input
    file_path = hook_input.get("tool_input", {}).get("file_path", "")
    cwd = hook_input.get("cwd", "")
    logger.info(f"file_path: {file_path}")
    logger.info(f"cwd: {cwd}")

    # Only run for TypeScript files
    if not file_path.endswith((".ts", ".tsx")):
        logger.info("Skipping non-TypeScript file")
        print(json.dumps({}))
        return

    # Skip declaration files and node_modules
    if file_path.endswith(".d.ts") or "node_modules" in file_path:
        logger.info("Skipping declaration file or node_modules")
        print(json.dumps({}))
        return

    # Find nearest tsconfig.json
    tsconfig = find_tsconfig(file_path)
    if not tsconfig:
        logger.info("No tsconfig.json found, skipping type check")
        print(json.dumps({}))
        return

    project_dir = tsconfig.parent
    logger.info(f"Found tsconfig at: {tsconfig}")
    logger.info(f"Running tsc in: {project_dir}")

    # Get appropriate tsc command for this project
    tsc_cmd = get_tsc_command(project_dir)
    logger.info(f"Using command: {' '.join(tsc_cmd)}")

    # Run tsc --noEmit in the project directory
    try:
        result = subprocess.run(
            tsc_cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(project_dir)
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if stdout:
            for line in stdout.split('\n')[:30]:  # Limit log lines
                logger.info(f"  {line}")

        if result.returncode == 0:
            logger.info("RESULT: PASS - TypeScript type check successful")
            print(json.dumps({}))
        else:
            logger.info(f"RESULT: BLOCK (exit code {result.returncode})")
            if stderr:
                for line in stderr.split('\n')[:10]:
                    logger.info(f"  stderr: {line}")

            # Extract errors related to the changed file if possible
            error_output = stdout or stderr or "TypeScript type check failed"

            # Filter to show most relevant errors first
            error_lines = error_output.split('\n')
            relevant_errors = [line for line in error_lines if file_path in line or "error TS" in line]
            if relevant_errors:
                error_summary = '\n'.join(relevant_errors[:10])
            else:
                error_summary = '\n'.join(error_lines[:15])

            print(json.dumps({
                "decision": "block",
                "reason": f"TypeScript type errors found:\n{error_summary[:1000]}\n\nPlease fix these type errors before continuing."
            }))

    except subprocess.TimeoutExpired:
        logger.info("RESULT: BLOCK (timeout)")
        print(json.dumps({
            "decision": "block",
            "reason": "TypeScript type check timed out after 120 seconds"
        }))
    except FileNotFoundError:
        logger.info("RESULT: PASS (npx/tsc not found, skipping)")
        print(json.dumps({}))


if __name__ == "__main__":
    main()
