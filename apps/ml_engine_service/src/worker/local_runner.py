from __future__ import annotations

import argparse
from uuid import uuid4

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
from apps.shared.domain.entities.prediction_job import PredictionJob
from apps.shared.domain.value_objects.dataset import Dataset
from apps.shared.domain.value_objects.model_version import ModelVersion
from apps.shared.domain.value_objects.options import Options
from apps.shared.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from apps.shared.domain.value_objects.smiles import Smiles


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
    parser.add_argument("--dataset", default="KIBA", choices=["KIBA", "DAVIS"])
    parser.add_argument("--smiles", default="CCO")
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    repository = SQLAlchemyPredictionJobRepository()
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
        model_version = "gnn_v1"
    else:
        engine = DummyPredictionEngine()
        model_version = "gnn-1.0.0"
    usecase = RunPredictionJobUseCase(repository=repository, prediction_engine=engine)

    job = PredictionJob(
        id=uuid4(),
        smiles=Smiles(args.smiles),
        dataset=Dataset(args.dataset),
        options=Options(top_k=args.top_k, return_sequence=True),
        model_version=ModelVersion(model_version),
    )
    repository.save(job=job)

    usecase.execute(RunPredictionJobCmd(job_id=job.id))
    updated_job = repository.get_by_id(job_id=job.id)
    if updated_job is None:
        raise RuntimeError("Job was not found after execution")

    print(f"job_id={updated_job.id}")
    print(f"status={updated_job.status.value.value}")
    print(f"result_count={len(updated_job.result)}")
    for idx, item in enumerate(updated_job.result, start=1):
        print(f"{idx}. affinity={item.affinity} target_sequence={item.target_sequence}")


if __name__ == "__main__":
    main()
