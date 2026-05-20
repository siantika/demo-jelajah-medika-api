from __future__ import annotations

from typing import Protocol
from uuid import UUID

from apps.shared.job_management_domain.domain.entities.prediction_job import PredictionJob


class PredictionJobRepository(Protocol):
    def create(self, *, job: PredictionJob) -> None: ...

    def get_by_id(self, *, job_id: UUID) -> PredictionJob | None: ...
