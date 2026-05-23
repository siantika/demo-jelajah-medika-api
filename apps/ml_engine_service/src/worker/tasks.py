from __future__ import annotations

import asyncio
from uuid import UUID

from apps.ml_engine_service.src.application.usecase.run_prediction_job_usecase import (
    RunPredictionJobCmd,
    RunPredictionJobUseCase,
)
from apps.ml_engine_service.src.worker.container import (
    get_prediction_engine,
    get_repository,
)


def run_prediction_job(self, *, job_id: str) -> None:
    usecase = RunPredictionJobUseCase(
        repository=get_repository(),
        prediction_engine=get_prediction_engine(),
    )
    asyncio.run(usecase.execute(RunPredictionJobCmd(job_id=UUID(job_id))))
