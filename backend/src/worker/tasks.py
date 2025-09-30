"""
Celery Tasks for Document Processing

Main asynchronous tasks for the Amharic Document Processing System:
- Document processing pipeline invocation
- Batch processing orchestration
- Search reindexing
- Export generation
- Maintenance tasks
"""

from typing import Dict, List, Optional, Any
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded, Retry
import logging
from datetime import datetime, timedelta

from .celery_app import celery_app

logger = logging.getLogger(__name__)


class BaseDocumentTask(Task):
    """
    Base task class with common error handling and retry logic
    """
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(
            f"Task {self.name} [{task_id}] failed: {exc}",
            extra={
                'task_id': task_id,
                'exception': str(exc),
                'args': str(args)[:100],
            }
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry"""
        logger.warning(
            f"Task {self.name} [{task_id}] retrying: {exc}",
            extra={
                'task_id': task_id,
                'exception': str(exc),
                'retry_count': self.request.retries,
            }
        )

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        logger.info(
            f"Task {self.name} [{task_id}] succeeded",
            extra={
                'task_id': task_id,
                'result_preview': str(retval)[:100] if retval else None,
            }
        )


@celery_app.task(
    base=BaseDocumentTask,
    name='process_document',
    bind=True,
    track_started=True
)
def process_document_task(
    self,
    document_id: str,
    job_id: Optional[str] = None,
    priority: str = 'standard',
    configuration: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process a single document through the CrewAI pipeline.

    Args:
        document_id: Document UUID to process
        job_id: Optional parent job ID
        priority: Priority level (urgent, standard, bulk)
        configuration: Processing configuration overrides

    Returns:
        Processing result with status and metadata
    """
    try:
        logger.info(f"Starting document processing: {document_id}")

        # Import here to avoid circular dependencies
        from backend.src.services.processing import ProcessingService
        from backend.src.agents.orchestrator import process_document_pipeline

        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={
                'document_id': document_id,
                'job_id': job_id,
                'started_at': datetime.utcnow().isoformat()
            }
        )

        # Execute CrewAI document processing pipeline
        result = process_document_pipeline(
            document_id=document_id,
            configuration=configuration or {}
        )

        # Update processing service with results
        processing_service = ProcessingService()
        processing_service.update_document_status(
            document_id=document_id,
            status='completed',
            result=result
        )

        logger.info(f"Document processing completed: {document_id}")

        return {
            'status': 'success',
            'document_id': document_id,
            'job_id': job_id,
            'result': result,
            'completed_at': datetime.utcnow().isoformat()
        }

    except SoftTimeLimitExceeded:
        logger.error(f"Document processing timeout: {document_id}")
        self.update_state(
            state='TIMEOUT',
            meta={'document_id': document_id, 'error': 'Processing timeout'}
        )
        raise

    except Exception as exc:
        logger.error(f"Document processing error: {document_id} - {exc}")
        self.update_state(
            state='FAILURE',
            meta={'document_id': document_id, 'error': str(exc)}
        )
        raise


