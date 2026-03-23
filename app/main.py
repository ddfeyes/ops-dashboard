"""Ops Dashboard — FastAPI backend with all M1 endpoints."""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agents import get_ao_sessions, get_openclaw_agents
from app.kanban import fetch_kanban_cards
from app.system import get_hetzner_metrics, get_mac_metrics, get_server_metrics
from app.usage import get_usage

app = FastAPI(title="Ops Dashboard", version="0.1.0")

_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ops-dashboard.111miniapp.com",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=4)


@app.on_event("shutdown")
async def _shutdown() -> None:
    _executor.shutdown(wait=False)


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(os.path.join(_static_dir, "index.html"))


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/kanban")
async def kanban() -> list[dict]:
    loop = asyncio.get_running_loop()
    try:
        cards = await loop.run_in_executor(_executor, fetch_kanban_cards)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return cards


@app.get("/api/agents")
async def agents() -> dict[str, Any]:
    """Return AO sessions and OpenClaw agent list."""
    loop = asyncio.get_running_loop()
    sessions, agent_list = await asyncio.gather(
        loop.run_in_executor(_executor, get_ao_sessions),
        loop.run_in_executor(_executor, get_openclaw_agents),
    )
    return {"sessions": sessions, "agents": agent_list}


@app.get("/api/system")
async def system_metrics() -> dict[str, Any]:
    """Return server (local/Hetzner) + optional Mac system metrics."""
    loop = asyncio.get_running_loop()
    server_result, mac_result = await asyncio.gather(
        loop.run_in_executor(_executor, get_server_metrics),
        loop.run_in_executor(_executor, get_mac_metrics),
        return_exceptions=True,
    )

    server: dict[str, Any] | None = None
    server_error: str | None = None
    if isinstance(server_result, BaseException):
        server_error = str(server_result)
    else:
        server = server_result

    mac: dict[str, Any] | None = None
    mac_error: str | None = None
    if isinstance(mac_result, BaseException):
        mac_error = str(mac_result)
    elif mac_result is not None and "error" in mac_result:
        mac_error = mac_result.get("error")
        mac = None
    else:
        mac = mac_result

    # Legacy keys for backward compat with old frontend
    return {
        "server": server,
        "server_error": server_error,
        "mac": server,  # frontend "mac" panel now shows server metrics
        "hetzner": server,  # keep legacy key
        "hetzner_error": server_error,
        "mac_remote": mac,
        "mac_remote_error": mac_error,
    }


@app.get("/api/usage")
async def usage() -> dict[str, Any]:
    """Return Anthropic API usage from local Claude Code session logs."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, get_usage)
