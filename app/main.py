import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.kanban import fetch_kanban_cards

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
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return cards
