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

    stage4a_routed is set to True by Stage 4a when conditions 1+2 hold but
    condition 3 (description similarity) fails — indicating the candidate shares
    classification_type and signal_refs with another but has a materially
    different description.  Stage 4b uses named-instance framing for the entire
    group when any member carries this flag.  Never persisted to the ledger.
    """

    cell_id: str
    column: str
    classification_type: str
    description: str
    signal_refs: list[str]
    confidence: float
    stage4a_routed: bool = False
    trigger_condition: Optional[str] = None
    justification: Optional[str] = None
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


@dataclass
class ExecutionWarning:
    """
    Runtime execution condition stored in AnalysisPass outputs.cci_data.execution_warnings.

    warning_type values (per spec v0.11 §4.4):
      step4_read_failure              — SSL/connection drop during existing CCI read
      step4_nonetype_excluded         — malformed CCI excluded from cluster review
      step4_sub_group_split           — group size exceeded cap and was split into sub-groups
      stage4a_named_instance_routed   — one or more candidates in group carry stage4a_routed=True;
                                        named-instance framing variant used for the AI cluster call
    detail is a freeform dict whose structure varies by warning_type.
    """

    warning_type: str
    detail: dict

    def to_dict(self) -> dict:
        return {"warning_type": self.warning_type, "detail": self.detail}
