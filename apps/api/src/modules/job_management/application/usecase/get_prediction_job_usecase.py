from __future__ import annotations

from modules.job_management.application.dto import (
    GetJobStatusResult,
    GetPredictionJobQuery,
)
from modules.job_management.domain.repositories.prediction_job_repository import (
    PredictionJobRepository,
)


class PredictionJobNotFoundError(LookupError):
    def __init__(self, *, job_id: object) -> None:
        super().__init__(f"Prediction job not found: {job_id}")
        self.job_id = job_id


class GetPredictionJobUseCase:
    def __init__(self, repository: PredictionJobRepository):
        self.repository = repository

    def execute(self, query: GetPredictionJobQuery) -> GetJobStatusResult:
        job = self.repository.get_by_id(job_id=query.job_id)
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
