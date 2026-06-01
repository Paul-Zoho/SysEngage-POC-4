"""
Shared ledger helpers for mechanism orchestration.

Extracted from mechanisms/source_capture/__init__.py so that every mechanism
can create the required FK anchors (project + stakeholder) before opening its
main transaction, without importing from another mechanism.

Per Row 4 Applied §5 transactional discipline:
- Project and Stakeholder records MUST be committed in isolated mini-transactions
  BEFORE the main mechanism transaction opens.
- This ensures FK anchors survive if the main transaction rolls back, allowing
  commit_failure_pass() to insert an AnalysisPass with the correct FKs.

ensure_domain_register_seeded() is called from Stage 1 pre-flight of Pass 3c
before the mechanism transaction opens. It seeds a DomainRegister row for the
project in the register table if one does not already exist.

ensure_requirement_register_seeded() is called from Pass 3d __init__ before
the mechanism transaction opens. Same pattern as ensure_domain_register_seeded().
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select, text

from core.db import get_session
from models.project import ProjectModel
from models.stakeholder import StakeholderModel


def ensure_project_committed(project_id: str) -> None:
    """
    Create project record in its own committed transaction if it does not exist.

    CRITICAL: committing separately ensures the project row persists even if
    the subsequent main mechanism transaction rolls back. This allows
    commit_failure_pass() to insert an AnalysisPass with the correct FK.
    """
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


def ensure_stakeholder_committed(practitioner_id: str) -> None:
    """
    Create stakeholder record in its own committed transaction if it does not exist.
    Same rationale as ensure_project_committed.
    """
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


def ensure_domain_register_seeded(project_id: str) -> None:
    """
    Seed a DomainRegister row in the register table for project_id if absent.

    Called from Pass 3c Stage 1 before the mechanism transaction opens.
    Per Domain Derivation Mechanism Spec v0.13 §5.1 and §10:
      register_id = 'DR-001', register_type = 'Domain'.
      member_ids starts as '[]' — updated on every Pass 3c run.

    If the register table does not exist (migration not applied), raises
    immediately so Stage 1 can produce the correct failure_reason.
    """
    session = get_session()
    try:
        result = session.execute(
            text(
                "SELECT register_id FROM register "
                "WHERE register_type = 'Domain' AND project_id = :pid"
            ),
            {"pid": project_id},
        ).fetchone()
        if result is None:
            session.execute(
                text(
                    "INSERT INTO register "
                    "(register_id, register_type, project_id, member_ids, completeness_rule) "
                    "VALUES (:rid, 'Domain', :pid, :mi, :cr)"
                ),
                {
                    "rid": "DR-001",
                    "pid": project_id,
                    "mi": json.dumps([]),
                    "cr": (
                        "This register SHALL contain the identifiers of ALL "
                        "Domain elements present in the ledger."
                    ),
                },
            )
            session.commit()
        else:
            session.rollback()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_requirement_register_seeded(project_id: str) -> None:
    """
    Seed a RequirementRegister row in the register table for project_id if absent.

    Called from Pass 3d __init__ before the mechanism transaction opens.
    Per Requirement Derivation Mechanism Spec v0.1 §5.1:
      register_id = 'RR-001', register_type = 'Requirement'.
      member_ids starts as '[]' — replaced on every Pass 3d run.

    If the register table does not exist (migration not applied), raises
    immediately so the orchestrator can produce the correct failure_reason.
    """
    session = get_session()
    try:
        result = session.execute(
            text(
                "SELECT register_id FROM register "
                "WHERE register_type = 'Requirement' AND project_id = :pid"
            ),
            {"pid": project_id},
        ).fetchone()
        if result is None:
            session.execute(
                text(
                    "INSERT INTO register "
                    "(register_id, register_type, project_id, member_ids, completeness_rule) "
                    "VALUES (:rid, 'Requirement', :pid, :mi, :cr)"
                ),
                {
                    "rid": "RR-001",
                    "pid": project_id,
                    "mi": json.dumps([]),
                    "cr": (
                        "This register SHALL contain the identifiers of ALL "
                        "Requirement elements present in the ledger."
                    ),
                },
            )
            session.commit()
        else:
            session.rollback()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
