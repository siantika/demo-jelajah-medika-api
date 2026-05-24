from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequestedPayload(BaseModel):
    job_id: UUID
    smiles: str
    dataset_name: str
    model_version: str
    top_k: int = Field(default=10, ge=1)
    return_sequences: bool = True


class PredictionRequestedMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: Literal["prediction.requested"] = "prediction.requested"
    schema_version: Literal[1] = 1
    message_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: PredictionRequestedPayload
