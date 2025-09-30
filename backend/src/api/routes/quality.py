"""Quality router exposing metrics and summary endpoints with filters."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_async_session
from ...services.quality import get_quality_metrics_service
from ...services.audit import get_audit_service
from ...models.schemas.quality import (
    QualityMetricsResponse,
    QualityMetricsListResponse,
    QualitySummaryResponse,
    QualityThresholdsRequest,
    QualityThresholdsResponse,
    QualityReportRequest,
    QualityReportResponse
)
from ...config.settings import get_settings
from .auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/quality", tags=["quality"])
settings = get_settings()


@router.get(
    "/metrics/{document_id}",
    response_model=QualityMetricsResponse,
    summary="Get document quality metrics",
    description="Get detailed quality metrics for a specific document"
)
async def get_document_quality_metrics(
    document_id: UUID,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get quality metrics for a specific document."""
    quality_service = get_quality_metrics_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        metrics = await quality_service.get_document_metrics(
            session=session,
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document metrics not found"
            )
        
        # Log metrics access
        await audit_service.log_quality_event(
            session=session,
            action="METRICS_ACCESSED",
            document_id=document_id,
            user_id=current_user.id,
            details={"metrics_type": "document_specific"}
        )
        
        return QualityMetricsResponse(
            document_id=document_id,
            overall_quality_score=metrics.overall_quality_score,
            ocr_confidence=metrics.ocr_confidence,
            text_extraction_accuracy=metrics.text_extraction_accuracy,
            language_detection_confidence=metrics.language_detection_confidence,
            amharic_content_ratio=metrics.amharic_content_ratio,
            processing_time_seconds=metrics.processing_time_seconds,
            file_size_bytes=metrics.file_size_bytes,
            page_count=metrics.page_count,
            error_count=metrics.error_count,
            warning_count=metrics.warning_count,
            sla_compliance=metrics.sla_compliance,
            quality_checks={
                "text_legibility": metrics.text_legibility_score,
                "content_completeness": metrics.content_completeness_score,
                "format_preservation": metrics.format_preservation_score,
                "metadata_accuracy": metrics.metadata_accuracy_score
            },
            anomalies=metrics.detected_anomalies,
            recommendations=metrics.quality_recommendations,
            created_at=metrics.created_at,
            updated_at=metrics.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document quality metrics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document quality metrics"
        )


