from __future__ import annotations

import asyncio
import hashlib
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from apps.ml_engine_service.src.application.ports.prediction_job_repository import (
    PredictionJobRepository,
)
from apps.shared.domain.entities.prediction_job import PredictionJob
from apps.shared.domain.value_objects.dataset import Dataset
from apps.shared.domain.value_objects.job_status import JobStatus, JobStatusEnum
from apps.shared.domain.value_objects.model_version import ModelVersion
from apps.shared.domain.value_objects.options import Options
from apps.shared.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.domain.value_objects.smiles import Smiles
from apps.shared.infra.db.models.jobs import jobs


class SQLAlchemyPredictionJobRepository(PredictionJobRepository):
    def __init__(
        self,
        database_url: str | None = None,
    ) -> None:
        url = database_url or os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is required for SQLAlchemyPredictionJobRepository")

        self._database_url = url

    def save(self, *, job: PredictionJob) -> None:
        asyncio.run(self._save(job=job))

    def get_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        return asyncio.run(self._get_by_id(job_id=job_id))

    async def _save(self, *, job: PredictionJob) -> None:
        payload = self._to_row(job)
        async with self._engine_ctx() as (_, session_factory):
            stmt = insert(jobs).values(**payload)
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=[jobs.c.id],
                set_=payload,
            )
            async with session_factory() as session:
                await session.execute(upsert_stmt)
                await session.commit()

    async def _get_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        stmt = select(jobs).where(jobs.c.id == job_id)
        async with self._engine_ctx() as (_, session_factory):
            async with session_factory() as session:
                row = (await session.execute(stmt)).mappings().first()
        if row is None:
            return None
        return self._from_row(dict(row))

    @asynccontextmanager
    async def _engine_ctx(self):
        engine: AsyncEngine = create_async_engine(self._database_url, pool_pre_ping=True)
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        try:
            yield engine, session_factory
        finally:
            await engine.dispose()

    @staticmethod
    def _to_row(job: PredictionJob) -> dict:
        status_map = {
            JobStatusEnum.PENDING: "QUEUED",
            JobStatusEnum.RUNNING: "PROCESSING",
            JobStatusEnum.SUCCESS: "COMPLETED",
            JobStatusEnum.FAILED: "FAILED",
        }
        return {
            "id": job.id,
            "type": "prediction",
            "status": status_map[job.status.value],
            "payload": {
                "smiles": str(job.smiles),
                "dataset": str(job.dataset),
                "top_k": job.options.top_k,
                "return_sequence": job.options.return_sequence,
                "model_version": str(job.model_version),
            },
            "result": [
                {
                    "affinity": item.affinity,
                    "sequence_target": item.target_sequence,
                    "target_index": None,
                }
                for item in job.result
            ],
            "error_message": job.error,
            "idempotency_key": str(job.id),
            "request_hash": _build_request_hash(
                smiles=str(job.smiles),
                dataset=str(job.dataset),
                top_k=job.options.top_k,
                return_sequence=job.options.return_sequence,
                model_version=str(job.model_version),
            ),
            "correlation_id": str(job.id),
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }

    @staticmethod
    def _from_row(row: dict) -> PredictionJob:
        payload = row.get("payload") or {}
        reverse_status_map = {
            "QUEUED": JobStatusEnum.PENDING,
            "PROCESSING": JobStatusEnum.RUNNING,
            "COMPLETED": JobStatusEnum.SUCCESS,
            "FAILED": JobStatusEnum.FAILED,
            "CANCELLED": JobStatusEnum.FAILED,
        }
        result_items = []
        for item in (row.get("result") or []):
            sequence_target = item.get("sequence_target") or item.get("target_sequence")
            if not sequence_target:
                continue
            result_items.append(
                PredictionResultItem(
                    affinity=float(item["affinity"]),
                    target_sequence=str(sequence_target),
                )
            )
        return PredictionJob(
            id=UUID(str(row["id"])),
            smiles=Smiles(str(payload["smiles"])),
            dataset=Dataset(str(payload["dataset"])),
            options=Options(
                top_k=int(payload["top_k"]),
                return_sequence=bool(payload["return_sequence"]),
            ),
            model_version=ModelVersion(str(payload["model_version"])),
            status=JobStatus(reverse_status_map[str(row["status"])]),
            result=result_items,
            error=row.get("error_message"),
            created_at=_as_datetime(row["created_at"]),
            updated_at=_as_datetime(row["updated_at"]),
        )


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError(f"Expected datetime value, got {type(value)!r}")


def _build_request_hash(
    *,
    smiles: str,
    dataset: str,
    top_k: int,
    return_sequence: bool,
    model_version: str,
) -> str:
    payload = {
        "smiles": smiles.strip(),
        "dataset_name": dataset,
        "model_version": model_version,
        "options": {
            "top_k": top_k,
            "return_sequences": return_sequence,
        },
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
