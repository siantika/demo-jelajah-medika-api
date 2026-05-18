
import math
import re
from dataclasses import dataclass

from modules.job_management.domain.exceptions import InvalidValueObject

_AMINO_ACID_PATTERN = re.compile(r"^[ACDEFGHIKLMNPQRSTVWYBXZUO]+$")


@dataclass(frozen=True)
class PredictionResultItem:
    affinity: float
    target_sequence: str

    def __post_init__(self):
        self._validate_affinity(self.affinity)
        normalized = self._validate_sequence(self.target_sequence)

        # Store the normalized version (upper-case, stripped)
        object.__setattr__(self, "target_sequence", normalized)

    @staticmethod
    def _validate_affinity(value: float) -> None:
        if not isinstance(value, (int, float)):
            raise InvalidValueObject(
                name="PredictionResultItem.affinity",
                reason="Affinity must be a number",
                value=value
            )
        if math.isnan(value) or math.isinf(value):
            raise InvalidValueObject(
                name="PredictionResultItem.affinity",
                reason="Affinity must be a finite number",
                value=value
            )

    @staticmethod
    def _validate_sequence(seq: str) -> str:
        if seq is None:
            raise InvalidValueObject(
                name="PredictionResultItem.target_sequence",
                reason="Target sequence cannot be None",
                value=seq
            )
        s = seq.strip().upper()
        if not s:
            raise InvalidValueObject(
                name="PredictionResultItem.target_sequence",
                reason="Target sequence cannot be empty",
                value=seq
            )
        # Reasonable length (you may adjust as needed)
        if len(s) > 10000:
            raise InvalidValueObject(
                name="PredictionResultItem.target_sequence",
                reason="Target sequence is too long",
                value=s
            )
        # Validate common amino acid characters
        if not _AMINO_ACID_PATTERN.match(s):
            raise InvalidValueObject(
                name="PredictionResultItem.target_sequence",
                reason="Target sequence contains invalid amino acid characters",
                value=s
            )
        return s
