from __future__ import annotations

from apps.api.src.modules.job_management.application.ports.smiles_validator import SmilesValidator
from apps.shared.job_management.domain.value_objects.smiles import Smiles


class DomainSmilesValidator(SmilesValidator):
    def is_valid(self, *, smiles: str) -> bool:
        try:
            Smiles(smiles)
            return True
        except Exception:
            return False
