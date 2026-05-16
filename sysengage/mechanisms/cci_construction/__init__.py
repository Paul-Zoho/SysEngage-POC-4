"""
CCI Construction — Phase 3 Pass 3b orchestration entry point.

Per CCI Construction Mechanism Spec v0.2 §1, §3, §4:
- Six steps: Step 1 (Signal assembly), Step 2 (ZachmanCell upsert + batch
  partitioning), Step 3 (per-batch AI derivation), Step 4 (per-cell
  deduplication sweep), Step 5 (identifier allocation + atomic commit),
  Step 6 (AnalysisPass record production).
- Step 2a commits ZachmanCell upserts in its own short transaction BEFORE
  the main transaction opens (FK anchor idempotency per spec §4.2).
- AI invocations (Steps 3, 4b) complete BEFORE the main transaction opens.
- Single atomic transaction commits CCIs + AnalysisPass (Step 5).
- On failure: main transaction rolls back; AnalysisPass failure record
  commits in a separate transaction for auditability.

Public surface: run() + CCIConstructionError.
No cross-mechanism imports — only core.*, models.*, and own steps.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from core.audit_trail import (
    commit_failure_pass,
    create_analysis_pass_record,
    persist_analysis_pass,
)
from core.db import get_session
from core.ledger import ensure_project_committed, ensure_stakeholder_committed
from mechanisms.cci_construction.step1_signal_assembly import assemble_eligible_signals
from mechanisms.cci_construction.step2_zachman_cell_upsert import (
    partition_signals_into_batches,
    upsert_zachman_cells,
)
from mechanisms.cci_construction.step3_cci_derivation import derive_ccis_for_batches
from mechanisms.cci_construction.step4_deduplication import deduplicate_per_cell
from mechanisms.cci_construction.step5_commit import commit_ccis
from mechanisms.cci_construction.step6_analysis_pass import (
    build_cci_data,
    compute_execution_status,
    finalise_cci_pass_completed,
    finalise_cci_pass_completed_with_warnings,
    finalise_cci_pass_failed,
)
from models import ProjectProfileModel
from sqlalchemy import select


class CCIConstructionError(Exception):
    """Raised when the mechanism fails after committing the failure AnalysisPass."""


def run(
    *,
    project_id: str,
    practitioner_id: str,
    row_ref: int,
) -> dict[str, Any]:
    """
    Execute Phase 3 Pass 3b CCI Construction.

    Parameters
    ----------
    project_id      : ledger project identifier
    practitioner_id : practitioner stakeholder_id (SG-03 attribution)
    row_ref         : Zachman row number being analysed (1-6)

    Returns
    -------
    dict with keys: pass_id, execution_status, cci_data
    """
    _start_monotonic = time.monotonic()

    # --- FK anchors in isolated mini-transactions (before main session) ---
    ensure_project_committed(project_id)
    ensure_stakeholder_committed(practitioner_id)

    pass_data = create_analysis_pass_record(
        project_id=project_id,
        practitioner_id=practitioner_id,
        phase_id="PH001",
        pass_type="Per-row",
        mechanism="CCIConstruction",
        evaluated_scope=f"All Row {row_ref} Signals",
        confidence=1.0,
    )
    pass_data["mode_active"] = "DM"
    pass_data["declared_transformation_modes"] = ["IM", "DM"]

    # --- Read ProjectProfile (outside transaction) ---
    profile = _load_project_profile(project_id)
    consolidation_threshold = (
        profile.cci_consolidation_threshold if profile else 0.80
    )
    batch_size = profile.cci_batch_size if profile else 20

    # ------------------------------------------------------------------ #
    # STEP 1 — Assemble eligible Signal set (DM, read-only)               #
    # ------------------------------------------------------------------ #
    read_session = get_session()
    try:
        eligible_signals, integrity_violations = assemble_eligible_signals(
            project_id=project_id,
            row_ref=row_ref,
            session=read_session,
        )
    except Exception as exc:
        read_session.close()
        finalise_cci_pass_failed(
            pass_data,
            failure_reason=f"Step 1 signal assembly failed: {exc}",
            failure_pass="Step1",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise CCIConstructionError(str(exc)) from exc
    finally:
        read_session.close()

    if integrity_violations:
        pass_data.setdefault("_integrity_violations", []).extend(integrity_violations)

    # ------------------------------------------------------------------ #
    # STEP 2a — Upsert ZachmanCells (own short transaction)               #
    # ------------------------------------------------------------------ #
    try:
        upsert_zachman_cells(project_id=project_id, row_ref=row_ref)
    except Exception as exc:
        finalise_cci_pass_failed(
            pass_data,
            failure_reason=f"Step 2a ZachmanCell upsert failed: {exc}",
            failure_pass="Step2a",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise CCIConstructionError(str(exc)) from exc

    # STEP 2b — Partition signals into batches (DM, in-memory)
    batches = partition_signals_into_batches(
        signals=eligible_signals,
        batch_size=batch_size,
    )
    total_batches = len(batches)
    eligible_signal_ids = {sig.signal_id for sig in eligible_signals}

    # ------------------------------------------------------------------ #
    # STEP 3 — Per-batch CCI derivation (AI, outside main transaction)    #
    # ------------------------------------------------------------------ #
    if eligible_signals:
        try:
            all_candidates, candidates_rejected_step3, batches_processed, batches_failed = (
                derive_ccis_for_batches(
                    batches=batches,
                    row_ref=row_ref,
                    project_id=project_id,
                    eligible_signal_ids=eligible_signal_ids,
                    pass_data=pass_data,
                )
            )
        except Exception as exc:
            finalise_cci_pass_failed(
                pass_data,
                failure_reason=f"Step 3 CCI derivation failed: {exc}",
                failure_pass="Step3",
                start_monotonic=_start_monotonic,
            )
            commit_failure_pass(pass_data)
            raise CCIConstructionError(str(exc)) from exc
    else:
        all_candidates = []
        candidates_rejected_step3 = 0
        batches_processed = 0
        batches_failed = 0

    # If every batch failed with AI, fail fast
    if total_batches > 0 and batches_failed == total_batches:
        finalise_cci_pass_failed(
            pass_data,
            failure_reason=(
                f"All {total_batches} batch(es) failed AI invocation — "
                "no CCIs could be derived"
            ),
            failure_pass="Step3",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise CCIConstructionError(
            f"All {total_batches} batch(es) failed AI invocation"
        )

    # ------------------------------------------------------------------ #
    # STEP 4 — Per-cell deduplication sweep (DM + AI, outside main tx)   #
    # ------------------------------------------------------------------ #
    dedup_session = get_session()
    try:
        surviving_candidates, existing_updates, merge_records, consolidation_flags = (
            deduplicate_per_cell(
                all_candidates=all_candidates,
                row_ref=row_ref,
                project_id=project_id,
                consolidation_threshold=consolidation_threshold,
                pass_data=pass_data,
                session=dedup_session,
            )
        )
    except Exception as exc:
        dedup_session.close()
        finalise_cci_pass_failed(
            pass_data,
            failure_reason=f"Step 4 deduplication failed: {exc}",
            failure_pass="Step4",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise CCIConstructionError(str(exc)) from exc
    finally:
        dedup_session.close()

    # ------------------------------------------------------------------ #
    # STEP 5 — Atomic transaction: INSERT CCIs + AnalysisPass             #
    # ------------------------------------------------------------------ #
    session = get_session()
    try:
        new_ci_ids, ccis_created, ccis_merged, candidates_rejected_step5 = commit_ccis(
            session=session,
            surviving_candidates=surviving_candidates,
            existing_updates=existing_updates,
            row_ref=row_ref,
            project_id=project_id,
        )

        total_candidates_rejected = candidates_rejected_step3 + candidates_rejected_step5

        # ------------------------------------------------------------------ #
        # STEP 6 — AnalysisPass record production (inside main transaction)  #
        # ------------------------------------------------------------------ #
        execution_status, warning_reasons = compute_execution_status(
            batches_processed=batches_processed,
            batches_failed=batches_failed,
            total_batches=total_batches,
            candidates_rejected_step5=candidates_rejected_step5,
            integrity_violations=pass_data.get("_integrity_violations", []),
            consolidation_flags=consolidation_flags,
        )

        cci_data = build_cci_data(
            row_ref=row_ref,
            batches_processed=batches_processed,
            batches_failed=batches_failed,
            ccis_created=ccis_created,
            ccis_merged=ccis_merged,
            candidates_rejected=total_candidates_rejected,
            new_ci_ids=new_ci_ids,
            merge_records=merge_records,
            consolidation_flags=consolidation_flags,
            integrity_violations=pass_data.get("_integrity_violations", []),
            project_id=project_id,
        )

        all_confidences = pass_data.get("_collected_confidences", [])
        mean_confidence = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 1.0
        )
        pass_data["confidence"] = mean_confidence

        if execution_status == "Completed":
            finalise_cci_pass_completed(
                pass_data,
                cci_data=cci_data,
                start_monotonic=_start_monotonic,
            )
        else:
            finalise_cci_pass_completed_with_warnings(
                pass_data,
                cci_data=cci_data,
                warning_reasons=warning_reasons,
                start_monotonic=_start_monotonic,
            )

        pass_id = persist_analysis_pass(session, pass_data)
        session.commit()

        return {
            "pass_id": pass_id,
            "execution_status": pass_data["execution_status"],
            "cci_data": cci_data,
        }

    except CCIConstructionError:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        finalise_cci_pass_failed(
            pass_data,
            failure_reason=f"Step 5 transaction commit failed: {exc}",
            failure_pass="Step5",
            start_monotonic=_start_monotonic,
        )
        commit_failure_pass(pass_data)
        raise CCIConstructionError(str(exc)) from exc
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
