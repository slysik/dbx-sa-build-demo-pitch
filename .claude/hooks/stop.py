#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///
"""
Stop Hook - Runs when the main Claude Code agent has finished responding.

Input schema (from docs):
{
    "session_id": "abc123",
    "transcript_path": "~/.claude/projects/.../transcript.jsonl",
    "cwd": "/Users/...",
    "permission_mode": "default",
    "hook_event_name": "Stop",
    "stop_hook_active": true  // true when Claude is continuing from a stop hook
}

Output schema options (from docs):
1. Exit code 0 - allows Claude to stop
2. Exit code 2 - blocks stoppage, shows stderr to Claude
3. JSON output with decision control:
   {
     "decision": "block" | undefined,
     "reason": "Must be provided when Claude is blocked from stopping"
   }

Note: "block" prevents Claude from stopping. You must populate reason
      for Claude to know how to proceed.
      stop_hook_active should be checked to prevent infinite loops.
"""

import argparse
import json
import os
import random
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


def get_completion_messages():
    """Return list of friendly completion messages."""
    return [
        "Work complete!",
        "All done!",
        "Task finished!",
        "Job complete!",
        "Ready for next task!"
    ]


def get_tts_script_path():
    """
    Determine which TTS script to use based on available API keys.
    Priority order: ElevenLabs > OpenAI > pyttsx3
    """
    # Get current script directory and construct utils/tts path
    script_dir = Path(__file__).parent
    tts_dir = script_dir / "utils" / "tts"
    
    # Check for ElevenLabs API key (highest priority)
    if os.getenv('ELEVENLABS_API_KEY'):
        elevenlabs_script = tts_dir / "elevenlabs_tts.py"
        if elevenlabs_script.exists():
            return str(elevenlabs_script)
    
    # Check for OpenAI API key (second priority)
    if os.getenv('OPENAI_API_KEY'):
        openai_script = tts_dir / "openai_tts.py"
        if openai_script.exists():
            return str(openai_script)
    
    # Fall back to pyttsx3 (no API key required)
    pyttsx3_script = tts_dir / "pyttsx3_tts.py"
    if pyttsx3_script.exists():
        return str(pyttsx3_script)
    
    return None


