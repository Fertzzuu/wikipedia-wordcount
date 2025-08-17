from __future__ import annotations

import asyncio
from typing import AsyncIterator, Dict, List, Tuple, Set

import httpx


class WikiClient:
    """
    Minimal async MediaWiki client.
    - query(): async generator over paginated 'query' chunks
    - crawl_extracts_stream(): stream extracts as soon as available
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        *,
        base_url: str = "https://en.wikipedia.org/w/api.php",
        user_agent: str = "WikiCrawler/1.0 (contact: marcell.megyeri@mail.com)",
        timeout: float = 15.0,
    ) -> None:
        self._client = client
        self._semaphore = semaphore
        self._base_url = base_url
        self._user_agent = user_agent
        self._timeout = timeout

    async def query(self, params: Dict) -> AsyncIterator[Dict]:
        """
        Yields each 'query' object from the MediaWiki API,
        following 'continue' pagination until exhausted.
        """
        last_continue: Dict = {}
        while True:
            request_params = dict(params)
            request_params.update(last_continue)

            async with self._semaphore:
                response = await self._client.get(
                    self._base_url,
                    params=request_params,
                    headers={"User-Agent": self._user_agent},
                    timeout=self._timeout,
                )
            response.raise_for_status()
            payload = response.json()

            if "error" in payload:
                raise RuntimeError(f"MediaWiki API error: {payload['error']}")

            query_block = payload.get("query")
            if query_block is not None:
                yield query_block

            continue_block = payload.get("continue")
            if not continue_block:
                break
            last_continue = continue_block

    async def crawl_extracts_stream(
        self,
        root_title: str,
        max_depth: int,
        *,
        max_links_per_page: int = 100,
    ) -> AsyncIterator[str]:
        """
        Streams page extracts recursively up to `max_depth`.
        """
        visited_titles: Set[str] = set()
        pages_to_visit: asyncio.Queue[Tuple[str, int]] = asyncio.Queue()
        await pages_to_visit.put((root_title, max_depth))

        while not pages_to_visit.empty():
            current_title, remaining_depth = await pages_to_visit.get()

            base_params = {
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "redirects": 1,
                "prop": "extracts|links",
                "explaintext": 1,
                "plnamespace": 0,
                "pllimit": "max",
                "titles": current_title,
            }

            canonical_title: str | None = None
            extract_already_emitted = False
            collected_links: List[str] = []

            async for payload in self.query(base_params):
                pages = payload.get("pages") or []
                if not pages:
                    continue

                page = pages[0]
                current_canonical = page.get("title", current_title)

                if canonical_title is None:
                    canonical_title = current_canonical
                    if canonical_title in visited_titles:
                        break
                    visited_titles.add(canonical_title)

                if not extract_already_emitted:
                    extract_text = page.get("extract") or ""
                    if extract_text:
                        yield extract_text
                        extract_already_emitted = True

                if remaining_depth > 0:
                    new_links = [
                        link["title"]
                        for link in (page.get("links") or [])
                        if link.get("ns") == 0 and "title" in link
                    ]
                    collected_links.extend(new_links)

                    to_schedule = sorted(collected_links)[:max_links_per_page]
                    collected_links = to_schedule  # enforce bound across chunks

                    for child_title in to_schedule:
                        if child_title not in visited_titles:
                            visited_titles.add(child_title)
                            await pages_to_visit.put((child_title, remaining_depth - 1))

            pages_to_visit.task_done()
