import asyncio
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.system import get_mac_metrics, get_hetzner_metrics

app = FastAPI(title="Ops Dashboard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/system")
async def system_metrics() -> dict[str, Any]:
    """Return Mac + Hetzner system metrics."""
    mac = await asyncio.get_event_loop().run_in_executor(None, get_mac_metrics)

    hetzner: dict[str, Any] | None = None
    hetzner_error: str | None = None
    try:
        hetzner = await asyncio.get_event_loop().run_in_executor(
            None, get_hetzner_metrics
        )
    except Exception as exc:
        hetzner_error = str(exc)

    return {
        "mac": mac,
        "hetzner": hetzner,
        "hetzner_error": hetzner_error,
    }
