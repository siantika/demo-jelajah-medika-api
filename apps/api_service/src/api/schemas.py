from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StrictSchema(BaseModel):
    class Config:
        extra = "forbid"  # Reject unexpected fields for every schema


# ===== OPTIONS =====

class PredictionOptions(StrictSchema):
    """Options for prediction job."""
    top_k: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Return top-k highest affinity results",
        example=100
    )
    return_sequences: Optional[bool] = Field(
        default=False,
        description="Whether to include full protein sequence in response",
        example=False
    )


# ===== REQUEST =====

class PredictionCreateRequest(StrictSchema):
    """Request schema for creating a prediction job."""
    smiles: str = Field(
        ..., min_length=1, max_length=2000,
        description="SMILES string of the molecule",
        example="CCO"
    )
    dataset_name: Literal["davis", "kiba"] = Field(
        ..., description="Dataset to use for prediction.", example="davis"
    )
    model_version: str = Field(
        default="gnn_v1", min_length=1, max_length=64,
        description="Model version to use for prediction.",
        example="gnn_v1"
    )
    options: Optional[PredictionOptions] = Field(
        default=None, description="Additional prediction options."
    )
    
class PredictionCreateResponse(StrictSchema):
    """Response schema after creating a prediction job."""
    job_id: UUID = Field(..., description="Job identifier.", example="123e4567-e89b-12d3-a456-426614174000")
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"] = Field(..., description="Job status.", example="PENDING")
    created_at: datetime = Field(..., description="Job creation timestamp.")
    status_url: str = Field(..., description="URL to check job status.", example="/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000")
    model_version: str = Field(..., description="Model version used.", example="gnn_v1")

class PredictionItem(StrictSchema):
    """Single prediction result item."""
    affinity: float = Field(..., description="Predicted affinity value.", example=13.91)
    sequence_target: Optional[str] = Field(
        default=None, description="Protein sequence (if return_sequences=True).", example="ERFELGDGRKPVK..."
    )
    target_index: Optional[int] = Field(
        default=None, description="Target index (if return_sequences=False).", example=0
    )

class JobMetrics(StrictSchema):
    """Metrics for prediction job."""
    queue_ms: Optional[int] = Field(default=None, description="Queue waiting time in ms.", example=50)
    inference_ms: Optional[int] = Field(default=None, description="Inference time in ms.", example=900)
    total_ms: Optional[int] = Field(default=None, description="Total time in ms.", example=980)
    model_backend: Optional[str] = Field(default=None, description="Model backend identifier.", example="legacy_gnn")
    model_version: Optional[str] = Field(default=None, description="Model version used for inference.", example="gnn_v1")

class JobStatusResponse(StrictSchema):
    """Status and result of a prediction job."""
    job_id: UUID = Field(..., description="Job identifier.", example="123e4567-e89b-12d3-a456-426614174000")
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"] = Field(..., description="Job status.", example="SUCCESS")
    created_at: datetime = Field(..., description="Job creation timestamp.")
    updated_at: datetime = Field(..., description="Job last update timestamp.")
    result: Optional[List[PredictionItem]] = Field(default=None, description="Prediction results.")
    metrics: Optional[JobMetrics] = Field(default=None, description="Job metrics.")
    error_code: Optional[str] = Field(default=None, description="Error code if job failed.")
    error_message: Optional[str] = Field(default=None, description="Error message if job failed.")


class QueueMetricsResponse(StrictSchema):
    """Basic queue metrics from Redis."""
    queued: int = Field(..., ge=0, description="Number of jobs waiting in queued list.", example=12)
    processing: int = Field(..., ge=0, description="Number of jobs currently being processed.", example=3)
    retry: int = Field(..., ge=0, description="Number of jobs in retry schedule.", example=2)
    dlq: int = Field(..., ge=0, description="Number of jobs moved to dead-letter queue.", example=1)
