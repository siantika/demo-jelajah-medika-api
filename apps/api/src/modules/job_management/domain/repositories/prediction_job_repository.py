from __future__ import annotations

from typing import Protocol
from uuid import UUID

from modules.job_management.domain.entities.prediction_job import PredictionJob


class PredictionJobRepository(Protocol):
    def get_by_id(self, *, job_id: UUID) -> PredictionJob | None: ...