def get_llm_completion_message():
    """
    Generate completion message using available LLM services.
    Priority order: OpenAI > Anthropic > Ollama > fallback to random message
    
    Returns:
        str: Generated or fallback completion message
    """
    # Get current script directory and construct utils/llm path
    script_dir = Path(__file__).parent
    llm_dir = script_dir / "utils" / "llm"
    
    # Try OpenAI first (highest priority)
    if os.getenv('OPENAI_API_KEY'):
        oai_script = llm_dir / "oai.py"
        if oai_script.exists():
            try:
                result = subprocess.run([
                    "uv", "run", str(oai_script), "--completion"
                ], 
                capture_output=True,
                text=True,
                timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
    
    # Try Anthropic second
    if os.getenv('ANTHROPIC_API_KEY'):
        anth_script = llm_dir / "anth.py"
        if anth_script.exists():
            try:
                result = subprocess.run([
                    "uv", "run", str(anth_script), "--completion"
                ], 
                capture_output=True,
                text=True,
                timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
    
    # Try Ollama third (local LLM)
    ollama_script = llm_dir / "ollama.py"
    if ollama_script.exists():
        try:
            result = subprocess.run([
                "uv", "run", str(ollama_script), "--completion"
            ], 
            capture_output=True,
            text=True,
            timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
    
    # Fallback to random predefined message
    messages = get_completion_messages()
    return random.choice(messages)

def extract_recent_activity(transcript_path, max_entries=50):
    """
    Extract recent user and assistant messages from the transcript.
    Returns a brief summary of what happened this session.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return None

    messages = []
    try:
        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        # Read last N lines for recent activity
        recent_lines = lines[-max_entries:] if len(lines) > max_entries else lines

        for line in recent_lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entry_type = entry.get("type", "")

                if entry_type == "user":
                    message = entry.get("message", {})
                    content = message.get("content", "") if isinstance(message, dict) else ""
                    if isinstance(content, str) and content:
                        messages.append(f"- User: {content[:150]}")
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    messages.append(f"- User: {text[:150]}")
                                    break

                elif entry_type == "assistant":
                    message = entry.get("message", {})
                    content = message.get("content", "") if isinstance(message, dict) else ""
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    messages.append(f"- Assistant: {text[:150]}")
                                    break
                    elif isinstance(content, str) and content:
                        messages.append(f"- Assistant: {content[:150]}")

            except json.JSONDecodeError:
                continue

    except Exception:
        return None

    return messages[-20:] if messages else None  # Last 20 messages max


def generate_scratchpad_summary(transcript_path, llm_dir):
    """
    Generate a scratchpad summary using LLM or structured extraction.
    Returns a markdown-formatted scratchpad update or None.
    """
    activity = extract_recent_activity(transcript_path)
    if not activity:
        return None

    activity_text = "\n".join(activity)

    # Try LLM-based summarization (OpenAI > Anthropic > Ollama)
    prompt_text = (
        "Summarize this Claude Code session into a scratchpad update. "
        "Extract: (1) what task was being worked on, (2) what was completed, "
        "(3) what remains to be done, (4) any key decisions or details, "
        "(5) specific resume instructions for the next session. "
        "Be concise but include specific file paths and technical details.\n\n"
        f"Session activity:\n{activity_text}"
    )

    # LLM scripts accept the prompt as positional args (not --prompt flag)
    # Try OpenAI
    if os.getenv('OPENAI_API_KEY'):
        oai_script = llm_dir / "oai.py"
        if oai_script.exists():
            try:
                result = subprocess.run(
                    ["uv", "run", str(oai_script), prompt_text],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass

    # Try Anthropic
    if os.getenv('ANTHROPIC_API_KEY'):
        anth_script = llm_dir / "anth.py"
        if anth_script.exists():
            try:
                result = subprocess.run(
                    ["uv", "run", str(anth_script), prompt_text],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass

    # Try Ollama
    ollama_script = llm_dir / "ollama.py"
    if ollama_script.exists():
        try:
            result = subprocess.run(
                ["uv", "run", str(ollama_script), prompt_text],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass

    # Fallback: structured extraction without LLM
    from datetime import datetime
    fallback = f"""Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Recent Activity (auto-extracted)

{activity_text}

## Resume Instructions

Review the activity above and continue where the session left off.
Check specs/state.md for plan alignment and TaskList for pending tasks."""

    return fallback


def save_scratchpad(transcript_path, cwd):
    """
    Auto-save scratchpad from session transcript.
    Reads transcript, generates summary, writes to SCRATCHPAD.md.
    """
    from datetime import datetime

    script_dir = Path(__file__).parent
    llm_dir = script_dir / "utils" / "llm"

    scratchpad_path = Path(cwd) / "SCRATCHPAD.md"

    # Generate summary from transcript
    summary = generate_scratchpad_summary(transcript_path, llm_dir)

    if summary:
        # Build updated scratchpad
        header = (
            "# Scratchpad\n\n"
            "> Session bridge file. Auto-injected into Claude's context via UserPromptSubmit hook.\n"
            "> Updated automatically by Stop hook or manually via `/checkpoint`.\n"
            "> After `/clear`, Claude reads this to resume without re-explanation.\n\n"
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (auto-saved by stop hook)\n\n"
        )

        try:
            # Read existing scratchpad to preserve any manual sections
            existing_content = ""
            if scratchpad_path.exists():
                existing_content = scratchpad_path.read_text()

            # Check if existing has manual content we should keep
            # (look for content that's not template/auto-generated)
            manual_sections = []
            if existing_content and "## Key Details Not Yet In Files" in existing_content:
                # Extract manual key details section if it has content
                parts = existing_content.split("## Key Details Not Yet In Files")
                if len(parts) > 1:
                    details_section = parts[1].split("##")[0].strip()
                    if details_section and "(Anything decided" not in details_section:
                        manual_sections.append(
                            f"## Key Details Not Yet In Files\n\n{details_section}"
                        )

            # Write updated scratchpad
            content = header + summary
            if manual_sections:
                content += "\n\n" + "\n\n".join(manual_sections)

            scratchpad_path.write_text(content)

        except Exception:
            pass  # Don't block session stop on scratchpad errors


def announce_completion():
    """Announce completion using the best available TTS service."""
    try:
        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available
        
        # Get completion message (LLM-generated or fallback)
        completion_message = get_llm_completion_message()
        
        # Call the TTS script with the completion message
        subprocess.run([
            "uv", "run", tts_script, completion_message
        ], 
        capture_output=True,  # Suppress output
        timeout=10  # 10-second timeout
        )
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if TTS encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
        pass


def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--chat', action='store_true', help='Copy transcript to chat.json')
        parser.add_argument('--notify', action='store_true', help='Enable TTS completion announcement')
        parser.add_argument('--save-scratchpad', action='store_true',
                          help='Auto-save session state to SCRATCHPAD.md')
        args = parser.parse_args()
        
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Extract required fields per docs
        # stop_hook_active is true when Claude is continuing from a stop hook
        # Check this to prevent infinite loops
        stop_hook_active = input_data.get("stop_hook_active", False)

        # Example: Block stopping if stop_hook_active is False and some condition
        # Uncomment to use decision/reason output format per docs:
        # if not stop_hook_active and should_continue():
        #     output = {
        #         "decision": "block",
        #         "reason": "Please complete the remaining tasks before stopping"
        #     }
        #     print(json.dumps(output))
        #     sys.exit(0)

        # Log stop_hook_active status for debugging
        _ = stop_hook_active  # Acknowledged but not blocking by default

        # Ensure log directory exists
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "stop.json")

        # Read existing log data or initialize empty list
        if os.path.exists(log_path):
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
        
        # Handle --chat switch
        if args.chat and 'transcript_path' in input_data:
            transcript_path = input_data['transcript_path']
            if os.path.exists(transcript_path):
                # Read .jsonl file and convert to JSON array
                chat_data = []
                try:
                    with open(transcript_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    chat_data.append(json.loads(line))
                                except json.JSONDecodeError:
                                    pass  # Skip invalid lines
                    
                    # Write to logs/chat.json
                    chat_file = os.path.join(log_dir, 'chat.json')
                    with open(chat_file, 'w') as f:
                        json.dump(chat_data, f, indent=2)
                except Exception:
                    pass  # Fail silently

        # Auto-save scratchpad from session transcript
        if args.save_scratchpad and 'transcript_path' in input_data:
            cwd = input_data.get('cwd', os.getcwd())
            save_scratchpad(input_data['transcript_path'], cwd)

        # Announce completion via TTS (only if --notify flag is set)
        if args.notify:
            announce_completion()

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == "__main__":
    main()
