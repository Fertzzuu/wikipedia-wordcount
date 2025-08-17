import asyncio
import unittest
from typing import Any, Dict, List, Optional, Tuple

import httpx
from httpx import AsyncClient

from app.clients.wiki import WikiClient


class _FakeResponse:
    def __init__(self, url: str, payload: Dict[str, Any], status_code: int = 200):
        self._url = url
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            # Construct a real HTTPStatusError so behavior matches httpx
            req = httpx.Request("GET", self._url)
            res = httpx.Response(self.status_code, request=req)
            raise httpx.HTTPStatusError("error", request=req, response=res)


class _FakeAsyncClient(AsyncClient):
    def __init__(self, payloads: List[Dict[str, Any]]):
        # Each .get() pops one payload from this queue
        self._queue: List[Dict[str, Any]] = list(payloads)
        self.calls: List[Dict[str, Any]] = []  # capture url/params/headers/timeout

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> _FakeResponse:
        self.calls.append(
            {
                "url": url,
                "params": dict(params or {}),
                "headers": dict(headers or {}),
                "timeout": timeout,
            }
        )
        if not self._queue:
            raise AssertionError("FakeAsyncClient: no more payloads queued for GET")
        payload = self._queue.pop(0)
        return _FakeResponse(url, payload, status_code=200)

    async def aclose(self) -> None:
        return


class TestWikiClientQuery(unittest.IsolatedAsyncioTestCase):
    async def test_query_single_page_no_continue_yields_once(self):
        fake_payloads = [
            {
                "query": {
                    "pages": [{"title": "Root", "extract": "Root text", "links": []}]
                }
            }
        ]
        fake_http = _FakeAsyncClient(fake_payloads)
        wiki = WikiClient(
            client=fake_http,
            semaphore=asyncio.Semaphore(10),
            user_agent="TestAgent/1.0",
        )

        yielded = []
        async for block in wiki._query({"action": "query", "titles": "Root"}):
            yielded.append(block)

        self.assertEqual(len(yielded), 1)
        self.assertEqual(yielded[0]["pages"][0]["title"], "Root")
        self.assertEqual(
            fake_http.calls[0]["headers"].get("User-Agent"), "TestAgent/1.0"
        )
        self.assertTrue(fake_http.calls[0]["url"].endswith("/w/api.php"))

    async def test_query_pagination_merges_continue_params(self):
        fake_payloads = [
            {"query": {"chunk": 1}, "continue": {"foo": "bar", "continue": "-||"}},
            {"query": {"chunk": 2}},
        ]
        fake_http = _FakeAsyncClient(fake_payloads)
        wiki = WikiClient(
            client=fake_http,
            semaphore=asyncio.Semaphore(10),
            user_agent="UA",
        )

        yielded = []
        params = {"action": "query", "prop": "links", "titles": "Root"}
        async for block in wiki._query(params):
            yielded.append(block)

        self.assertEqual([b["chunk"] for b in yielded], [1, 2])
        self.assertIn("foo", fake_http.calls[1]["params"])
        self.assertEqual(fake_http.calls[1]["params"]["foo"], "bar")

    async def test_query_raises_on_api_error_field(self):
        fake_payloads = [{"error": {"code": "bad", "info": "broken"}}]
        fake_http = _FakeAsyncClient(fake_payloads)
        wiki = WikiClient(fake_http, asyncio.Semaphore(1), user_agent="UA")

        with self.assertRaises(RuntimeError):
            async for _ in wiki._query({"action": "query", "titles": "X"}):
                pass


