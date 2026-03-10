#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///
"""
PostToolUseFailure Hook - Runs after a tool fails.

Input schema (similar to PostToolUse but with error instead of tool_response):
{
    "session_id": "abc123",
    "transcript_path": "/path/to/transcript.jsonl",
    "cwd": "/path/to/cwd",
    "permission_mode": "default",
    "hook_event_name": "PostToolUseFailure",
    "tool_name": "Bash",
    "tool_input": { ... },
    "error": { ... },  // Error object with failure details
    "tool_use_id": "toolu_01ABC123..."
}

The 'error' field contains details about why the tool failed.
This hook is useful for logging failures, triggering alerts, or
providing feedback to Claude about the failure.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


def append_lesson(tool_name: str, error: dict, cwd: str) -> None:
    """Auto-append SQL execution failures to tasks/lessons.md with TODO placeholder."""
    try:
        lessons_path = Path(cwd) / "tasks" / "lessons.md" if cwd else Path("tasks/lessons.md")
        if not lessons_path.parent.exists():
            lessons_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract error message (handle both dict and string)
        error_msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        # Truncate long errors
        if len(error_msg) > 120:
            error_msg = error_msg[:120] + "..."

        today = datetime.now().strftime("%Y-%m-%d")
        # Count existing pipeline rules to get next number
        existing = ""
        if lessons_path.exists():
            existing = lessons_path.read_text()
        pipe_count = existing.count("| ") // 2  # rough count of table rows
        next_num = max(pipe_count, 1)

        lesson_line = f"| {next_num} | {today} | {error_msg} | TODO: add rule |\n"

        with open(lessons_path, "a") as f:
            f.write(lesson_line)
    except Exception:
        pass  # Never block on lesson capture failure


def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Add timestamp to the log entry
        input_data['logged_at'] = datetime.now().isoformat()

        # Extract key fields for enhanced logging
        tool_name = input_data.get('tool_name', 'unknown')
        tool_use_id = input_data.get('tool_use_id', 'unknown')
        error = input_data.get('error', {})

        # Create a structured log entry with error details
        log_entry = {
            'timestamp': input_data['logged_at'],
            'session_id': input_data.get('session_id', ''),
            'hook_event_name': input_data.get('hook_event_name', 'PostToolUseFailure'),
            'tool_name': tool_name,
            'tool_use_id': tool_use_id,
            'tool_input': input_data.get('tool_input', {}),
            'error': error,
            'cwd': input_data.get('cwd', ''),
            'permission_mode': input_data.get('permission_mode', ''),
            'transcript_path': input_data.get('transcript_path', ''),
            'raw_input': input_data
        }

        # Ensure log directory exists
        log_dir = Path.cwd() / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'post_tool_use_failure.json'

        # Read existing log data or initialize empty list
        if log_path.exists():
            with open(log_path, 'r') as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []

        # Append new log entry
        log_data.append(log_entry)

        # Write back to file with formatting
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)

        # Auto-append SQL failures to tasks/lessons.md
        if tool_name in ('mcp__databricks__execute_sql', 'mcp__databricks__execute_sql_multi'):
            append_lesson(tool_name, error, input_data.get('cwd', ''))

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Exit cleanly on any other error
        sys.exit(0)


if __name__ == '__main__':
    main()
