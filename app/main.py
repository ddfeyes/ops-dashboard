"""Ops Dashboard — FastAPI backend with all M1 endpoints."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agents import get_ao_sessions, get_openclaw_agents
from app.kanban import fetch_kanban_cards
from app.system import get_hetzner_metrics, get_mac_metrics
from app.usage import get_usage

app = FastAPI(title="Ops Dashboard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=4)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/kanban")
async def kanban() -> list[dict]:
    loop = asyncio.get_event_loop()
    try:
        cards = await loop.run_in_executor(_executor, fetch_kanban_cards)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return cards


@app.get("/api/agents")
async def agents() -> dict[str, Any]:
    """Return AO sessions and OpenClaw agent list."""
    loop = asyncio.get_event_loop()
    sessions = await loop.run_in_executor(_executor, get_ao_sessions)
    agent_list = await loop.run_in_executor(_executor, get_openclaw_agents)
    return {"sessions": sessions, "agents": agent_list}


@app.get("/api/system")
async def system_metrics() -> dict[str, Any]:
    """Return Mac + Hetzner system metrics."""
    loop = asyncio.get_event_loop()
    mac = await loop.run_in_executor(_executor, get_mac_metrics)

    hetzner: dict[str, Any] | None = None
    hetzner_error: str | None = None
    try:
        hetzner = await loop.run_in_executor(_executor, get_hetzner_metrics)
    except Exception as exc:
        hetzner_error = str(exc)

    return {
        "mac": mac,
        "hetzner": hetzner,
        "hetzner_error": hetzner_error,
    }


@app.get("/api/usage")
async def usage() -> dict[str, Any]:
    """Return Anthropic API usage from local Claude Code session logs."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, get_usage)
