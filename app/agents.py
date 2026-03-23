"""AO session status + OpenClaw agent list."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

# OpenClaw config candidates (in priority order)
_OPENCLAW_CONFIG_PATHS = [
    Path.home() / ".openclaw-lain-core" / "openclaw.json",
    Path.home() / ".openclaw" / "openclaw.json",
    Path("/root/.openclaw-lain-core/openclaw.json"),
    Path("/root/.openclaw/openclaw.json"),
]

# Optional: inject static agent list via env var (JSON array of {id, name, emoji, model, workspace})
_STATIC_AGENTS_JSON = os.getenv("OPENCLAW_AGENTS_JSON", "")

# Optional: inject AO sessions via env var (JSON array)
_STATIC_AO_SESSIONS_JSON = os.getenv("AO_SESSIONS_JSON", "")


def _find_openclaw_config() -> Path | None:
    for p in _OPENCLAW_CONFIG_PATHS:
        if p.exists():
            return p
    return None


def get_ao_sessions() -> list[dict[str, Any]]:
    """Run `ao status --json` and return the parsed session list.
    
    Falls back to AO_SESSIONS_JSON env var if `ao` is not installed.
    """
    # Try env var override first (useful when ao isn't on the container)
    if _STATIC_AO_SESSIONS_JSON:
        try:
            raw = json.loads(_STATIC_AO_SESSIONS_JSON)
            if isinstance(raw, list):
                return raw
        except json.JSONDecodeError:
            pass

    # Try running ao CLI
    try:
        result = subprocess.run(
            ["ao", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        raw_list: list[dict] = json.loads(result.stdout)
    except FileNotFoundError:
        # ao not installed — return sentinel so frontend can show helpful message
        return [{"_error": "ao_not_installed", "_message": "ao CLI not available in this environment"}]
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []

    sessions = []
    for item in raw_list:
        sessions.append(
            {
                "name": item.get("name"),
                "branch": item.get("branch"),
                "pr": item.get("prNumber"),
                "pr_url": item.get("pr"),
                "ci": item.get("ciStatus"),
                "activity": item.get("activity"),
                "age": item.get("lastActivity"),
                "project": item.get("project"),
                "status": item.get("status"),
                "review": item.get("reviewDecision"),
                "pending_threads": item.get("pendingThreads"),
            }
        )
    return sessions


def get_openclaw_agents() -> list[dict[str, Any]]:
    """Read OpenClaw agent configs and return the agent list.
    
    Falls back to OPENCLAW_AGENTS_JSON env var if config file not found.
    """
    # Try env var override first
    if _STATIC_AGENTS_JSON:
        try:
            raw = json.loads(_STATIC_AGENTS_JSON)
            if isinstance(raw, list):
                return raw
        except json.JSONDecodeError:
            pass

    # Try reading config file
    config_path = _find_openclaw_config()
    if config_path is None:
        return []

    try:
        with config_path.open() as f:
            config: dict = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    agent_list: list[dict] = config.get("agents", {}).get("list", [])
    agents = []
    for agent in agent_list:
        identity = agent.get("identity", {})
        model = agent.get("model")
        agents.append(
            {
                "id": agent.get("id"),
                "name": identity.get("name") or agent.get("name") or agent.get("id"),
                "model": model,
                "workspace": agent.get("workspace"),
                "emoji": identity.get("emoji"),
            }
        )
    return agents
