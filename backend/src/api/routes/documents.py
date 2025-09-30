"""Documents router for file upload, metadata retrieval, and deletion."""

from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_async_session
from ...services.documents import get_document_service
from ...services.processing import get_processing_orchestrator
from ...services.audit import get_audit_service
from ...models.schemas.documents import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentMetadataResponse
)
from ...config.settings import get_settings
from .auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
settings = get_settings()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],  # 10 uploads per minute
    summary="Upload document",
    description="Upload a document for processing"
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    metadata: Optional[str] = Form(None, description="JSON metadata for the document"),
    start_processing: bool = Form(True, description="Whether to start processing immediately"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Upload a document file."""
    document_service = get_document_service(settings)
    processing_service = get_processing_orchestrator(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required"
            )
            
        # Check file size
        if file.size and file.size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
            )
            
        # Read file data
        file_data = await file.read()
        
        # Parse metadata if provided
        doc_metadata = {}
        if metadata:
            import json
            try:
                doc_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON metadata"
                )
                
        # Upload document
        document = await document_service.upload_document(
            session=session,
            file_data=file_data,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            user_id=current_user.id,
            metadata=doc_metadata
        )
        
        # Log upload event
        await audit_service.log_document_event(
            session=session,
            action="CREATED",
            document_id=document.id,
            user_id=current_user.id,
            details={
                "filename": file.filename,
                "size": len(file_data),
                "content_type": file.content_type
            }
        )
        
        # Start processing if requested
        job = None
        if start_processing:
            job = await processing_service.create_job(
                session=session,
                document_id=document.id,
                job_type="full_processing",
                metadata={"source": "api_upload"}
            )
            
        return DocumentUploadResponse(
            success=True,
            document_id=document.id,
            filename=document.filename,
            file_size=document.file_size,
            content_type=document.content_type,
            processing_job_id=job.id if job else None,
            processing_started=job is not None,
            upload_timestamp=document.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed"
        )


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List documents",
    description="Get list of documents with optional filtering"
)
async def list_documents(
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of documents to return"),
    status_filter: Optional[str] = Query(None, description="Filter by document status"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get list of user's documents."""
    document_service = get_document_service(settings)
    
    try:
        documents, total_count = await document_service.get_user_documents(
            session=session,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            status_filter=status_filter,
            content_type_filter=content_type
        )
        
        document_responses = [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                content_type=doc.content_type,
                file_size=doc.file_size,
                status=doc.status,
                metadata=doc.metadata,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                user_id=doc.user_id
            )
            for doc in documents
        ]
        
        return DocumentListResponse(
            documents=document_responses,
            total_count=total_count,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"List documents failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document",
    description="Get document details by ID"
)
async def get_document(
    document_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get document by ID."""
    document_service = get_document_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        document = await document_service.get_document_by_id(
            session=session,
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        # Log view event
        await audit_service.log_document_event(
            session=session,
            action="VIEWED",
            document_id=document.id,
            user_id=current_user.id,
            details={"filename": document.filename}
        )
        
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            content_type=document.content_type,
            file_size=document.file_size,
            status=document.status,
            metadata=document.metadata,
            created_at=document.created_at,
            updated_at=document.updated_at,
            user_id=document.user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )


@router.get(
    "/{document_id}/metadata",
    response_model=DocumentMetadataResponse,
    summary="Get document metadata",
    description="Get detailed metadata for a document"
)
async def get_document_metadata(
    document_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get document metadata including processing results."""
    document_service = get_document_service(settings)
    
    try:
        metadata = await document_service.get_document_metadata(
            session=session,
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        return DocumentMetadataResponse(
            document_id=document_id,
            filename=metadata["filename"],
            content_type=metadata["content_type"],
            file_size=metadata["file_size"],
            status=metadata["status"],
            metadata=metadata.get("metadata", {}),
            processing_info=metadata.get("processing_info", {}),
            quality_metrics=metadata.get("quality_metrics", {}),
            created_at=metadata["created_at"],
            updated_at=metadata.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document metadata failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document metadata"
        )


@router.delete(
    "/{document_id}",
    summary="Delete document",
    description="Delete a document and all associated data"
)
async def delete_document(
    document_id: UUID,
    permanent: bool = Query(False, description="Whether to permanently delete (cannot be undone)"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a document."""
    document_service = get_document_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Get document first to verify ownership
        document = await document_service.get_document_by_id(
            session=session,
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        # Delete document
        success = await document_service.delete_document(
            session=session,
            document_id=document_id,
            user_id=current_user.id,
            permanent=permanent
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete document"
            )
            
        # Log deletion event
        await audit_service.log_document_event(
            session=session,
            action="DELETED",
            document_id=document_id,
            user_id=current_user.id,
            details={
                "filename": document.filename,
                "permanent": permanent
            }
        )
        
        return {
            "success": True,
            "message": f"Document {'permanently deleted' if permanent else 'moved to trash'}",
            "document_id": str(document_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )


@router.post(
    "/{document_id}/reprocess",
    summary="Reprocess document",
    description="Start reprocessing of an existing document"
)
async def reprocess_document(
    document_id: UUID,
    job_type: str = Query("full_processing", description="Type of processing job"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Reprocess an existing document."""
    document_service = get_document_service(settings)
    processing_service = get_processing_orchestrator(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Verify document exists and belongs to user
        document = await document_service.get_document_by_id(
            session=session,
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        # Create new processing job
        job = await processing_service.create_job(
            session=session,
            document_id=document_id,
            job_type=job_type,
            metadata={"source": "api_reprocess", "reprocess": True}
        )
        
        # Log reprocess event
        await audit_service.log_document_event(
            session=session,
            action="PROCESSED",
            document_id=document_id,
            user_id=current_user.id,
            details={
                "job_type": job_type,
                "job_id": str(job.id)
            }
        )
        
        return {
            "success": True,
            "message": "Document reprocessing started",
            "document_id": str(document_id),
            "job_id": str(job.id),
            "job_type": job_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document reprocess failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start document reprocessing"
        )


@router.get(
    "/{document_id}/download",
    summary="Download document",
    description="Download the original document file"
)
async def download_document(
    document_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Download original document file."""
    document_service = get_document_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Get document and file data
        document, file_data = await document_service.get_document_file(
            session=session,
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not document or not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found"
            )
            
        # Log download event
        await audit_service.log_document_event(
            session=session,
            action="VIEWED",
            document_id=document_id,
            user_id=current_user.id,
            details={
                "action": "download",
                "filename": document.filename
            }
        )
        
        from fastapi.responses import Response
        
        return Response(
            content=file_data,
            media_type=document.content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{document.filename}\"",
                "Content-Length": str(len(file_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document download failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download document"
        )