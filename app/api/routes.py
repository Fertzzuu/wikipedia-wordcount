from __future__ import annotations

from typing import List, Tuple

import numpy as np
from fastapi import APIRouter, Depends, Query
from app.di import get_wiki_client
from app.clients.wiki import WikiClient
from app.core.text import (
    vectorize_counts,
    to_freq_dict,
    apply_ignore_list,
    apply_percentile,
)
from app.api.schemas import (
    WordFrequencyResponse,
    KeywordsRequest,
)

router = APIRouter()


async def _crawl_and_vectorize(
    client: WikiClient, article: str, depth: int
) -> Tuple[np.ndarray, np.ndarray]:
    collected_extracts: List[str] = []
    async for extract_text in client.crawl_extracts_stream(
        article, depth, max_links_per_page=100
    ):
        collected_extracts.append(extract_text)
    return vectorize_counts(collected_extracts)


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

    word_counts, vocabulary = await _crawl_and_vectorize(client, article, depth)
    return to_freq_dict(word_counts, vocabulary)


@router.post("/keywords", response_model=WordFrequencyResponse)
async def post_keywords(
    request: KeywordsRequest,
    wiki_client: WikiClient = Depends(get_wiki_client),
):
    """Get word counts from Wikipedia articles based on extra parameters"""
    word_counts, vocabulary = await _crawl_and_vectorize(
        wiki_client, request.article, request.depth
    )

    if request.ignore_list:
        word_counts, vocabulary = apply_ignore_list(
            word_counts, vocabulary, request.ignore_list
        )

    word_counts, vocabulary = apply_percentile(
        word_counts, vocabulary, request.percentile
    )

    return to_freq_dict(word_counts, vocabulary)
