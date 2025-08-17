from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, Query
from app.di import get_wiki_client
from app.clients.wiki import WikiClient
from app.core.text import vectorize_counts, to_freq_dict, apply_ignore_list, apply_percentile
from app.api.schemas import (
    WordFrequencyResponse,
)

router = APIRouter()


@router.get(
    "/word-frequency",
    response_model=WordFrequencyResponse,
    summary="Compute word frequencies by crawling Wikipedia up to a depth",
)
async def get_word_frequency(
        article: str = Query(..., description="Wikipedia article title"),
        depth: int = Query(0, ge=0, description="Traversal depth"),
        client: WikiClient = Depends(get_wiki_client),
):
    """Traverse Wikipedia articles up to `max_depth` and return word frequencies."""
    collected_extracts: List[str] = []

    async for extract_text in client.crawl_extracts_stream(
            article, depth, max_links_per_page=100
    ):
        collected_extracts.append(extract_text)

    word_counts, vocabulary = vectorize_counts(collected_extracts)
    return to_freq_dict(word_counts, vocabulary)


# @router.post(
#     "/keywords",
#     response_model=WordFrequencyResponse,
#     summary="Filter word frequencies by ignore list and percentile",
# )
# async def post_keywords(
#         body: KeywordsRequest,
#         client: WikiClient = Depends(get_wiki_client),
# ):
#     """Same as `/word-frequency`, but excludes `ignore_list` and keeps words
#     whose counts are at/above the given `percentile`.
#     """
#     result: Dict[str, Dict[str, float]] = await compute_keywords(
#         client,
#         body.article,
#         body.depth,
#         body.ignore_list,
#         body.percentile,
#     )
#     return result
