from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api_service.src.application.ports.job_queue import IJobQueue
from apps.api_service.src.application.ports.prediction_job_repository import (
    IPredictionJobRepository,
)
from apps.api_service.src.application.ports.smiles_validator import ISmilesValidator
from apps.api_service.src.application.usecase.create_prediction_usecase import (
    CreatePredictionJobUseCase,
)
from apps.api_service.src.application.usecase.get_prediction_job_usecase import (
    GetPredictionJobUseCase,
)
from apps.api_service.src.infra.repositories.sqlalchemy_prediction_job_repository import (
    SQLAlchemyPredictionJobRepository,
)
from apps.api_service.src.infra.smiles_validator_default import DomainSmilesValidator
from apps.api_service.src.shared.database.session import db_session_dependency


def get_repository(
    db: Annotated[AsyncSession, Depends(db_session_dependency)],
) -> IPredictionJobRepository:
    return SQLAlchemyPredictionJobRepository(db=db)

def get_job_queue() -> IJobQueue:
    pass # return InProcessJobQueue()

def get_smiles_validator() -> ISmilesValidator:
    return DomainSmilesValidator()

def get_create_prediction_usecase(
    repository: Annotated[IPredictionJobRepository, Depends(get_repository)],
    job_queue: Annotated[IJobQueue, Depends(get_job_queue)],
    smiles_validator: Annotated[ISmilesValidator, Depends(get_smiles_validator)],
) -> CreatePredictionJobUseCase:
    return CreatePredictionJobUseCase(
        repository=repository,
        job_queue=job_queue,
        smiles_validator=smiles_validator,
    )


def get_get_prediction_job_usecase(
    repository: Annotated[IPredictionJobRepository, Depends(get_repository)],
) -> GetPredictionJobUseCase:
    return GetPredictionJobUseCase(repository=repository)


CreatePredictionUseCaseDep = Annotated[CreatePredictionJobUseCase, Depends(get_create_prediction_usecase)]
GetPredictionJobUseCaseDep = Annotated[GetPredictionJobUseCase, Depends(get_get_prediction_job_usecase)]
RepositoryDep = Annotated[IPredictionJobRepository, Depends(get_repository)]
