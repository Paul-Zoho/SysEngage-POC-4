"""
Shared in-memory types for CCI Construction mechanism.

CandidateCCI: in-memory struct for a candidate CCI before identifier allocation.
ExistingCCIUpdate: in-memory struct for an update to be applied to an existing CCI.

These are the transport types between Steps 3, 4, and 5.
No DB interaction in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CandidateCCI:
    """
    In-memory candidate CCI struct produced by Stage 3b and surviving Step 4.

    ci_id is None until Step 5 allocates the identifier.
    cell_id is derived deterministically from column: ZC-R{row_ref}-C-{column}.
    """

    cell_id: str
    column: str
    classification_type: str
    description: str
    signal_refs: list[str]
    confidence: float
    trigger_condition: Optional[str]
    justification: Optional[str]
    ci_id: Optional[str] = None


@dataclass
class ExistingCCIUpdate:
    """
    In-memory record of an update to be applied to an existing committed CCI.

    Produced by Stage 4c when a new candidate is determined to be a duplicate
    of an existing CCI.  The existing ci_id is preserved unconditionally.

    merged_signal_refs: union of existing + candidate signal_refs (sorted).
    merged_confidence: max(existing, candidate).
    merged_description: AI merged_description if non-null; otherwise original.
    original_descriptions: [existing_desc, candidate_desc] for audit trail.
    """

    ci_id: str
    cell_id: str
    merged_signal_refs: list[str]
    merged_confidence: float
    merged_description: str
    original_descriptions: list[str]


@dataclass
class MergeRecord:
    """Audit record stored in AnalysisPass outputs.cci_data.merges."""

    surviving_ci_id: str
    original_descriptions: list[str]
    merged_signal_refs: list[str]

    def to_dict(self) -> dict:
        return {
            "surviving_ci_id": self.surviving_ci_id,
            "original_descriptions": self.original_descriptions,
            "merged_signal_refs": self.merged_signal_refs,
        }


@dataclass
class ConsolidationFlag:
    """Audit record stored in AnalysisPass outputs.cci_data.consolidation_flags."""

    cell_id: str
    candidates_in: int
    ccis_out: int
    ratio: float

    def to_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "candidates_in": self.candidates_in,
            "ccis_out": self.ccis_out,
            "ratio": round(self.ratio, 4),
        }
