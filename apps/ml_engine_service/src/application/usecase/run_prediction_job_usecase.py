from __future__ import annotations

from apps.shared.src.contracts.prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.ml_engine_service.src.application.usecase.dto import RunPredictionJobCmd
from apps.shared.src.contracts.prediction_engine import PredictionEngine
from apps.shared.src.domain.entities.prediction_job import PredictionJob
from apps.shared.src.domain.errors import MLInferenceError, PredictionJobNotFoundError


class RunPredictionJobUseCase:
    def __init__(
        self,
        repository: IPredictionJobRepository,
        prediction_engine: PredictionEngine,
        
    ):
        self.repository = repository
        self.prediction_engine = prediction_engine
       

    async def execute(self, cmd: RunPredictionJobCmd) -> PredictionJob:
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
        except Exception as err:
            job.mark_failed(str(err))
            await self.repository.save(job=job)
            raise MLInferenceError(str(err)) from err

        await self.repository.save(job=job)

        return job
