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

# Optional: inject pre-computed agent status JSON
# Format: {"lain": {"status": "active", "last_seen": "<ISO>"}, ...}
_AGENTS_STATUS_JSON = os.getenv("OPENCLAW_AGENTS_STATUS_JSON", "")

# Optional: path to OpenClaw sessions directory (mount from host)
# e.g. /openclaw-sessions → maps to ~/.openclaw/agents on host
_OPENCLAW_SESSIONS_DIR = os.getenv("OPENCLAW_SESSIONS_DIR", "")

# Optional: base directory where agent workspaces are mounted
# e.g. /agents → agent lain at /agents/lain, masami at /agents/masami, etc.
# The code will scan for most-recently-modified file in each agent workspace.
_OPENCLAW_AGENTS_DIR = os.getenv("OPENCLAW_AGENTS_DIR", "")

# Workspace path remapping: rewrite workspace paths from one prefix to another.
# e.g. OPENCLAW_WORKSPACE_PREFIX_FROM=/Users/aivan OPENCLAW_WORKSPACE_PREFIX_TO=/agents
_WORKSPACE_PREFIX_FROM = os.getenv("OPENCLAW_WORKSPACE_PREFIX_FROM", "")
_WORKSPACE_PREFIX_TO = os.getenv("OPENCLAW_WORKSPACE_PREFIX_TO", "")

# Active threshold: sessions active within this many seconds are "active"
_ACTIVE_THRESHOLD_SECS = 300  # 5 minutes

# Idle threshold: sessions that haven't been modified in this many seconds are "offline"
# (beyond idle — considered very stale)
_OFFLINE_THRESHOLD_SECS = 3 * 3600  # 3 hours


def _find_openclaw_config() -> Path | None:
    for p in _OPENCLAW_CONFIG_PATHS:
        if p.exists():
            return p
    return None


def _remap_workspace(workspace: str | None) -> str | None:
    """Apply workspace path prefix remapping if configured."""
    if not workspace:
        return workspace
    if _WORKSPACE_PREFIX_FROM and _WORKSPACE_PREFIX_TO:
        if workspace.startswith(_WORKSPACE_PREFIX_FROM):
            return _WORKSPACE_PREFIX_TO + workspace[len(_WORKSPACE_PREFIX_FROM):]
    return workspace


def _get_workspace_last_seen(workspace: str | None) -> dict | None:
    """Scan an agent's workspace directory to determine last activity time via file mtime."""
    if not workspace:
        return None
    p = Path(workspace)
    if not p.exists() or not p.is_dir():
        return None
    try:
        now = time.time()
        best_mtime = 0.0
        # Check key indicator files first (memory, STATE.yaml, inbox, logs)
        priority_globs = ["memory/*.md", "memory/*.json", "STATE.yaml", "inbox/*.md",
                          "inbox/*.json", "logs/*.log", "HEARTBEAT.md", "*.md"]
        for pattern in priority_globs:
            for f in p.glob(pattern):
                try:
                    mt = f.stat().st_mtime
                    if mt > best_mtime:
                        best_mtime = mt
                except OSError:
                    continue
        # Fallback: any file in root level
        if best_mtime == 0:
            for f in p.iterdir():
                if f.is_file():
                    try:
                        mt = f.stat().st_mtime
                        if mt > best_mtime:
                            best_mtime = mt
                    except OSError:
                        continue
        if best_mtime == 0:
            return None
        age_secs = now - best_mtime
        if age_secs < _ACTIVE_THRESHOLD_SECS:
            status = "active"
        elif age_secs < _OFFLINE_THRESHOLD_SECS:
            status = "idle"
        else:
            status = "offline"
        return {
            "status": status,
            "last_seen_iso": _secs_to_iso(best_mtime),
            "_last_ms": int(best_mtime * 1000),
        }
    except Exception:
        return None


def _secs_to_iso(secs: float) -> str | None:
    try:
        import datetime
        return datetime.datetime.fromtimestamp(secs, tz=datetime.timezone.utc).isoformat()
    except Exception:
        return None


