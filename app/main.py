# main.py
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx
from fastapi import FastAPI

from app.clients.wiki import WikiClient
from app.api.routes import router as api_router
from app.di import set_wiki_client

CONCURRENCY_LIMIT: int = 8
USER_AGENT: str = "WikiCrawler/1.0 (contact: marcell.megyeri@mail.com)"
HTTP_TIMEOUT_SECONDS: float = 15.0

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Wikipedia Word-Frequency API")

_async_client: Optional[httpx.AsyncClient] = None
_request_semaphore: Optional[asyncio.Semaphore] = None
_wiki_client: Optional[WikiClient] = None


@app.on_event("startup")
async def on_startup() -> None:
    """
    Create one AsyncClient + one Semaphore for the whole app,
    then wrap them in a WikiClient.
    """
    global _async_client, _request_semaphore, _wiki_client

    _async_client = httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS)
    _request_semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    set_wiki_client(WikiClient(
        client=_async_client,
        semaphore=_request_semaphore,
        user_agent=USER_AGENT,
        timeout=HTTP_TIMEOUT_SECONDS,
    ))

    logger.info("Startup complete: httpx client + WikiClient initialized.")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Close the shared AsyncClient cleanly."""
    global _async_client

    if _async_client is not None:
        try:
            await _async_client.aclose()
        finally:
            _async_client = None

    logger.info("Shutdown complete: httpx client closed.")


def get_wiki_client() -> WikiClient:
    """
    Dependency provider for routes/services.
    FastAPI will call this when a handler declares:
      wiki_client: WikiClient = Depends(get_wiki_client)
    """
    if _wiki_client is None:
        # Shouldn’t happen in normal operation; protects tests/misconfig.
        raise RuntimeError("WikiClient is not initialized yet (startup not run).")
    return _wiki_client


# Optional: a simple health endpoint
@app.get("/")
async def healthcheck() -> dict:
    return {"status": "ok"}


# Mount your API routes
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

