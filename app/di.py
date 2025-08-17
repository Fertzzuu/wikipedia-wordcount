from typing import Optional
from app.clients.wiki import WikiClient

_wiki_client: Optional[WikiClient] = None


def set_wiki_client(client: WikiClient) -> None:
    """Called from startup to register the shared WikiClient."""
    global _wiki_client
    _wiki_client = client


def get_wiki_client() -> WikiClient:
    """FastAPI dependency provider used by routes and services."""
    if _wiki_client is None:
        raise RuntimeError("WikiClient is not initialized (startup not completed).")
    return _wiki_client
