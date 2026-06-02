"""
Pass 3d — Requirement Derivation mechanism orchestrator.

Per Requirement Derivation Mechanism Spec v0.1 §3 and §4:
  Stateful multi-stage mechanism:
    Stage 1  — Pre-flight, CCI/Domain assembly, re-run scenario detection (DM)
    Stage 2  — Per-Domain AI derivation loop (IM)
    Stage 3  — Structural validation and Non-Loss repair (DM + IM conditional)
    Stage 4  — Entity production, domain_refs derivation, ledger commit (DM)

mode_active = "IM", declared_transformation_modes = ["IM", "DM"]

Pass-level housekeeping (FK anchors, register seeding) committed BEFORE the
main transaction opens so FK integrity is preserved even if the main
transaction rolls back.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.db import format_identifier, get_next_sequence_value, get_session
from core.ledger import (
    ensure_project_committed,
    ensure_requirement_register_seeded,
    ensure_stakeholder_committed,
)
from mechanisms.requirement_derivation.stage1_preflight import run_stage1
from mechanisms.requirement_derivation.stage2_ai_derivation import run_stage2
from mechanisms.requirement_derivation.stage3_structural_validation import run_stage3
from mechanisms.requirement_derivation.stage4_entity_production import run_stage4
from models.analysis_pass import AnalysisPassModel

_log = logging.getLogger(__name__)


def commit_failure_pass(
    *,
    project_id: str,
    practitioner_id: str,
    row_ref: int,
    pass_started_at: datetime,
    failure_reason: str,
    stage_reached: str,
    outputs_partial: dict[str, Any] | None = None,
    execution_warnings: list[dict[str, Any]] | None = None,
) -> None:
    """Commit a Failed AnalysisPass in an isolated transaction."""
    session = get_session()
    try:
        seq_val = get_next_sequence_value(session, "p_id_seq")
        pass_id = format_identifier("P", seq_val)
        now = datetime.now(timezone.utc)
        session.add(
            AnalysisPassModel(
                pass_id=pass_id,
                phase_id="PH003",
                pass_type="Universal",
                mechanism="RequirementDerivation",
                evaluated_scope=f"Row {row_ref} for {project_id}",
                confidence=0.0,
                pass_started_at=pass_started_at,
                pass_completed_at=now,
                execution_status="Failed",
                mode_active="IM",
                declared_transformation_modes=["IM", "DM"],
                elapsed_ms=int((now - pass_started_at).total_seconds() * 1000),
                practitioner_id=practitioner_id,
                project_id=project_id,
                outputs={
                    "failure_reason": failure_reason,
                    "stage_reached": stage_reached,
                    "mechanism_data": outputs_partial or {},
                    "execution_warnings": execution_warnings or [],
                },
            )
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        _log.error("commit_failure_pass itself failed: %s", exc)
        raise
    finally:
        session.close()


def run_requirement_derivation(
    *,
    project_id: str,
    practitioner_id: str,
    row_ref: int,
) -> dict[str, Any]:
    """
    Run Pass 3d Requirement Derivation for one row of one project.

    Returns a summary dict with execution_status, pass_id, and key metrics.
    All DB side effects are committed within this function.
    """
    pass_started_at = datetime.now(timezone.utc)

    # Phase 0 — FK anchor commits + register seed (isolated transactions)
    try:
        ensure_project_committed(project_id)
        ensure_stakeholder_committed(practitioner_id)
        ensure_requirement_register_seeded(project_id)
    except Exception as exc:
        _log.error("Phase 0 housekeeping failed: %s", exc)
        try:
            commit_failure_pass(
                project_id=project_id,
                practitioner_id=practitioner_id,
                row_ref=row_ref,
                pass_started_at=pass_started_at,
                failure_reason=f"Phase 0 housekeeping error: {exc}",
                stage_reached="phase0",
            )
        except Exception:
            pass
        return {"execution_status": "Failed", "failure_reason": str(exc)}

    session = get_session()
    try:
        # Stage 1 — Pre-flight, assembly, scenario detection
        stage1 = run_stage1(
            project_id=project_id,
            row_ref=row_ref,
            session=session,
        )

        # Zero-CCI early exit
        if stage1.status == "zero_cci_exit":
            now = datetime.now(timezone.utc)
            seq_val = get_next_sequence_value(session, "p_id_seq")
            pass_id = format_identifier("P", seq_val)
            session.add(
                AnalysisPassModel(
                    pass_id=pass_id,
                    phase_id="PH003",
                    pass_type="Universal",
                    mechanism="RequirementDerivation",
                    evaluated_scope=f"Row {row_ref} for {project_id}",
                    confidence=1.0,
                    pass_started_at=pass_started_at,
                    pass_completed_at=now,
                    execution_status="CompletedWithWarnings",
                    mode_active="IM",
                    declared_transformation_modes=["IM", "DM"],
                    elapsed_ms=int((now - pass_started_at).total_seconds() * 1000),
                    practitioner_id=practitioner_id,
                    project_id=project_id,
                    outputs={
                        "mechanism_data": {
                            "row_ref": row_ref,
                            "scenario": "ZeroCCI",
                            "cci_count_input": 0,
                            "domain_count": 0,
                            "requirement_count_produced": 0,
                        },
                        "execution_warnings": stage1.execution_warnings,
                    },
                )
            )
            session.commit()
            return {
                "execution_status": "CompletedWithWarnings",
                "pass_id": pass_id,
                "scenario": "ZeroCCI",
                "cci_count_input": 0,
                "requirement_count_produced": 0,
            }

        # Hard failure from Stage 1
        if stage1.status == "failed":
            session.rollback()
            commit_failure_pass(
                project_id=project_id,
                practitioner_id=practitioner_id,
                row_ref=row_ref,
                pass_started_at=pass_started_at,
                failure_reason=stage1.failure_reason or "Stage 1 failed",
                stage_reached="stage1",
                execution_warnings=stage1.execution_warnings,
            )
            return {
                "execution_status": "Failed",
                "failure_reason": stage1.failure_reason,
            }

        # IdempotentRerun — write a no-op pass and return
        if stage1.status == "idempotent_exit":
            now = datetime.now(timezone.utc)
            seq_val = get_next_sequence_value(session, "p_id_seq")
            pass_id = format_identifier("P", seq_val)
            prior_md = (
                stage1.prior_pass.outputs.get("mechanism_data", {})
                if stage1.prior_pass
                else {}
            )
            session.add(
                AnalysisPassModel(
                    pass_id=pass_id,
                    phase_id="PH003",
                    pass_type="Universal",
                    mechanism="RequirementDerivation",
                    evaluated_scope=f"Row {row_ref} for {project_id}",
                    confidence=1.0,
                    pass_started_at=pass_started_at,
                    pass_completed_at=now,
                    execution_status="Completed",
                    mode_active="IM",
                    declared_transformation_modes=["IM", "DM"],
                    elapsed_ms=int((now - pass_started_at).total_seconds() * 1000),
                    practitioner_id=practitioner_id,
                    project_id=project_id,
                    outputs={
                        "mechanism_data": {
                            "row_ref": row_ref,
                            "scenario": "IdempotentRerun",
                            "cci_count_input": len(stage1.eligible_ccis),
                            "domain_count": len(stage1.active_domains),
                            "requirement_count_produced": prior_md.get(
                                "requirement_count_produced", 0
                            ),
                            "requirement_input_hash": stage1.current_hash,
                            "domain_id_set": sorted(
                                d.domain_id for d in stage1.active_domains
                            ),
                        },
                        "execution_warnings": stage1.execution_warnings,
                    },
                )
            )
            session.commit()
            return {
                "execution_status": "Completed",
                "pass_id": pass_id,
                "scenario": "IdempotentRerun",
                "cci_count_input": len(stage1.eligible_ccis),
                "requirement_count_produced": prior_md.get(
                    "requirement_count_produced", 0
                ),
            }

        # Stage 2 — Per-Domain AI derivation
        stage2 = run_stage2(
            stage1=stage1,
            session=session,
            project_id=project_id,
            row_ref=row_ref,
        )

        if stage2.status == "failed":
            session.rollback()
            commit_failure_pass(
                project_id=project_id,
                practitioner_id=practitioner_id,
                row_ref=row_ref,
                pass_started_at=pass_started_at,
                failure_reason=stage2.failure_reason or "Stage 2 failed",
                stage_reached="stage2",
                execution_warnings=stage1.execution_warnings + stage2.execution_warnings,
            )
            return {
                "execution_status": "Failed",
                "failure_reason": stage2.failure_reason,
            }

        # Stage 3 — Structural validation + Non-Loss repair
        stage3 = run_stage3(
            stage1=stage1,
            stage2=stage2,
            practitioner_id=practitioner_id,
            project_id=project_id,
            row_ref=row_ref,
        )

        if stage3.status == "failed":
            session.rollback()
            commit_failure_pass(
                project_id=project_id,
                practitioner_id=practitioner_id,
                row_ref=row_ref,
                pass_started_at=pass_started_at,
                failure_reason=stage3.failure_reason or "Stage 3 failed",
                stage_reached="stage3",
                execution_warnings=(
                    stage1.execution_warnings
                    + stage2.execution_warnings
                    + stage3.execution_warnings
                ),
            )
            return {
                "execution_status": "Failed",
                "failure_reason": stage3.failure_reason,
            }

        # Build pass_data dict for Stage 4 (mutable, passed in)
        pass_data: dict[str, Any] = {}

        # Stage 4 — Entity production and ledger commit
        stage4 = run_stage4(
            stage1=stage1,
            stage2=stage2,
            stage3=stage3,
            project_id=project_id,
            row_ref=row_ref,
            practitioner_id=practitioner_id,
            pass_data=pass_data,
            session=session,
        )

        if stage4.status == "failed":
            commit_failure_pass(
                project_id=project_id,
                practitioner_id=practitioner_id,
                row_ref=row_ref,
                pass_started_at=pass_started_at,
                failure_reason=stage4.failure_reason or "Stage 4 failed",
                stage_reached="stage4",
                execution_warnings=(
                    stage1.execution_warnings
                    + stage2.execution_warnings
                    + stage3.execution_warnings
                ),
            )
            return {
                "execution_status": "Failed",
                "failure_reason": stage4.failure_reason,
            }

        # --- Write AnalysisPass in a new session (Stage 4 committed separately) ---
        pass_session = get_session()
        try:
            now = datetime.now(timezone.utc)
            seq_val = get_next_sequence_value(pass_session, "p_id_seq")
            pass_id = format_identifier("P", seq_val)

            # Final execution_status
            if (
                stage3.status == "ok_with_warnings"
                or stage3.orphaned_ccis
                or stage3.concern_entities
            ):
                execution_status = "CompletedWithWarnings"
            else:
                execution_status = "Completed"

            all_warnings = (
                stage1.execution_warnings
                + stage2.execution_warnings
                + stage3.execution_warnings
                + list(pass_data.get("execution_warnings_stage4", []))
            )

            concern_entities_out = stage3.concern_entities

            pass_session.add(
                AnalysisPassModel(
                    pass_id=pass_id,
                    phase_id="PH003",
                    pass_type="Universal",
                    mechanism="RequirementDerivation",
                    evaluated_scope=f"Row {row_ref} for {project_id}",
                    confidence=1.0,
                    pass_started_at=pass_started_at,
                    pass_completed_at=now,
                    execution_status=execution_status,
                    mode_active="IM",
                    declared_transformation_modes=["IM", "DM"],
                    elapsed_ms=int((now - pass_started_at).total_seconds() * 1000),
                    practitioner_id=practitioner_id,
                    project_id=project_id,
                    outputs={
                        "mechanism_data": {
                            "row_ref": row_ref,
                            "run_scenario": stage2.effective_scenario,
                            "requirement_input_hash": stage1.current_hash,
                            "domain_id_set": sorted(
                                d.domain_id for d in stage1.active_domains
                            ),
                            "cci_count_input": len(stage1.eligible_ccis),
                            "domain_count_input": len(stage1.active_domains),
                            "large_cci_set_advisory": stage1.large_cci_set_advisory,
                            "idempotent": stage2.effective_scenario == "IdempotentRerun",
                            "repair_prompt_issued": stage3.repair_prompt_issued,
                            "orphaned_ccis": stage3.orphaned_ccis,
                            "validation_failures": (
                                stage2.validation_failures + stage3.validation_failures
                            ),
                            "duplicate_requirements_collapsed": (
                                stage3.duplicate_requirements_collapsed
                            ),
                            "subject_vocabulary_flags": stage3.subject_vocabulary_flags,
                            "requirement_count_produced": stage4.requirement_count_produced,
                            "requirement_count_retired": stage4.requirement_count_retired,
                            "requirement_type_distribution": stage4.requirement_type_distribution,
                            "requirements_produced": stage4.requirements_produced,
                            "downstream_rerun_required": stage4.downstream_rerun_required,
                            "retirement_mapping": stage4.retirement_mapping,
                            "mode_violations": [],
                        },
                        "execution_warnings": all_warnings,
                        "ai_model_fingerprints": (
                            stage2.ai_model_fingerprints
                            + stage3.ai_model_fingerprints
                        ),
                        "concern_entities": concern_entities_out,
                    },
                )
            )
            pass_session.commit()

        except Exception as exc:
            pass_session.rollback()
            _log.error("AnalysisPass commit failed: %s", exc)
            raise
        finally:
            pass_session.close()

        return {
            "execution_status": execution_status,
            "pass_id": pass_id,
            "scenario": stage2.effective_scenario,
            "cci_count_input": len(stage1.eligible_ccis),
            "domain_count": len(stage1.active_domains),
            "requirement_count_produced": stage4.requirement_count_produced,
            "requirement_count_retired": stage4.requirement_count_retired,
            "requirement_type_distribution": stage4.requirement_type_distribution,
            "orphaned_ccis": stage3.orphaned_ccis,
            "downstream_rerun_required": stage4.downstream_rerun_required,
        }

    except Exception as exc:
        session.rollback()
        _log.error("Unhandled exception in run_requirement_derivation: %s", exc)
        try:
            commit_failure_pass(
                project_id=project_id,
                practitioner_id=practitioner_id,
                row_ref=row_ref,
                pass_started_at=pass_started_at,
                failure_reason=f"Unhandled exception: {exc}",
                stage_reached="unknown",
            )
        except Exception:
            pass
        raise
    finally:
        session.close()
