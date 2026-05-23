from __future__ import annotations

from apps.ml_engine_service.src.application.ports.prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.ml_engine_service.src.application.usecase.dto import RunPredictionJobCmd
from apps.shared.contracts.prediction_engine import PredictionEngine
from apps.shared.domain.errors import PredictionJobNotFoundError


class RunPredictionJobUseCase:
    def __init__(
        self,
        repository: IPredictionJobRepository,
        prediction_engine: PredictionEngine,
    ):
        self.repository = repository
        self.prediction_engine = prediction_engine

    async def execute(self, cmd: RunPredictionJobCmd) -> None:
        job = await self.repository.find_by_id(job_id=cmd.job_id)
        if job is None:
            raise PredictionJobNotFoundError(job_id=cmd.job_id)

        job.mark_running()
        await self.repository.save(job=job)

        try:
            prediction_result = self.prediction_engine.predict(
                smiles=str(job.smiles),
                dataset_name=str(job.dataset),
                model_version=str(job.model_version),
                top_k=job.options.top_k,
                return_sequences=job.options.return_sequence,
            )
            job.mark_success(prediction_result)
            await self.repository.save(job=job)
        except Exception as exc:
            job.mark_failed(str(exc))
            await self.repository.save(job=job)
            raise
