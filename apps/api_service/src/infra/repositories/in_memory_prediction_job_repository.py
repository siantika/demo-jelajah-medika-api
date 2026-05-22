from __future__ import annotations

from copy import deepcopy
from threading import RLock
from uuid import UUID

from apps.api_service.src.application.ports.prediction_job_repository import (
    PredictionJobRepository,
)
from apps.shared.domain.entities.prediction_job import (
    PredictionJob,
)


class InMemoryPredictionJobRepository(PredictionJobRepository):
    def __init__(self) -> None:
        self._jobs: dict[UUID, PredictionJob] = {}
        self._lock = RLock()

    def create(self, *, job: PredictionJob) -> None:
        with self._lock:
            self._jobs[job.id] = deepcopy(job)

    def get_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return deepcopy(job) if job is not None else None
