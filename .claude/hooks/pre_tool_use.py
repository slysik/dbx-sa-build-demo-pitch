#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

"""
Pre-tool-use hook for Claude Code.

This hook runs BEFORE a tool is executed and can:
1. Allow/deny/ask permission for tool execution via permissionDecision
2. Modify tool inputs before execution via updatedInput
3. Provide additional context to Claude via additionalContext

JSON Output Schema:
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow" | "deny" | "ask",
    "permissionDecisionReason": "Explanation for the decision",
    "updatedInput": { ... },  // Modified tool inputs (optional)
    "additionalContext": "..."  // Context shown to Claude (optional)
  }
}
"""

import json
import sys
import re
from pathlib import Path


def is_dangerous_rm_command(command):
    """
    Comprehensive detection of dangerous rm commands.
    Matches various forms of rm -rf and similar destructive patterns.
    """
    # Normalize command by removing extra spaces and converting to lowercase
    normalized = ' '.join(command.lower().split())

    # Pattern 1: Standard rm -rf variations
    patterns = [
        r'\brm\s+.*-[a-z]*r[a-z]*f',  # rm -rf, rm -fr, rm -Rf, etc.
        r'\brm\s+.*-[a-z]*f[a-z]*r',  # rm -fr variations
        r'\brm\s+--recursive\s+--force',  # rm --recursive --force
        r'\brm\s+--force\s+--recursive',  # rm --force --recursive
        r'\brm\s+-r\s+.*-f',  # rm -r ... -f
        r'\brm\s+-f\s+.*-r',  # rm -f ... -r
    ]

    # Check for dangerous patterns
    for pattern in patterns:
        if re.search(pattern, normalized):
            return True

    # Pattern 2: Check for rm with recursive flag targeting dangerous paths
    dangerous_paths = [
        r'/',           # Root directory
        r'/\*',         # Root with wildcard
        r'~',           # Home directory
        r'~/',          # Home directory path
        r'\$HOME',      # Home environment variable
        r'\.\.',        # Parent directory references
        r'\*',          # Wildcards in general rm -rf context
        r'\.',          # Current directory
        r'\.\s*$',      # Current directory at end of command
    ]

    if re.search(r'\brm\s+.*-[a-z]*r', normalized):  # If rm has recursive flag
        for path in dangerous_paths:
            if re.search(path, normalized):
                return True

    return False


def is_env_file_access(tool_name, tool_input):
    """
    Check if any tool is trying to access .env files containing sensitive data.
    """
    if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Bash']:
        # Check file paths for file-based tools
        if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write']:
            file_path = tool_input.get('file_path', '')
            if '.env' in file_path and not file_path.endswith('.env.sample'):
                return True

        # Check bash commands for .env file access
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            # Pattern to detect .env file access (but allow .env.sample)
            env_patterns = [
                r'\b\.env\b(?!\.sample)',  # .env but not .env.sample
                r'cat\s+.*\.env\b(?!\.sample)',  # cat .env
                r'echo\s+.*>\s*\.env\b(?!\.sample)',  # echo > .env
                r'touch\s+.*\.env\b(?!\.sample)',  # touch .env
                r'cp\s+.*\.env\b(?!\.sample)',  # cp .env
                r'mv\s+.*\.env\b(?!\.sample)',  # mv .env
            ]

            for pattern in env_patterns:
                if re.search(pattern, command):
                    return True

    return False


def create_hook_output(
    permission_decision="allow",
    permission_reason=None,
    updated_input=None,
    additional_context=None
):
    """
    Create a properly formatted hook output JSON.

    Args:
        permission_decision: "allow", "deny", or "ask"
        permission_reason: Explanation for the decision
        updated_input: Dict of modified tool inputs (optional)
        additional_context: String context to show Claude (optional)

    Returns:
        Dict formatted for hook output
    """
    hook_output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission_decision,
        }
    }

    if permission_reason:
        hook_output["hookSpecificOutput"]["permissionDecisionReason"] = permission_reason

    if updated_input is not None:
        hook_output["hookSpecificOutput"]["updatedInput"] = updated_input

    if additional_context:
        hook_output["hookSpecificOutput"]["additionalContext"] = additional_context

    return hook_output


# ============================================================================
# Example Input Modification Functions (Uncomment to use)
# ============================================================================

