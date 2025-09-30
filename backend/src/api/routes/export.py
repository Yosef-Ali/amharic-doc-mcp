"""Export router enabling export requests, template management, and signature configuration."""

from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_limiter.depends import RateLimiter
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from ...db.database import get_async_session
from ...services.export import get_export_service
from ...services.audit import get_audit_service
from ...models.schemas.export import (
    ExportRequest,
    ExportResponse,
    ExportTemplateRequest,
    ExportTemplateResponse,
    ExportTemplateListResponse,
    ExportStatusResponse,
    SignatureConfigRequest,
    SignatureConfigResponse
)
from ...config.settings import get_settings
from .auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/export", tags=["export"])
settings = get_settings()


@router.post(
    "/documents/{document_id}",
    response_model=ExportResponse,
    dependencies=[Depends(RateLimiter(times=20, seconds=60))],  # 20 exports per minute
    summary="Export document",
    description="Export a document to specified format with optional template and signature"
)
async def export_document(
    document_id: UUID,
    request: ExportRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Export document to specified format."""
    export_service = get_export_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Validate export format
        supported_formats = ["pdf", "docx", "html", "markdown", "json", "txt"]
        if request.format.lower() not in supported_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format. Supported formats: {supported_formats}"
            )
            
        # Create export job
        export_job = await export_service.create_export_job(
            session=session,
            document_id=document_id,
            user_id=current_user.id,
            export_format=request.format,
            template_id=request.template_id,
            options=request.options or {},
            include_metadata=request.include_metadata,
            watermark_config=request.watermark_config,
            signature_config=request.signature_config
        )
        
        # Log export event
        await audit_service.log_export_event(
            session=session,
            action="EXPORT_REQUESTED",
            document_id=document_id,
            user_id=current_user.id,
            details={
                "format": request.format,
                "template_id": str(request.template_id) if request.template_id else None,
                "include_metadata": request.include_metadata,
                "job_id": str(export_job.id)
            }
        )
        
        return ExportResponse(
            success=True,
            export_id=export_job.id,
            document_id=document_id,
            format=request.format,
            status="processing",
            created_at=export_job.created_at,
            download_url=f"/api/v1/export/download/{export_job.id}",
            estimated_completion=export_job.estimated_completion
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Document export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document export failed"
        )


@router.get(
    "/status/{export_id}",
    response_model=ExportStatusResponse,
    summary="Get export status",
    description="Get status of an export job"
)
async def get_export_status(
    export_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get export job status."""
    export_service = get_export_service(settings)
    
    try:
        export_job = await export_service.get_export_job(
            session=session,
            export_id=export_id,
            user_id=current_user.id
        )
        
        if not export_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found"
            )
            
        return ExportStatusResponse(
            export_id=export_job.id,
            document_id=export_job.document_id,
            status=export_job.status,
            format=export_job.export_format,
            progress_percentage=export_job.progress,
            created_at=export_job.created_at,
            updated_at=export_job.updated_at,
            completed_at=export_job.completed_at,
            download_url=f"/api/v1/export/download/{export_job.id}" if export_job.status == "completed" else None,
            error_message=export_job.error_message,
            file_size=export_job.output_file_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get export status failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get export status"
        )


