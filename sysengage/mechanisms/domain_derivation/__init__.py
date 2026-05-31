"""
Domain Derivation mechanism — Pass 3c orchestrator.

Per Domain Derivation Mechanism Spec v0.17 §4:
  Stage 1 — Pre-flight, CCI assembly, re-run scenario detection (DM)
  Stage 2 — AI grouping act (IM)
  Stage 3 — Structural validation with conditional repair (DM + conditional IM)
  Stage 4 — Entity production and ledger commit (DM)

Entry point: run(project_id, practitioner_id, row_ref) → dict

Returned dict keys:
  pass_id, execution_status, mechanism_data

mechanism_data keys (per spec §7):
  row_ref, scenario, cci_count_input, domain_count_produced, domain_count_retired,
  domains_produced, cci_set_hash, downstream_rerun_required, retirement_mapping,
  orphaned_ccis, repair_prompt_issued, cross_cutting_advisories,
  validation_failures, large_cci_set_advisory, mode_violations,
  ai_model_fingerprints, idempotent (IdempotentRerun only)
"""

from __future__ import annotations

import logging
from typing import Any

from core.audit_trail import (
    commit_failure_pass,
    create_analysis_pass_record,
    finalise_pass_success,
    persist_analysis_pass,
)
from core.db import get_session
from core.ledger import (
    ensure_domain_register_seeded,
    ensure_project_committed,
    ensure_stakeholder_committed,
)
from mechanisms.domain_derivation.stage1_preflight import run_stage1
from mechanisms.domain_derivation.stage2_ai_grouping import run_stage2
from mechanisms.domain_derivation.stage3_structural_validation import run_stage3
from mechanisms.domain_derivation.stage4_entity_production import run_stage4

_log = logging.getLogger(__name__)


