from __future__ import annotations

import os
from datetime import datetime
from uuid import UUID

from apps.api.src.job_management_api.application.ports.prediction_job_repository import (
    PredictionJobRepository,
)
from sqlalchemy import (
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apps.shared.job_management_domain.domain.entities.prediction_job import (
    PredictionJob,
)
from apps.shared.job_management_domain.domain.value_objects.dataset import Dataset
from apps.shared.job_management_domain.domain.value_objects.job_status import (
    JobStatus,
    JobStatusEnum,
)
from apps.shared.job_management_domain.domain.value_objects.model_version import (
    ModelVersion,
)
from apps.shared.job_management_domain.domain.value_objects.options import Options
from apps.shared.job_management_domain.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.job_management_domain.domain.value_objects.smiles import Smiles
from apps.shared.job_management_domain.infra.db.models.prediction_jobs import (
    prediction_jobs,
)


class SQLAlchemyPredictionJobRepository(PredictionJobRepository):
    """
    Async SQLAlchemy implementation of PredictionJobRepository.

    Lifecycle
    ---------
    The engine and connection pool are created once in __init__ and shared
    across all operations.  Call ``await repo.dispose()`` (e.g. in an app
    shutdown / lifespan handler) to cleanly close the pool.

    Usage with FastAPI lifespan
    ---------------------------
    ```python
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repo = SQLAlchemyPredictionJobRepository()
        app.state.repo = repo
        yield
        await repo.dispose()
    ```
    """

    def __init__(self, database_url: str | None = None) -> None:
        url = database_url or os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is required for SQLAlchemyPredictionJobRepository")

        self._engine: AsyncEngine = create_async_engine(
            url,
            pool_pre_ping=True,   # verify connections before use
            pool_size=10,         # tune to your workload
            max_overflow=20,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    # ------------------------------------------------------------------
    # Public interface (fully async)
    # ------------------------------------------------------------------

    async def create(self, *, job: PredictionJob) -> None:
        """Persist a new PredictionJob.  Raises IntegrityError on duplicate id."""
        stmt = insert(prediction_jobs).values(**self._to_row(job))
        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()

    async def get_by_id(self, *, job_id: UUID) -> PredictionJob | None:
        """Return the job with the given id, or None if not found."""
        stmt = select(prediction_jobs).where(prediction_jobs.c.id == job_id)
        async with self._session_factory() as session:
            row = (await session.execute(stmt)).mappings().first()
        return self._from_row(dict(row)) if row is not None else None

    async def update_status(
        self,
        *,
        job_id: UUID,
        status: JobStatus,
        result: list[PredictionResultItem] | None = None,
        error: str | None = None,
        updated_at: datetime,
    ) -> None:
        """Update status (and optionally result / error) for an existing job."""
        values: dict = {
            "status": status.value.value,
            "updated_at": updated_at,
        }
        if result is not None:
            values["result"] = [
                {"affinity": item.affinity, "target_sequence": item.target_sequence}
                for item in result
            ]
        if error is not None:
            values["error"] = error

        stmt = (
            update(prediction_jobs)
            .where(prediction_jobs.c.id == job_id)
            .values(**values)
        )
        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()

    async def dispose(self) -> None:
        """Dispose the connection pool.  Call once at application shutdown."""
        await self._engine.dispose()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
    raise TypeError(f"Expected datetime, got {type(value)!r}")