def _fetch_gateway_sessions() -> dict[str, dict]:
    """Fetch live session data. Returns dict keyed by short agent id.
    
    Tries (in order):
    1. OPENCLAW_AGENTS_STATUS_JSON env var (pre-computed)
    2. OPENCLAW_SESSIONS_DIR — read sessions.json files from mounted dir
    3. OpenClaw gateway HTTP API
    """
    # 1. Pre-computed status injection
    if _AGENTS_STATUS_JSON:
        try:
            raw = json.loads(_AGENTS_STATUS_JSON)
            if isinstance(raw, dict):
                return raw
        except json.JSONDecodeError:
            pass

    # 2. Read sessions.json files from mounted directory
    if _OPENCLAW_SESSIONS_DIR:
        by_agent: dict[str, dict] = {}
        sessions_base = Path(_OPENCLAW_SESSIONS_DIR)
        now_ms = int(time.time() * 1000)
        if sessions_base.exists():
            for agent_dir in sessions_base.iterdir():
                if not agent_dir.is_dir():
                    continue
                agent_id = agent_dir.name
                sessions_file = agent_dir / "sessions" / "sessions.json"
                if not sessions_file.exists():
                    continue
                try:
                    with sessions_file.open() as f:
                        sess_data: dict = json.load(f)
                    # sessions_data is dict: session_key -> session_object
                    # Find most recently updated session
                    best_ms = 0
                    for _sk, sv in sess_data.items():
                        if isinstance(sv, dict):
                            updated_ms = sv.get("updatedAt") or 0
                            if updated_ms > best_ms:
                                best_ms = updated_ms
                    if best_ms > 0:
                        status = "active" if (now_ms - best_ms) < _ACTIVE_THRESHOLD_SECS * 1000 else "idle"
                        by_agent[agent_id] = {
                            "status": status,
                            "last_seen_iso": _ms_to_iso(best_ms),
                            "_last_ms": best_ms,
                        }
                except Exception:
                    continue
        if by_agent:
            return by_agent

    # 3. Gateway HTTP API
    if not _OPENCLAW_GATEWAY_URL or _urllib_request is None:
        return {}
    try:
        url = f"{_OPENCLAW_GATEWAY_URL.rstrip('/')}/api/sessions"
        if not url.startswith(("http://", "https://")):
            return {}
        req = _urllib_request.Request(url, headers={"Accept": "application/json"})
        with _urllib_request.urlopen(req, timeout=3) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            sessions_list = data if isinstance(data, list) else data.get("sessions", [])
            by_agent = {}
            now_ms = int(time.time() * 1000)
            for s in sessions_list:
                agent_id = s.get("agentId") or s.get("agent_id") or s.get("id", "")
                parts = agent_id.split(":")
                short_id = parts[1] if len(parts) >= 2 and parts[0] == "agent" else agent_id
                last_active_ms = s.get("lastActiveAt") or s.get("last_active_at") or s.get("updatedAt") or 0
                if not last_active_ms:
                    last_active_ms = s.get("createdAt") or 0
                status = "active" if (now_ms - last_active_ms) < _ACTIVE_THRESHOLD_SECS * 1000 else "idle"
                existing = by_agent.get(short_id)
                if existing is None or last_active_ms > (existing.get("_last_ms") or 0):
                    by_agent[short_id] = {
                        "status": status,
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
    Enriches agents with live status from:
    1. OpenClaw gateway / sessions dir (if reachable)
    2. Agent workspace file mtime scan (via OPENCLAW_AGENTS_DIR mount)
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

        # Determine workspace path (remap if needed)
        workspace = agent.get("workspace")
        mapped_workspace = _remap_workspace(workspace)

        # If no live data from gateway, try workspace mtime scan
        # Also try OPENCLAW_AGENTS_DIR/<agent_id> if set
        if not live:
            # Try mounted agents dir first
            if _OPENCLAW_AGENTS_DIR:
                agents_base = Path(_OPENCLAW_AGENTS_DIR)
                agent_dir = agents_base / agent_id
                if not agent_dir.exists():
                    # try fragments subdir
                    agent_dir = agents_base / "fragments" / agent_id.replace("fragment-", "")
                workspace_data = _get_workspace_last_seen(str(agent_dir) if agent_dir.exists() else None)
                if workspace_data:
                    live = workspace_data
            # Fallback to remapped workspace path
            if not live and mapped_workspace:
                workspace_data = _get_workspace_last_seen(mapped_workspace)
                if workspace_data:
                    live = workspace_data

        agents.append(
            {
                "id": agent_id,
                "name": agent.get("name") or agent_id,
                "model": agent.get("model"),
                "workspace": workspace,
                "emoji": agent.get("emoji"),
                "status": live.get("status"),        # "active" | "idle" | "offline" | None
                "last_seen": live.get("last_seen_iso") or live.get("last_seen"),  # ISO timestamp or None
            }
        )
    return agents
