"""AO session status + OpenClaw agent list."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# OpenClaw config candidates (in priority order)
_OPENCLAW_CONFIG_PATHS = [
    Path.home() / ".openclaw-lain-core" / "openclaw.json",
    Path.home() / ".openclaw" / "openclaw.json",
]


def _find_openclaw_config() -> Path | None:
    for p in _OPENCLAW_CONFIG_PATHS:
        if p.exists():
            return p
    return None


def get_ao_sessions() -> list[dict[str, Any]]:
    """Run `ao status --json` and return the parsed session list."""
    try:
        result = subprocess.run(
            ["ao", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        raw: list[dict] = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return []

    sessions = []
    for item in raw:
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
    """Read OpenClaw agent configs and return the agent list."""
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
