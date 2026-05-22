from __future__ import annotations

from apps.api_service.src.application.dto import (
    GetJobStatusResult,
    GetPredictionJobQuery,
)
from apps.api_service.src.application.ports.prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.shared.domain.errors import PredictionJobNotFoundError


class GetPredictionJobUseCase:
    def __init__(self, repository: IPredictionJobRepository):
        self.repository = repository

    async def execute(self, query: GetPredictionJobQuery) -> GetJobStatusResult:
        job = await self.repository.find_by_id(job_id=query.job_id)
        if job is None:
            raise PredictionJobNotFoundError(job_id=query.job_id)

        result_payload = [
            {
                "affinity": item.affinity,
                "target_sequence": item.target_sequence,
            }
            for item in job.result
        ] or None

        return GetJobStatusResult(
            job_id=job.id,
            status=str(job.status),
            created_at=job.created_at,
            updated_at=job.updated_at,
            result=result_payload,
            metrics=None,
            error_code=None,
            error_message=job.error,
        )

