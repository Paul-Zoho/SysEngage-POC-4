"""
Audit trail helpers for AnalysisPass lifecycle management.

Per Row 4 Applied §10 and Mechanism Implementation Spec §7:
- One AnalysisPass record per mechanism execution.
- Created at mechanism start, finalised at mechanism end (success or failure).
- On failure: main transaction rolls back; AnalysisPass with failure detail
  commits in a SEPARATE transaction so failures remain auditable.

Per Row 4 Applied §5 transactional discipline:
- All canonical entities commit atomically in one transaction.
- AnalysisPass failure record commits in a second, separate transaction.
"""

import time
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from core.db import get_session, get_next_sequence_value, format_identifier
from models.analysis_pass import AnalysisPassModel


def create_analysis_pass_record(
    *,
    project_id: str,
    practitioner_id: str,
    phase_id: str = "PH001",
) -> dict[str, Any]:
    """
    Build the in-memory AnalysisPass data dict at mechanism start.
    Not yet persisted — the orchestrator holds it until execution completes.

    Returns a mutable dict that the orchestrator updates during execution.
    """
    return {
        "project_id": project_id,
        "practitioner_id": practitioner_id,
        "phase_id": phase_id,
        "pass_started_at": datetime.now(timezone.utc),
        "pass_completed_at": None,
        "execution_status": "In-Progress",
        "mode_active": "LPM",
        "declared_transformation_modes": ["LPM"],
        "mode_violations": [],
        "ai_model_fingerprints": [],
        "elapsed_ms": None,
        "outputs": {},
        "_start_monotonic": time.monotonic(),
    }


def finalise_pass_success(
    pass_data: dict[str, Any],
    *,
    read_witness: dict[str, Any],
    mechanism_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Update pass_data dict for a successful execution.
    Called just before the commit transaction.
    """
    elapsed = time.monotonic() - pass_data.pop("_start_monotonic")
    pass_data["execution_status"] = "Success"
    pass_data["pass_completed_at"] = datetime.now(timezone.utc)
    pass_data["elapsed_ms"] = int(elapsed * 1000)
    pass_data["outputs"] = {
        "read_witness": read_witness,
        "mechanism_data": mechanism_data,
        "mode_violations": pass_data.get("mode_violations", []),
    }
    return pass_data


def finalise_pass_partial_success(
    pass_data: dict[str, Any],
    *,
    read_witness: dict[str, Any],
    mechanism_data: dict[str, Any],
    failure_reason: str,
) -> dict[str, Any]:
    """
    Update pass_data for PartialSuccess (e.g., decoding failed mid-stream
    but some Sources were captured).
    """
    elapsed = time.monotonic() - pass_data.pop("_start_monotonic")
    pass_data["execution_status"] = "PartialSuccess"
    pass_data["pass_completed_at"] = datetime.now(timezone.utc)
    pass_data["elapsed_ms"] = int(elapsed * 1000)
    pass_data["outputs"] = {
        "read_witness": read_witness,
        "mechanism_data": mechanism_data,
        "mode_violations": pass_data.get("mode_violations", []),
        "partial_failure_reason": failure_reason,
    }
    return pass_data


def finalise_pass_failure(
    pass_data: dict[str, Any],
    *,
    failure_reason: str,
    failure_pass: str,
    mode_violations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Update pass_data for a failed execution.
    The orchestrator will commit this in a separate transaction.
    """
    start_mono = pass_data.pop("_start_monotonic", None)
    elapsed = time.monotonic() - start_mono if start_mono else 0
    pass_data["execution_status"] = "Failed"
    pass_data["pass_completed_at"] = datetime.now(timezone.utc)
    pass_data["elapsed_ms"] = int(elapsed * 1000)
    pass_data["outputs"] = {
        "failure_reason": failure_reason,
        "failure_pass": failure_pass,
        "mode_violations": mode_violations or pass_data.get("mode_violations", []),
    }
    return pass_data


def persist_analysis_pass(session: Session, pass_data: dict[str, Any]) -> str:
    """
    Assign a pass_id from the Postgres sequence and insert the AnalysisPass row.
    Does NOT commit — caller is responsible for commit/rollback.

    Returns the assigned pass_id.
    """
    seq_val = get_next_sequence_value(session, "p_id_seq")
    pass_id = format_identifier("P", seq_val)

    record = AnalysisPassModel(
        pass_id=pass_id,
        phase_id=pass_data["phase_id"],
        pass_started_at=pass_data["pass_started_at"],
        pass_completed_at=pass_data.get("pass_completed_at"),
        execution_status=pass_data["execution_status"],
        mode_active=pass_data["mode_active"],
        declared_transformation_modes=pass_data["declared_transformation_modes"],
        elapsed_ms=pass_data.get("elapsed_ms"),
        practitioner_id=pass_data["practitioner_id"],
        project_id=pass_data["project_id"],
        outputs=pass_data.get("outputs", {}),
    )
    session.add(record)
    return pass_id


def commit_failure_pass(pass_data: dict[str, Any]) -> str:
    """
    Commit the AnalysisPass failure record in a SEPARATE transaction.

    Per Row 4 Applied §5: on mechanism failure, main transaction rolls back,
    but the AnalysisPass failure record must still be committed for auditability.

    Returns the committed pass_id.
    """
    session = get_session()
    try:
        pass_id = persist_analysis_pass(session, pass_data)
        session.commit()
        return pass_id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
