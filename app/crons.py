"""OpenClaw cron job status from injected env var."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

OPENCLAW_GATEWAY_CRONS_JSON = os.getenv("OPENCLAW_GATEWAY_CRONS_JSON", "")


def get_crons() -> list[dict[str, Any]]:
    """Parse cron job data from OPENCLAW_GATEWAY_CRONS_JSON env var."""
    raw = OPENCLAW_GATEWAY_CRONS_JSON.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        result = []
        for j in jobs:
            state = j.get("state", {})
            sched = j.get("schedule", {})
            interval_ms = sched.get("everyMs", 0)
            interval_min = round(interval_ms / 60000) if interval_ms else None
            # Also try cron expression parsing (schedule.kind=="cron" uses expr)
            cron_expr = sched.get("expr", "")
            if not interval_min and cron_expr:
                import re
                m = re.match(r"^\*/(\d+)\s+\*", cron_expr)
                if m:
                    interval_min = int(m.group(1))
            last_run_ms = state.get("lastRunAtMs", 0)
            next_run_ms = state.get("nextRunAtMs", 0)
            last_run_iso = (
                datetime.fromtimestamp(last_run_ms / 1000, tz=timezone.utc).isoformat()
                if last_run_ms
                else None
            )
            next_run_iso = (
                datetime.fromtimestamp(next_run_ms / 1000, tz=timezone.utc).isoformat()
                if next_run_ms
                else None
            )
            result.append(
                {
                    "id": j.get("id"),
                    "name": j.get("name", ""),
                    "agent": j.get("agentId", ""),
                    "enabled": j.get("enabled", True),
                    "interval_min": interval_min,
                    "last_run": last_run_iso,
                    "next_run": next_run_iso,
                    "last_status": state.get("lastRunStatus", "unknown"),
                    "last_duration_ms": state.get("lastDurationMs", 0),
                    "consecutive_errors": state.get("consecutiveErrors", 0),
                    "schedule_expr": sched.get("expr", ""),
                }
            )
        # Sort by last_run descending (most recent first)
        return sorted(result, key=lambda x: x.get("last_run") or "", reverse=True)
    except Exception:
        return []
