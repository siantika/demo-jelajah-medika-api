from __future__ import annotations

from uuid import UUID, uuid4

from apps.api_service.src.application.ports.job_queue import IJobQueue


class InProcessJobQueue(IJobQueue):
    def enqueue_prediction(self, *, job_id: UUID) -> str:
        # Temporary queue without Celery: return synthetic task id.
        return str(uuid4())


class CeleryJobQueue(InProcessJobQueue):
    pass


def build_celery_app() -> None:
    return None
