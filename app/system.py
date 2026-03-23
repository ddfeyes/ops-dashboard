"""System metrics: Mac (psutil) + Hetzner (SSH via paramiko)."""

from __future__ import annotations

import json
import re
from typing import Any

import paramiko
import psutil

HETZNER_HOST = "94.130.65.86"
HETZNER_PORT = 2203
HETZNER_USER = "user3"


# ---------------------------------------------------------------------------
# Mac metrics
# ---------------------------------------------------------------------------

def get_mac_metrics() -> dict[str, Any]:
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
        pass  # Not available on all platforms

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
    }


# ---------------------------------------------------------------------------
# Hetzner metrics via SSH
# ---------------------------------------------------------------------------

def _ssh_client() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=HETZNER_HOST,
        port=HETZNER_PORT,
        username=HETZNER_USER,
        timeout=10,
    )
    return client


def _run(client: paramiko.SSHClient, cmd: str) -> str:
    _, stdout, _ = client.exec_command(cmd, timeout=15)
    return stdout.read().decode(errors="replace")


def _parse_top(output: str) -> dict[str, float]:
    """Parse cpu% and mem% from `top -bn1` output."""
    cpu_idle = 0.0
    mem_percent = 0.0

    for line in output.splitlines():
        # Example: %Cpu(s):  3.2 us,  1.0 sy,  0.0 ni, 94.5 id, ...
        if re.search(r"%Cpu", line, re.IGNORECASE):
            m = re.search(r"([\d.]+)\s*id", line)
            if m:
                cpu_idle = float(m.group(1))
        # Example: MiB Mem :  64220.5 total,  12345.0 free,  ...  used, ...
        elif re.search(r"MiB Mem", line, re.IGNORECASE):
            total_m = re.search(r"([\d.]+)\s*total", line)
            used_m = re.search(r"([\d.]+)\s*used", line)
            if total_m and used_m:
                total = float(total_m.group(1))
                used = float(used_m.group(1))
                if total > 0:
                    mem_percent = round(used / total * 100, 1)

    return {
        "cpu_percent": round(100.0 - cpu_idle, 1),
        "memory_percent": mem_percent,
    }


def _parse_df(output: str) -> list[dict[str, Any]]:
    """Parse `df -h` output into a list of filesystem entries."""
    lines = output.strip().splitlines()
    results: list[dict[str, Any]] = []
    for line in lines[1:]:  # skip header
        parts = line.split()
        if len(parts) < 6:
            continue
        results.append({
            "filesystem": parts[0],
            "size": parts[1],
            "used": parts[2],
            "avail": parts[3],
            "use_percent": parts[4],
            "mount": parts[5],
        })
    return results


def _parse_docker_ps(output: str) -> list[dict[str, Any]]:
    """Parse `docker ps --format json` output (one JSON object per line)."""
    containers: list[dict[str, Any]] = []
    for line in output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            containers.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return containers


def get_hetzner_metrics() -> dict[str, Any]:
    client = _ssh_client()
    try:
        top_out = _run(client, "top -bn1")
        df_out = _run(client, "df -h")
        docker_out = _run(client, "docker ps --format json")
    finally:
        client.close()

    cpu_mem = _parse_top(top_out)
    filesystems = _parse_df(df_out)
    containers = _parse_docker_ps(docker_out)

    # Summarise root filesystem usage
    root_disk = next(
        (fs for fs in filesystems if fs["mount"] == "/"),
        filesystems[0] if filesystems else {},
    )

    return {
        "cpu_percent": cpu_mem["cpu_percent"],
        "memory_percent": cpu_mem["memory_percent"],
        "disk": {
            "filesystem": root_disk.get("filesystem"),
            "size": root_disk.get("size"),
            "used": root_disk.get("used"),
            "avail": root_disk.get("avail"),
            "use_percent": root_disk.get("use_percent"),
            "mount": root_disk.get("mount"),
        },
        "filesystems": filesystems,
        "containers": containers,
        "container_count": len(containers),
    }
