"""Celery application factory for background workflow processing.

The coordinator API dispatches workflow tasks to this Celery app via Redis.
A separate container runs the Celery worker using the same coordinator image
but with a different entrypoint.
"""

from celery import Celery

from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery = Celery(
    "coordinator",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    task_default_queue="workflow",
    task_default_retry_delay=5,
    task_max_retries=3,
)