class TestWikiClientCrawlExtractsStream(unittest.IsolatedAsyncioTestCase):
    async def test_depth0_yields_root_extract_only(self):
        fake_payloads = [
            {
                "query": {
                    "pages": [
                        {
                            "title": "Root",
                            "extract": "Root text",
                            "links": [{"ns": 0, "title": "A"}, {"ns": 0, "title": "B"}],
                        }
                    ]
                }
            }
        ]
        wiki = WikiClient(
            _FakeAsyncClient(fake_payloads), asyncio.Semaphore(5), user_agent="UA"
        )

        extracts = []
        async for text in wiki.crawl_extracts_stream(
            "Root", max_depth=0, max_links_per_page=10
        ):
            extracts.append(text)

        self.assertEqual(extracts, ["Root text"])

    async def test_depth1_schedules_children_in_sorted_order(self):
        fake_payloads = [
            {
                "query": {
                    "pages": [
                        {
                            "title": "Root",
                            "extract": "Root text",
                            "links": [{"ns": 0, "title": "B"}, {"ns": 0, "title": "A"}],
                        }
                    ]
                }
            },
            {"query": {"pages": [{"title": "A", "extract": "A text", "links": []}]}},
            {"query": {"pages": [{"title": "B", "extract": "B text", "links": []}]}},
        ]
        wiki = WikiClient(
            _FakeAsyncClient(fake_payloads), asyncio.Semaphore(5), user_agent="UA"
        )

        extracts = []
        async for text in wiki.crawl_extracts_stream(
            "Root", max_depth=1, max_links_per_page=10
        ):
            extracts.append(text)

        self.assertEqual(extracts, ["Root text", "A text", "B text"])

    async def test_deduplicates_visited_titles(self):
        fake_payloads = [
            {
                "query": {
                    "pages": [
                        {
                            "title": "Root",
                            "extract": "Root text",
                            "links": [{"ns": 0, "title": "A"}, {"ns": 0, "title": "B"}],
                        }
                    ]
                }
            },
            {
                "query": {
                    "pages": [
                        {
                            "title": "A",
                            "extract": "A text",
                            "links": [{"ns": 0, "title": "B"}],
                        }
                    ]
                }
            },
            {"query": {"pages": [{"title": "B", "extract": "B text", "links": []}]}},
        ]
        wiki = WikiClient(
            _FakeAsyncClient(fake_payloads), asyncio.Semaphore(5), user_agent="UA"
        )

        extracts = []
        async for text in wiki.crawl_extracts_stream(
            "Root", max_depth=1, max_links_per_page=10
        ):
            extracts.append(text)

        self.assertEqual(extracts, ["Root text", "A text", "B text"])  # B only once

    async def test_respects_max_links_per_page(self):
        fake_payloads = [
            {
                "query": {
                    "pages": [
                        {
                            "title": "Root",
                            "extract": "Root text",
                            "links": [{"ns": 0, "title": "Z"}, {"ns": 0, "title": "A"}],
                        }
                    ]
                }
            },
            {"query": {"pages": [{"title": "A", "extract": "A text", "links": []}]}},
        ]
        wiki = WikiClient(
            _FakeAsyncClient(fake_payloads), asyncio.Semaphore(5), user_agent="UA"
        )

        extracts = []
        async for text in wiki.crawl_extracts_stream(
            "Root", max_depth=1, max_links_per_page=1
        ):
            extracts.append(text)

        self.assertEqual(extracts, ["Root text", "A text"])

    async def test_skips_empty_extract_but_still_crawls_children(self):
        fake_payloads = [
            {
                "query": {
                    "pages": [
                        {
                            "title": "Root",
                            "extract": "",
                            "links": [{"ns": 0, "title": "A"}],
                        }
                    ]
                }
            },
            {"query": {"pages": [{"title": "A", "extract": "A text", "links": []}]}},
        ]
        wiki = WikiClient(
            _FakeAsyncClient(fake_payloads), asyncio.Semaphore(5), user_agent="UA"
        )

        extracts = []
        async for text in wiki.crawl_extracts_stream(
            "Root", max_depth=1, max_links_per_page=10
        ):
            extracts.append(text)

        self.assertEqual(extracts, ["A text"])

    async def test_uses_canonical_title_for_visited(self):
        fake_payloads = [
            {
                "query": {
                    "pages": [
                        {
                            "title": "Earth (planet)",
                            "extract": "Earth text",
                            "links": [{"ns": 0, "title": "Earth (planet)"}],
                        }
                    ]
                }
            }
        ]
        wiki = WikiClient(
            _FakeAsyncClient(fake_payloads), asyncio.Semaphore(5), user_agent="UA"
        )

        extracts = []
        async for text in wiki.crawl_extracts_stream(
            "Earth", max_depth=1, max_links_per_page=10
        ):
            extracts.append(text)

        self.assertEqual(extracts, ["Earth text"])


if __name__ == "__main__":
    unittest.main()
