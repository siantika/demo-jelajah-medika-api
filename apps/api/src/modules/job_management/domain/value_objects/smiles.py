from __future__ import annotations

import re
from dataclasses import dataclass

from modules.job_management.domain.exceptions import InvalidValueObject

_SMILES_ALLOWED_RE = re.compile(r"^[A-Za-z0-9@\+\-\=\#\/\\\.\%\(\)\[\]]+$")


@dataclass(frozen=True)
class Smiles:
    value: str

    def __post_init__(self) -> None:
        raw = self.value
        if raw is None:
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES cannot be None",
                value=raw
            )

        s = raw.strip()
        if not s:
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES cannot be empty",
                value=raw
            )

        # Reasonable length (you may adjust as needed)
        if len(s) > 2000:
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES is too long",
                value=s
            )

        # SMILES must not contain whitespace
        if any(ch.isspace() for ch in s):
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES must not contain whitespace",
                value=s
            )

        # Sanity check for common SMILES characters
        # (element letters, ring closure digits, bond symbols, brackets/parentheses, % for ring >9, etc)
        if not _SMILES_ALLOWED_RE.match(s):
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES contains invalid characters",
                value=s
            )

        # Check balance of () and [] (and no closing before opening)
        self._check_balanced(s)

        # Check simple ring closure digits: each digit 0-9 must appear an even number of times
        # (this is a rough rule but effective for common typos)
        self._check_ring_digits_even(s)

        # normalisasi: simpan versi stripped
        object.__setattr__(self, "value", s)
    
    def __str__(self) -> str:
        return self.value

    @staticmethod
    def _check_balanced(s: str) -> None:
        paren = 0
        bracket = 0
        for ch in s:
            if ch == "(":
                paren += 1
            elif ch == ")":
                paren -= 1
                if paren < 0:
                    raise InvalidValueObject(
                        name="Smiles",
                        reason="SMILES has unmatched ')'",
                        value=s
                    )

            elif ch == "[":
                bracket += 1
            elif ch == "]":
                bracket -= 1
                if bracket < 0:
                    raise InvalidValueObject(
                        name="Smiles",
                        reason="SMILES has unmatched ']'",
                        value=s
                    )

        if paren != 0:
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES has unbalanced parentheses '()'",
                value=s
            )
        if bracket != 0:
            raise InvalidValueObject(
                name="Smiles",
                reason="SMILES has unbalanced brackets '[]'",
                value=s
            )

    @staticmethod
    def _check_ring_digits_even(s: str) -> None:
        # Ignore digits that appear after '%' (two-digit ring index, e.g. %10)
        # Remove %dd pattern so those digits are not counted.
        s_wo_percent = re.sub(r"%\d{2}", "", s)

        counts = [0] * 10
        for ch in s_wo_percent:
            if ch.isdigit():
                counts[ord(ch) - 48] += 1

        # Ring closures usually appear in pairs (e.g. C1CCCCC1)
        for d, c in enumerate(counts):
            if c % 2 != 0:
                raise InvalidValueObject(
                    name="Smiles",
                    reason=f"SMILES has unpaired ring digit '{d}'",
                    value=s
                )
