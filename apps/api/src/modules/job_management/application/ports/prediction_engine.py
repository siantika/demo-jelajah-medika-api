from __future__ import annotations

from typing import Protocol

from modules.job_management.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)


class PredictionEngine(Protocol):
    def predict(
        self,
        *,
        smiles: str,
        dataset_name: str,
        model_version: str,
        top_k: int,
        return_sequences: bool,
    ) -> list[PredictionResultItem]: ...
