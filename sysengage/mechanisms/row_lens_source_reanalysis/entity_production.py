"""
Entity production — build Signal/Concern ORM models from in-memory raw dicts.

Single-stream realisation of Row-Lens Source Re-Analysis v0.2.
Shared by orchestrator (__init__.py) for in-transaction model construction.
Also provides referential integrity and mutual exclusivity checks (decidable criteria).

LPM constraint: source_text and requirement_text are NEVER modified.

v0.2 changes vs v0.1:
- RowLensRunState: stream1_source_count/stream2_* replaced by source_count
- run_referential_integrity_checks: requirements_by_id param removed;
  valid_ids is Sources only (no Requirement ids valid in single-stream model).
- SR-1 is already enforced by Stage 1 before items reach this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from models.signal import SignalModel
from models.concern import ConcernModel


@dataclass
class RowLensRunState:
    """
    In-memory state accumulated across two stages.
    Holds raw signal/concern/oos data before DB identifiers are assigned.
    """

    signals_raw: list[dict]
    concerns_raw: list[dict]
    out_of_scope_refs: list[str]
    source_count: int
    row_ref: int
    practitioner_id: str
    failure_detail: list[dict] = field(default_factory=list)


def build_signal_model(
    *,
    signal_id: str,
    raw: dict,
    row_ref: int,
    project_id: str,
) -> SignalModel:
    """
    Construct a SignalModel from a raw classification result dict.
    LPM: description characterises content; source_text is never written here.
    """
    return SignalModel(
        signal_id=signal_id,
        signal_type=raw["signal_type"],
        row_target=str(row_ref),
        description=raw["description"],
        source_refs=raw["source_refs"],
        sourceatom_refs=raw.get("sourceatom_refs", []),
        confidence=raw["confidence"],
        derived_from_concern_id=raw.get("derived_from_concern_id"),
        project_id=project_id,
        created_at=datetime.now(timezone.utc),
    )


def build_concern_model(
    *,
    concern_id: str,
    raw: dict,
    row_ref: int,
    project_id: str,
    practitioner_id: str,
) -> ConcernModel:
    """
    Construct a ConcernModel from a raw classification result dict.
    state="Open" at production time per spec §5.1 CN-5 criterion.
    LPM: description characterises content; source_text is never written here.
    """
    return ConcernModel(
        concern_id=concern_id,
        source_refs=raw["source_refs"],
        description=raw["description"],
        state="Open",
        produced_in_row=str(row_ref),
        practitioner_id=practitioner_id,
        dispositioned_with_outcome=None,
        disposition_rationale=None,
        confidence=raw["confidence"],
        project_id=project_id,
        created_at=datetime.now(timezone.utc),
    )


def run_referential_integrity_checks(
    *,
    run_state: RowLensRunState,
    sources_by_id: dict[str, object],
) -> list[dict]:
    """
    Referential integrity sweep — single-stream model (v0.2).

    All source_refs in Signals and Concerns must point at Source elements.
    Requirement ids are not valid in single-stream source_refs — they should
    have been caught by SR-1 in Stage 1, but we re-check here for safety.

    Returns list of failure dicts: {item_id, reason}
    Items in the failure list are excluded from the commit set.
    """
    import re as _re
    _REQ_ID_RE = _re.compile(r"^R\d{3}$")

    failures: list[dict] = []

    for raw in run_state.signals_raw:
        for ref in raw.get("source_refs", []):
            if _REQ_ID_RE.match(str(ref)):
                failures.append(
                    {
                        "item_id": ref,
                        "reason": (
                            f"SR-1: Signal source_ref {ref!r} is a Requirement id — "
                            "not valid in single-stream model (F83)"
                        ),
                    }
                )
            elif ref not in sources_by_id:
                failures.append(
                    {
                        "item_id": ref,
                        "reason": f"SG-1: Signal source_ref {ref!r} not in Source ledger",
                    }
                )

    for raw in run_state.concerns_raw:
        for ref in raw.get("source_refs", []):
            if _REQ_ID_RE.match(str(ref)):
                failures.append(
                    {
                        "item_id": ref,
                        "reason": (
                            f"SR-1: Concern source_ref {ref!r} is a Requirement id — "
                            "not valid in single-stream model (F83)"
                        ),
                    }
                )
            elif ref not in sources_by_id:
                failures.append(
                    {
                        "item_id": ref,
                        "reason": f"CN-3: Concern source_ref {ref!r} not in Source ledger",
                    }
                )

    return failures


def run_mutual_exclusivity_check(*, run_state: RowLensRunState) -> list[dict]:
    """
    ME-1: No source_id may appear in both Signal.source_refs and Concern.source_refs.
    Per spec §5.4: Concern takes precedence; Signal is removed from commit set.

    Returns failure dicts for Signal items that violate ME-1.
    """
    concern_source_ids: set[str] = set()
    for raw in run_state.concerns_raw:
        concern_source_ids.update(raw.get("source_refs", []))

    failures: list[dict] = []
    for raw in run_state.signals_raw:
        for ref in raw.get("source_refs", []):
            if ref in concern_source_ids:
                failures.append(
                    {
                        "item_id": ref,
                        "reason": (
                            f"ME-1: {ref!r} appears in both Signal and Concern source_refs. "
                            "Concern takes precedence; Signal excluded."
                        ),
                    }
                )
    return failures