# def modify_bash_command(tool_input):
#     """
#     Example: Modify bash commands before execution.
#     Could add safety flags, change directories, etc.
#     """
#     command = tool_input.get('command', '')
#
#     # Example: Prefix all git commands with a specific config
#     if command.startswith('git '):
#         tool_input['command'] = f'git -c user.name="Claude" {command[4:]}'
#
#     # Example: Add timeout to long-running commands
#     if 'npm install' in command or 'yarn install' in command:
#         tool_input['timeout'] = 300000  # 5 minute timeout
#
#     return tool_input


# def modify_file_path(tool_input, base_dir=None):
#     """
#     Example: Normalize or restrict file paths.
#     Could enforce working within a specific directory.
#     """
#     file_path = tool_input.get('file_path', '')
#
#     # Example: Ensure all paths are within a specific base directory
#     if base_dir and not file_path.startswith(base_dir):
#         tool_input['file_path'] = f"{base_dir}/{file_path.lstrip('/')}"
#
#     return tool_input


# def add_context_for_production(tool_name, tool_input):
#     """
#     Example: Add warning context when operating in production.
#     """
#     command = tool_input.get('command', '') if tool_name == 'Bash' else ''
#
#     # Detect production-related operations
#     prod_indicators = ['prod', 'production', 'live', 'deploy']
#     if any(indicator in command.lower() for indicator in prod_indicators):
#         return "WARNING: This appears to be a production operation. Proceed with caution."
#
#     return None


def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # ====================================================================
        # Permission Checks (deny dangerous operations)
        # ====================================================================

        # Check for .env file access (blocks access to sensitive environment files)
        if is_env_file_access(tool_name, tool_input):
            output = create_hook_output(
                permission_decision="deny",
                permission_reason="Access to .env files containing sensitive data is prohibited. Use .env.sample for template files instead.",
                additional_context="This tool call was blocked because it attempted to access a .env file which may contain secrets."
            )
            print(json.dumps(output))
            sys.exit(0)

        # Check for dangerous rm -rf commands
        if tool_name == 'Bash':
            command = tool_input.get('command', '')

            if is_dangerous_rm_command(command):
                output = create_hook_output(
                    permission_decision="deny",
                    permission_reason="Dangerous rm command detected and prevented.",
                    additional_context="This command was blocked because it contains a potentially destructive rm pattern that could delete important files."
                )
                print(json.dumps(output))
                sys.exit(0)

        # ====================================================================
        # Input Modification Examples (Uncomment to enable)
        # ====================================================================

        # updated_input = None
        # additional_context = None

        # # Example: Modify bash commands
        # if tool_name == 'Bash':
        #     updated_input = modify_bash_command(tool_input.copy())
        #     additional_context = add_context_for_production(tool_name, tool_input)

        # # Example: Modify file operations
        # if tool_name in ['Read', 'Write', 'Edit']:
        #     updated_input = modify_file_path(tool_input.copy(), base_dir='/allowed/path')

        # # If we modified the input, output the changes
        # if updated_input and updated_input != tool_input:
        #     output = create_hook_output(
        #         permission_decision="allow",
        #         permission_reason="Tool input was modified for safety/compliance.",
        #         updated_input=updated_input,
        #         additional_context=additional_context
        #     )
        #     print(json.dumps(output))
        #     sys.exit(0)

        # ====================================================================
        # Logging (optional - for debugging/auditing)
        # ====================================================================

        # Ensure log directory exists
        log_dir = Path.cwd() / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'pre_tool_use.json'

        # Read existing log data or initialize empty list
        if log_path.exists():
            with open(log_path, 'r') as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []

        # Append new data
        log_data.append(input_data)

        # Write back to file with formatting
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)

        # ====================================================================
        # Default: Allow the tool call
        # ====================================================================

        # For allowed operations, we can either:
        # 1. Exit with code 0 and no output (implicit allow)
        # 2. Output explicit allow JSON (shown below, commented out)

        # Explicit allow with context (uncomment if needed):
        # output = create_hook_output(
        #     permission_decision="allow",
        #     permission_reason="Tool call approved.",
        #     additional_context="No issues detected with this operation."
        # )
        # print(json.dumps(output))

        sys.exit(0)

    except json.JSONDecodeError:
        # Gracefully handle JSON decode errors
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == '__main__':
    main()
