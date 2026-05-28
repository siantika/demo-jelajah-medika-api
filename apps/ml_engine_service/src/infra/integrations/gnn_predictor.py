from __future__ import annotations

from pathlib import Path

from apps.ml_engine_service.src.infra.integrations.gnn.predictor import GNNPredictorCore
from apps.shared.src.contracts.i_prediction_engine import PredictionEngine
from apps.shared.src.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)


class GNNPredictionEngine(PredictionEngine):
    def __init__(
        self,
        *,
        assets_root: str,
        args: dict | None = None,
        is_threshold: bool = False,
    ) -> None:
        self.assets_root = Path(assets_root).expanduser().resolve()
        self.args = args or {
            "features": 64,
            "GNN_depth": 2,
            "MLP_depth": 2,
            "mode": "regression",
        }
        self.is_threshold = is_threshold

    def predict(
        self,
        *,
        smiles: str,
        dataset_name: str,
        model_version: str,
        top_k: int,
        return_sequences: bool,
    ) -> list[PredictionResultItem]:
        if model_version != "gnn_v1":
            raise ValueError(f"Unsupported model_version '{model_version}' for GNN predictor")

        predictor = GNNPredictorCore(
            args=self.args,
            dataset_name=dataset_name.lower(),
            is_threshold=self.is_threshold,
            assets_root=self.assets_root,
        )
        raw = predictor.predict_target(smiles)
        rows = raw[:top_k]

        return [
            PredictionResultItem(
                affinity=row["affinity"],
                target_sequence=row["sequence_target"],
            )
            for row in rows
        ]