@router.get(
    "/metrics",
    response_model=QualityMetricsListResponse,
    summary="List quality metrics",
    description="Get list of quality metrics with optional filtering"
)
async def list_quality_metrics(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    quality_threshold: Optional[float] = Query(None, ge=0.0, le=1.0, description="Filter by minimum quality score"),
    sla_compliant: Optional[bool] = Query(None, description="Filter by SLA compliance"),
    date_from: Optional[str] = Query(None, description="Start date for filtering (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date for filtering (YYYY-MM-DD)"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get list of quality metrics with filtering."""
    quality_service = get_quality_metrics_service(settings)
    
    try:
        # Parse date filters
        date_from_dt = None
        date_to_dt = None
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_from format. Use YYYY-MM-DD"
                )
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_to format. Use YYYY-MM-DD"
                )
        
        metrics_list, total_count = await quality_service.get_user_metrics(
            session=session,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            quality_threshold=quality_threshold,
            sla_compliant=sla_compliant,
            date_from=date_from_dt,
            date_to=date_to_dt
        )
        
        metrics_responses = [
            QualityMetricsResponse(
                document_id=metric.document_id,
                overall_quality_score=metric.overall_quality_score,
                ocr_confidence=metric.ocr_confidence,
                text_extraction_accuracy=metric.text_extraction_accuracy,
                language_detection_confidence=metric.language_detection_confidence,
                amharic_content_ratio=metric.amharic_content_ratio,
                processing_time_seconds=metric.processing_time_seconds,
                file_size_bytes=metric.file_size_bytes,
                page_count=metric.page_count,
                error_count=metric.error_count,
                warning_count=metric.warning_count,
                sla_compliance=metric.sla_compliance,
                quality_checks={
                    "text_legibility": metric.text_legibility_score,
                    "content_completeness": metric.content_completeness_score,
                    "format_preservation": metric.format_preservation_score,
                    "metadata_accuracy": metric.metadata_accuracy_score
                },
                anomalies=metric.detected_anomalies,
                recommendations=metric.quality_recommendations,
                created_at=metric.created_at,
                updated_at=metric.updated_at
            )
            for metric in metrics_list
        ]
        
        return QualityMetricsListResponse(
            metrics=metrics_responses,
            total_count=total_count,
            skip=skip,
            limit=limit,
            filters_applied={
                "quality_threshold": quality_threshold,
                "sla_compliant": sla_compliant,
                "date_from": date_from,
                "date_to": date_to
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List quality metrics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quality metrics"
        )


@router.get(
    "/summary",
    response_model=QualitySummaryResponse,
    summary="Get quality summary",
    description="Get aggregated quality summary statistics"
)
async def get_quality_summary(
    date_from: Optional[str] = Query(None, description="Start date for summary (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date for summary (YYYY-MM-DD)"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get quality summary statistics."""
    quality_service = get_quality_metrics_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Parse date filters
        date_from_dt = None
        date_to_dt = None
        if date_from:
            try:
                date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_from format. Use YYYY-MM-DD"
                )
        if date_to:
            try:
                date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_to format. Use YYYY-MM-DD"
                )
        
        summary = await quality_service.get_quality_summary(
            session=session,
            user_id=current_user.id,
            date_from=date_from_dt,
            date_to=date_to_dt
        )
        
        # Log summary access
        await audit_service.log_quality_event(
            session=session,
            action="SUMMARY_ACCESSED",
            user_id=current_user.id,
            details={
                "date_from": date_from,
                "date_to": date_to,
                "documents_analyzed": summary.get("total_documents", 0)
            }
        )
        
        return QualitySummaryResponse(
            total_documents=summary.get("total_documents", 0),
            average_quality_score=summary.get("average_quality_score", 0.0),
            average_ocr_confidence=summary.get("average_ocr_confidence", 0.0),
            sla_compliance_rate=summary.get("sla_compliance_rate", 0.0),
            total_processing_time=summary.get("total_processing_time", 0.0),
            average_processing_time=summary.get("average_processing_time", 0.0),
            total_errors=summary.get("total_errors", 0),
            total_warnings=summary.get("total_warnings", 0),
            quality_distribution={
                "excellent": summary.get("quality_excellent", 0),  # >0.9
                "good": summary.get("quality_good", 0),           # 0.7-0.9
                "fair": summary.get("quality_fair", 0),           # 0.5-0.7
                "poor": summary.get("quality_poor", 0)            # <0.5
            },
            top_issues=summary.get("top_issues", []),
            improvement_recommendations=summary.get("recommendations", []),
            trends={
                "quality_trend": summary.get("quality_trend", "stable"),
                "performance_trend": summary.get("performance_trend", "stable"),
                "error_trend": summary.get("error_trend", "stable")
            },
            date_range={
                "from": date_from,
                "to": date_to
            },
            generated_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get quality summary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quality summary"
        )


