"""
Entity production — build Signal/Concern ORM models from in-memory raw dicts.

Shared by orchestrator (__init__.py) for in-transaction model construction.
Also provides referential integrity and mutual exclusivity checks (decidable criteria).

LPM constraint: source_text and requirement_text are NEVER modified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from models.signal import SignalModel
from models.concern import ConcernModel


@dataclass
class RowLensRunState:
    """
    In-memory state accumulated across all four stages.
    Holds raw signal/concern/oos data before DB identifiers are assigned.
    """

    signals_raw: list[dict]
    concerns_raw: list[dict]
    out_of_scope_refs: list[str]
    stream1_source_count: int
    stream2_requirement_count: int
    stream2_domain_count: int
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
    requirements_by_id: dict[str, object],
) -> list[dict]:
    """
    Referential integrity sweep (spec §5.4 + decidable criteria SG-1, SG-2, CN-3, CN-4).

    Returns list of failure dicts: {item_id, reason}
    Items in the failure list are excluded from the commit set.
    """
    failures: list[dict] = []
    valid_ids = set(sources_by_id) | set(requirements_by_id)
    row_ref = run_state.row_ref

    for raw in run_state.signals_raw:
        for ref in raw.get("source_refs", []):
            if ref not in valid_ids:
                failures.append(
                    {
                        "item_id": ref,
                        "reason": f"SG-1: Signal source_ref {ref!r} not in Source or Requirement ledger",
                    }
                )
            elif ref in requirements_by_id:
                req = requirements_by_id[ref]
                req_row = int(getattr(req, "row_target", 0))
                if req_row >= row_ref:
                    failures.append(
                        {
                            "item_id": ref,
                            "reason": (
                                f"SG-2: Requirement {ref!r} row_target={req_row} "
                                f"must be < Signal row_target={row_ref}"
                            ),
                        }
                    )

    for raw in run_state.concerns_raw:
        for ref in raw.get("source_refs", []):
            if ref not in valid_ids:
                failures.append(
                    {
                        "item_id": ref,
                        "reason": f"CN-3: Concern source_ref {ref!r} not in Source or Requirement ledger",
                    }
                )
            elif ref in requirements_by_id:
                req = requirements_by_id[ref]
                req_row = int(getattr(req, "row_target", 0))
                if req_row >= row_ref:
                    failures.append(
                        {
                            "item_id": ref,
                            "reason": (
                                f"CN-4: Requirement {ref!r} row_target={req_row} "
                                f"must be < Concern produced_in_row={row_ref}"
                            ),
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
