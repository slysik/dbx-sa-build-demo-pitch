#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///
"""
PostToolUse Hook - Runs after a tool completes successfully.

Input schema (from docs):
{
    "session_id": "abc123",
    "transcript_path": "/path/to/transcript.jsonl",
    "cwd": "/path/to/cwd",
    "permission_mode": "default",
    "hook_event_name": "PostToolUse",
    "tool_name": "Write",
    "tool_input": { ... },
    "tool_response": { ... },
    "tool_use_id": "toolu_01ABC123..."
}

Output schema options (from docs):
1. Exit code 0 with no output - allows tool completion
2. Exit code 2 - shows stderr to Claude (tool already ran)
3. JSON output with decision control:
   {
     "decision": "block" | undefined,
     "reason": "Explanation for decision",
     "hookSpecificOutput": {
       "hookEventName": "PostToolUse",
       "additionalContext": "Additional information for Claude"
     }
   }

Note: "block" automatically prompts Claude with reason.
      additionalContext adds context for Claude to consider.
"""

import json
import sys
from pathlib import Path


def output_block_decision(reason):
    """
    Output JSON to block and provide feedback to Claude.
    Per docs: "block" automatically prompts Claude with reason.
    """
    output = {
        "decision": "block",
        "reason": reason
    }
    print(json.dumps(output))


def output_additional_context(context):
    """
    Output JSON with additionalContext for Claude.
    Per docs: additionalContext adds context for Claude to consider.
    """
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context
        }
    }
    print(json.dumps(output))


def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Extract relevant fields per docs
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        tool_response = input_data.get('tool_response', {})
        tool_use_id = input_data.get('tool_use_id', '')

        # Ensure log directory exists
        log_dir = Path.cwd() / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'post_tool_use.json'

        # Read existing log data or initialize empty list
        if log_path.exists():
            with open(log_path, 'r') as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []

        # Append new data with all relevant fields
        log_entry = {
            'tool_name': tool_name,
            'tool_input': tool_input,
            'tool_response': tool_response,
            'tool_use_id': tool_use_id,
            'session_id': input_data.get('session_id', ''),
            'cwd': input_data.get('cwd', ''),
            'permission_mode': input_data.get('permission_mode', ''),
            'raw_input': input_data
        }
        log_data.append(log_entry)

        # Write back to file with formatting
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)

        # Example: Provide feedback to Claude based on tool result
        # Uncomment to use:
        # if tool_name == "Write" and tool_response.get("success"):
        #     output_additional_context(f"File {tool_input.get('file_path')} written")

        # Example: Block and prompt Claude if something went wrong
        # Uncomment to use:
        # if some_condition:
        #     output_block_decision("Reason for blocking")
        #     sys.exit(0)

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Exit cleanly on any other error
        sys.exit(0)


if __name__ == '__main__':
    main()