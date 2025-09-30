"""Document ingestion service handling uploads and metadata persistence."""

from __future__ import annotations

import hashlib
import mimetypes
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, Dict, Optional, Protocol, Sequence

from src.config.settings import Settings
from src.db.models.document import DocumentStatus, DocumentType


@dataclass(slots=True)
class UploadPayload:
    """Normalized representation of an uploaded file."""

    filename: str
    content: bytes
    content_type: Optional[str] = None

    @property
    def size(self) -> int:
        return len(self.content)


@dataclass(slots=True)
class IngestedDocument:
    """Result returned after successful ingestion."""

    document_id: uuid.UUID
    filename: str
    storage_path: str
    content_hash: str
    status: DocumentStatus


class DocumentDTO(Protocol):
    """Minimal projection of a persisted document record."""

    id: uuid.UUID
    filename: str
    storage_path: str
    content_hash: str
    status: DocumentStatus


class DocumentRepository(Protocol):
    """Persistence gateway for document metadata."""

    async def hash_exists(self, content_hash: str) -> bool: ...

    async def create_document(
        self,
        *,
        document_id: uuid.UUID,
        owner_id: uuid.UUID,
        job_id: Optional[uuid.UUID],
        filename: str,
        document_type: DocumentType,
        file_size: int,
        mime_type: Optional[str],
        content_hash: str,
        storage_path: str,
        metadata: Dict[str, object],
    ) -> DocumentDTO: ...


class ObjectStorageClient(Protocol):
    """Object storage abstraction (e.g., MinIO/S3)."""

    async def upload(
        self,
        *,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: Optional[str],
    ) -> str: ...


class DocumentIngestionService:
    """Service orchestrating document ingestion workflows."""

    def __init__(
        self,
        *,
        settings: Settings,
        repository: DocumentRepository,
        storage_client: ObjectStorageClient,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._storage_client = storage_client

    async def ingest_documents(
        self,
        *,
        owner_id: uuid.UUID,
        files: Sequence[UploadPayload],
        job_id: Optional[uuid.UUID] = None,
    ) -> Sequence[IngestedDocument]:
        """Persist uploaded files and return metadata for downstream processing."""

        results: list[IngestedDocument] = []
        for file in files:
            self._enforce_size_limit(file)
            self._basic_sanity_check(file)

            content_hash = self._compute_hash(file.content)
            if await self._repository.hash_exists(content_hash):
                raise DuplicateDocumentError(file.filename)

            document_id = uuid.uuid4()
            object_name = self._build_object_name(owner_id, document_id, file.filename)
            storage_path = await self._upload_to_storage(
                object_name=object_name,
                payload=file,
            )

            document_type = self._determine_type(file.filename, file.content_type)
            record = await self._repository.create_document(
                document_id=document_id,
                owner_id=owner_id,
                job_id=job_id,
                filename=file.filename,
                document_type=document_type,
                file_size=file.size,
                mime_type=file.content_type,
                content_hash=content_hash,
                storage_path=storage_path,
                metadata={
                    "ingested_via": "DocumentIngestionService",
                    "hash_algorithm": "sha256",
                },
            )

            results.append(
                IngestedDocument(
                    document_id=record.id,
                    filename=record.filename,
                    storage_path=record.storage_path,
                    content_hash=record.content_hash,
                    status=record.status,
                )
            )

        return results

    def _enforce_size_limit(self, payload: UploadPayload) -> None:
        max_bytes = self._settings.max_file_size_mb * 1024 * 1024
        if payload.size > max_bytes:
            raise DocumentTooLargeError(payload.filename, payload.size, max_bytes)

    def _basic_sanity_check(self, payload: UploadPayload) -> None:
        if not payload.content:
            raise CorruptedDocumentError(payload.filename, "File content is empty")

    async def _upload_to_storage(
        self,
        *,
        object_name: str,
        payload: UploadPayload,
    ) -> str:
        try:
            return await self._storage_client.upload(
                bucket=self._settings.raw_documents_bucket,
                object_name=object_name,
                data=payload.content,
                content_type=payload.content_type,
            )
        except Exception as exc:  # pragma: no cover - infrastructure failure
            raise StorageError("Failed to upload document to object storage") from exc

    @staticmethod
    def _compute_hash(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _build_object_name(owner_id: uuid.UUID, document_id: uuid.UUID, filename: str) -> str:
        return f"{owner_id}/{document_id}/{filename}"

    @staticmethod
    def _determine_type(filename: str, content_type: Optional[str]) -> DocumentType:
        if content_type:
            if content_type.startswith("application/pdf"):
                return DocumentType.PDF
            if content_type.startswith("image/"):
                return DocumentType.IMAGE
            if content_type in {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            }:
                return DocumentType.WORD
            if content_type in {"text/csv", "application/csv"}:
                return DocumentType.CSV

        # Fallback to file extension mapping
        mime, _ = mimetypes.guess_type(filename)
        if mime:
            return DocumentIngestionService._determine_type(filename, mime)

        return DocumentType.WEB_CONTENT


class DocumentServiceError(RuntimeError):
    """Base error for document ingestion service."""


class DocumentTooLargeError(DocumentServiceError):
    def __init__(self, filename: str, actual_size: int, max_size: int) -> None:
        super().__init__(
            f"File '{filename}' exceeds size limit ({actual_size} bytes > {max_size} bytes)"
        )


class DuplicateDocumentError(DocumentServiceError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"Duplicate document detected for '{filename}'")


class CorruptedDocumentError(DocumentServiceError):
    def __init__(self, filename: str, reason: str) -> None:
        super().__init__(f"Document '{filename}' failed validation: {reason}")


class StorageError(DocumentServiceError):
    """Raised when persisting to object storage fails."""


__all__ = [
    "DocumentIngestionService",
    "UploadPayload",
    "IngestedDocument",
    "DocumentTooLargeError",
    "DuplicateDocumentError",
    "CorruptedDocumentError",
    "StorageError",
]
