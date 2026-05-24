from __future__ import annotations

from typing import Protocol
from uuid import UUID

from apps.shared.src.domain.entities.prediction_job import PredictionJob


class IPredictionJobRepository(Protocol):
    def save(self, *, job: PredictionJob) -> None: ...

    def find_by_id(self, *, job_id: UUID) -> PredictionJob | None: ...
