"""MCP tool adapters exposing core functionality to CopilotKit frontend."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from ...services.documents import get_document_service
from ...services.processing import get_processing_orchestrator
from ...services.search import get_search_service
from ...services.export import get_export_service
from ...services.summarization import get_summarization_service
from ...services.webhooks import get_webhook_service, WebhookEventType
from ...services.quality import get_quality_service
from ...services.audit import get_audit_service
from ...config.settings import Settings

logger = logging.getLogger(__name__)


class MCPToolAdapter:
    """Base adapter for MCP tool integration."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        # Initialize all services
        self.document_service = get_document_service(settings)
        self.processing_service = get_processing_orchestrator(settings)
        self.search_service = get_search_service(settings)
        self.export_service = get_export_service(settings)
        self.summarization_service = get_summarization_service(settings)
        self.webhook_service = get_webhook_service(settings)
        self.quality_service = get_quality_service(settings)
        self.audit_service = get_audit_service(settings)
        
    async def upload_document(
        self,
        session: Any,  # AsyncSession
        file_data: bytes,
        filename: str,
        content_type: str,
        user_id: UUID,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload a document and start processing."""
        try:
            # Upload document
            document = await self.document_service.upload_document(
                session=session,
                file_data=file_data,
                filename=filename,
                content_type=content_type,
                user_id=user_id,
                metadata=metadata or {}
            )
            
            # Log audit event
            await self.audit_service.log_document_event(
                session=session,
                action="CREATED",
                document_id=document.id,
                user_id=user_id,
                details={"filename": filename, "size": len(file_data)}
            )
            
            # Start processing job
            job = await self.processing_service.create_job(
                session=session,
                document_id=document.id,
                job_type="document_analysis",
                metadata={"source": "mcp_upload"}
            )
            
            # Trigger webhook
            await self.webhook_service.trigger_webhook(
                session=session,
                event_type=WebhookEventType.DOCUMENT_UPLOADED,
                payload={
                    "document_id": str(document.id),
                    "filename": filename,
                    "job_id": str(job.id),
                    "user_id": str(user_id)
                },
                user_id=user_id
            )
            
            return {
                "success": True,
                "document_id": str(document.id),
                "job_id": str(job.id),
                "filename": filename,
                "status": "uploaded",
                "processing_started": True
            }
            
        except Exception as e:
            logger.error(f"Document upload failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "filename": filename
            }
            
    async def get_processing_progress(
        self,
        session: Any,
        job_id: str,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get processing job progress and status."""
        try:
            job_uuid = UUID(job_id)
            job = await self.processing_service.get_job_status(session, job_uuid)
            
            if not job:
                return {
                    "success": False,
                    "error": "Job not found",
                    "job_id": job_id
                }
                
            # Get quality metrics if completed
            quality_summary = None
            if job.status == "completed":
                quality_summary = await self.quality_service.get_document_quality_summary(
                    session, job.document_id
                )
                
            return {
                "success": True,
                "job_id": job_id,
                "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
                "progress": job.progress if hasattr(job, 'progress') else 0,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                "result": job.result,
                "quality_metrics": quality_summary
            }
            
        except Exception as e:
            logger.error(f"Progress query failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "job_id": job_id
            }
            
    async def search_documents(
        self,
        session: Any,
        query: str,
        user_id: UUID,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Search through processed documents."""
        try:
            # Log search query
            from ...services.search_suggestions import get_search_suggestions_service
            suggestions_service = get_search_suggestions_service(self.settings)
            
            # Perform search
            results = await self.search_service.search_documents(
                query=query,
                filters=filters,
                page=page,
                page_size=page_size,
                highlight=True
            )
            
            # Record search for analytics
            await suggestions_service.record_search_query(
                query=query,
                user_id=user_id,
                results_count=results.get("total", 0)
            )
            
            return {
                "success": True,
                "query": query,
                "results": results["documents"],
                "total": results["total"],
                "page": results["page"],
                "page_size": results["page_size"],
                "total_pages": results["total_pages"]
            }
            
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
            
    async def export_document(
        self,
        session: Any,
        document_id: str,
        export_format: str,
        user_id: UUID,
        template_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Export a processed document in specified format."""
        try:
            from ...db.models.export_template import ExportFormat
            
            doc_uuid = UUID(document_id)
            template_uuid = UUID(template_id) if template_id else None
            
            # Convert format string to enum
            format_mapping = {
                "pdf": ExportFormat.PDF,
                "docx": ExportFormat.DOCX,
                "html": ExportFormat.HTML,
                "markdown": ExportFormat.MARKDOWN,
                "json": ExportFormat.JSON
            }
            
            format_enum = format_mapping.get(export_format.lower())
            if not format_enum:
                return {
                    "success": False,
                    "error": f"Unsupported export format: {export_format}",
                    "document_id": document_id
                }
                
            # Export document
            export_data, filename = await self.export_service.export_document(
                session=session,
                document_id=doc_uuid,
                export_format=format_enum,
                template_id=template_uuid,
                options=options or {}
            )
            
            # Log audit event
            await self.audit_service.log_document_event(
                session=session,
                action="EXPORTED",
                document_id=doc_uuid,
                user_id=user_id,
                details={
                    "export_format": export_format,
                    "filename": filename,
                    "size": len(export_data)
                }
            )
            
            # Trigger webhook
            await self.webhook_service.trigger_webhook(
                session=session,
                event_type=WebhookEventType.EXPORT_COMPLETED,
                payload={
                    "document_id": document_id,
                    "export_format": export_format,
                    "filename": filename,
                    "user_id": str(user_id)
                },
                user_id=user_id
            )
            
            # Return base64 encoded data for frontend
            import base64
            encoded_data = base64.b64encode(export_data).decode('utf-8')
            
            return {
                "success": True,
                "document_id": document_id,
                "format": export_format,
                "filename": filename,
                "data": encoded_data,
                "size": len(export_data)
            }
            
        except Exception as e:
            logger.error(f"Document export failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }
            
    async def generate_summary(
        self,
        session: Any,
        document_id: str,
        user_id: UUID,
        summary_type: str = "extractive",
        language: str = "amh"
    ) -> Dict[str, Any]:
        """Generate summary for a processed document."""
        try:
            doc_uuid = UUID(document_id)
            
            # Get document content (this would typically fetch from MongoDB)
            # For now, using mock content
            content = "Sample Amharic document content for summarization..."
            
            # Generate summary
            summary_result = await self.summarization_service.generate_summary(
                session=session,
                document_id=doc_uuid,
                content=content,
                language=language,
                summary_type=summary_type
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "summary_type": summary_type,
                "language": language,
                "summary": summary_result["summary"],
                "confidence": summary_result["confidence"],
                "length": len(summary_result["summary"]),
                "compression_ratio": summary_result.get("compression_ratio", 0),
                "cached": summary_result.get("cached", False)
            }
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }
            
    async def manage_webhook_subscription(
        self,
        session: Any,
        action: str,
        user_id: UUID,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        subscription_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Manage webhook subscriptions (create, update, delete, list)."""
        try:
            if action == "create":
                if not url or not events:
                    return {
                        "success": False,
                        "error": "URL and events are required for creating subscription"
                    }
                    
                # Convert event strings to enums
                webhook_events = []
                for event in events:
                    try:
                        webhook_events.append(WebhookEventType(event))
                    except ValueError:
                        return {
                            "success": False,
                            "error": f"Invalid event type: {event}"
                        }
                        
                subscription = await self.webhook_service.create_subscription(
                    session=session,
                    url=url,
                    events=webhook_events,
                    user_id=user_id,
                    **kwargs
                )
                
                return {
                    "success": True,
                    "action": "created",
                    "subscription_id": str(subscription.id),
                    "url": subscription.url,
                    "events": subscription.events,
                    "active": subscription.active
                }
                
            elif action == "update":
                if not subscription_id:
                    return {
                        "success": False,
                        "error": "Subscription ID is required for update"
                    }
                    
                sub_uuid = UUID(subscription_id)
                webhook_events = [WebhookEventType(e) for e in events] if events else None
                
                subscription = await self.webhook_service.update_subscription(
                    session=session,
                    subscription_id=sub_uuid,
                    url=url,
                    events=webhook_events,
                    **kwargs
                )
                
                if not subscription:
                    return {
                        "success": False,
                        "error": "Subscription not found"
                    }
                    
                return {
                    "success": True,
                    "action": "updated",
                    "subscription_id": subscription_id,
                    "url": subscription.url,
                    "events": subscription.events,
                    "active": subscription.active
                }
                
            elif action == "delete":
                if not subscription_id:
                    return {
                        "success": False,
                        "error": "Subscription ID is required for delete"
                    }
                    
                sub_uuid = UUID(subscription_id)
                deleted = await self.webhook_service.delete_subscription(session, sub_uuid)
                
                return {
                    "success": deleted,
                    "action": "deleted",
                    "subscription_id": subscription_id
                }
                
            elif action == "list":
                subscriptions = await self.webhook_service.get_subscriptions(
                    session=session,
                    user_id=user_id
                )
                
                return {
                    "success": True,
                    "action": "listed",
                    "subscriptions": [
                        {
                            "id": str(sub.id),
                            "url": sub.url,
                            "events": sub.events,
                            "active": sub.active,
                            "created_at": sub.created_at.isoformat()
                        }
                        for sub in subscriptions
                    ]
                }
                
            else:
                return {
                    "success": False,
                    "error": f"Unsupported action: {action}"
                }
                
        except Exception as e:
            logger.error(f"Webhook management failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
            
    async def get_system_status(
        self,
        session: Any,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get system status and health information."""
        try:
            # Get processing statistics
            processing_stats = await self.processing_service.get_processing_statistics(session)
            
            # Get quality report
            quality_report = await self.quality_service.get_system_quality_report(session, days=7)
            
            # Get user activity summary
            user_activity = await self.audit_service.get_user_activity_summary(
                session, user_id, days=7
            )
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "processing_statistics": processing_stats,
                "quality_metrics": {
                    "ocr_statistics": quality_report.get("ocr_statistics", {}),
                    "sla_statistics": quality_report.get("sla_statistics", {}),
                    "anomalies_detected": quality_report.get("anomalies_detected", 0)
                },
                "user_activity": {
                    "total_activities": user_activity.get("total_activities", 0),
                    "recent_activities_count": len(user_activity.get("recent_activities", []))
                },
                "system_health": "operational"
            }
            
        except Exception as e:
            logger.error(f"System status query failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "system_health": "degraded"
            }


# Global MCP adapter instance
_mcp_adapter: Optional[MCPToolAdapter] = None


def get_mcp_adapter(settings: Settings) -> MCPToolAdapter:
    """Get the global MCP tool adapter instance."""
    global _mcp_adapter
    if _mcp_adapter is None:
        _mcp_adapter = MCPToolAdapter(settings)
    return _mcp_adapter


# Tool registry for CopilotKit integration
MCP_TOOLS = {
    "upload_document": {
        "name": "upload_document",
        "description": "Upload a document and start processing",
        "parameters": {
            "file_data": {"type": "bytes", "required": True},
            "filename": {"type": "string", "required": True},
            "content_type": {"type": "string", "required": True},
            "metadata": {"type": "object", "required": False}
        }
    },
    "get_processing_progress": {
        "name": "get_processing_progress",
        "description": "Get processing job progress and status",
        "parameters": {
            "job_id": {"type": "string", "required": True}
        }
    },
    "search_documents": {
        "name": "search_documents",
        "description": "Search through processed documents",
        "parameters": {
            "query": {"type": "string", "required": True},
            "filters": {"type": "object", "required": False},
            "page": {"type": "integer", "default": 1},
            "page_size": {"type": "integer", "default": 20}
        }
    },
    "export_document": {
        "name": "export_document",
        "description": "Export a processed document in specified format",
        "parameters": {
            "document_id": {"type": "string", "required": True},
            "export_format": {"type": "string", "enum": ["pdf", "docx", "html", "markdown", "json"], "required": True},
            "template_id": {"type": "string", "required": False},
            "options": {"type": "object", "required": False}
        }
    },
    "generate_summary": {
        "name": "generate_summary",
        "description": "Generate summary for a processed document",
        "parameters": {
            "document_id": {"type": "string", "required": True},
            "summary_type": {"type": "string", "enum": ["extractive", "abstractive", "keyword"], "default": "extractive"},
            "language": {"type": "string", "default": "amh"}
        }
    },
    "manage_webhook_subscription": {
        "name": "manage_webhook_subscription", 
        "description": "Manage webhook subscriptions",
        "parameters": {
            "action": {"type": "string", "enum": ["create", "update", "delete", "list"], "required": True},
            "url": {"type": "string", "required": False},
            "events": {"type": "array", "items": {"type": "string"}, "required": False},
            "subscription_id": {"type": "string", "required": False}
        }
    },
    "get_system_status": {
        "name": "get_system_status",
        "description": "Get system status and health information",
        "parameters": {}
    }
}