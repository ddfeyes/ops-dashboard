"""System metrics: local server (psutil + docker) + optional Mac via SSH tunnel."""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any

import psutil

# The dashboard runs ON the Hetzner server.
# Local psutil = Hetzner server metrics.
# "Mac" panel is shown as N/A unless a MAC_SSH_HOST is configured.

MAC_SSH_HOST = os.getenv("MAC_SSH_HOST", "")  # e.g. "user@192.168.x.x"
MAC_SSH_PORT = int(os.getenv("MAC_SSH_PORT", "22"))


# ---------------------------------------------------------------------------
# Local server metrics (runs wherever the container is — Hetzner)
# ---------------------------------------------------------------------------

def get_server_metrics() -> dict[str, Any]:
    """Return metrics for the local machine (the Hetzner server)."""
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    temps: dict[str, float] = {}
    try:
        sensor_data = psutil.sensors_temperatures()  # type: ignore[attr-defined]
        if sensor_data:
            for name, entries in sensor_data.items():
                for entry in entries:
                    label = entry.label or name
                    temps[label] = entry.current
    except (AttributeError, Exception):
        pass

    # Docker containers (if docker socket is available)
    containers = _get_docker_containers()

    return {
        "cpu_percent": cpu,
        "memory": {
            "total_gb": round(mem.total / 1024**3, 2),
            "used_gb": round(mem.used / 1024**3, 2),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1024**3, 2),
            "used_gb": round(disk.used / 1024**3, 2),
            "percent": disk.percent,
        },
        "temperatures": temps,
        "containers": containers,
        "container_count": len(containers),
        "label": "Hetzner Server",
    }


def _get_docker_containers() -> list[dict[str, Any]]:
    """Return running docker containers via CLI (no socket needed if docker CLI is installed)."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if result.returncode != 0:
            return []
        containers = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return containers
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return []


# ---------------------------------------------------------------------------
# Mac metrics — only if MAC_SSH_HOST is configured
# ---------------------------------------------------------------------------

def get_mac_metrics() -> dict[str, Any] | None:
    """Return Mac metrics if MAC_SSH_HOST env var is set, else None."""
    if not MAC_SSH_HOST:
        return None
    try:
        import paramiko  # type: ignore

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=MAC_SSH_HOST,
            port=MAC_SSH_PORT,
            timeout=8,
        )
        # Run a Python snippet on the Mac to get psutil metrics
        cmd = (
            "python3 -c \""
            "import psutil, json; "
            "m=psutil.virtual_memory(); d=psutil.disk_usage('/'); "
            "print(json.dumps({'cpu':psutil.cpu_percent(interval=0.3), "
            "'mem_pct':m.percent,'mem_total':round(m.total/1024**3,2),"
            "'mem_used':round(m.used/1024**3,2),'disk_pct':d.percent,"
            "'disk_total':round(d.total/1024**3,2),'disk_used':round(d.used/1024**3,2)}))\""
        )
        _, stdout, _ = client.exec_command(cmd, timeout=12)
        raw = stdout.read().decode(errors="replace").strip()
        client.close()
        data = json.loads(raw)
        return {
            "cpu_percent": data.get("cpu", 0),
            "memory": {
                "total_gb": data.get("mem_total", 0),
                "used_gb": data.get("mem_used", 0),
                "percent": data.get("mem_pct", 0),
            },
            "disk": {
                "total_gb": data.get("disk_total", 0),
                "used_gb": data.get("disk_used", 0),
                "percent": data.get("disk_pct", 0),
            },
            "label": "Mac",
        }
    except Exception as exc:
        return {"error": str(exc), "label": "Mac"}


# ---------------------------------------------------------------------------
# Backward-compat shims used by main.py
# ---------------------------------------------------------------------------

def get_hetzner_metrics() -> dict[str, Any]:
    """Alias: local server metrics (dashboard runs on Hetzner)."""
    return get_server_metrics()
