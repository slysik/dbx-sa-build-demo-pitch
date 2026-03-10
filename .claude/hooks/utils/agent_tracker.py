"""
Shared active-agent tracker.

SubagentStart adds agents, SubagentStop removes them.
Status line reads the tracker to display running agents.

File-based with atomic writes to /tmp/claude-active-agents.json
"""

import json
import os
import tempfile
from datetime import datetime

TRACKER_PATH = "/tmp/claude-active-agents.json"


def _read_tracker() -> list[dict]:
    """Read current active agents list."""
    if not os.path.exists(TRACKER_PATH):
        return []
    try:
        with open(TRACKER_PATH, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _write_tracker(agents: list[dict]) -> None:
    """Atomic write to tracker file."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", dir="/tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(agents, f, indent=2)
        os.replace(tmp_path, TRACKER_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def register_agent(agent_id: str, agent_type: str, description: str = "") -> None:
    """Add an agent to the active tracker."""
    agents = _read_tracker()
    # Don't add duplicates
    if any(a["agent_id"] == agent_id for a in agents):
        return
    agents.append({
        "agent_id": agent_id,
        "agent_type": agent_type,
        "description": description,
        "started_at": datetime.now().isoformat(),
    })
    _write_tracker(agents)


def deregister_agent(agent_id: str) -> None:
    """Remove an agent from the active tracker."""
    agents = _read_tracker()
    agents = [a for a in agents if a["agent_id"] != agent_id]
    _write_tracker(agents)


def get_active_agents() -> list[dict]:
    """Get list of currently active agents."""
    return _read_tracker()


def clear_all() -> None:
    """Clear all tracked agents (e.g., on session start)."""
    _write_tracker([])
