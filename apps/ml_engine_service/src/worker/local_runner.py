from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.ml_engine_service.src.application.usecase.run_prediction_job_usecase import (
    RunPredictionJobCmd,
    RunPredictionJobUseCase,
)
from apps.ml_engine_service.src.infra.integrations.gnn_predictor import (
    GNNPredictionEngine,
)
from apps.ml_engine_service.src.infra.repositories.sqlalchemy_prediction_job_repository import (
    SQLAlchemyPredictionJobRepository,
)
from apps.shared.src.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)


class DummyPredictionEngine:
    def predict(
        self,
        *,
        smiles: str,
        dataset_name: str,
        model_version: str,
        top_k: int,
        return_sequences: bool,
    ) -> list[PredictionResultItem]:
        del smiles, dataset_name, model_version, top_k, return_sequences
        return [
            PredictionResultItem(affinity=0.91, target_sequence="ACDEFGHIK"),
            PredictionResultItem(affinity=0.84, target_sequence="LMNPQRSTV"),
        ]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local runner for ML inference without Celery.")
    parser.add_argument("--mode", choices=["real", "dummy"], default="real")
    parser.add_argument(
        "--assets-root",
        default="/home/sian/sian/projects/jelajah_medika/api/prod",
        help="Root directory containing static/models and static/data",
    )
    parser.add_argument("--job-id", required=True, help="Existing job ID in jobs table")
    return parser.parse_args()


def _load_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    env_file = Path(".env")
    if env_file.exists():
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip().upper() == "DATABASE_URL":
                parsed = value.strip().strip('"').strip("'")
                if parsed:
                    return parsed

    raise RuntimeError("DATABASE_URL is required (env var or .env at project root)")


async def _main() -> None:
    args = _parse_args()
    database_url = _load_database_url()

    engine_db = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        bind=engine_db,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        repository = SQLAlchemyPredictionJobRepository(db=session)

        if args.mode == "real":
            engine = GNNPredictionEngine(
                assets_root=args.assets_root,
                args={
                    "features": 40,
                    "GNN_depth": 3,
                    "MLP_depth": 2,
                    "mode": "regression",
                },
            )
        else:
            engine = DummyPredictionEngine()
        usecase = RunPredictionJobUseCase(repository=repository, prediction_engine=engine)

        await usecase.execute(RunPredictionJobCmd(job_id=UUID(args.job_id)))
        updated_job = await repository.find_by_id(job_id=UUID(args.job_id))
        if updated_job is None:
            raise RuntimeError("Job was not found after execution")

        print(f"job_id={updated_job.id}")
        print(f"status={updated_job.status.value.value}")
        print(f"result_count={len(updated_job.result)}")
        for idx, item in enumerate(updated_job.result, start=1):
            print(f"{idx}. affinity={item.affinity} target_sequence={item.target_sequence}")
    await engine_db.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