@celery_app.task(
    base=BaseDocumentTask,
    name='batch_process_documents',
    bind=True,
    track_started=True
)
def batch_process_documents_task(
    self,
    job_id: str,
    document_ids: List[str],
    configuration: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process multiple documents in batch.

    Args:
        job_id: Batch job UUID
        document_ids: List of document UUIDs to process
        configuration: Processing configuration

    Returns:
        Batch processing results
    """
    try:
        logger.info(f"Starting batch processing: {job_id} ({len(document_ids)} documents)")

        from backend.src.services.processing import ProcessingService

        processing_service = ProcessingService()

        # Update job status
        processing_service.update_job_status(
            job_id=job_id,
            status='running',
            total_documents=len(document_ids)
        )

        results = []
        completed = 0
        failed = 0

        # Process each document
        for i, document_id in enumerate(document_ids, 1):
            try:
                # Update progress
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'job_id': job_id,
                        'current': i,
                        'total': len(document_ids),
                        'percent': int((i / len(document_ids)) * 100)
                    }
                )

                # Invoke single document processing task
                result = process_document_task.apply_async(
                    args=[document_id, job_id],
                    kwargs={'configuration': configuration},
                    queue='standard'
                )

                results.append({
                    'document_id': document_id,
                    'task_id': result.id,
                    'status': 'queued'
                })

                completed += 1

            except Exception as exc:
                logger.error(f"Failed to queue document {document_id}: {exc}")
                failed += 1
                results.append({
                    'document_id': document_id,
                    'status': 'failed',
                    'error': str(exc)
                })

        # Update final job status
        processing_service.update_job_status(
            job_id=job_id,
            status='completed',
            completed_documents=completed,
            failed_documents=failed
        )

        logger.info(f"Batch processing completed: {job_id} ({completed} succeeded, {failed} failed)")

        return {
            'status': 'success',
            'job_id': job_id,
            'total': len(document_ids),
            'completed': completed,
            'failed': failed,
            'results': results,
            'completed_at': datetime.utcnow().isoformat()
        }

    except Exception as exc:
        logger.error(f"Batch processing error: {job_id} - {exc}")
        raise


@celery_app.task(
    base=BaseDocumentTask,
    name='reindex_document',
    bind=True
)
def reindex_document_task(
    self,
    document_id: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Reindex a document in the search engine.

    Args:
        document_id: Document UUID to reindex
        force: Force reindex even if already indexed

    Returns:
        Reindexing result
    """
    try:
        logger.info(f"Reindexing document: {document_id}")

        from backend.src.services.search import SearchService

        search_service = SearchService()

        # Reindex document
        result = search_service.reindex_document(
            document_id=document_id,
            force=force
        )

        logger.info(f"Document reindexed: {document_id}")

        return {
            'status': 'success',
            'document_id': document_id,
            'result': result,
            'completed_at': datetime.utcnow().isoformat()
        }

    except Exception as exc:
        logger.error(f"Reindexing error: {document_id} - {exc}")
        raise


@celery_app.task(
    base=BaseDocumentTask,
    name='generate_export',
    bind=True
)
def generate_export_task(
    self,
    document_id: str,
    export_format: str,
    template_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate document export in specified format.

    Args:
        document_id: Document UUID to export
        export_format: Target format (pdf, docx, html, markdown, json)
        template_id: Optional export template UUID
        options: Export options (watermark, signature, etc.)

    Returns:
        Export generation result with file path
    """
    try:
        logger.info(f"Generating export: {document_id} -> {export_format}")

        from backend.src.services.export import ExportService

        export_service = ExportService()

        # Generate export
        result = export_service.generate_export(
            document_id=document_id,
            export_format=export_format,
            template_id=template_id,
            options=options or {}
        )

        logger.info(f"Export generated: {document_id} -> {result['file_path']}")

        return {
            'status': 'success',
            'document_id': document_id,
            'format': export_format,
            'file_path': result['file_path'],
            'file_size': result.get('file_size'),
            'completed_at': datetime.utcnow().isoformat()
        }

    except Exception as exc:
        logger.error(f"Export generation error: {document_id} - {exc}")
        raise


@celery_app.task(
    base=BaseDocumentTask,
    name='cleanup_old_files'
)
def cleanup_old_files_task(days: int = 30) -> Dict[str, Any]:
    """
    Clean up old temporary and processed files.

    Args:
        days: Age threshold in days for cleanup

    Returns:
        Cleanup result with counts
    """
    try:
        logger.info(f"Starting file cleanup (older than {days} days)")

        from backend.src.services.documents import DocumentService

        document_service = DocumentService()

        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Clean up old files
        result = document_service.cleanup_old_files(cutoff_date=cutoff_date)

        logger.info(
            f"File cleanup completed: {result['files_deleted']} files deleted, "
            f"{result['space_freed']} bytes freed"
        )

        return {
            'status': 'success',
            'cutoff_date': cutoff_date.isoformat(),
            'files_deleted': result['files_deleted'],
            'space_freed': result['space_freed'],
            'completed_at': datetime.utcnow().isoformat()
        }

    except Exception as exc:
        logger.error(f"Cleanup error: {exc}")
        raise


# Task monitoring and management functions

def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the status of a task by ID"""
    result = celery_app.AsyncResult(task_id)
    return {
        'task_id': task_id,
        'state': result.state,
        'info': result.info,
        'ready': result.ready(),
        'successful': result.successful() if result.ready() else None,
        'failed': result.failed() if result.ready() else None,
    }


def cancel_task(task_id: str) -> Dict[str, Any]:
    """Cancel a running task"""
    celery_app.control.revoke(task_id, terminate=True)
    return {
        'task_id': task_id,
        'status': 'cancelled',
        'cancelled_at': datetime.utcnow().isoformat()
    }


def get_queue_stats() -> Dict[str, Any]:
    """Get statistics for all queues"""
    inspect = celery_app.control.inspect()

    return {
        'active': inspect.active(),
        'scheduled': inspect.scheduled(),
        'reserved': inspect.reserved(),
        'stats': inspect.stats(),
    }