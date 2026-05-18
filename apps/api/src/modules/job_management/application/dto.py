from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

JobStatus = Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"]


@dataclass(frozen=True)
class PredictionOptionsCmd:
    top_k: int = 100
    return_sequences: bool = False


@dataclass(frozen=True, kw_only=True)
class CreatePredictionCmd:
    smiles: str
    dataset_name: Literal["davis", "kiba"]
    model_version: str 
    options: Optional[PredictionOptionsCmd] = None



@dataclass(frozen=True)
class GetJobStatusResult:
    job_id: UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    result: Optional[list[dict]]
    metrics: Optional[dict]
    error_code: Optional[str]
    error_message: Optional[str]


@dataclass(frozen=True, kw_only=True)
class GetPredictionJobQuery:
    job_id: UUID
