from dataclasses import dataclass
from enum import Enum

from apps.shared.domain.exceptions import InvalidValueObject


class DatasetEnum(str, Enum):
    KIBA = "KIBA"
    DAVIS = "DAVIS"
    

@dataclass(frozen=True)
class Dataset:
    name: str 
    
    def __post_init__(self):
        raw = self.name
        if raw is None:
            raise InvalidValueObject(
                name="Dataset",
                reason="Dataset cannot be None",
                value=raw,
            )
        s = raw.strip().upper()
        try:
            dataset = DatasetEnum(s)
        except ValueError as exc:
            raise InvalidValueObject(
                name="Dataset",
                reason="Dataset must be one of: KIBA, DAVIS",
                value=raw,
            ) from exc
        object.__setattr__(self, "name", dataset.value)

    def __str__(self) -> str:
        return self.name
