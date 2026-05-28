"""
Conftest for Pass 3c Domain Derivation tests.

Mirrors the pattern from tests/cci_construction/conftest.py:
  - Uses Neon test branch isolation (via NEON_DATABASE_URL env var).
  - Provides session fixture with rollback semantics for unit tests.
  - Provides a pre-seeded project + project_profile for integration tests.
  - Provides mock AI fixtures for deterministic structural validation tests.

Run tests individually per replit.md convention — NOT as a full suite.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.db import get_session
from models import (
    AnalysisPassModel,
    CellContentItemModel,
    DomainCCIMembershipModel,
    DomainModel,
    ProjectModel,
    ProjectProfileModel,
    ZachmanCellModel,
)

PROJECT_ID = "TEST_DD_3C"
PRACTITIONER_ID = "SH001"
ROW_REF = 4


# ---------------------------------------------------------------------------
# Session fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def session() -> Generator[Session, None, None]:
    s = get_session()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


# ---------------------------------------------------------------------------
# DB seeding helpers
# ---------------------------------------------------------------------------


def seed_project(session: Session) -> None:
    """Insert project if not present."""
    from datetime import datetime, timezone

    existing = session.execute(
        text("SELECT project_id FROM project WHERE project_id = :pid"),
        {"pid": PROJECT_ID},
    ).fetchone()
    if not existing:
        session.add(
            ProjectModel(
                project_id=PROJECT_ID,
                name=f"Test Project {PROJECT_ID}",
            )
        )
        session.flush()


def seed_project_profile(session: Session) -> None:
    """Insert project_profile if not present."""
    existing = session.execute(
        text("SELECT project_id FROM project_profile WHERE project_id = :pid"),
        {"pid": PROJECT_ID},
    ).fetchone()
    if not existing:
        session.add(
            ProjectProfileModel(
                project_id=PROJECT_ID,
            )
        )
        session.flush()


def seed_zachman_cell(session: Session, cell_id: str, column: str) -> None:
    """Upsert a ZachmanCell for testing."""
    existing = session.execute(
        text(
            "SELECT cell_id FROM zachman_cell "
            "WHERE cell_id = :cid AND project_id = :pid"
        ),
        {"cid": cell_id, "pid": PROJECT_ID},
    ).fetchone()
    if not existing:
        session.add(
            ZachmanCellModel(
                cell_id=cell_id,
                project_id=PROJECT_ID,
                row_target=str(ROW_REF),
                column=column,
            )
        )
        session.flush()


def seed_cci(
    session: Session,
    ci_id: str,
    cell_id: str,
    column: str,
    classification_type: str,
    description: str,
) -> None:
    """Upsert a CellContentItem for testing."""
    existing = session.execute(
        text(
            "SELECT ci_id FROM cell_content_item "
            "WHERE ci_id = :cid AND project_id = :pid"
        ),
        {"cid": ci_id, "pid": PROJECT_ID},
    ).fetchone()
    if not existing:
        session.add(
            CellContentItemModel(
                ci_id=ci_id,
                cell_id=cell_id,
                classification_type=classification_type,
                signal_refs=[],
                description=description,
                confidence=1.0,
                project_id=PROJECT_ID,
            )
        )
        session.flush()


def seed_3b_pass(session: Session) -> None:
    """Insert a mock completed Pass 3b AnalysisPass so Stage 1 precondition passes."""
    from datetime import datetime, timezone

    from core.db import format_identifier, get_next_sequence_value

    existing = session.execute(
        text(
            "SELECT pass_id FROM analysis_pass "
            "WHERE project_id = :pid AND mechanism = 'CellContentItemConstruction' "
            "LIMIT 1"
        ),
        {"pid": PROJECT_ID},
    ).fetchone()
    if not existing:
        seq_val = get_next_sequence_value(session, "p_id_seq")
        pass_id = format_identifier("P", seq_val)
        now = datetime.now(timezone.utc)
        session.add(
            AnalysisPassModel(
                pass_id=pass_id,
                phase_id="PH001",
                pass_type="Universal",
                mechanism="CellContentItemConstruction",
                evaluated_scope=f"Row {ROW_REF} for {PROJECT_ID}",
                confidence=1.0,
                pass_started_at=now,
                pass_completed_at=now,
                execution_status="Completed",
                mode_active="LPM",
                declared_transformation_modes=["LPM"],
                elapsed_ms=100,
                practitioner_id=PRACTITIONER_ID,
                project_id=PROJECT_ID,
                outputs={
                    "cci_data": {"row_ref": ROW_REF, "cci_count": 5},
                    "read_witness": {},
                },
            )
        )
        session.flush()


def seed_domain_register(session: Session) -> None:
    """Ensure DomainRegister row exists for the test project."""
    existing = session.execute(
        text(
            "SELECT register_id FROM register "
            "WHERE register_type = 'Domain' AND project_id = :pid"
        ),
        {"pid": PROJECT_ID},
    ).fetchone()
    if not existing:
        session.execute(
            text(
                "INSERT INTO register "
                "(register_id, register_type, project_id, member_ids, completeness_rule) "
                "VALUES (:rid, 'Domain', :pid, '[]', 'Test register')"
            ),
            {"rid": "DR-001", "pid": PROJECT_ID},
        )
        session.flush()


# ---------------------------------------------------------------------------
# Standard 5-CCI fixture for Row 4
# ---------------------------------------------------------------------------


def seed_standard_test_dataset(session: Session) -> None:
    """Seed project, profile, ZachmanCells, CCIs, 3b pass, and domain register."""
    seed_project(session)
    seed_project_profile(session)
    seed_domain_register(session)

    cells = [
        ("ZC-R4-C-What", "What"),
        ("ZC-R4-C-How", "How"),
        ("ZC-R4-C-Where", "Where"),
    ]
    for cell_id, column in cells:
        seed_zachman_cell(session, cell_id, column)

    ccis = [
        (
            "CCI-ROW4-C-What-001",
            "ZC-R4-C-What",
            "What",
            "Component",
            "Authentication service component",
        ),
        (
            "CCI-ROW4-C-What-002",
            "ZC-R4-C-What",
            "What",
            "Component",
            "Database access layer component",
        ),
        (
            "CCI-ROW4-C-How-001",
            "ZC-R4-C-How",
            "How",
            "Process",
            "OAuth2 token validation process",
        ),
        (
            "CCI-ROW4-C-How-002",
            "ZC-R4-C-How",
            "How",
            "Process",
            "Database query execution process",
        ),
        (
            "CCI-ROW4-C-Where-001",
            "ZC-R4-C-Where",
            "Where",
            "Location",
            "Cloud deployment target location",
        ),
    ]
    for ci_id, cell_id, column, cls_type, desc in ccis:
        seed_cci(session, ci_id, cell_id, column, cls_type, desc)

    seed_3b_pass(session)


# ---------------------------------------------------------------------------
# AI response builder helpers (for mock patch targets)
# ---------------------------------------------------------------------------


def make_grouping_response(proposals: list[dict]) -> str:
    """Build a valid DomainGroupingResponse JSON string."""
    return json.dumps({"proposals": proposals})


def make_incremental_response(actions: list[dict]) -> str:
    """Build a valid DomainIncrementalResponse JSON string."""
    return json.dumps({"actions": actions})


def make_repair_response(actions: list[dict]) -> str:
    """Build a valid DomainRepairResponse JSON string."""
    return json.dumps({"actions": actions})
