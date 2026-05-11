"""
Source Capture mechanism — orchestration entry point.

Per Implementation Spec v0.4 §3.1 and §1 (Module location).

Exposes run_source_capture() as the single entry point for the mechanism.
Internally sequences Passes 0 → 0A → 0B → 0C.

Pass names (v0.4 canonical):
  Pass 0  — Read Witness
  Pass 0A — Source Capture (sentence-level)
  Pass 0B — Segment Construction (heading-based)
  Pass 0C — SourceAtom Splitting (default no-op in v1)

Entity persistence order (v2.11 canonical):
  1. Sources (Pass 0A output) — assigned IDs first; form the anchor for source_refs.
  2. Segments (Pass 0B output) — source_refs populated from assigned Source IDs.
  3. SourceAtoms (Pass 0C output) — reference their parent Source via source_ref.

Critical architectural commitments enforced here:
  1. LPM byte-preservation: Source Pydantic models frozen=True (schemas/source.py).
  2. Mode declaration: @pass_mode("LPM") on each Pass function.
  3. Mechanism provenance on AnalysisPass.outputs (F4/F10).
  4. One Postgres transaction per execution — all entities commit atomically.
     On failure: rollback main transaction; commit AnalysisPass failure record
     in a separate transaction for auditability (Row 4 Applied §5).
  5. Identifier sequencing via Postgres sequences (core/db.py).

Transactional discipline (Row 4 Applied §5):
  - Project + Stakeholder records committed in an isolated mini-transaction FIRST.
    This ensures they exist as FK anchors even if the main transaction rolls back.
  - All canonical entities (Source, Segment, SourceAtom, AnalysisPass) commit
    atomically in ONE main transaction on success.
  - On failure: main transaction rolls back; AnalysisPass failure record commits
    in a SEPARATE transaction (also relies on project+stakeholder existing).

Re-execution semantics (Implementation Spec v0.4 §10.4):
  - Detect existing Sources via input_hash match on prior AnalysisPass records.
  - If hash matches an existing successful execution for this project: skip.
  - If no match: run all Passes and append new entities.
  - Existing entities never modified (LPM).

Canonical field changes from v0.3 → v0.4:
  - Source: no longer carries segment_id FK (F24 fix). Sources are autonomous.
  - Segment: carries source_refs = list of source_ids (canonical v2.11 relation).
  - AnalysisPass: carries pass_type, mechanism, evaluated_scope, confidence (F25/F27 fix).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from core.audit_trail import (
    create_analysis_pass_record,
    finalise_pass_success,
    finalise_pass_partial_success,
    persist_analysis_pass,
    commit_failure_pass,
)
from core.db import (
    get_session,
    get_next_sequence_value,
    get_next_n_sequence_values,
    format_identifier,
)
from core.modes.decorator import ModeViolationError
from mechanisms.source_capture.errors import (
    EmptyInputError,
    InputAccessError,
    UnsupportedFormatError,
    SegmentationPolicyError,
)
from mechanisms.source_capture.pass_0_read_witness import run_pass_0
from mechanisms.source_capture.pass_0a_source_capture import run_pass_0a
from mechanisms.source_capture.pass_0b_segment_construction import run_pass_0b
from mechanisms.source_capture.pass_0c_source_atom_splitting import run_pass_0c
from mappers.source_capture import (
    source_pydantic_to_sqlalchemy,
    segment_pydantic_to_sqlalchemy,
)
from models.project import ProjectModel
from models.stakeholder import StakeholderModel
from schemas.source import Source
from schemas.segment import Segment


@dataclass
class SourceCaptureResult:
    """
    Result of a Source Capture mechanism execution.
    Contains the assigned pass_id, entity counts, and all produced IDs for the caller.

    segment_ids and atom_ids are included so export_ledger() can scope DB queries
    using the explicit IDs assigned during this run without needing an extra DB
    column or a secondary lookup.
    """

    pass_id: str
    execution_status: str
    source_count: int
    segment_count: int
    source_atom_count: int
    source_ids: list[str]
    segment_ids: list[str] = None  # type: ignore[assignment]
    atom_ids: list[str] = None  # type: ignore[assignment]
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.segment_ids is None:
            self.segment_ids = []
        if self.atom_ids is None:
            self.atom_ids = []


def run_source_capture(
    file_path: Path,
    *,
    project_id: str,
    practitioner_id: str,
    read_mode: str = "Full",
    segmentation_policy: str = "default",
    re_execution_context: dict[str, Any] | None = None,
) -> SourceCaptureResult:
    """
    Execute the Source Capture mechanism end-to-end.

    Passes: 0 (Read Witness) → 0A (Source Capture, sentence-level) →
            0B (Segment Construction) → 0C (SourceAtom Splitting, no-op in v1).

    Entity persistence order:
      Sources first (IDs needed for Segment.source_refs) → flush →
      Segments (source_refs populated from Source IDs) → flush →
      SourceAtoms (reference parent Source via source_ref).

    Transactional discipline (Row 4 Applied §5):
      Step 1: Commit project+stakeholder in isolated mini-transaction (survives rollback).
      Step 2: Run mechanism; all entities commit atomically in ONE main transaction.
      Step 3: On failure: rollback main; commit AnalysisPass failure in SEPARATE transaction.

    Re-execution: if re_execution_context is provided, checks input_hash against
    existing AnalysisPass records. Skips if already captured; proceeds if new input.
    """
    pass_data = create_analysis_pass_record(
        project_id=project_id,
        practitioner_id=practitioner_id,
        pass_type="Universal",
        mechanism="SourceCapture",
        evaluated_scope="All input material in this project",
        confidence=1.0,
    )

    # --- Step 1: Commit project+stakeholder in isolated mini-transaction ---
    # CRITICAL: must happen BEFORE main session so FK anchors survive main-transaction rollback.
    _ensure_project_committed(project_id)
    _ensure_stakeholder_committed(practitioner_id)

    session = get_session()

    try:
        # --- Pass 0: Read Witness ---
        try:
            read_witness, decode_result = run_pass_0(file_path, read_mode=read_mode)
        except EmptyInputError as exc:
            session.close()
            _abort(pass_data, _sanitize(str(exc)), "Pass 0")
            return SourceCaptureResult(
                pass_id=commit_failure_pass(pass_data),
                execution_status="Failed",
                source_count=0,
                segment_count=0,
                source_atom_count=0,
                source_ids=[],
                failure_reason=_sanitize(str(exc)),
            )
        except (InputAccessError, UnsupportedFormatError) as exc:
            session.close()
            _abort(pass_data, _sanitize(str(exc)), "Pass 0")
            return SourceCaptureResult(
                pass_id=commit_failure_pass(pass_data),
                execution_status="Failed",
                source_count=0,
                segment_count=0,
                source_atom_count=0,
                source_ids=[],
                failure_reason=_sanitize(str(exc)),
            )

        # --- Re-execution check ---
        if re_execution_context is not None:
            existing_hash = _find_existing_hash(
                session, project_id, read_witness["input_hash"]
            )
            if existing_hash:
                session.close()
                pass_data2 = create_analysis_pass_record(
                    project_id=project_id,
                    practitioner_id=practitioner_id,
                    pass_type="Universal",
                    mechanism="SourceCapture",
                    evaluated_scope="All input material in this project",
                    confidence=1.0,
                )
                _abort(
                    pass_data2,
                    f"Re-execution skipped: input already captured "
                    f"(hash={read_witness['input_hash'][:8]}...)",
                    "Pass 0",
                )
                return SourceCaptureResult(
                    pass_id=commit_failure_pass(pass_data2),
                    execution_status="Failed",
                    source_count=0,
                    segment_count=0,
                    source_atom_count=0,
                    source_ids=[],
                    failure_reason="already_captured",
                )

        # --- Pass 0A: Source Capture (sentence-level) ---
        try:
            source_specs = run_pass_0a(decode_result, policy=segmentation_policy)
        except SegmentationPolicyError as exc:
            session.close()
            _abort(pass_data, _sanitize(str(exc)), "Pass 0A")
            return SourceCaptureResult(
                pass_id=commit_failure_pass(pass_data),
                execution_status="Failed",
                source_count=0,
                segment_count=0,
                source_atom_count=0,
                source_ids=[],
                failure_reason=_sanitize(str(exc)),
            )

        # --- Pass 0B: Segment Construction ---
        try:
            segment_specs = run_pass_0b(
                decode_result, source_specs, policy=segmentation_policy
            )
        except SegmentationPolicyError as exc:
            session.close()
            _abort(pass_data, _sanitize(str(exc)), "Pass 0B")
            return SourceCaptureResult(
                pass_id=commit_failure_pass(pass_data),
                execution_status="Failed",
                source_count=0,
                segment_count=0,
                source_atom_count=0,
                source_ids=[],
                failure_reason=_sanitize(str(exc)),
            )

        # --- Pass 0C: SourceAtom Splitting (no-op in v1, produce_atoms_for_prose=False) ---
        atom_specs = run_pass_0c(source_specs)

        # --- Assign IDs and persist in ONE transaction ---
        source_ids: list[str] = []
        segment_ids: list[str] = []
        atom_ids: list[str] = []

        # 1. Persist Sources FIRST — IDs needed for Segment.source_refs.
        src_index_to_id: dict[int, str] = {}
        non_text_ids: list[str] = []
        decoding_issue_ids: list[str] = []

        for src_idx, src_spec in enumerate(source_specs):
            seq_val = get_next_sequence_value(session, "s_id_seq")
            src_id = format_identifier("S", seq_val)
            source_ids.append(src_id)
            src_index_to_id[src_idx] = src_id

            source = Source(
                source_id=src_id,
                source_text=src_spec.source_text,
                segmentation_context=src_spec.segmentation_context,
                input_material_ref=str(file_path),
                confidence=1.0,
                is_non_text=src_spec.is_non_text,
                has_decoding_issues=src_spec.has_decoding_issues,
                project_id=project_id,
            )
            session.add(source_pydantic_to_sqlalchemy(source))

            if src_spec.is_non_text:
                non_text_ids.append(src_id)
            if src_spec.has_decoding_issues:
                decoding_issue_ids.append(src_id)

        # Flush Sources so IDs exist in the session before building source_refs.
        session.flush()

        # 2. Persist Segments — source_refs built from assigned Source IDs.
        src_index_to_seg_id: dict[int, str] = {}

        for seg_spec in segment_specs:
            seq_val = get_next_sequence_value(session, "seg_id_seq")
            seg_id = format_identifier("SEG", seq_val)
            segment_ids.append(seg_id)

            source_refs = [
                src_index_to_id[i]
                for i in seg_spec.source_spec_indices
                if i in src_index_to_id
            ]

            segment = Segment(
                segment_id=seg_id,
                title=seg_spec.title,
                description=seg_spec.description,
                source_refs=source_refs,
                project_id=project_id,
            )
            session.add(segment_pydantic_to_sqlalchemy(segment))

            for src_idx in seg_spec.source_spec_indices:
                src_index_to_seg_id[src_idx] = seg_id

        # Flush Segments before SourceAtom inserts so FK constraints are satisfied.
        session.flush()

        # 3. Persist SourceAtoms — bulk insert for performance.
        # Fetch ALL atom sequence values in ONE round trip, then ONE bulk INSERT.
        # This is critical for large inputs: individual inserts take >60s; bulk <2s.
        if atom_specs:
            sa_seq_vals = get_next_n_sequence_values(
                session, "sa_id_seq", len(atom_specs)
            )
            atom_rows: list[dict] = []
            now = datetime.now(timezone.utc)
            for atom_spec, seq_val in zip(atom_specs, sa_seq_vals):
                atom_id = format_identifier("SA", seq_val)
                atom_ids.append(atom_id)

                parent_src_id = src_index_to_id.get(atom_spec.source_spec_index, "")
                seg_id_for_atom = src_index_to_seg_id.get(atom_spec.source_spec_index)
                atom_rows.append(
                    {
                        "atom_id": atom_id,
                        "atom_text": atom_spec.atom_text,
                        "source_ref": parent_src_id,
                        "segment_ref": seg_id_for_atom,
                        "parent_atom_ref": None,
                        "confidence": 1.0,
                        "position": atom_spec.position,
                        "project_id": project_id,
                        "created_at": now,
                    }
                )

            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from models.source_atom import SourceAtomModel

            session.execute(pg_insert(SourceAtomModel), atom_rows)

        # 4. Build mechanism_data
        mechanism_data: dict[str, Any] = {
            "source_count": len(source_ids),
            "segment_count": len(segment_ids),
            "source_atom_count": len(atom_ids),
            "source_ids": source_ids,
            "cross_source_ordering": [],
            "non_text_source_ids": non_text_ids,
            "source_with_decoding_issues_ids": decoding_issue_ids,
        }

        # 5. Finalise AnalysisPass
        if not decode_result.read_completion_status:
            finalise_pass_partial_success(
                pass_data,
                read_witness=read_witness,
                mechanism_data=mechanism_data,
                failure_reason=decode_result.partial_failure_detail,
            )
        else:
            finalise_pass_success(
                pass_data,
                read_witness=read_witness,
                mechanism_data=mechanism_data,
            )

        pass_id = persist_analysis_pass(session, pass_data)

        # 6. Commit — ONE transaction for all entities + AnalysisPass
        session.commit()

        return SourceCaptureResult(
            pass_id=pass_id,
            execution_status=pass_data["execution_status"],
            source_count=len(source_ids),
            segment_count=len(segment_ids),
            source_atom_count=len(atom_ids),
            source_ids=source_ids,
            segment_ids=segment_ids,
            atom_ids=atom_ids,
        )

    except ModeViolationError as exc:
        session.rollback()
        session.close()
        violation_detail = {
            "mode": exc.mode,
            "violation_detail": exc.violation_detail,
            "original": str(exc.original),
        }
        pass_data.setdefault("mode_violations", []).append(violation_detail)
        _abort(pass_data, _sanitize(f"Mode violation: {exc.violation_detail}"), "unknown")
        return SourceCaptureResult(
            pass_id=commit_failure_pass(pass_data),
            execution_status="Failed",
            source_count=0,
            segment_count=0,
            source_atom_count=0,
            source_ids=[],
            failure_reason=_sanitize(str(exc)),
        )

    except Exception as exc:
        try:
            session.rollback()
        except Exception:
            pass
        try:
            session.close()
        except Exception:
            pass
        reason = _sanitize(f"Unexpected error: {exc}")
        _abort(pass_data, reason, "unknown")
        return SourceCaptureResult(
            pass_id=commit_failure_pass(pass_data),
            execution_status="Failed",
            source_count=0,
            segment_count=0,
            source_atom_count=0,
            source_ids=[],
            failure_reason=reason,
        )

    finally:
        try:
            session.close()
        except Exception:
            pass


def _sanitize(text: str) -> str:
    """
    Remove NUL bytes (\\x00) from strings before DB insert.

    psycopg2 rejects NUL characters in VARCHAR/TEXT columns.
    Binary fixtures (e.g., .xyz with embedded NUL bytes) can produce
    error messages containing NUL bytes when the exception text is captured.
    """
    return text.replace("\x00", "")


def _abort(pass_data: dict[str, Any], reason: str, failed_pass: str) -> None:
    """Update pass_data in-place for failure finalisation."""
    start = pass_data.pop("_start_monotonic", time.monotonic())
    elapsed = time.monotonic() - start
    pass_data["execution_status"] = "Failed"
    pass_data["pass_completed_at"] = datetime.now(timezone.utc)
    pass_data["elapsed_ms"] = int(elapsed * 1000)
    pass_data["outputs"] = {
        "failure_reason": reason,
        "failure_pass": failed_pass,
        "mode_violations": pass_data.get("mode_violations", []),
    }


def _ensure_project_committed(project_id: str) -> None:
    """
    Create project record in its own committed transaction if it doesn't exist.

    CRITICAL: committing separately ensures the project row persists even if
    the subsequent main mechanism transaction rolls back. This allows
    commit_failure_pass() to insert an AnalysisPass with the correct FK.
    """
    from sqlalchemy import select

    session = get_session()
    try:
        existing = session.execute(
            select(ProjectModel).where(ProjectModel.project_id == project_id)
        ).scalar_one_or_none()
        if not existing:
            session.add(
                ProjectModel(
                    project_id=project_id,
                    name=f"Project {project_id}",
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
        else:
            session.rollback()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _ensure_stakeholder_committed(practitioner_id: str) -> None:
    """
    Create stakeholder record in its own committed transaction if it doesn't exist.
    Same rationale as _ensure_project_committed.
    """
    from sqlalchemy import select

    session = get_session()
    try:
        existing = session.execute(
            select(StakeholderModel).where(
                StakeholderModel.stakeholder_id == practitioner_id
            )
        ).scalar_one_or_none()
        if not existing:
            session.add(
                StakeholderModel(
                    stakeholder_id=practitioner_id,
                    name=f"Practitioner {practitioner_id}",
                    stakeholder_type="practitioner",
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
        else:
            session.rollback()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _find_existing_hash(
    session: Session, project_id: str, input_hash: str
) -> bool:
    """
    Check if input_hash already exists in a successful AnalysisPass for this project.
    Per Implementation Spec v0.4 §10.4 re-execution semantics.
    """
    from sqlalchemy import select
    from models.analysis_pass import AnalysisPassModel

    result = (
        session.execute(
            select(AnalysisPassModel).where(
                AnalysisPassModel.project_id == project_id,
                AnalysisPassModel.execution_status.in_(["Success", "PartialSuccess"]),
            )
        )
        .scalars()
        .all()
    )

    for ap in result:
        rw = (ap.outputs or {}).get("read_witness", {})
        if rw.get("input_hash") == input_hash:
            return True
    return False
