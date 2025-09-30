"""
Celery Worker Entrypoint

Starts the Celery worker process for asynchronous document processing.

Usage:
    # Start worker with all queues
    python -m backend.src.worker

    # Start worker with specific queues
    python -m backend.src.worker --queues urgent,standard

    # Start worker with concurrency
    python -m backend.src.worker --concurrency 4

    # Start worker with autoscaling
    python -m backend.src.worker --autoscale 10,3
"""

import sys
import logging
from celery.bin import worker

from .celery_app import celery_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for Celery worker.
    """
    logger.info("Starting Amharic Document Processing Worker")
    logger.info(f"Broker: {celery_app.conf.broker_url}")
    logger.info(f"Backend: {celery_app.conf.result_backend}")

    # Create worker instance
    worker_instance = worker.worker(app=celery_app)

    # Worker options
    options = {
        'loglevel': 'INFO',
        'traceback': True,

        # Queue configuration
        'queues': ['urgent', 'standard', 'bulk'],  # Process all queues

        # Concurrency settings
        'concurrency': 4,  # Number of worker processes
        'pool': 'prefork',  # Use prefork pool (can be: prefork, eventlet, gevent)

        # Task execution
        'max_tasks_per_child': 100,  # Restart after 100 tasks (memory management)

        # Optimization
        'optimization': 'fair',  # Fair task distribution

        # Event monitoring
        'task_events': True,
        'send_events': True,

        # Heartbeat
        'heartbeat_interval': 10,  # Send heartbeat every 10 seconds

        # Time limits
        'task_time_limit': 3600,  # 1 hour hard limit
        'task_soft_time_limit': 3300,  # 55 minutes soft limit
    }

    # Start worker
    try:
        logger.info("Worker started successfully")
        logger.info(f"Processing queues: {options['queues']}")
        logger.info(f"Concurrency: {options['concurrency']}")

        worker_instance.run(**options)

    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)

    except Exception as exc:
        logger.error(f"Worker error: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()