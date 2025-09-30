"""
Celery Application Configuration

Configures Celery for asynchronous document processing with:
- Redis as message broker and result backend
- Priority queues (urgent, standard, bulk)
- Task routing based on document type
- Retry policies and error handling
- Monitoring and observability
"""

import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from kombu import Queue, Exchange
import logging

logger = logging.getLogger(__name__)

# Load configuration from environment
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

# Create Celery application
celery_app = Celery(
    'amharic_document_worker',
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        'backend.src.worker.tasks',
    ]
)

# Celery Configuration
celery_app.conf.update(
    # Task execution settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Addis_Ababa',
    enable_utc=True,

    # Task result settings
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,  # Store additional task metadata

    # Worker settings
    worker_prefetch_multiplier=1,  # Disable prefetching for better priority handling
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (memory management)
    worker_disable_rate_limits=False,

    # Task execution limits
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Task retry settings
    task_acks_late=True,  # Acknowledge task after execution
    task_reject_on_worker_lost=True,  # Requeue if worker crashes

    # Priority queue configuration
    task_default_queue='standard',
    task_default_exchange='tasks',
    task_default_exchange_type='direct',
    task_default_routing_key='standard',

    # Queue definitions with priorities
    task_queues=(
        Queue('urgent', Exchange('tasks'), routing_key='urgent', priority=10),
        Queue('standard', Exchange('tasks'), routing_key='standard', priority=5),
        Queue('bulk', Exchange('tasks'), routing_key='bulk', priority=1),
    ),

    # Task routing
    task_routes={
        'backend.src.worker.tasks.process_document_task': {
            'queue': 'standard',
            'routing_key': 'standard'
        },
        'backend.src.worker.tasks.batch_process_documents_task': {
            'queue': 'bulk',
            'routing_key': 'bulk'
        },
        'backend.src.worker.tasks.reindex_document_task': {
            'queue': 'standard',
            'routing_key': 'standard'
        },
        'backend.src.worker.tasks.generate_export_task': {
            'queue': 'standard',
            'routing_key': 'standard'
        },
        'backend.src.worker.tasks.cleanup_old_files_task': {
            'queue': 'bulk',
            'routing_key': 'bulk'
        },
    },

    # Monitoring and observability
    task_send_sent_event=True,  # Enable task sent events
    worker_send_task_events=True,  # Enable worker events
    task_track_started=True,  # Track task start time

    # Redis connection pool settings
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_pool_limit=10,

    # Beat schedule for periodic tasks
    beat_schedule={
        'cleanup-old-files-daily': {
            'task': 'backend.src.worker.tasks.cleanup_old_files_task',
            'schedule': 86400.0,  # Run daily
            'options': {'queue': 'bulk'}
        },
    },
)


# Task lifecycle hooks for monitoring
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Log task start"""
    logger.info(
        f"Task starting: {task.name} [id: {task_id}]",
        extra={
            'task_id': task_id,
            'task_name': task.name,
            'args': str(args)[:100],  # Truncate for logging
            'kwargs': str(kwargs)[:100],
        }
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra):
    """Log task completion"""
    logger.info(
        f"Task completed: {task.name} [id: {task_id}] - State: {state}",
        extra={
            'task_id': task_id,
            'task_name': task.name,
            'state': state,
            'result_preview': str(retval)[:100] if retval else None,
        }
    )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra):
    """Log task failures"""
    logger.error(
        f"Task failed: {sender.name} [id: {task_id}] - {exception}",
        extra={
            'task_id': task_id,
            'task_name': sender.name,
            'exception': str(exception),
            'traceback': str(traceback)[:500],  # Truncate for logging
        },
        exc_info=einfo
    )


# Health check task
@celery_app.task(name='health_check')
def health_check_task():
    """Simple health check task for monitoring"""
    return {'status': 'healthy', 'worker': 'amharic_document_worker'}


if __name__ == '__main__':
    celery_app.start()