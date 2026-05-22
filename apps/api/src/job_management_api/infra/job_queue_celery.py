from __future__ import annotations

import os
from uuid import UUID

from apps.api.src.job_management_api.application.ports.job_queue import JobQueue
from celery import Celery


class CeleryJobQueue(JobQueue):
    def __init__(self, app: Celery):
        self.app = app

    def enqueue_prediction(self, *, job_id: UUID) -> str:
        task = self.app.send_task(
            "prediction.run_job",
            kwargs={"job_id": str(job_id)},
        )
        return str(task.id)


def build_celery_app() -> Celery:
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    return Celery("api_job_queue", broker=broker_url, backend=result_backend)
