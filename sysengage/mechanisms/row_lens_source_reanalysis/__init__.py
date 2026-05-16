"""
Row-Lens Source Re-Analysis — Phase 3 Pass 3a orchestration entry point.

Per Row-Lens Source Re-Analysis Spec v0.1 §1, §3, §4:
- Four stages: Stage 1 (DM chunk assembly), Stage 2 (IM classification),
  Stage 3 (DM deduplication), Stage 4 (IM conflict sweep).
- AI invocations complete BEFORE the Postgres transaction opens (§3.2).
- Single atomic transaction commits Signals, Concerns, AnalysisPass.
- On failure: main transaction rolls back; AnalysisPass failure record
  commits in a separate transaction for auditability.

Verification criteria: 17 decidable criteria per spec §8.1.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from core.audit_trail import (
    create_analysis_pass_record,
    finalise_pass_failure,
    persist_analysis_pass,
    commit_failure_pass,
)
from core.db import get_session, get_next_sequence_value, format_identifier
from core.ledger import ensure_project_committed, ensure_stakeholder_committed
from mechanisms.row_lens_source_reanalysis.stage1_chunk_assembly import (
    assemble_chunks,
    ChunkAssemblyResult,
)
from mechanisms.row_lens_source_reanalysis.stage2_chunk_classification import (
    classify_chunks,
)
from mechanisms.row_lens_source_reanalysis.stage2_residual_classification import (
    classify_residuals,
)
from mechanisms.row_lens_source_reanalysis.stage3_deduplication import (
    deduplicate,
    DeduplicationResult,
)
from mechanisms.row_lens_source_reanalysis.stage4_conflict_sweep import (
    sweep_conflicts,
)
from mechanisms.row_lens_source_reanalysis.entity_production import (
    build_signal_model,
    build_concern_model,
    run_referential_integrity_checks,
    run_mutual_exclusivity_check,
    RowLensRunState,
)
from mechanisms.row_lens_source_reanalysis.analysis_pass_production import (
    build_row_lens_data,
    finalise_pass_completed,
    finalise_pass_completed_with_warnings,
    finalise_pass_failed,
)
from models import (
    ProjectProfileModel,
    SignalModel,
    ConcernModel,
)
from sqlalchemy import select


class RowLensExecutionError(Exception):
    """Raised when the mechanism fails after committing the failure AnalysisPass."""


def run(
    *,
    project_id: str,
    practitioner_id: str,
    row_ref: int,
) -> dict[str, Any]:
    """
    Execute Phase 3 Pass 3a Row-Lens Source Re-Analysis.

    Parameters
    ----------
    project_id      : ledger project identifier
    practitioner_id : practitioner stakeholder_id (SG-03 attribution)
    row_ref         : Zachman row number being analysed (1-6)

    Returns
    -------
    dict with keys: pass_id, execution_status, row_lens_data
    """
    pass_started_at = datetime.now(timezone.utc)
    _start_monotonic = time.monotonic()

    # --- FK anchors in isolated mini-transactions (before main session) ---
    ensure_project_committed(project_id)
    ensure_stakeholder_committed(practitioner_id)

    pass_data = create_analysis_pass_record(
        project_id=project_id,
        practitioner_id=practitioner_id,
        phase_id="PH001",
        pass_type="Per-row",
        mechanism="RowLensSourceReanalysis",
        evaluated_scope=f"All Sources + Row {row_ref - 1} Requirements",
        confidence=1.0,
    )
    pass_data["mode_active"] = "IM"
    pass_data["declared_transformation_modes"] = ["IM", "DM", "LPM"]

    # --- Read ProjectProfile (outside transaction) ---
    profile = _load_project_profile(project_id)
    concern_threshold = profile.concern_threshold if profile else 0.65
    chunk_match_threshold = profile.chunk_match_threshold if profile else 0.6
    residual_batch_size = profile.residual_batch_size if profile else 50

    # ------------------------------------------------------------------ #
    # STAGE 1 — DM: Domain-driven chunk assembly                          #
    # ------------------------------------------------------------------ #
    try:
        assembly: ChunkAssemblyResult = assemble_chunks(
            project_id=project_id,
            row_ref=row_ref,
            chunk_match_threshold=chunk_match_threshold,
        )
    except Exception as exc:
        finalise_pass_failed(
            pass_data,
            failure_reason=f"Stage 1 chunk assembly failed: {exc}",
            failure_pass="Stage1",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise RowLensExecutionError(str(exc)) from exc

    # ------------------------------------------------------------------ #
    # STAGE 2 — IM+DM: Per-chunk classification (AI outside transaction)  #
    # ------------------------------------------------------------------ #
    try:
        chunk_results = classify_chunks(
            chunks=assembly.chunks,
            row_ref=row_ref,
            concern_threshold=concern_threshold,
            pass_data=pass_data,
        )
    except Exception as exc:
        finalise_pass_failed(
            pass_data,
            failure_reason=f"Stage 2 chunk classification failed: {exc}",
            failure_pass="Stage2",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise RowLensExecutionError(str(exc)) from exc

    # --- Stage 2 residual classification ---
    try:
        residual_results = classify_residuals(
            residuals=assembly.residuals,
            row_ref=row_ref,
            concern_threshold=concern_threshold,
            residual_batch_size=residual_batch_size,
            pass_data=pass_data,
        )
    except Exception as exc:
        finalise_pass_failed(
            pass_data,
            failure_reason=f"Stage 2 residual classification failed: {exc}",
            failure_pass="Stage2",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise RowLensExecutionError(str(exc)) from exc

    # ------------------------------------------------------------------ #
    # STAGE 3 — DM: Deduplication + conflict flagging                     #
    # ------------------------------------------------------------------ #
    try:
        dedup: DeduplicationResult = deduplicate(
            chunk_results=chunk_results,
            residual_results=residual_results,
            chunk_assignment=assembly.chunk_assignment,
        )
    except Exception as exc:
        finalise_pass_failed(
            pass_data,
            failure_reason=f"Stage 3 deduplication failed: {exc}",
            failure_pass="Stage3",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise RowLensExecutionError(str(exc)) from exc

    # ------------------------------------------------------------------ #
    # STAGE 4 — IM+DM: Conflict sweep (AI outside transaction)            #
    # ------------------------------------------------------------------ #
    try:
        conflict_concerns = sweep_conflicts(
            conflicts=dedup.conflicts,
            sources_by_id=assembly.sources_by_id,
            row_ref=row_ref,
            pass_data=pass_data,
        )
    except Exception as exc:
        finalise_pass_failed(
            pass_data,
            failure_reason=f"Stage 4 conflict sweep failed: {exc}",
            failure_pass="Stage4",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise RowLensExecutionError(str(exc)) from exc

    # ------------------------------------------------------------------ #
    # IN-MEMORY ENTITY ASSEMBLY (DM, pre-transaction)                     #
    # ------------------------------------------------------------------ #
    run_state = RowLensRunState(
        signals_raw=dedup.signals,
        concerns_raw=dedup.concerns + conflict_concerns,
        out_of_scope_refs=dedup.out_of_scope_refs,
        stream1_source_count=assembly.stream1_source_count,
        stream2_requirement_count=assembly.stream2_requirement_count,
        stream2_domain_count=assembly.stream2_domain_count,
        row_ref=row_ref,
        practitioner_id=practitioner_id,
    )

    # Referential integrity and mutual exclusivity checks (decidable criteria)
    ri_failures = run_referential_integrity_checks(
        run_state=run_state,
        sources_by_id=assembly.sources_by_id,
        requirements_by_id=assembly.requirements_by_id,
    )
    me_failures = run_mutual_exclusivity_check(run_state=run_state)
    all_failures = ri_failures + me_failures

    # INV-1 invariant check
    inv_ok = _check_invariant(run_state)

    has_warnings = bool(all_failures) and inv_ok

    # ------------------------------------------------------------------ #
    # ATOMIC TRANSACTION: write Signals + Concerns + AnalysisPass         #
    # ------------------------------------------------------------------ #
    session = get_session()
    try:
        # Assign Signal IDs from sequence
        signal_models: list[SignalModel] = []
        for raw_signal in run_state.signals_raw:
            if raw_signal["source_refs"][0] in {f["item_id"] for f in all_failures}:
                continue
            seq_val = get_next_sequence_value(session, "sg_id_seq")
            signal_id = format_identifier("SG", seq_val)
            sm = build_signal_model(
                signal_id=signal_id,
                raw=raw_signal,
                row_ref=row_ref,
                project_id=project_id,
            )
            session.add(sm)
            signal_models.append(sm)

        # Assign Concern IDs from sequence
        concern_models: list[ConcernModel] = []
        for raw_concern in run_state.concerns_raw:
            if raw_concern["source_refs"][0] in {f["item_id"] for f in all_failures}:
                continue
            seq_val = get_next_sequence_value(session, "cn_id_seq")
            concern_id = format_identifier("CN", seq_val)
            cm = build_concern_model(
                concern_id=concern_id,
                raw=raw_concern,
                row_ref=row_ref,
                project_id=project_id,
                practitioner_id=practitioner_id,
            )
            session.add(cm)
            concern_models.append(cm)

        # Confidence = mean of all AI confidence scores collected during run
        all_confidences = pass_data.get("_collected_confidences", [])
        mean_confidence = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 1.0
        )

        row_lens_data = build_row_lens_data(
            row_ref=row_ref,
            assembly=assembly,
            signal_count=len(signal_models),
            concern_count=len(concern_models),
            out_of_scope_refs=run_state.out_of_scope_refs,
            chunk_assignment=assembly.chunk_assignment,
            ai_model_fingerprints=pass_data.get("ai_model_fingerprints", []),
            concern_threshold_used=concern_threshold,
            chunk_match_threshold_used=chunk_match_threshold,
            failure_detail=all_failures if all_failures else None,
        )

        if not inv_ok:
            finalise_pass_failed(
                pass_data,
                failure_reason=(
                    f"INV-1 violated: stream1({assembly.stream1_source_count}) + "
                    f"stream2({assembly.stream2_requirement_count}) != "
                    f"signals({len(signal_models)}) + concerns({len(concern_models)}) + "
                    f"oos({len(run_state.out_of_scope_refs)})"
                ),
                failure_pass="AnalysisPassProduction",
                start_monotonic=_start_monotonic,
            )
            pass_data["outputs"]["row_lens_data"] = row_lens_data
            persist_analysis_pass(session, pass_data)
            session.commit()
            raise RowLensExecutionError("INV-1 invariant violated — run failed")

        if has_warnings:
            finalise_pass_completed_with_warnings(
                pass_data,
                row_lens_data=row_lens_data,
                failure_detail=all_failures,
                start_monotonic=_start_monotonic,
            )
        else:
            finalise_pass_completed(
                pass_data,
                row_lens_data=row_lens_data,
                start_monotonic=_start_monotonic,
            )

        pass_data["confidence"] = mean_confidence
        pass_id = persist_analysis_pass(session, pass_data)
        session.commit()

        return {
            "pass_id": pass_id,
            "execution_status": pass_data["execution_status"],
            "row_lens_data": row_lens_data,
        }

    except RowLensExecutionError:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        finalise_pass_failed(
            pass_data,
            failure_reason=f"Transaction commit failed: {exc}",
            failure_pass="AnalysisPassProduction",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise RowLensExecutionError(str(exc)) from exc
    finally:
        session.close()


def _load_project_profile(project_id: str) -> ProjectProfileModel | None:
    session = get_session()
    try:
        return session.execute(
            select(ProjectProfileModel).where(
                ProjectProfileModel.project_id == project_id
            )
        ).scalar_one_or_none()
    finally:
        session.close()


def _check_invariant(run_state: RowLensRunState) -> bool:
    total_in = run_state.stream1_source_count + run_state.stream2_requirement_count
    total_out = (
        len(run_state.signals_raw)
        + len(run_state.concerns_raw)
        + len(run_state.out_of_scope_refs)
    )
    return total_in == total_out
