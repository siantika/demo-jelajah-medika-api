from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from apps.api.src.modules.job_management_api.application.ports.job_queue import JobQueue
from apps.api.src.modules.job_management_api.application.ports.prediction_job_repository import (
    PredictionJobRepository,
)
from apps.api.src.modules.job_management_api.application.ports.smiles_validator import SmilesValidator
from apps.api.src.modules.job_management_api.application.usecase.create_prediction_usecase import (
    CreatePredictionJobUseCase,
)
from apps.api.src.modules.job_management_api.application.usecase.get_prediction_job_usecase import (
    GetPredictionJobUseCase,
)
def get_repository(request: Request) -> PredictionJobRepository:
    return request.app.state.prediction_repository


def get_job_queue(request: Request) -> JobQueue:
    return request.app.state.job_queue


def get_smiles_validator(request: Request) -> SmilesValidator:
    return request.app.state.smiles_validator


def get_create_prediction_usecase(
    repository: Annotated[PredictionJobRepository, Depends(get_repository)],
    job_queue: Annotated[JobQueue, Depends(get_job_queue)],
    smiles_validator: Annotated[SmilesValidator, Depends(get_smiles_validator)],
) -> CreatePredictionJobUseCase:
    return CreatePredictionJobUseCase(
        repository=repository,
        job_queue=job_queue,
        smiles_validator=smiles_validator,
    )


def get_get_prediction_job_usecase(
    repository: Annotated[PredictionJobRepository, Depends(get_repository)],
) -> GetPredictionJobUseCase:
    return GetPredictionJobUseCase(repository=repository)


CreatePredictionUseCaseDep = Annotated[CreatePredictionJobUseCase, Depends(get_create_prediction_usecase)]
GetPredictionJobUseCaseDep = Annotated[GetPredictionJobUseCase, Depends(get_get_prediction_job_usecase)]
RepositoryDep = Annotated[PredictionJobRepository, Depends(get_repository)]
