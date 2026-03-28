"""API quota tracking for Claude/OpenRouter/etc.

Data sources (in priority order):
1. OPENCLAW_QUOTAS_JSON env var — pre-computed JSON injected at startup
2. Direct provider API (Anthropic /v1/users/information) if ANTHROPIC_API_KEY is set
3. Fallback: static limits from env with used=null (unknown)

Env var format for OPENCLAW_QUOTAS_JSON:
    {"claude_5h": {"used": 420000, "limit": 2000000}, "claude_7d": {"used": 7500000, "limit": 10000000}}
"""

from __future__ import annotations

import json
import os
from typing import Any

try:
    import urllib.request as _urllib_request
    import urllib.error as _urllib_error
except ImportError:
    _urllib_request = None
    _urllib_error = None

# Pre-computed quota data injected at startup (same pattern as OPENCLAW_AGENTS_STATUS_JSON)
_QUOTAS_JSON = os.getenv("OPENCLAW_QUOTAS_JSON", "")

# Anthropic API key (set in container env)
_ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Static fallback limits (matching usage.py defaults)
_FIVE_HOUR_LIMIT = int(os.getenv("FIVE_HOUR_LIMIT", "2000000"))   # Claude 5h input limit
_SEVEN_DAY_LIMIT = int(os.getenv("SEVEN_DAY_LIMIT", "10000000"))  # Claude 7d total limit

# OpenRouter — read from OPENROUTER_API_KEY if present (for OpenRouter quota)
_OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


def _pct(used: int | None, limit: int) -> float | None:
    if used is None or limit <= 0:
        return None
    return round(min(used / limit * 100, 100.0), 1)


def _fetch_anthropic_quotas() -> dict[str, Any] | None:
    """Call Anthropic /v1/users/information to get real-time usage."""
    if not _ANTHROPIC_API_KEY or _urllib_request is None:
        return None
    try:
        req = _urllib_request.Request(
            "https://api.anthropic.com/v1/users/information",
            headers={
                "x-api-key": _ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Accept": "application/json",
            },
            method="GET",
        )
        with _urllib_request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # Response shape: {"usage":{"claude_5h": {...}, "claude_7d": {...}}}
            usage = data.get("usage", {})
            return {
                "claude_5h": {
                    "used": usage.get("claude_5h", {}).get("used", 0),
                    "limit": usage.get("claude_5h", {}).get("limit", _FIVE_HOUR_LIMIT),
                },
                "claude_7d": {
                    "used": usage.get("claude_7d", {}).get("used", 0),
                    "limit": usage.get("claude_7d", {}).get("limit", _SEVEN_DAY_LIMIT),
                },
            }
    except Exception:
        return None


def get_quotas() -> dict[str, Any]:
    """Return quota data for all providers.

    Returns:
        {
          "anthropic": {
            "5h": {"used": int, "limit": int, "pct": float | None},
            "7d": {"used": int, "limit": int, "pct": float | None},
          },
          "openrouter": {...} | null,
          "source": "env_json" | "api" | "static",
          "fetched_at": "<ISO timestamp>",
        }
    """
    source = "static"
    result: dict[str, Any] = {
        "anthropic": {
            "5h": {"used": None, "limit": _FIVE_HOUR_LIMIT, "pct": None},
            "7d": {"used": None, "limit": _SEVEN_DAY_LIMIT, "pct": None},
        },
        "openrouter": None,
        "source": source,
        "fetched_at": None,
    }

    # Priority 1: pre-computed JSON injection
    if _QUOTAS_JSON:
        try:
            parsed = json.loads(_QUOTAS_JSON)
            if isinstance(parsed, dict):
                claude_5h = parsed.get("claude_5h", {})
                claude_7d = parsed.get("claude_7d", {})
                if isinstance(claude_5h, dict) and isinstance(claude_7d, dict):
                    result["anthropic"]["5h"] = {
                        "used": claude_5h.get("used"),
                        "limit": claude_5h.get("limit", _FIVE_HOUR_LIMIT),
                        "pct": _pct(claude_5h.get("used"), claude_5h.get("limit", _FIVE_HOUR_LIMIT)),
                    }
                    result["anthropic"]["7d"] = {
                        "used": claude_7d.get("used"),
                        "limit": claude_7d.get("limit", _SEVEN_DAY_LIMIT),
                        "pct": _pct(claude_7d.get("used"), claude_7d.get("limit", _SEVEN_DAY_LIMIT)),
                    }
                    result["openrouter"] = parsed.get("openrouter")
                    result["source"] = "env_json"
                    result["fetched_at"] = parsed.get("fetched_at") or _iso_now()
                    return result
        except (json.JSONDecodeError, TypeError):
            pass

    # Priority 2: direct API call
    if _ANTHROPIC_API_KEY:
        api_quotas = _fetch_anthropic_quotas()
        if api_quotas:
            result["anthropic"]["5h"] = {
                "used": api_quotas["claude_5h"]["used"],
                "limit": api_quotas["claude_5h"]["limit"],
                "pct": _pct(api_quotas["claude_5h"]["used"], api_quotas["claude_5h"]["limit"]),
            }
            result["anthropic"]["7d"] = {
                "used": api_quotas["claude_7d"]["used"],
                "limit": api_quotas["claude_7d"]["limit"],
                "pct": _pct(api_quotas["claude_7d"]["used"], api_quotas["claude_7d"]["limit"]),
            }
            result["source"] = "api"
            result["fetched_at"] = _iso_now()
            return result

    # Priority 3: static fallback — used is null, limits are known
    result["fetched_at"] = _iso_now()
    return result


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
