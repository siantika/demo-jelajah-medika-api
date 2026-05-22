from __future__ import annotations

from typing import Protocol
from uuid import UUID

from apps.shared.domain.entities.prediction_job import PredictionJob


class PredictionJobRepository(Protocol):
    def save(self, *, job: PredictionJob) -> None: ...

    def get_by_id(self, *, job_id: UUID) -> PredictionJob | None: ...
