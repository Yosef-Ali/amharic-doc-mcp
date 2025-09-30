"""Processing router for job creation, status queries, cancellation, and manual review promotion."""

from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_async_session
from ...services.processing import get_processing_orchestrator
from ...services.audit import get_audit_service
from ...models.schemas.processing import (
    ProcessingJobCreateRequest,
    ProcessingJobResponse,
    ProcessingJobListResponse,
    ProcessingStatusResponse,
    ProcessingTaskResponse,
    JobCancellationResponse,
    ManualReviewPromotionRequest,
    ManualReviewPromotionResponse
)
from ...config.settings import get_settings
from .auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/processing", tags=["processing"])
settings = get_settings()


@router.post(
    "/jobs",
    response_model=ProcessingJobResponse,
    dependencies=[Depends(RateLimiter(times=20, seconds=60))],  # 20 jobs per minute
    summary="Create processing job",
    description="Create a new processing job for document analysis"
)
async def create_processing_job(
    request: ProcessingJobCreateRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new processing job."""
    processing_service = get_processing_orchestrator(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Create the processing job
        job = await processing_service.create_job(
            session=session,
            document_id=request.document_id,
            job_type=request.job_type,
            priority=request.priority,
            metadata=request.metadata or {}
        )
        
        # Log job creation event
        await audit_service.log_processing_event(
            session=session,
            action="JOB_CREATED",
            job_id=job.id,
            user_id=current_user.id,
            details={
                "document_id": str(request.document_id),
                "job_type": request.job_type,
                "priority": request.priority.value if request.priority else "MEDIUM"
            }
        )
        
        return ProcessingJobResponse(
            id=job.id,
            document_id=job.document_id,
            job_type=job.job_type,
            priority=job.priority,
            status=job.status,
            metadata=job.metadata,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            user_id=job.user_id
        )
        
    except ValueError as e:
        # Handle queue overflow or validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Processing job creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create processing job"
        )


@router.get(
    "/jobs",
    response_model=ProcessingJobListResponse,
    summary="List processing jobs",
    description="Get list of processing jobs with optional filtering"
)
async def list_processing_jobs(
    skip: int = Query(0, ge=0, description="Number of jobs to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of jobs to return"),
    status_filter: Optional[str] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get list of user's processing jobs."""
    processing_service = get_processing_orchestrator(settings)
    
    try:
        jobs, total_count = await processing_service.get_user_jobs(
            session=session,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            status_filter=status_filter,
            job_type_filter=job_type
        )
        
        job_responses = [
            ProcessingJobResponse(
                id=job.id,
                document_id=job.document_id,
                job_type=job.job_type,
                priority=job.priority,
                status=job.status,
                metadata=job.metadata,
                created_at=job.created_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                error_message=job.error_message,
                user_id=job.user_id
            )
            for job in jobs
        ]
        
        return ProcessingJobListResponse(
            jobs=job_responses,
            total_count=total_count,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"List processing jobs failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processing jobs"
        )


@router.get(
    "/jobs/{job_id}",
    response_model=ProcessingJobResponse,
    summary="Get processing job",
    description="Get processing job details by ID"
)
async def get_processing_job(
    job_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get processing job by ID."""
    processing_service = get_processing_orchestrator(settings)
    audit_service = get_audit_service(settings)
    
    try:
        job = await processing_service.get_job_by_id(
            session=session,
            job_id=job_id,
            user_id=current_user.id
        )
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found"
            )
            
        # Log view event
        await audit_service.log_processing_event(
            session=session,
            action="JOB_VIEWED",
            job_id=job_id,
            user_id=current_user.id,
            details={"job_type": job.job_type}
        )
        
        return ProcessingJobResponse(
            id=job.id,
            document_id=job.document_id,
            job_type=job.job_type,
            priority=job.priority,
            status=job.status,
            metadata=job.metadata,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            user_id=job.user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get processing job failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processing job"
        )


@router.get(
    "/jobs/{job_id}/tasks",
    response_model=List[ProcessingTaskResponse],
    summary="Get job tasks",
    description="Get all tasks associated with a processing job"
)
async def get_job_tasks(
    job_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get all tasks for a processing job."""
    processing_service = get_processing_orchestrator(settings)
    
    try:
        # Verify job ownership
        job = await processing_service.get_job_by_id(
            session=session,
            job_id=job_id,
            user_id=current_user.id
        )
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found"
            )
            
        tasks = await processing_service.get_job_tasks(
            session=session,
            job_id=job_id
        )
        
        return [
            ProcessingTaskResponse(
                id=task.id,
                job_id=task.job_id,
                task_type=task.task_type,
                status=task.status,
                agent_type=task.agent_type,
                input_data=task.input_data,
                output_data=task.output_data,
                confidence_score=task.confidence_score,
                retry_count=task.retry_count,
                error_message=task.error_message,
                created_at=task.created_at,
                updated_at=task.updated_at,
                started_at=task.started_at,
                completed_at=task.completed_at
            )
            for task in tasks
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get job tasks failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job tasks"
        )


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobCancellationResponse,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],  # 10 cancellations per minute
    summary="Cancel processing job",
    description="Cancel a running or queued processing job"
)
async def cancel_processing_job(
    job_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Cancel a processing job."""
    processing_service = get_processing_orchestrator(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Verify job ownership and get current status
        job = await processing_service.get_job_by_id(
            session=session,
            job_id=job_id,
            user_id=current_user.id
        )
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found"
            )
            
        # Attempt cancellation
        success = await processing_service.cancel_job(
            session=session,
            job_id=job_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job cannot be cancelled in its current state"
            )
            
        # Log cancellation event
        await audit_service.log_processing_event(
            session=session,
            action="JOB_CANCELLED",
            job_id=job_id,
            user_id=current_user.id,
            details={
                "job_type": job.job_type,
                "previous_status": job.status
            }
        )
        
        return JobCancellationResponse(
            success=True,
            message="Processing job cancelled successfully",
            job_id=job_id,
            cancelled_at=job.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job cancellation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel processing job"
        )


@router.post(
    "/jobs/{job_id}/promote",
    response_model=ManualReviewPromotionResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],  # 5 promotions per minute
    summary="Promote job to manual review",
    description="Promote a job to manual review queue"
)
async def promote_to_manual_review(
    job_id: UUID,
    request: ManualReviewPromotionRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Promote a job to manual review queue."""
    processing_service = get_processing_orchestrator(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Verify job ownership
        job = await processing_service.get_job_by_id(
            session=session,
            job_id=job_id,
            user_id=current_user.id
        )
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found"
            )
            
        # Promote to manual review
        success = await processing_service.promote_to_manual_review(
            session=session,
            job_id=job_id,
            user_id=current_user.id,
            reason=request.reason,
            reviewer_notes=request.reviewer_notes
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job cannot be promoted to manual review"
            )
            
        # Log promotion event
        await audit_service.log_processing_event(
            session=session,
            action="JOB_PROMOTED_TO_REVIEW",
            job_id=job_id,
            user_id=current_user.id,
            details={
                "reason": request.reason,
                "reviewer_notes": request.reviewer_notes,
                "job_type": job.job_type
            }
        )
        
        return ManualReviewPromotionResponse(
            success=True,
            message="Job promoted to manual review queue",
            job_id=job_id,
            review_queue_position=await processing_service.get_review_queue_position(
                session=session,
                job_id=job_id
            ),
            promoted_at=job.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual review promotion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to promote job to manual review"
        )


@router.get(
    "/status",
    response_model=ProcessingStatusResponse,
    summary="Get processing system status",
    description="Get overall processing system status and queue information"
)
async def get_processing_status(
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get processing system status."""
    processing_service = get_processing_orchestrator(settings)
    
    try:
        status_info = await processing_service.get_processing_statistics(session)
        
        return ProcessingStatusResponse(
            system_status="healthy",
            total_jobs=status_info["total"],
            queued_jobs=status_info["queued"],
            running_jobs=status_info["running"],
            completed_jobs=status_info["completed"],
            failed_jobs=status_info["failed"],
            manual_review_queue=status_info.get("manual_review", 0),
            average_processing_time=status_info.get("avg_processing_time", 0.0),
            queue_health=status_info.get("queue_health", "unknown")
        )
        
    except Exception as e:
        logger.error(f"Get processing status failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processing status"
        )