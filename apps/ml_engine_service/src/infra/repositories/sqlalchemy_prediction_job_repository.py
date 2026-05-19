from __future__ import annotations

import asyncio
import os
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID, insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from apps.shared.job_management.contracts.repositories.prediction_job_repository import (
    PredictionJobRepository,
)
from apps.shared.job_management.domain.entities.prediction_job import PredictionJob
from apps.shared.job_management.domain.value_objects.dataset import Dataset
from apps.shared.job_management.domain.value_objects.job_status import JobStatus, JobStatusEnum
from apps.shared.job_management.domain.value_objects.model_version import ModelVersion
from apps.shared.job_management.domain.value_objects.options import Options
from apps.shared.job_management.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.job_management.domain.value_objects.smiles import Smiles

metadata = MetaData()

prediction_jobs = Table(
    "prediction_jobs",
    metadata,
    Column("id", PGUUID(as_uuid=True), primary_key=True),
    Column("smiles", Text, nullable=False),
    Column("dataset", String(16), nullable=False),
    Column("top_k", Integer, nullable=False),
    Column("return_sequence", Boolean, nullable=False),
    Column("model_version", String(64), nullable=False),
    Column("status", String(16), nullable=False),
    Column("result", JSONB, nullable=False, default=list),
    Column("error", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


class SQLAlchemyPredictionJobRepository(PredictionJobRepository):
    def __init__(self, database_url: str | None = None) -> None:
        url = database_url or os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is required for SQLAlchemyPredictionJobRepository")

        self._engine: AsyncEngine = create_async_engine(url, pool_pre_ping=True)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        self._schema_ready = False

    def save(self, *, job: PredictionJob) -> None:
        asyncio.run(self._save(job=job))

    def get_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        return asyncio.run(self._get_by_id(job_id=job_id))

    async def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
        self._schema_ready = True

    async def _save(self, *, job: PredictionJob) -> None:
        await self._ensure_schema()
        payload = self._to_row(job)
        stmt = insert(prediction_jobs).values(**payload)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=[prediction_jobs.c.id],
            set_=payload,
        )
        async with self._session_factory() as session:
            await session.execute(upsert_stmt)
            await session.commit()

    async def _get_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        await self._ensure_schema()
        stmt = select(prediction_jobs).where(prediction_jobs.c.id == job_id)
        async with self._session_factory() as session:
            row = (await session.execute(stmt)).mappings().first()
        if row is None:
            return None
        return self._from_row(dict(row))

    @staticmethod
    def _to_row(job: PredictionJob) -> dict:
        return {
            "id": job.id,
            "smiles": str(job.smiles),
            "dataset": str(job.dataset),
            "top_k": job.options.top_k,
            "return_sequence": job.options.return_sequence,
            "model_version": str(job.model_version),
            "status": job.status.value.value,
            "result": [
                {
                    "affinity": item.affinity,
                    "target_sequence": item.target_sequence,
                }
                for item in job.result
            ],
            "error": job.error,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    @staticmethod
    def _from_row(row: dict) -> PredictionJob:
        result_items = [
            PredictionResultItem(
                affinity=float(item["affinity"]),
                target_sequence=str(item["target_sequence"]),
            )
            for item in (row.get("result") or [])
        ]
        return PredictionJob(
            id=UUID(str(row["id"])),
            smiles=Smiles(str(row["smiles"])),
            dataset=Dataset(str(row["dataset"])),
            options=Options(
                top_k=int(row["top_k"]),
                return_sequence=bool(row["return_sequence"]),
            ),
            model_version=ModelVersion(str(row["model_version"])),
            status=JobStatus(JobStatusEnum(str(row["status"]))),
            result=result_items,
            error=row.get("error"),
            created_at=_as_datetime(row["created_at"]),
            updated_at=_as_datetime(row["updated_at"]),
        )


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError(f"Expected datetime value, got {type(value)!r}")