def run(
    *,
    project_id: str,
    practitioner_id: str,
    row_ref: int,
) -> dict[str, Any]:
    """
    Execute Pass 3c Domain Derivation for project_id / row_ref.

    Returns dict with keys: pass_id, execution_status, mechanism_data.
    Raises on unexpected errors (session leaks, etc.) after recording the
    failure AnalysisPass in a separate committed transaction.
    """
    _log.info(
        "Pass 3c DomainDerivation — project=%s row=%d practitioner=%s",
        project_id,
        row_ref,
        practitioner_id,
    )

    # FK anchors and DomainRegister seed — committed before main transaction
    ensure_project_committed(project_id)
    ensure_stakeholder_committed(practitioner_id)
    try:
        ensure_domain_register_seeded(project_id)
    except Exception as exc:
        pass_data = create_analysis_pass_record(
            project_id=project_id,
            practitioner_id=practitioner_id,
            mechanism="DomainDerivation",
            pass_type="Universal",
            evaluated_scope=f"Row {row_ref} CCIs for project {project_id}",
        )
        from core.audit_trail import finalise_pass_failure
        finalise_pass_failure(
            pass_data,
            failure_reason=f"DomainRegister seed failed: {exc}",
            failure_pass="pre-flight",
        )
        pass_id = commit_failure_pass(pass_data)
        return {
            "pass_id": pass_id,
            "execution_status": "Failed",
            "mechanism_data": {
                "row_ref": row_ref,
                "failure_reason": str(exc),
                "failure_pass": "pre-flight",
            },
        }

    # Build pass record (in-memory, not yet persisted)
    pass_data = create_analysis_pass_record(
        project_id=project_id,
        practitioner_id=practitioner_id,
        mechanism="DomainDerivation",
        pass_type="Universal",
        evaluated_scope=f"Row {row_ref} CCIs for project {project_id}",
    )
    # Correct mode fields — audit_trail default is "LPM" (shared); DD is IM-primary
    # Per spec v0.14 §6: mode_active="IM", declared_transformation_modes=["IM","DM"]
    pass_data["mode_active"] = "IM"
    pass_data["declared_transformation_modes"] = ["IM", "DM"]

    session = get_session()
    try:
        # Stage 1 — Pre-flight and CCI assembly
        stage1 = run_stage1(
            project_id=project_id,
            row_ref=row_ref,
            session=session,
        )

        if stage1.status == "failed":
            from core.audit_trail import finalise_pass_failure
            finalise_pass_failure(
                pass_data,
                failure_reason=stage1.failure_reason or "Stage 1 failure",
                failure_pass="Stage1",
            )
            pass_id = commit_failure_pass(pass_data)
            return {
                "pass_id": pass_id,
                "execution_status": "Failed",
                "mechanism_data": {
                    "row_ref": row_ref,
                    "failure_reason": stage1.failure_reason,
                    "failure_pass": "Stage1",
                },
            }

        if stage1.status == "zero_cci_exit":
            mechanism_data: dict[str, Any] = {
                "row_ref": row_ref,
                "scenario": stage1.scenario,
                "cci_count_input": 0,
                "domain_count_produced": 0,
                "domain_count_retired": 0,
                "domains_produced": [],
                "cci_set_hash": stage1.current_hash,
                "downstream_rerun_required": False,
                "retirement_mapping": [],
                "orphaned_ccis": [],
                "repair_prompt_issued": False,
                "cross_cutting_advisories": [],
                "validation_failures": [],
                "large_cci_set_advisory": False,
                "mode_violations": [],
                "ai_model_fingerprints": [],
            }
            read_witness: dict[str, Any] = {
                "cci_count": 0,
                "project_id": project_id,
                "row_ref": row_ref,
            }
            finalise_pass_success(
                pass_data,
                read_witness=read_witness,
                mechanism_data=mechanism_data,
            )
            pass_data["execution_status"] = "CompletedWithWarnings"
            pass_data["outputs"]["execution_warnings"] = stage1.execution_warnings
            pass_id = _commit_pass(session, pass_data)
            return {
                "pass_id": pass_id,
                "execution_status": "CompletedWithWarnings",
                "mechanism_data": mechanism_data,
            }

        if stage1.status == "idempotent_exit":
            prior_md = stage1.prior_pass.outputs.get("mechanism_data", {})
            _log.info(
                "IdempotentRerun — returning prior pass_id=%s",
                stage1.prior_pass.pass_id,
            )
            mechanism_data = {
                "row_ref": row_ref,
                "scenario": "IdempotentRerun",
                "cci_count_input": len(stage1.eligible_ccis),
                "idempotent": True,
                "cci_set_hash": stage1.current_hash,
                "large_cci_set_advisory": stage1.large_cci_set_advisory,
                "mode_violations": [],
                "ai_model_fingerprints": [],
                **{
                    k: prior_md.get(k)
                    for k in (
                        "domain_count_produced",
                        "domain_count_retired",
                        "domains_produced",
                        "downstream_rerun_required",
                        "retirement_mapping",
                        "orphaned_ccis",
                        "repair_prompt_issued",
                        "cross_cutting_advisories",
                        "validation_failures",
                    )
                    if k in prior_md
                },
            }
            read_witness = {
                "cci_count": len(stage1.eligible_ccis),
                "project_id": project_id,
                "row_ref": row_ref,
            }
            finalise_pass_success(
                pass_data,
                read_witness=read_witness,
                mechanism_data=mechanism_data,
            )
            pass_data["execution_status"] = "Completed"
            pass_id = _commit_pass(session, pass_data)
            return {
                "pass_id": pass_id,
                "execution_status": "Completed",
                "mechanism_data": mechanism_data,
            }

        # Stage 2 — AI grouping
        stage2 = run_stage2(
            stage1=stage1,
            session=session,
            project_id=project_id,
            row_ref=row_ref,
        )

        if stage2.status == "failed":
            from core.audit_trail import finalise_pass_failure
            finalise_pass_failure(
                pass_data,
                failure_reason=stage2.failure_reason or "Stage 2 AI failure",
                failure_pass="Stage2",
            )
            pass_id = commit_failure_pass(pass_data)
            return {
                "pass_id": pass_id,
                "execution_status": "Failed",
                "mechanism_data": {
                    "row_ref": row_ref,
                    "failure_reason": stage2.failure_reason,
                    "failure_pass": "Stage2",
                },
            }

        # Merge AI fingerprints into pass_data
        pass_data["ai_model_fingerprints"] = list(stage2.ai_model_fingerprints)

        # Stage 3 — Structural validation
        stage3 = run_stage3(
            stage1=stage1,
            stage2=stage2,
            practitioner_id=practitioner_id,
            project_id=project_id,
            row_ref=row_ref,
        )

        if stage3.status == "failed":
            from core.audit_trail import finalise_pass_failure
            finalise_pass_failure(
                pass_data,
                failure_reason=stage3.failure_reason or "Stage 3 validation failure",
                failure_pass="Stage3",
            )
            pass_id = commit_failure_pass(pass_data)
            return {
                "pass_id": pass_id,
                "execution_status": "Failed",
                "mechanism_data": {
                    "row_ref": row_ref,
                    "failure_reason": stage3.failure_reason,
                    "failure_pass": "Stage3",
                },
            }

        # Merge Stage 3 AI fingerprints
        pass_data["ai_model_fingerprints"] = (
            pass_data.get("ai_model_fingerprints", [])
            + list(stage3.ai_model_fingerprints)
        )

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
            from core.audit_trail import finalise_pass_failure
            finalise_pass_failure(
                pass_data,
                failure_reason=stage4.failure_reason or "Stage 4 ledger commit failure",
                failure_pass="Stage4",
            )
            pass_id = commit_failure_pass(pass_data)
            return {
                "pass_id": pass_id,
                "execution_status": "Failed",
                "mechanism_data": {
                    "row_ref": row_ref,
                    "failure_reason": stage4.failure_reason,
                    "failure_pass": "Stage4",
                },
            }

        # Assemble mechanism_data and read_witness
        cci_count = len(stage1.eligible_ccis)
        mechanism_data = {
            "row_ref": row_ref,
            "scenario": stage2.effective_scenario,
            "cci_count_input": cci_count,
            "domain_count_produced": stage4.domain_count_produced,
            "domain_count_retired": stage4.domain_count_retired,
            "domains_produced": stage4.domains_produced,
            "cci_set_hash": stage1.current_hash,
            "downstream_rerun_required": stage4.downstream_rerun_required,
            "retirement_mapping": stage4.retirement_mapping,
            "orphaned_ccis": stage3.orphaned_ccis,
            "repair_prompt_issued": stage3.repair_prompt_issued,
            "cross_cutting_advisories": stage3.cross_cutting_advisories,
            "validation_failures": stage3.validation_failures,
            "large_cci_set_advisory": stage1.large_cci_set_advisory,
            "mode_violations": [],
            "ai_model_fingerprints": pass_data.get("ai_model_fingerprints", []),
        }
        read_witness = {
            "cci_count": cci_count,
            "project_id": project_id,
            "row_ref": row_ref,
        }

        # Collect all execution warnings
        all_warnings = (
            stage1.execution_warnings
            + stage2.execution_warnings
            + stage3.execution_warnings
        )
        # large_cci_set advisory
        if stage1.large_cci_set_advisory:
            all_warnings.append(
                {
                    "type": "large_cci_set_advisory",
                    "cci_count": cci_count,
                    "threshold": stage1.domain_large_cci_set_advisory_threshold,
                }
            )

        finalise_pass_success(
            pass_data,
            read_witness=read_witness,
            mechanism_data=mechanism_data,
        )

        # Determine execution status
        has_warnings = bool(all_warnings) or stage3.status == "ok_with_warnings"
        incremental_fallback = any(
            w.get("type") == "incremental_fallback_to_fullrerun"
            for w in all_warnings
        )
        execution_status = (
            "CompletedWithWarnings"
            if (has_warnings or incremental_fallback)
            else "Completed"
        )
        pass_data["execution_status"] = execution_status
        if all_warnings:
            pass_data["outputs"]["execution_warnings"] = all_warnings

        # VER-3c-12: FirstRun/FullRerun MUST produce at least one Domain
        if stage2.effective_scenario in ("FirstRun", "FullRerun"):
            if stage4.domain_count_produced == 0:
                from core.audit_trail import finalise_pass_failure
                finalise_pass_failure(
                    pass_data,
                    failure_reason=(
                        f"VER-3c-12: {stage2.effective_scenario} produced zero Domains "
                        f"after structural validation — specification violation"
                    ),
                    failure_pass="Stage4",
                )
                pass_id = commit_failure_pass(pass_data)
                return {
                    "pass_id": pass_id,
                    "execution_status": "Failed",
                    "mechanism_data": {
                        "row_ref": row_ref,
                        "failure_reason": "VER-3c-12: zero Domains produced",
                        "failure_pass": "Stage4",
                    },
                }

        pass_id = _commit_pass(session, pass_data)
        _log.info(
            "Pass 3c complete — pass_id=%s status=%s domains_produced=%d",
            pass_id,
            execution_status,
            stage4.domain_count_produced,
        )
        return {
            "pass_id": pass_id,
            "execution_status": execution_status,
            "mechanism_data": mechanism_data,
        }

    except Exception as exc:
        from core.audit_trail import finalise_pass_failure
        try:
            session.rollback()
        except Exception:
            pass
        finalise_pass_failure(
            pass_data,
            failure_reason=f"Unhandled exception: {exc}",
            failure_pass="unknown",
        )
        pass_id = commit_failure_pass(pass_data)
        raise

    finally:
        session.close()


def _commit_pass(session: Any, pass_data: dict[str, Any]) -> str:
    """Commit the AnalysisPass record in a fresh session (separate from the ledger session)."""
    from core.db import get_session as _get_session

    commit_session = _get_session()
    try:
        pass_id = persist_analysis_pass(commit_session, pass_data)
        commit_session.commit()
        return pass_id
    except Exception:
        commit_session.rollback()
        raise
    finally:
        commit_session.close()
