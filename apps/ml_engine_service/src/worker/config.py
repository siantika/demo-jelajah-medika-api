from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from apps.shared.src.queues import MLQueue


class WorkerSettings(BaseSettings):
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    queue_key: str = Field(
        MLQueue.QUEUED,
        validation_alias=AliasChoices("ML_QUEUE_KEY", "REDIS_QUEUE_KEY"),
    )
    assets_root: str = Field(".", alias="ML_ASSETS_ROOT")
    poll_interval: float = Field(1.0, alias="ML_WORKER_POLL_INTERVAL")
    gnn_features: int = Field(40, alias="ML_GNN_FEATURES")
    gnn_depth: int = Field(3, alias="ML_GNN_DEPTH")
    mlp_depth: int = Field(2, alias="ML_MLP_DEPTH")
    max_retries: int = Field(3, alias="ML_MAX_RETRIES")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


def load_worker_settings() -> WorkerSettings:
    return WorkerSettings()
