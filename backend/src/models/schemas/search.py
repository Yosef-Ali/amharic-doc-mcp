"""Search API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .documents import PaginationMeta, DocumentMetadata


class SearchFacets(BaseModel):
    """Facet filters supplied by the client."""

    document_type: Optional[List[str]] = None
    language: Optional[List[str]] = None
    author: Optional[List[str]] = None
    date_range: Optional[str] = Field(
        default=None, description="ISO8601 interval, e.g. 2024-01-01/2024-01-31"
    )
    topic_categories: Optional[List[str]] = None
    processing_quality: Optional[List[str]] = None


class SearchRequest(BaseModel):
    """Payload for document search."""

    query: str = Field(..., min_length=1)
    facets: Optional[SearchFacets] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort: Optional[str] = Field(
        default=None, description="Sort expression such as 'relevance' or 'indexed_at:desc'"
    )


class SearchHit(BaseModel):
    """Single search result entry."""

    document: DocumentMetadata
    highlights: Dict[str, List[str]] = Field(default_factory=dict)
    score: Optional[float] = None
    indexed_at: Optional[datetime] = None


class SearchResponse(BaseModel):
    """Search response with results and pagination metadata."""

    results: List[SearchHit]
    pagination: PaginationMeta
    facets: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="Facet counts keyed by facet name",
    )


class SuggestionResponse(BaseModel):
    """Autocomplete suggestions for search terms."""

    suggestions: List[str]


class ReindexRequest(BaseModel):
    """Parameters to trigger search reindex jobs."""

    document_ids: Optional[List[str]] = Field(
        default=None, description="Subset of documents to reindex"
    )
    rebuild_embeddings: bool = False
    force: bool = False
