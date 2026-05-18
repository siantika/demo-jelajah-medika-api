from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from apps.ml_engine_service.src.application.ports.prediction_engine import PredictionEngine
from apps.shared.job_management.contracts.repositories.prediction_job_repository import (
    PredictionJobRepository,
)


class PredictionJobNotFoundError(LookupError):
    def __init__(self, *, job_id: object) -> None:
        super().__init__(f"Prediction job not found: {job_id}")
        self.job_id = job_id


@dataclass(frozen=True)
class RunPredictionJobCmd:
    job_id: UUID


class RunPredictionJobUseCase:
    def __init__(
        self,
        repository: PredictionJobRepository,
        prediction_engine: PredictionEngine,
    ):
        self.repository = repository
        self.prediction_engine = prediction_engine

    def execute(self, cmd: RunPredictionJobCmd) -> None:
        job = self.repository.get_by_id(job_id=cmd.job_id)
        if job is None:
            raise PredictionJobNotFoundError(job_id=cmd.job_id)

        job.mark_running()
        self.repository.save(job=job)

        try:
            prediction_result = self.prediction_engine.predict(
                smiles=str(job.smiles),
                dataset_name=str(job.dataset),
                model_version=str(job.model_version),
                top_k=job.options.top_k,
                return_sequences=job.options.return_sequence,
            )
            job.mark_success(prediction_result)
            self.repository.save(job=job)
        except Exception as exc:
            job.mark_failed(str(exc))
            self.repository.save(job=job)
            raise
