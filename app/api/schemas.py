from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field
from pydantic import RootModel


class WordStat(BaseModel):
    """Statistics for a single word.

    count: absolute frequency across all traversed pages
    percent: percentage of total tokens (0..100]
    """
    count: int = Field(..., ge=0, description="Absolute count of the word")
    percent: float = Field(..., ge=0.0, le=100.0, description="Percentage of total tokens")


class WordFrequencyResponse(RootModel[Dict[str, WordStat]]):
    """Mapping from word -> WordStat."""
    pass


class WordFrequencyQuery(BaseModel):
    """Query parameters for GET /word-frequency.

    Note: Used via `Depends(WordFrequencyQuery)` in the route if you want a model,
    otherwise you can keep them as plain query params.
    """
    article: str = Field(..., description="Wikipedia article title to start from")
    depth: int = Field(0, ge=0, description="Traversal depth (0 = only the start article)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"article": "Earth", "depth": 2}
            ]
        }
    }


class KeywordsRequest(BaseModel):
    """Request body for POST /keywords."""
    article: str = Field(..., description="Wikipedia article title to start from")
    depth: int = Field(0, ge=0, description="Traversal depth (0 = only the start article)")
    ignore_list: List[str] = Field(default_factory=list, description="Words to exclude from the results")
    percentile: int = Field(..., ge=0, le=100, description="Keep words with count >= this percentile of counts")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "article": "Earth",
                    "depth": 2,
                    "ignore_list": ["the", "of", "and"],
                    "percentile": 80
                }
            ]
        }
    }
