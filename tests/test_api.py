import unittest
from typing import AsyncIterator, List, Optional

from fastapi.testclient import TestClient

from app.main import app
from app.di import get_wiki_client


class FakeWikiClient:
    def __init__(self, extracts: Optional[List[str]] = None):
        self._extracts = extracts or [
            "Apple banana apple.",
            "Banana orange.",
        ]

    async def crawl_extracts_stream(
        self,
        root_title: str,
        max_depth: int,
        *,
        max_links_per_page: int = 100,
    ) -> AsyncIterator[str]:
        for txt in self._extracts:
            yield txt


def override_get_wiki_client() -> FakeWikiClient:
    return FakeWikiClient()


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_wiki_client] = override_get_wiki_client
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_word_frequency_happy_path(self):
        resp = self.client.get(
            "/word-frequency", params={"article": "Earth", "depth": 0}
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()

        self.assertIn("apple", payload)
        self.assertIn("banana", payload)
        self.assertIn("orange", payload)

        self.assertEqual(payload["apple"]["count"], 2)
        self.assertEqual(payload["banana"]["count"], 2)
        self.assertEqual(payload["orange"]["count"], 1)

        total_percent = sum(v["percent"] for v in payload.values())
        self.assertAlmostEqual(total_percent, 100.0, places=6)
        for item in payload.values():
            self.assertGreaterEqual(item["percent"], 0.0)
            self.assertLessEqual(item["percent"], 100.0)

    def test_word_frequency_requires_article(self):
        resp = self.client.get("/word-frequency", params={"depth": 0})
        self.assertEqual(
            resp.status_code, 422
        )

    def test_word_frequency_depth_param_ok(self):
        resp = self.client.get(
            "/word-frequency", params={"article": "Earth", "depth": 2}
        )
        self.assertEqual(resp.status_code, 200)


    def test_keywords_happy_path_with_filters(self):
        body = {
            "article": "Earth",
            "depth": 1,
            "ignore_list": ["banana"],  # remove banana entirely
            "percentile": 50,  # percentile of counts [2,1] -> cutoff ~1.5 => keep apple (2)
        }
        resp = self.client.post("/keywords", json=body)
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()

        self.assertIn("apple", payload)
        self.assertNotIn("banana", payload)
        self.assertNotIn("orange", payload)

        self.assertEqual(payload["apple"]["count"], 2)
        self.assertAlmostEqual(payload["apple"]["percent"], 100.0, places=6)

    def test_keywords_empty_ignore_and_zero_percentile_keeps_all(self):
        body = {
            "article": "Earth",
            "depth": 0,
            "ignore_list": [],
            "percentile": 0,
        }
        resp = self.client.post("/keywords", json=body)
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertSetEqual(set(payload.keys()), {"apple", "banana", "orange"})

        self.assertEqual(payload["apple"]["count"], 2)
        self.assertEqual(payload["banana"]["count"], 2)
        self.assertEqual(payload["orange"]["count"], 1)

    def test_keywords_validation_errors(self):
        resp = self.client.post("/keywords")
        self.assertEqual(resp.status_code, 422)

        body = {
            "article": "Earth",
            "depth": 0,
            "ignore_list": [],
            "percentile": 101,
        }
        resp = self.client.post("/keywords", json=body)
        self.assertEqual(resp.status_code, 422)

    def test_override_extracts_per_test(self):
        def custom_override():
            return FakeWikiClient(extracts=["alpha beta beta", "beta gamma"])

        app.dependency_overrides[get_wiki_client] = custom_override

        try:
            resp = self.client.get(
                "/word-frequency", params={"article": "X", "depth": 0}
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["beta"]["count"], 3)
            self.assertEqual(data["alpha"]["count"], 1)
            self.assertEqual(data["gamma"]["count"], 1)
        finally:
            app.dependency_overrides[get_wiki_client] = override_get_wiki_client


if __name__ == "__main__":
    unittest.main()