@router.get(
    "/download/{export_id}",
    summary="Download exported file",
    description="Download the exported document file"
)
async def download_exported_file(
    export_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Download exported document file."""
    export_service = get_export_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Get export job and validate ownership
        export_job = await export_service.get_export_job(
            session=session,
            export_id=export_id,
            user_id=current_user.id
        )
        
        if not export_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found"
            )
            
        if export_job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Export not ready for download. Status: {export_job.status}"
            )
            
        # Get file data
        file_data, filename = await export_service.get_export_file(
            session=session,
            export_id=export_id
        )
        
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found"
            )
            
        # Log download event
        await audit_service.log_export_event(
            session=session,
            action="EXPORT_DOWNLOADED",
            document_id=export_job.document_id,
            user_id=current_user.id,
            details={
                "export_id": str(export_id),
                "filename": filename,
                "file_size": len(file_data)
            }
        )
        
        # Determine content type based on format
        content_type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "html": "text/html",
            "markdown": "text/markdown",
            "json": "application/json",
            "txt": "text/plain"
        }
        
        content_type = content_type_map.get(export_job.export_format.lower(), "application/octet-stream")
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Content-Length": str(len(file_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export file download failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download export file"
        )


@router.get(
    "/templates",
    response_model=ExportTemplateListResponse,
    summary="List export templates",
    description="Get list of available export templates"
)
async def list_export_templates(
    skip: int = Query(0, ge=0, description="Number of templates to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of templates to return"),
    format_filter: Optional[str] = Query(None, description="Filter by export format"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get list of export templates."""
    export_service = get_export_service(settings)
    
    try:
        templates, total_count = await export_service.get_export_templates(
            session=session,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            format_filter=format_filter
        )
        
        template_responses = [
            ExportTemplateResponse(
                id=template.id,
                name=template.name,
                description=template.description,
                format=template.format,
                config=template.config,
                is_default=template.is_default,
                is_public=template.is_public,
                created_by=template.created_by,
                created_at=template.created_at,
                updated_at=template.updated_at
            )
            for template in templates
        ]
        
        return ExportTemplateListResponse(
            templates=template_responses,
            total_count=total_count,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"List export templates failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve export templates"
        )


@router.post(
    "/templates",
    response_model=ExportTemplateResponse,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],  # 10 template creations per minute
    summary="Create export template",
    description="Create a new export template"
)
async def create_export_template(
    request: ExportTemplateRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new export template."""
    export_service = get_export_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        template = await export_service.create_export_template(
            session=session,
            name=request.name,
            description=request.description,
            format=request.format,
            config=request.config,
            is_public=request.is_public,
            created_by=current_user.id
        )
        
        # Log template creation
        await audit_service.log_export_event(
            session=session,
            action="TEMPLATE_CREATED",
            user_id=current_user.id,
            details={
                "template_id": str(template.id),
                "name": request.name,
                "format": request.format,
                "is_public": request.is_public
            }
        )
        
        return ExportTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            format=template.format,
            config=template.config,
            is_default=template.is_default,
            is_public=template.is_public,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Create export template failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export template"
        )


@router.get(
    "/templates/{template_id}",
    response_model=ExportTemplateResponse,
    summary="Get export template",
    description="Get export template by ID"
)
async def get_export_template(
    template_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get export template by ID."""
    export_service = get_export_service(settings)
    
    try:
        template = await export_service.get_export_template(
            session=session,
            template_id=template_id,
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export template not found"
            )
            
        return ExportTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            format=template.format,
            config=template.config,
            is_default=template.is_default,
            is_public=template.is_public,
            created_by=template.created_by,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get export template failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve export template"
        )


@router.delete(
    "/templates/{template_id}",
    summary="Delete export template",
    description="Delete an export template"
)
async def delete_export_template(
    template_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete export template."""
    export_service = get_export_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Get template first to verify ownership
        template = await export_service.get_export_template(
            session=session,
            template_id=template_id,
            user_id=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export template not found"
            )
            
        # Check ownership for non-public templates
        if not template.is_public and template.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete this template"
            )
            
        # Delete template
        success = await export_service.delete_export_template(
            session=session,
            template_id=template_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete export template"
            )
            
        # Log template deletion
        await audit_service.log_export_event(
            session=session,
            action="TEMPLATE_DELETED",
            user_id=current_user.id,
            details={
                "template_id": str(template_id),
                "name": template.name,
                "format": template.format
            }
        )
        
        return {
            "success": True,
            "message": "Export template deleted successfully",
            "template_id": str(template_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete export template failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete export template"
        )


@router.post(
    "/signature/config",
    response_model=SignatureConfigResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],  # 5 config updates per minute
    summary="Configure digital signature",
    description="Configure digital signature settings for exports"
)
async def configure_signature(
    request: SignatureConfigRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Configure digital signature settings."""
    export_service = get_export_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        config = await export_service.configure_signature(
            session=session,
            user_id=current_user.id,
            certificate_path=request.certificate_path,
            private_key_path=request.private_key_path,
            signature_reason=request.signature_reason,
            signature_location=request.signature_location,
            visible_signature=request.visible_signature,
            signature_position=request.signature_position
        )
        
        # Log signature configuration
        await audit_service.log_export_event(
            session=session,
            action="SIGNATURE_CONFIGURED",
            user_id=current_user.id,
            details={
                "signature_reason": request.signature_reason,
                "visible_signature": request.visible_signature,
                "has_certificate": bool(request.certificate_path)
            }
        )
        
        return SignatureConfigResponse(
            success=True,
            config_id=config.id,
            signature_reason=config.signature_reason,
            signature_location=config.signature_location,
            visible_signature=config.visible_signature,
            signature_position=config.signature_position,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Configure signature failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure digital signature"
        )