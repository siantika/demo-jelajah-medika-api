from __future__ import annotations

from sqlalchemy import Column, DateTime, Enum, Integer, MetaData, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

metadata = MetaData()

jobs = Table(
    "jobs",
    metadata,
    Column("id", PGUUID(as_uuid=True), primary_key=True),
    Column("type", String(100), nullable=False),
    Column(
        "status",
        Enum(
            "QUEUED",
            "PROCESSING",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
            name="job_status_enum",
        ),
        nullable=False,
    ),
    Column("payload", JSONB, nullable=False),
    Column("result", JSONB, nullable=True),
    Column("error_code", String(100), nullable=True),
    Column("error_message", Text, nullable=True),
    Column("retry_count", Integer, nullable=False, default=0),
    Column("max_retries", Integer, nullable=False, default=3),
    Column("next_retry_at", DateTime(timezone=True), nullable=True),
    Column("idempotency_key", String(255), nullable=True, unique=True),
    Column("request_hash", String(255), nullable=True),
    Column("correlation_id", String(100), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
