from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from apps.api_service.src.api.dependencies import (
    CreatePredictionUseCaseDep,
    GetPredictionJobUseCaseDep,
    GetQueueMetricsUseCaseDep,
)
from apps.api_service.src.api.schemas import (
    JobStatusResponse,
    PredictionCreateRequest,
    PredictionCreateResponse,
    PredictionItem,
    QueueMetricsResponse,
)
from apps.api_service.src.application.dto import (
    CreatePredictionCmd,
    GetPredictionJobQuery,
    PredictionOptionsCmd,
)

router = APIRouter(prefix="/api/v1", tags=["api_service"])


@router.post("/predictions", response_model=PredictionCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_prediction(
    request: PredictionCreateRequest,
    usecase: CreatePredictionUseCaseDep,
) -> PredictionCreateResponse:
    result = await usecase.execute(
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

    return PredictionCreateResponse(
        job_id=result.id,
        status=result.status.value,
        created_at=result.created_at,
        status_url=f"/api/v1/jobs/{result.id}",
        model_version=request.model_version,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_prediction_job(
    job_id: UUID,
    usecase: GetPredictionJobUseCaseDep,
) -> JobStatusResponse:
    result = await usecase.execute(GetPredictionJobQuery(job_id=job_id))

    items = None
    if result.result is not None:
        items = [
            PredictionItem(
                affinity=item["affinity"],
                sequence_target=item.get("target_sequence") or item.get("sequence_target"),
                target_index=item.get("target_index"),
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


@router.get("/queues/metrics", response_model=QueueMetricsResponse)
async def get_queue_metrics(usecase: GetQueueMetricsUseCaseDep) -> QueueMetricsResponse:
    result = await usecase.execute()
    return QueueMetricsResponse(
        queued=result.queued,
        processing=result.processing,
        retry=result.retry,
        dlq=result.dlq,
    )
