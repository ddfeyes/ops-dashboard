"""Anthropic API usage tracking via local Claude Code session logs."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Configurable token limits via environment variables
SESSION_TOKEN_LIMIT = int(os.getenv("SESSION_TOKEN_LIMIT", "200000"))
WEEKLY_ALL_TOKEN_LIMIT = int(os.getenv("WEEKLY_ALL_TOKEN_LIMIT", "10000000"))
WEEKLY_SONNET_TOKEN_LIMIT = int(os.getenv("WEEKLY_SONNET_TOKEN_LIMIT", "7500000"))

CLAUDE_HOME = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_HOME / "projects"


def _week_start_utc() -> datetime:
    """Return the start of the current ISO week (Monday 00:00 UTC)."""
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _next_week_start_utc() -> datetime:
    return _week_start_utc() + timedelta(days=7)


def _parse_jsonl(path: Path, since: datetime | None = None) -> dict[str, Any]:
    """Extract token usage from a Claude Code JSONL session file.

    Each assistant message in the JSONL has a ``message.usage`` object.
    We accumulate totals and break them down by model name.
    """
    totals: dict[str, int] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }
    by_model: dict[str, dict[str, int]] = {}

    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if entry.get("type") != "assistant":
                    continue

                msg = entry.get("message", {})
                usage = msg.get("usage")
                if not usage:
                    continue

                # Optional time filter
                if since is not None:
                    ts_raw = entry.get("timestamp")
                    if ts_raw:
                        try:
                            ts = datetime.fromisoformat(
                                ts_raw.replace("Z", "+00:00")
                            )
                            if ts < since:
                                continue
                        except (ValueError, TypeError):
                            pass

                model: str = msg.get("model", "unknown")
                inp = int(usage.get("input_tokens", 0))
                out = int(usage.get("output_tokens", 0))
                cache_create = int(usage.get("cache_creation_input_tokens", 0))
                cache_read = int(usage.get("cache_read_input_tokens", 0))

                totals["input_tokens"] += inp
                totals["output_tokens"] += out
                totals["cache_creation_tokens"] += cache_create
                totals["cache_read_tokens"] += cache_read

                bucket = by_model.setdefault(model, {"input_tokens": 0, "output_tokens": 0})
                bucket["input_tokens"] += inp
                bucket["output_tokens"] += out

    except OSError:
        pass

    return {**totals, "by_model": by_model}


def _all_jsonl_files() -> list[Path]:
    """Return all JSONL session files under ~/.claude/projects/."""
    if not PROJECTS_DIR.exists():
        return []
    return sorted(
        PROJECTS_DIR.rglob("*.jsonl"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
    )


def _merge_usage(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Merge two usage dicts (accumulated totals)."""
    merged: dict[str, Any] = {
        "input_tokens": a["input_tokens"] + b["input_tokens"],
        "output_tokens": a["output_tokens"] + b["output_tokens"],
        "cache_creation_tokens": a["cache_creation_tokens"] + b["cache_creation_tokens"],
        "cache_read_tokens": a["cache_read_tokens"] + b["cache_read_tokens"],
        "by_model": dict(a.get("by_model", {})),
    }
    for model, counts in b.get("by_model", {}).items():
        existing = merged["by_model"].setdefault(
            model, {"input_tokens": 0, "output_tokens": 0}
        )
        existing["input_tokens"] += counts["input_tokens"]
        existing["output_tokens"] += counts["output_tokens"]
    return merged


def _pct(used: int, limit: int) -> float:
    if limit <= 0:
        return 0.0
    return round(min(used / limit * 100, 100.0), 1)


def _sonnet_tokens(by_model: dict[str, dict[str, int]]) -> int:
    total = 0
    for model, counts in by_model.items():
        if "sonnet" in model.lower():
            total += counts.get("input_tokens", 0) + counts.get("output_tokens", 0)
    return total


def get_usage() -> dict[str, Any]:
    """Aggregate token usage from local Claude Code session logs.

    Returns:
        A dict with keys:
        - current_session: token counts for the most-recent session
        - current_session_pct: pct of SESSION_TOKEN_LIMIT used
        - weekly_all: total token counts for the past 7 days
        - weekly_all_pct: pct of WEEKLY_ALL_TOKEN_LIMIT used
        - weekly_sonnet_pct: pct of WEEKLY_SONNET_TOKEN_LIMIT (Sonnet only)
        - reset_times: when weekly counter resets (next Monday UTC)
        - limits: the configured limits for context
        - source: where data came from
    """
    all_files = _all_jsonl_files()

    # Current session: most recently written JSONL file
    current_usage: dict[str, Any] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "by_model": {},
    }
    current_session_file: str | None = None

    if all_files:
        newest = all_files[-1]
        current_usage = _parse_jsonl(newest)
        current_session_file = str(newest.relative_to(CLAUDE_HOME))

    # Weekly: all files with mtime within the last 7 days
    week_start = _week_start_utc()
    week_start_ts = week_start.timestamp()

    weekly_usage: dict[str, Any] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "by_model": {},
    }

    for path in all_files:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= week_start_ts:
            file_usage = _parse_jsonl(path, since=week_start)
            weekly_usage = _merge_usage(weekly_usage, file_usage)

    # Token totals
    session_total = current_usage["input_tokens"] + current_usage["output_tokens"]
    weekly_all_total = weekly_usage["input_tokens"] + weekly_usage["output_tokens"]
    weekly_sonnet_total = _sonnet_tokens(weekly_usage["by_model"])

    next_reset = _next_week_start_utc()

    return {
        "current_session": {
            "input_tokens": current_usage["input_tokens"],
            "output_tokens": current_usage["output_tokens"],
            "cache_creation_tokens": current_usage["cache_creation_tokens"],
            "cache_read_tokens": current_usage["cache_read_tokens"],
            "total_tokens": session_total,
            "by_model": current_usage["by_model"],
            "source_file": current_session_file,
        },
        "current_session_pct": _pct(session_total, SESSION_TOKEN_LIMIT),
        "weekly_all": {
            "input_tokens": weekly_usage["input_tokens"],
            "output_tokens": weekly_usage["output_tokens"],
            "total_tokens": weekly_all_total,
            "sonnet_tokens": weekly_sonnet_total,
            "by_model": weekly_usage["by_model"],
        },
        "weekly_all_pct": _pct(weekly_all_total, WEEKLY_ALL_TOKEN_LIMIT),
        "weekly_sonnet_pct": _pct(weekly_sonnet_total, WEEKLY_SONNET_TOKEN_LIMIT),
        "reset_times": {
            "weekly": next_reset.isoformat(),
        },
        "limits": {
            "session_token_limit": SESSION_TOKEN_LIMIT,
            "weekly_all_token_limit": WEEKLY_ALL_TOKEN_LIMIT,
            "weekly_sonnet_token_limit": WEEKLY_SONNET_TOKEN_LIMIT,
        },
        "source": "claude_code_local_logs",
    }
