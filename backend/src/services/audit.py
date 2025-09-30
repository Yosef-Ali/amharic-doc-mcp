"""Audit trail service for persisting immutable events and exposing review queries."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, text
from sqlalchemy.orm import selectinload

from ..db.models.audit_log import AuditLog, AuditAction, AuditResource
from ..db.models.user import User
from ..db.models.document import Document
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditService:
    """Service for managing audit trails and compliance logging."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.retention_days = 2555  # 7 years for compliance (GDPR/Ethiopian law)
        
    async def log_event(
        self,
        session: AsyncSession,
        action: AuditAction,
        resource_type: AuditResource,
        resource_id: UUID,
        user_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: AuditSeverity = AuditSeverity.LOW,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditLog:
        """Log an audit event."""
        # Sanitize and validate details
        sanitized_details = self._sanitize_details(details or {})
        
        # Create audit log entry
        audit_log = AuditLog(
            id=uuid4(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            details=sanitized_details,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            severity=severity.value,
            timestamp=datetime.utcnow()
        )
        
        session.add(audit_log)
        await session.commit()
        await session.refresh(audit_log)
        
        # Log to application logger based on severity
        log_message = f"Audit: {action.value} on {resource_type.value} {resource_id}"
        if user_id:
            log_message += f" by user {user_id}"
            
        if severity == AuditSeverity.CRITICAL:
            logger.critical(log_message)
        elif severity == AuditSeverity.HIGH:
            logger.error(log_message)
        elif severity == AuditSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
            
        return audit_log
        
    async def log_authentication_event(
        self,
        session: AsyncSession,
        action: str,  # login, logout, failed_login, etc.
        user_id: Optional[UUID],
        success: bool,
        ip_address: str,
        user_agent: str,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log authentication-related events."""
        severity = AuditSeverity.MEDIUM if not success else AuditSeverity.LOW
        
        audit_details = {
            "success": success,
            "authentication_method": details.get("method", "local") if details else "local",
            **(details or {})
        }
        
        return await self.log_event(
            session=session,
            action=AuditAction.LOGIN if "login" in action else AuditAction.LOGOUT,
            resource_type=AuditResource.USER,
            resource_id=user_id or uuid4(),  # Use dummy ID for failed logins
            user_id=user_id,
            details=audit_details,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
    async def log_document_event(
        self,
        session: AsyncSession,
        action: AuditAction,
        document_id: UUID,
        user_id: UUID,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log document-related events."""
        # Determine severity based on action
        severity_map = {
            AuditAction.CREATED: AuditSeverity.LOW,
            AuditAction.VIEWED: AuditSeverity.LOW,
            AuditAction.UPDATED: AuditSeverity.MEDIUM,
            AuditAction.DELETED: AuditSeverity.HIGH,
            AuditAction.PROCESSED: AuditSeverity.LOW,
            AuditAction.EXPORTED: AuditSeverity.MEDIUM
        }
        
        severity = severity_map.get(action, AuditSeverity.LOW)
        
        return await self.log_event(
            session=session,
            action=action,
            resource_type=AuditResource.DOCUMENT,
            resource_id=document_id,
            user_id=user_id,
            details=details,
            severity=severity,
            ip_address=ip_address
        )
        
    async def log_processing_event(
        self,
        session: AsyncSession,
        action: AuditAction,
        job_id: UUID,
        document_id: UUID,
        user_id: Optional[UUID],
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log processing job events."""
        processing_details = {
            "job_id": str(job_id),
            "document_id": str(document_id),
            **(details or {})
        }
        
        severity = AuditSeverity.MEDIUM if action == AuditAction.FAILED else AuditSeverity.LOW
        
        return await self.log_event(
            session=session,
            action=action,
            resource_type=AuditResource.PROCESSING_JOB,
            resource_id=job_id,
            user_id=user_id,
            details=processing_details,
            severity=severity
        )
        
    async def log_security_event(
        self,
        session: AsyncSession,
        event_type: str,
        resource_id: UUID,
        user_id: Optional[UUID],
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.HIGH
    ) -> AuditLog:
        """Log security-related events."""
        security_details = {
            "event_type": event_type,
            "threat_level": severity.value,
            **details
        }
        
        return await self.log_event(
            session=session,
            action=AuditAction.SECURITY_EVENT,
            resource_type=AuditResource.SYSTEM,
            resource_id=resource_id,
            user_id=user_id,
            details=security_details,
            severity=severity,
            ip_address=ip_address
        )
        
    async def get_audit_trail(
        self,
        session: AsyncSession,
        resource_type: Optional[AuditResource] = None,
        resource_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        actions: Optional[List[AuditAction]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[AuditLog], int]:
        """Get audit trail with filtering and pagination."""
        query = select(AuditLog).options(
            selectinload(AuditLog.user)
        )
        
        # Apply filters
        conditions = []
        
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
            
        if resource_id:
            conditions.append(AuditLog.resource_id == resource_id)
            
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
            
        if actions:
            conditions.append(AuditLog.action.in_([action.value for action in actions]))
            
        if start_date:
            conditions.append(AuditLog.timestamp >= start_date)
            
        if end_date:
            conditions.append(AuditLog.timestamp <= end_date)
            
        if severity:
            conditions.append(AuditLog.severity == severity.value)
            
        if conditions:
            query = query.where(and_(*conditions))
            
        # Add ordering and pagination
        query = query.order_by(desc(AuditLog.timestamp))
        
        # Get total count
        count_query = select(func.count(AuditLog.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
            
        total_count = (await session.execute(count_query)).scalar()
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        result = await session.execute(query)
        audit_logs = result.scalars().all()
        
        return list(audit_logs), total_count
        
    async def get_user_activity_summary(
        self,
        session: AsyncSession,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get activity summary for a specific user."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get activity counts by action
        result = await session.execute(
            select(AuditLog.action, func.count(AuditLog.id))
            .where(and_(
                AuditLog.user_id == user_id,
                AuditLog.timestamp >= start_date
            ))
            .group_by(AuditLog.action)
        )
        
        activity_counts = {action: count for action, count in result.all()}
        
        # Get recent activities
        recent_result = await session.execute(
            select(AuditLog)
            .where(and_(
                AuditLog.user_id == user_id,
                AuditLog.timestamp >= start_date
            ))
            .order_by(desc(AuditLog.timestamp))
            .limit(20)
        )
        
        recent_activities = recent_result.scalars().all()
        
        # Get activity timeline (by day)
        timeline_result = await session.execute(
            text("""
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM audit_logs 
                WHERE user_id = :user_id AND timestamp >= :start_date
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """),
            {"user_id": user_id, "start_date": start_date}
        )
        
        timeline = [
            {"date": row.date.isoformat(), "count": row.count}
            for row in timeline_result.all()
        ]
        
        return {
            "user_id": str(user_id),
            "period_days": days,
            "total_activities": sum(activity_counts.values()),
            "activity_breakdown": activity_counts,
            "recent_activities": [
                {
                    "action": log.action.value,
                    "resource_type": log.resource_type.value,
                    "resource_id": str(log.resource_id),
                    "timestamp": log.timestamp.isoformat(),
                    "severity": log.severity
                }
                for log in recent_activities
            ],
            "activity_timeline": timeline
        }
        
    async def get_resource_access_history(
        self,
        session: AsyncSession,
        resource_type: AuditResource,
        resource_id: UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get access history for a specific resource."""
        result = await session.execute(
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(and_(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id
            ))
            .order_by(desc(AuditLog.timestamp))
            .limit(limit)
        )
        
        audit_logs = result.scalars().all()
        
        return [
            {
                "action": log.action.value,
                "user_id": str(log.user_id) if log.user_id else None,
                "user_email": log.user.email if log.user else None,
                "timestamp": log.timestamp.isoformat(),
                "ip_address": log.ip_address,
                "severity": log.severity,
                "details": log.details
            }
            for log in audit_logs
        ]
        
    async def get_security_events(
        self,
        session: AsyncSession,
        days: int = 7,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent security events."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        conditions = [
            AuditLog.action == AuditAction.SECURITY_EVENT,
            AuditLog.timestamp >= start_date
        ]
        
        if severity:
            conditions.append(AuditLog.severity == severity.value)
            
        result = await session.execute(
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(and_(*conditions))
            .order_by(desc(AuditLog.timestamp))
            .limit(limit)
        )
        
        security_events = result.scalars().all()
        
        return [
            {
                "event_type": log.details.get("event_type"),
                "severity": log.severity,
                "user_id": str(log.user_id) if log.user_id else None,
                "user_email": log.user.email if log.user else None,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat(),
                "details": log.details
            }
            for log in security_events
        ]
        
    async def export_audit_trail(
        self,
        session: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"  # json, csv
    ) -> str:
        """Export audit trail for compliance reporting."""
        # Get all audit logs in date range
        result = await session.execute(
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            ))
            .order_by(AuditLog.timestamp)
        )
        
        audit_logs = result.scalars().all()
        
        # Convert to export format
        export_data = []
        for log in audit_logs:
            export_data.append({
                "id": str(log.id),
                "timestamp": log.timestamp.isoformat(),
                "action": log.action.value,
                "resource_type": log.resource_type.value,
                "resource_id": str(log.resource_id),
                "user_id": str(log.user_id) if log.user_id else None,
                "user_email": log.user.email if log.user else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "session_id": log.session_id,
                "severity": log.severity,
                "details": json.dumps(log.details, ensure_ascii=False)
            })
            
        if format.lower() == "json":
            return json.dumps(export_data, ensure_ascii=False, indent=2)
        elif format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if export_data:
                writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)
                
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")
            
    async def cleanup_old_logs(
        self,
        session: AsyncSession,
        retention_days: Optional[int] = None
    ) -> int:
        """Clean up audit logs older than retention period."""
        retention_days = retention_days or self.retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Delete old logs
        result = await session.execute(
            text("DELETE FROM audit_logs WHERE timestamp < :cutoff_date"),
            {"cutoff_date": cutoff_date}
        )
        
        deleted_count = result.rowcount
        await session.commit()
        
        logger.info(f"Cleaned up {deleted_count} audit logs older than {retention_days} days")
        
        return deleted_count
        
    async def get_compliance_report(
        self,
        session: AsyncSession,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate compliance report for audit review."""
        # Get audit statistics
        stats_result = await session.execute(
            select(
                AuditLog.action,
                AuditLog.severity,
                func.count(AuditLog.id)
            )
            .where(and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            ))
            .group_by(AuditLog.action, AuditLog.severity)
        )
        
        stats = {}
        for action, severity, count in stats_result.all():
            if action.value not in stats:
                stats[action.value] = {}
            stats[action.value][severity] = count
            
        # Get user activity summary
        user_activity_result = await session.execute(
            select(
                AuditLog.user_id,
                func.count(AuditLog.id)
            )
            .where(and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.user_id.isnot(None)
            ))
            .group_by(AuditLog.user_id)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        )
        
        top_users = [
            {"user_id": str(user_id), "activity_count": count}
            for user_id, count in user_activity_result.all()
        ]
        
        # Get security events summary
        security_result = await session.execute(
            select(func.count(AuditLog.id))
            .where(and_(
                AuditLog.action == AuditAction.SECURITY_EVENT,
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            ))
        )
        
        security_event_count = security_result.scalar()
        
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary_statistics": stats,
            "top_active_users": top_users,
            "security_events_count": security_event_count,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize audit details to remove sensitive information."""
        sensitive_keys = {
            "password", "token", "secret", "key", "credential",
            "authorization", "session", "cookie", "signature"
        }
        
        sanitized = {}
        for key, value in details.items():
            key_lower = key.lower()
            
            # Remove sensitive keys
            if any(sensitive_key in key_lower for sensitive_key in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            # Truncate very long strings
            elif isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "...[TRUNCATED]"
            # Keep other values as-is
            else:
                sanitized[key] = value
                
        return sanitized


# Global audit service instance
_audit_service: Optional[AuditService] = None


def get_audit_service(settings: Settings) -> AuditService:
    """Get the global audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService(settings)
    return _audit_service