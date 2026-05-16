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
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

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
