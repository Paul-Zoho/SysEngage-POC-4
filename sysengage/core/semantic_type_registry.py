"""
Semantic-type accreting registry — §4.4.3c (v0.37 [G]).

Session-scoped (in-memory, per-run) exact-match-or-mint registry.
Never pre-populated. Never rejects a novel term.
Emits PLB-3d-07 soft near-duplicate advisory when a new term is sufficiently
similar to an already-registered term (difflib SequenceMatcher ratio ≥ 0.75).
"""

from __future__ import annotations

import difflib
from typing import Any


_NEAR_DUPLICATE_THRESHOLD = 0.75
_MIN_NEAR_DUP_LEN = 3


class SemanticTypeRegistry:
    """
    Accreting semantic-type registry for one RD pass run.

    Usage::

        registry = SemanticTypeRegistry()
        result = registry.register("monetary_value")
        # result: {"outcome": "minted"|"reused", "near_duplicates": [...]}
        summary = registry.summary()
        # summary: {"minted": 5, "reused": 3, "near_duplicates": [...]}
    """

    def __init__(self) -> None:
        self._known: dict[str, int] = {}
        self._near_dup_warnings: list[dict[str, Any]] = []
        self._minted: int = 0
        self._reused: int = 0

    def register(self, semantic_type: str) -> dict[str, Any]:
        """
        Register one semantic_type token (must be a non-empty string).

        Returns:
            {"outcome": "minted"|"reused", "near_duplicates": list[str]}
        """
        if not semantic_type:
            return {"outcome": "minted", "near_duplicates": []}

        if semantic_type in self._known:
            self._known[semantic_type] += 1
            self._reused += 1
            return {"outcome": "reused", "near_duplicates": []}

        near_dups: list[str] = []
        if len(semantic_type) >= _MIN_NEAR_DUP_LEN:
            for known in self._known:
                if len(known) < _MIN_NEAR_DUP_LEN:
                    continue
                ratio = difflib.SequenceMatcher(None, semantic_type, known).ratio()
                if ratio >= _NEAR_DUPLICATE_THRESHOLD:
                    near_dups.append(known)

        self._known[semantic_type] = 1
        self._minted += 1

        if near_dups:
            self._near_dup_warnings.append(
                {
                    "check_id": "PLB-3d-07",
                    "semantic_type": semantic_type,
                    "near_duplicates": near_dups,
                    "detail": (
                        f"semantic_type {semantic_type!r} is similar to existing "
                        f"term(s) {near_dups!r} — verify these are intentionally distinct"
                    ),
                }
            )

        return {"outcome": "minted", "near_duplicates": near_dups}

    def summary(self) -> dict[str, Any]:
        """Return the registry summary block for mechanism_data (§7)."""
        return {
            "minted": self._minted,
            "reused": self._reused,
            "near_duplicates": self._near_dup_warnings,
        }