@router.get(
    "/thresholds",
    response_model=QualityThresholdsResponse,
    summary="Get quality thresholds",
    description="Get current quality threshold configuration"
)
async def get_quality_thresholds(
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get current quality threshold settings."""
    quality_service = get_quality_metrics_service(settings)
    
    try:
        thresholds = await quality_service.get_quality_thresholds(
            session=session,
            user_id=current_user.id
        )
        
        return QualityThresholdsResponse(
            ocr_confidence_threshold=thresholds.get("ocr_confidence", 0.85),
            quality_score_threshold=thresholds.get("quality_score", 0.70),
            processing_time_sla_seconds=thresholds.get("processing_time_sla", 30.0),
            error_rate_threshold=thresholds.get("error_rate", 0.05),
            warning_rate_threshold=thresholds.get("warning_rate", 0.10),
            amharic_content_minimum=thresholds.get("amharic_content_min", 0.10),
            manual_review_threshold=thresholds.get("manual_review", 0.60),
            auto_reject_threshold=thresholds.get("auto_reject", 0.30),
            created_at=thresholds.get("created_at"),
            updated_at=thresholds.get("updated_at")
        )
        
    except Exception as e:
        logger.error(f"Get quality thresholds failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quality thresholds"
        )


@router.post(
    "/thresholds",
    response_model=QualityThresholdsResponse,
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],  # 10 threshold updates per minute
    summary="Update quality thresholds",
    description="Update quality threshold configuration"
)
async def update_quality_thresholds(
    request: QualityThresholdsRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Update quality threshold settings."""
    quality_service = get_quality_metrics_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Check user permissions
        if current_user.role not in ["admin", "moderator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update quality thresholds"
            )
        
        # Update thresholds
        updated_thresholds = await quality_service.update_quality_thresholds(
            session=session,
            user_id=current_user.id,
            ocr_confidence_threshold=request.ocr_confidence_threshold,
            quality_score_threshold=request.quality_score_threshold,
            processing_time_sla_seconds=request.processing_time_sla_seconds,
            error_rate_threshold=request.error_rate_threshold,
            warning_rate_threshold=request.warning_rate_threshold,
            amharic_content_minimum=request.amharic_content_minimum,
            manual_review_threshold=request.manual_review_threshold,
            auto_reject_threshold=request.auto_reject_threshold
        )
        
        # Log threshold update
        await audit_service.log_quality_event(
            session=session,
            action="THRESHOLDS_UPDATED",
            user_id=current_user.id,
            details={
                "ocr_confidence": request.ocr_confidence_threshold,
                "quality_score": request.quality_score_threshold,
                "processing_sla": request.processing_time_sla_seconds
            }
        )
        
        return QualityThresholdsResponse(
            ocr_confidence_threshold=updated_thresholds.ocr_confidence_threshold,
            quality_score_threshold=updated_thresholds.quality_score_threshold,
            processing_time_sla_seconds=updated_thresholds.processing_time_sla_seconds,
            error_rate_threshold=updated_thresholds.error_rate_threshold,
            warning_rate_threshold=updated_thresholds.warning_rate_threshold,
            amharic_content_minimum=updated_thresholds.amharic_content_minimum,
            manual_review_threshold=updated_thresholds.manual_review_threshold,
            auto_reject_threshold=updated_thresholds.auto_reject_threshold,
            created_at=updated_thresholds.created_at,
            updated_at=updated_thresholds.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update quality thresholds failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update quality thresholds"
        )


@router.post(
    "/report",
    response_model=QualityReportResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],  # 5 reports per minute
    summary="Generate quality report",
    description="Generate comprehensive quality report"
)
async def generate_quality_report(
    request: QualityReportRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Generate a comprehensive quality report."""
    quality_service = get_quality_metrics_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        report = await quality_service.generate_quality_report(
            session=session,
            user_id=current_user.id,
            report_type=request.report_type,
            date_from=request.date_from,
            date_to=request.date_to,
            include_charts=request.include_charts,
            include_recommendations=request.include_recommendations,
            document_ids=request.document_ids
        )
        
        # Log report generation
        await audit_service.log_quality_event(
            session=session,
            action="REPORT_GENERATED",
            user_id=current_user.id,
            details={
                "report_type": request.report_type,
                "date_range": f"{request.date_from} to {request.date_to}",
                "documents_included": len(request.document_ids) if request.document_ids else "all"
            }
        )
        
        return QualityReportResponse(
            report_id=report.id,
            report_type=request.report_type,
            status="completed",
            summary=report.summary,
            detailed_metrics=report.detailed_metrics,
            charts_data=report.charts_data if request.include_charts else None,
            recommendations=report.recommendations if request.include_recommendations else None,
            export_urls={
                "pdf": f"/api/v1/quality/report/{report.id}/download?format=pdf",
                "excel": f"/api/v1/quality/report/{report.id}/download?format=excel",
                "json": f"/api/v1/quality/report/{report.id}/download?format=json"
            },
            date_range={
                "from": request.date_from.isoformat() if request.date_from else None,
                "to": request.date_to.isoformat() if request.date_to else None
            },
            generated_at=report.created_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Generate quality report failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate quality report"
        )