"""MongoDB repository for extracted document content."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable, List, Optional

from motor.core import AgnosticCollection, AgnosticDatabase
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class NamedEntityDocument(BaseModel):
    """Named entity metadata captured during NLP processing."""

    text: str
    entity_type: str
    start_position: int
    end_position: int
    confidence: float
    amharic_canonical: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)


class AmharicAnalysisDocument(BaseModel):
    """Aggregated Amharic analysis metrics for extracted content."""

    word_count: int
    sentence_count: int
    paragraph_count: int
    language_confidence: float = Field(..., ge=0.0, le=1.0)
    script_type: str
    readability_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)


class StructuredBlock(BaseModel):
    """Represents structured document fragments (tables, sections, etc.)."""

    headers: List[Dict[str, Any]] = Field(default_factory=list)
    paragraphs: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    images: List[Dict[str, Any]] = Field(default_factory=list)
    footnotes: List[Dict[str, Any]] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)


class ExtractedContentDocument(BaseModel):
    """Full representation of extracted document content for persistence."""

    document_id: str
    raw_text: str
    structured_data: StructuredBlock = Field(default_factory=StructuredBlock)
    amharic_analysis: AmharicAnalysisDocument
    ocr_confidence: Optional[float] = None
    named_entities: List[NamedEntityDocument] = Field(default_factory=list)
    summary: Optional[str] = None
    extracted_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        payload = self.model_dump(by_alias=True)
        payload["structured_data"] = self.structured_data.to_dict()
        payload["amharic_analysis"] = self.amharic_analysis.to_dict()
        payload["named_entities"] = [entity.to_dict() for entity in self.named_entities]
        return payload


class ExtractedContentRepository:
    """Provides CRUD operations for extracted content snapshots."""

    COLLECTION_NAME = "extracted_content"

    def __init__(self, database: AgnosticDatabase) -> None:
        self._database = database
        self._collection: AgnosticCollection = database[self.COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        """Create indexes required for query performance."""
        indexes = [
            IndexModel([("document_id", ASCENDING), ("extracted_at", ASCENDING)]),
            IndexModel([("document_id", ASCENDING)], name="idx_document_id"),
        ]
        await self._collection.create_indexes(indexes)

    async def save(self, content: ExtractedContentDocument) -> str:
        """Persist a new extracted content snapshot."""
        payload = content.to_dict()
        result = await self._collection.insert_one(payload)
        return str(result.inserted_id)

    async def bulk_save(self, contents: Iterable[ExtractedContentDocument]) -> List[str]:
        """Persist multiple snapshots in a single operation."""
        documents = [content.to_dict() for content in contents]
        if not documents:
            return []
        result = await self._collection.insert_many(documents)
        return [str(_id) for _id in result.inserted_ids]

    async def get_latest_by_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the most recent extracted content snapshot for a document."""
        return await self._collection.find_one(
            {"document_id": document_id},
            sort=[("extracted_at", -1)],
        )

    async def list_versions(self, document_id: str) -> List[Dict[str, Any]]:
        """List all stored versions for a given document."""
        cursor = self._collection.find({"document_id": document_id}).sort("extracted_at", ASCENDING)
        return [doc async for doc in cursor]

    async def delete_by_document(self, document_id: str) -> int:
        """Remove all snapshots for a document (e.g., GDPR deletion)."""
        result = await self._collection.delete_many({"document_id": document_id})
        return result.deleted_count
