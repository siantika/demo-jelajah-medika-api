from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from apps.api_service.src.api.dependencies import (
    CreatePredictionUseCaseDep,
    GetPredictionJobUseCaseDep,
    RepositoryDep,
)
from apps.api_service.src.api.schemas import (
    JobStatusResponse,
    PredictionCreateRequest,
    PredictionCreateResponse,
    PredictionItem,
)
from apps.api_service.src.application.dto import (
    CreatePredictionCmd,
    GetPredictionJobQuery,
    PredictionOptionsCmd,
)
from apps.shared.job_management_domain.domain.errors import PredictionJobNotFoundError
from apps.shared.job_management_domain.domain.exceptions import InvalidValueObject

router = APIRouter(prefix="/v1", tags=["job_management"])


@router.post("/predictions", response_model=PredictionCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_prediction(
    request: PredictionCreateRequest,
    usecase: CreatePredictionUseCaseDep,
    repository: RepositoryDep,
) -> PredictionCreateResponse:
    try:
        result = usecase.execute(
            CreatePredictionCmd(
                smiles=request.smiles,
                dataset_name=request.dataset_name,
                model_version=request.model_version,
                options=PredictionOptionsCmd(
                    top_k=request.options.top_k if request.options else 100,
                    return_sequences=request.options.return_sequences if request.options else False,
                ),
            )
        )
    except InvalidValueObject as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return PredictionCreateResponse(
        job_id=result.job_id,
        status="PENDING",
        created_at=repository.get_by_id(job_id=result.job_id).created_at,
        status_url=f"/v1/jobs/{result.job_id}",
        model_version=request.model_version,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_prediction_job(
    job_id: UUID,
    usecase: GetPredictionJobUseCaseDep,
) -> JobStatusResponse:
    try:
        result = usecase.execute(GetPredictionJobQuery(job_id=job_id))
    except PredictionJobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    items = None
    if result.result is not None:
        items = [
            PredictionItem(
                affinity=item["affinity"],
                sequence_target=item.get("target_sequence"),
            )
            for item in result.result
        ]

    return JobStatusResponse(
        job_id=result.job_id,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
        result=items,
        metrics=result.metrics,
        error_code=result.error_code,
        error_message=result.error_message,
    )
