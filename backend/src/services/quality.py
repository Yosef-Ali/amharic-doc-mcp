"""Quality metrics service for OCR accuracy, SLA compliance, and anomaly detection."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from ..db.models.document import Document
from ..db.models.processing_job import ProcessingJob, JobStatus
from ..db.models.processing_task import ProcessingTask, TaskStatus, AgentType
from ..db.models.quality_metric import QualityMetric, MetricType
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class QualityMetricsService:
    """Service for aggregating and analyzing quality metrics."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ocr_accuracy_threshold = 0.95
        self.sla_thresholds = {
            "urgent": 300,  # 5 minutes
            "standard": 1800,  # 30 minutes  
            "bulk": 14400  # 4 hours
        }
        
    async def record_ocr_accuracy(
        self,
        session: AsyncSession,
        document_id: UUID,
        character_accuracy: float,
        word_accuracy: float,
        confidence_score: float,
        processing_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QualityMetric:
        """Record OCR accuracy metrics for a document."""
        metric = QualityMetric(
            document_id=document_id,
            metric_type=MetricType.OCR_ACCURACY,
            value=character_accuracy,
            metadata={
                "character_accuracy": character_accuracy,
                "word_accuracy": word_accuracy,
                "confidence_score": confidence_score,
                "processing_time": processing_time,
                **(metadata or {})
            },
            recorded_at=datetime.utcnow()
        )
        
        session.add(metric)
        await session.commit()
        await session.refresh(metric)
        
        logger.info(f"Recorded OCR accuracy {character_accuracy:.3f} for document {document_id}")
        
        # Check for accuracy anomalies
        if character_accuracy < self.ocr_accuracy_threshold:
            await self._flag_accuracy_anomaly(session, document_id, character_accuracy)
            
        return metric
        
    async def record_processing_sla(
        self,
        session: AsyncSession,
        job_id: UUID,
        processing_time: float,
        priority: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QualityMetric:
        """Record SLA compliance metrics for a processing job."""
        sla_threshold = self.sla_thresholds.get(priority.lower(), 1800)
        is_compliant = processing_time <= sla_threshold
        
        # Get job details
        result = await session.execute(
            select(ProcessingJob)
            .options(selectinload(ProcessingJob.document))
            .where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise ValueError(f"Processing job {job_id} not found")
            
        metric = QualityMetric(
            document_id=job.document_id,
            metric_type=MetricType.PROCESSING_SLA,
            value=processing_time,
            metadata={
                "job_id": str(job_id),
                "priority": priority,
                "sla_threshold": sla_threshold,
                "is_compliant": is_compliant,
                "job_type": job.job_type,
                **(metadata or {})
            },
            recorded_at=datetime.utcnow()
        )
        
        session.add(metric)
        await session.commit()
        await session.refresh(metric)
        
        logger.info(f"Recorded SLA metric: {processing_time:.2f}s ({'compliant' if is_compliant else 'violation'}) for job {job_id}")
        
        # Flag SLA violations
        if not is_compliant:
            await self._flag_sla_violation(session, job_id, processing_time, sla_threshold)
            
        return metric
        
    async def get_document_quality_summary(
        self,
        session: AsyncSession,
        document_id: UUID
    ) -> Dict[str, Any]:
        """Get quality metrics summary for a specific document."""
        # Get OCR accuracy metrics
        ocr_result = await session.execute(
            select(QualityMetric)
            .where(and_(
                QualityMetric.document_id == document_id,
                QualityMetric.metric_type == MetricType.OCR_ACCURACY
            ))
            .order_by(QualityMetric.recorded_at.desc())
        )
        ocr_metrics = ocr_result.scalars().all()
        
        # Get SLA metrics
        sla_result = await session.execute(
            select(QualityMetric)
            .where(and_(
                QualityMetric.document_id == document_id,
                QualityMetric.metric_type == MetricType.PROCESSING_SLA
            ))
            .order_by(QualityMetric.recorded_at.desc())
        )
        sla_metrics = sla_result.scalars().all()
        
        # Calculate OCR summary
        ocr_summary = {}
        if ocr_metrics:
            latest_ocr = ocr_metrics[0]
            ocr_summary = {
                "character_accuracy": latest_ocr.metadata.get("character_accuracy", 0.0),
                "word_accuracy": latest_ocr.metadata.get("word_accuracy", 0.0),
                "confidence_score": latest_ocr.metadata.get("confidence_score", 0.0),
                "processing_time": latest_ocr.metadata.get("processing_time", 0.0),
                "meets_threshold": latest_ocr.value >= self.ocr_accuracy_threshold
            }
            
        # Calculate SLA summary
        sla_summary = {}
        if sla_metrics:
            latest_sla = sla_metrics[0]
            sla_summary = {
                "processing_time": latest_sla.value,
                "is_compliant": latest_sla.metadata.get("is_compliant", False),
                "priority": latest_sla.metadata.get("priority", "standard"),
                "sla_threshold": latest_sla.metadata.get("sla_threshold", 1800)
            }
            
        return {
            "document_id": str(document_id),
            "ocr_metrics": ocr_summary,
            "sla_metrics": sla_summary,
            "total_metrics_recorded": len(ocr_metrics) + len(sla_metrics),
            "last_updated": max(
                (ocr_metrics[0].recorded_at if ocr_metrics else datetime.min),
                (sla_metrics[0].recorded_at if sla_metrics else datetime.min)
            ).isoformat() if (ocr_metrics or sla_metrics) else None
        }
        
    async def get_system_quality_report(
        self,
        session: AsyncSession,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get system-wide quality metrics report."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # OCR accuracy statistics
        ocr_result = await session.execute(
            select(QualityMetric)
            .where(and_(
                QualityMetric.metric_type == MetricType.OCR_ACCURACY,
                QualityMetric.recorded_at >= start_date
            ))
        )
        ocr_metrics = ocr_result.scalars().all()
        
        ocr_stats = {}
        if ocr_metrics:
            accuracies = [m.value for m in ocr_metrics]
            ocr_stats = {
                "total_documents": len(ocr_metrics),
                "average_accuracy": mean(accuracies),
                "min_accuracy": min(accuracies),
                "max_accuracy": max(accuracies),
                "std_deviation": stdev(accuracies) if len(accuracies) > 1 else 0,
                "below_threshold_count": len([a for a in accuracies if a < self.ocr_accuracy_threshold]),
                "compliance_rate": len([a for a in accuracies if a >= self.ocr_accuracy_threshold]) / len(accuracies)
            }
            
        # SLA compliance statistics
        sla_result = await session.execute(
            select(QualityMetric)
            .where(and_(
                QualityMetric.metric_type == MetricType.PROCESSING_SLA,
                QualityMetric.recorded_at >= start_date
            ))
        )
        sla_metrics = sla_result.scalars().all()
        
        sla_stats = {}
        if sla_metrics:
            processing_times = [m.value for m in sla_metrics]
            compliant_count = len([m for m in sla_metrics if m.metadata.get("is_compliant", False)])
            
            sla_stats = {
                "total_jobs": len(sla_metrics),
                "average_processing_time": mean(processing_times),
                "min_processing_time": min(processing_times),
                "max_processing_time": max(processing_times),
                "compliant_jobs": compliant_count,
                "violation_jobs": len(sla_metrics) - compliant_count,
                "compliance_rate": compliant_count / len(sla_metrics),
                "by_priority": self._calculate_sla_by_priority(sla_metrics)
            }
            
        # Anomaly detection
        anomalies = await self._detect_quality_anomalies(session, start_date)
        
        return {
            "report_period_days": days,
            "report_generated_at": datetime.utcnow().isoformat(),
            "ocr_statistics": ocr_stats,
            "sla_statistics": sla_stats,
            "anomalies_detected": len(anomalies),
            "anomaly_summary": anomalies
        }
        
    async def get_quality_trends(
        self,
        session: AsyncSession,
        metric_type: MetricType,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get quality trends over time."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        result = await session.execute(
            select(QualityMetric)
            .where(and_(
                QualityMetric.metric_type == metric_type,
                QualityMetric.recorded_at >= start_date
            ))
            .order_by(QualityMetric.recorded_at)
        )
        metrics = result.scalars().all()
        
        # Group by day
        daily_trends = {}
        for metric in metrics:
            day_key = metric.recorded_at.date().isoformat()
            if day_key not in daily_trends:
                daily_trends[day_key] = []
            daily_trends[day_key].append(metric.value)
            
        # Calculate daily statistics
        trends = []
        for day, values in daily_trends.items():
            trends.append({
                "date": day,
                "count": len(values),
                "average": mean(values),
                "min": min(values),
                "max": max(values),
                "std_dev": stdev(values) if len(values) > 1 else 0
            })
            
        return trends
        
    async def _flag_accuracy_anomaly(
        self,
        session: AsyncSession,
        document_id: UUID,
        accuracy: float
    ) -> None:
        """Flag OCR accuracy anomaly."""
        anomaly_metric = QualityMetric(
            document_id=document_id,
            metric_type=MetricType.ANOMALY_DETECTION,
            value=accuracy,
            metadata={
                "anomaly_type": "low_ocr_accuracy",
                "threshold": self.ocr_accuracy_threshold,
                "severity": "high" if accuracy < 0.8 else "medium"
            },
            recorded_at=datetime.utcnow()
        )
        
        session.add(anomaly_metric)
        await session.commit()
        
        logger.warning(f"OCR accuracy anomaly detected: {accuracy:.3f} for document {document_id}")
        
    async def _flag_sla_violation(
        self,
        session: AsyncSession,
        job_id: UUID,
        processing_time: float,
        threshold: float
    ) -> None:
        """Flag SLA violation."""
        # Get job to find document_id
        result = await session.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if job:
            violation_metric = QualityMetric(
                document_id=job.document_id,
                metric_type=MetricType.ANOMALY_DETECTION,
                value=processing_time,
                metadata={
                    "anomaly_type": "sla_violation",
                    "job_id": str(job_id),
                    "threshold": threshold,
                    "overrun": processing_time - threshold,
                    "severity": "high" if processing_time > threshold * 2 else "medium"
                },
                recorded_at=datetime.utcnow()
            )
            
            session.add(violation_metric)
            await session.commit()
            
            logger.warning(f"SLA violation detected: {processing_time:.2f}s (threshold: {threshold}s) for job {job_id}")
            
    def _calculate_sla_by_priority(self, sla_metrics: List[QualityMetric]) -> Dict[str, Any]:
        """Calculate SLA statistics by priority."""
        by_priority = {}
        
        for metric in sla_metrics:
            priority = metric.metadata.get("priority", "standard")
            if priority not in by_priority:
                by_priority[priority] = {
                    "total": 0,
                    "compliant": 0,
                    "processing_times": []
                }
                
            by_priority[priority]["total"] += 1
            if metric.metadata.get("is_compliant", False):
                by_priority[priority]["compliant"] += 1
            by_priority[priority]["processing_times"].append(metric.value)
            
        # Calculate statistics for each priority
        for priority, stats in by_priority.items():
            times = stats["processing_times"]
            stats["compliance_rate"] = stats["compliant"] / stats["total"]
            stats["average_time"] = mean(times)
            stats["min_time"] = min(times)
            stats["max_time"] = max(times)
            del stats["processing_times"]  # Remove raw data
            
        return by_priority
        
    async def _detect_quality_anomalies(
        self,
        session: AsyncSession,
        start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Detect and summarize quality anomalies."""
        result = await session.execute(
            select(QualityMetric)
            .where(and_(
                QualityMetric.metric_type == MetricType.ANOMALY_DETECTION,
                QualityMetric.recorded_at >= start_date
            ))
            .order_by(QualityMetric.recorded_at.desc())
        )
        anomalies = result.scalars().all()
        
        anomaly_summary = []
        for anomaly in anomalies:
            anomaly_summary.append({
                "type": anomaly.metadata.get("anomaly_type"),
                "severity": anomaly.metadata.get("severity"),
                "value": anomaly.value,
                "threshold": anomaly.metadata.get("threshold"),
                "document_id": str(anomaly.document_id),
                "detected_at": anomaly.recorded_at.isoformat(),
                "metadata": {k: v for k, v in anomaly.metadata.items() 
                           if k not in ["anomaly_type", "severity", "threshold"]}
            })
            
        return anomaly_summary


# Global quality metrics service instance
_quality_service: Optional[QualityMetricsService] = None


def get_quality_service(settings: Settings) -> QualityMetricsService:
    """Get the global quality metrics service instance."""
    global _quality_service
    if _quality_service is None:
        _quality_service = QualityMetricsService(settings)
    return _quality_service