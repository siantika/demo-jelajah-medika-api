from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class PredictionOptionsCmd:
    top_k: int = 100
    return_sequences: bool = False


@dataclass(frozen=True, kw_only=True)
class CreatePredictionCmd:
    smiles: str
    dataset_name: Literal["davis", "kiba"]
    model_version: str 
    options: Optional[PredictionOptionsCmd] = None
