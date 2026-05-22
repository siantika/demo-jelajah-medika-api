from __future__ import annotations

from typing import Protocol


class SmilesValidator(Protocol):
    def is_valid(self, *, smiles: str) -> bool: ...
