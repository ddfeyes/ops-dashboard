"""AO session status + OpenClaw agent list."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

try:
    import urllib.request as _urllib_request
    import urllib.error as _urllib_error
except ImportError:
    _urllib_request = None  # type: ignore
    _urllib_error = None  # type: ignore

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

# Optional: OpenClaw gateway URL for live session data
# e.g. http://host.docker.internal:18789 or http://172.17.0.1:18789
_OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://host.docker.internal:18789")

# Active threshold: sessions active within this many seconds are "active"
_ACTIVE_THRESHOLD_SECS = 300  # 5 minutes


def _find_openclaw_config() -> Path | None:
    for p in _OPENCLAW_CONFIG_PATHS:
        if p.exists():
            return p
    return None


def _fetch_gateway_sessions() -> dict[str, dict]:
    """Fetch live session data from OpenClaw gateway. Returns dict keyed by agent id."""
    if not _OPENCLAW_GATEWAY_URL or _urllib_request is None:
        return {}
    try:
        url = f"{_OPENCLAW_GATEWAY_URL.rstrip('/')}/sessions"
        req = _urllib_request.Request(url, headers={"Accept": "application/json"})
        with _urllib_request.urlopen(req, timeout=3) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            # data is expected to be a list of session objects or dict
            sessions_list = data if isinstance(data, list) else data.get("sessions", [])
            # Build lookup: agentId -> latest session info
            by_agent: dict[str, dict] = {}
            now_ms = int(time.time() * 1000)
            for s in sessions_list:
                agent_id = s.get("agentId") or s.get("agent_id") or s.get("id", "")
                # Strip channel prefix if present (e.g. "agent:lain:...")
                parts = agent_id.split(":")
                short_id = parts[1] if len(parts) >= 2 and parts[0] == "agent" else agent_id
                last_active_ms = s.get("lastActiveAt") or s.get("last_active_at") or s.get("updatedAt") or 0
                if not last_active_ms:
                    last_active_ms = s.get("createdAt") or 0
                status = "active" if (now_ms - last_active_ms) < _ACTIVE_THRESHOLD_SECS * 1000 else "idle"
                # Keep the most recent session per agent
                existing = by_agent.get(short_id)
                if existing is None or last_active_ms > (existing.get("_last_ms") or 0):
                    by_agent[short_id] = {
                        "status": status,
                        "last_seen": last_active_ms,
                        "last_seen_iso": _ms_to_iso(last_active_ms),
                        "_last_ms": last_active_ms,
                    }
            return by_agent
    except Exception:
        return {}


def _ms_to_iso(ms: int) -> str | None:
    if not ms:
        return None
    try:
        import datetime
        return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).isoformat()
    except Exception:
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
    """Read OpenClaw agent configs and return the agent list with live status.
    
    Falls back to OPENCLAW_AGENTS_JSON env var if config file not found.
    Enriches agents with live status from OpenClaw gateway if reachable.
    """
    # Try env var override first
    base_agents: list[dict[str, Any]] = []
    if _STATIC_AGENTS_JSON:
        try:
            raw = json.loads(_STATIC_AGENTS_JSON)
            if isinstance(raw, list):
                base_agents = raw
        except json.JSONDecodeError:
            pass

    if not base_agents:
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
        for agent in agent_list:
            identity = agent.get("identity", {})
            base_agents.append(
                {
                    "id": agent.get("id"),
                    "name": identity.get("name") or agent.get("name") or agent.get("id"),
                    "model": agent.get("model"),
                    "workspace": agent.get("workspace"),
                    "emoji": identity.get("emoji"),
                }
            )

    # Enrich with live session data from gateway
    live_sessions = _fetch_gateway_sessions()

    agents = []
    for agent in base_agents:
        agent_id = agent.get("id") or ""
        live = live_sessions.get(agent_id, {})
        agents.append(
            {
                "id": agent_id,
                "name": agent.get("name") or agent_id,
                "model": agent.get("model"),
                "workspace": agent.get("workspace"),
                "emoji": agent.get("emoji"),
                "status": live.get("status"),        # "active" | "idle" | None
                "last_seen": live.get("last_seen_iso"),  # ISO timestamp or None
            }
        )
    return agents
