#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///
"""
PreCompact Hook - Handles context window compaction events.

This hook is triggered before Claude compacts the conversation context.
It supports two trigger types via matchers in settings.json:
  - "manual": User explicitly requested compaction (/compact command)
  - "auto": Automatic compaction when context window is full

Input Schema:
{
    "session_id": "abc123",
    "transcript_path": "~/.claude/projects/.../session.jsonl",
    "permission_mode": "default",
    "hook_event_name": "PreCompact",
    "trigger": "manual" | "auto",
    "custom_instructions": ""
}

Usage in settings.json:
  "PreCompact": [
    {
      "matcher": "manual",
      "hooks": [{ "type": "command", "command": "... --verbose --backup" }]
    },
    {
      "matcher": "auto",
      "hooks": [{ "type": "command", "command": "..." }]
    }
  ]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


# Trigger type constants
TRIGGER_MANUAL = "manual"
TRIGGER_AUTO = "auto"


def get_transcript_stats(transcript_path):
    """Get statistics about the transcript file."""
    stats = {
        "line_count": 0,
        "file_size_kb": 0,
        "exists": False
    }

    try:
        if os.path.exists(transcript_path):
            stats["exists"] = True
            stats["file_size_kb"] = round(os.path.getsize(transcript_path) / 1024, 2)
            with open(transcript_path, 'r') as f:
                stats["line_count"] = sum(1 for _ in f)
    except Exception:
        pass

    return stats


def log_pre_compact(input_data, trigger):
    """Log pre-compact event to logs directory with trigger-specific information."""
    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'pre_compact.json'

    # Read existing log data or initialize empty list
    if log_file.exists():
        with open(log_file, 'r') as f:
            try:
                log_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                log_data = []
    else:
        log_data = []

    # Enhance log entry with metadata
    log_entry = {
        **input_data,
        "logged_at": datetime.now().isoformat(),
        "trigger_type": trigger,
        "is_manual": trigger == TRIGGER_MANUAL,
        "is_auto": trigger == TRIGGER_AUTO
    }

    # Add transcript stats if path is available
    transcript_path = input_data.get('transcript_path', '')
    if transcript_path:
        expanded_path = os.path.expanduser(transcript_path)
        log_entry["transcript_stats"] = get_transcript_stats(expanded_path)

    # Append the enhanced log entry
    log_data.append(log_entry)

    # Write back to file with formatting
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2)


def backup_transcript(transcript_path, trigger):
    """Create a backup of the transcript before compaction."""
    try:
        expanded_path = os.path.expanduser(transcript_path)
        if not os.path.exists(expanded_path):
            return None

        # Create backup directory
        backup_dir = Path("logs") / "transcript_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename with timestamp and trigger type
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = Path(transcript_path).stem
        backup_name = f"{session_name}_pre_compact_{trigger}_{timestamp}.jsonl"
        backup_path = backup_dir / backup_name

        # Copy transcript to backup
        import shutil
        shutil.copy2(expanded_path, backup_path)

        return str(backup_path)
    except Exception:
        return None


def handle_manual_compaction(session_id, transcript_path, custom_instructions,
                              args, backup_path):
    """Handle manual compaction with verbose feedback."""
    messages = []

    # Header for manual compaction
    messages.append("[PreCompact] Manual compaction initiated")
    messages.append(f"  Session: {session_id[:8]}...")

    # Show transcript stats
    if transcript_path:
        expanded_path = os.path.expanduser(transcript_path)
        stats = get_transcript_stats(expanded_path)
        if stats["exists"]:
            messages.append(f"  Transcript: {stats['line_count']} lines, {stats['file_size_kb']} KB")

    # Show custom instructions if provided
    if custom_instructions:
        preview = custom_instructions[:100]
        if len(custom_instructions) > 100:
            preview += "..."
        messages.append(f"  Custom instructions: {preview}")

    # Show backup info
    if backup_path:
        messages.append(f"  Backup created: {backup_path}")
    elif args.backup:
        messages.append("  Backup requested but transcript not found")

    # Always print for manual compaction (verbose by default)
    for msg in messages:
        print(msg)


def handle_auto_compaction(session_id, transcript_path, args, backup_path):
    """Handle automatic compaction (context window full)."""
    # For auto compaction, only print if verbose is explicitly requested
    if args.verbose:
        messages = []
        messages.append("[PreCompact] Auto-compaction triggered (context window full)")
        messages.append(f"  Session: {session_id[:8]}...")

        if transcript_path:
            expanded_path = os.path.expanduser(transcript_path)
            stats = get_transcript_stats(expanded_path)
            if stats["exists"]:
                messages.append(f"  Transcript size: {stats['file_size_kb']} KB")

        if backup_path:
            messages.append(f"  Backup: {backup_path}")

        for msg in messages:
            print(msg)


def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description="PreCompact hook - handles context compaction events"
        )
        parser.add_argument('--backup', action='store_true',
                          help='Create backup of transcript before compaction')
        parser.add_argument('--verbose', action='store_true',
                          help='Print verbose output (always on for manual compaction)')
        parser.add_argument('--quiet', action='store_true',
                          help='Suppress all output')
        args = parser.parse_args()

        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())

        # Extract fields from PreCompact schema
        session_id = input_data.get('session_id', 'unknown')
        transcript_path = input_data.get('transcript_path', '')
        trigger = input_data.get('trigger', 'unknown')  # "manual" or "auto"
        custom_instructions = input_data.get('custom_instructions', '')
        # Also available: permission_mode, hook_event_name

        # Log the pre-compact event with trigger info
        log_pre_compact(input_data, trigger)

        # Create backup if requested
        backup_path = None
        if args.backup and transcript_path:
            backup_path = backup_transcript(transcript_path, trigger)

        # Handle based on trigger type (unless quiet mode)
        if not args.quiet:
            if trigger == TRIGGER_MANUAL:
                # Manual compaction gets verbose feedback by default
                handle_manual_compaction(
                    session_id, transcript_path, custom_instructions,
                    args, backup_path
                )
            elif trigger == TRIGGER_AUTO:
                # Auto compaction is quieter unless verbose requested
                handle_auto_compaction(
                    session_id, transcript_path, args, backup_path
                )
            elif args.verbose:
                # Unknown trigger type with verbose mode
                print(f"[PreCompact] Unknown trigger type: {trigger}")
                print(f"  Session: {session_id[:8]}...")

        # Success - compaction will proceed
        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == '__main__':
    main()