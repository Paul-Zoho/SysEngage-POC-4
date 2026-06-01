"""
Conftest for Pass 3d Requirement Derivation tests.

Mirrors the pattern from tests/domain_derivation/conftest.py:
  - Uses Neon test branch isolation (via NEON_DATABASE_URL env var).
  - Provides session fixture with rollback semantics for unit tests.
  - Provides a pre-seeded project + project_profile + Domains for integration tests.
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
    DomainModel,
    ProjectModel,
    ProjectProfileModel,
    ZachmanCellModel,
)

PROJECT_ID = "TEST_RD_3D"
PRACTITIONER_ID = "SH001"
ROW_REF = 4

# Standard 5-CCI, 2-Domain fixture (mirrors Pass 3c output for Row 4)
DOMAIN_A_ID = "D001"
DOMAIN_B_ID = "D002"
DOMAIN_A_CCIS = ["CCI-ROW4-C-What-001", "CCI-ROW4-C-How-001"]
DOMAIN_B_CCIS = ["CCI-ROW4-C-What-002", "CCI-ROW4-C-How-002", "CCI-ROW4-C-Where-001"]


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


def seed_domain(
    session: Session,
    domain_id: str,
    name: str,
    description: str,
    cci_refs: list[str],
) -> None:
    existing = session.execute(
        text(
            "SELECT domain_id FROM domain "
            "WHERE domain_id = :did AND project_id = :pid"
        ),
        {"did": domain_id, "pid": PROJECT_ID},
    ).fetchone()
    if not existing:
        session.add(
            DomainModel(
                domain_id=domain_id,
                project_id=PROJECT_ID,
                name=name,
                description=description,
                row_target=str(ROW_REF),
                cell_content_item_refs=cci_refs,
            )
        )
        session.flush()


def seed_3c_pass(session: Session) -> None:
    """Insert a mock completed Pass 3c AnalysisPass so Stage 1 precondition passes."""
    from datetime import datetime, timezone

    from core.db import format_identifier, get_next_sequence_value

    existing = session.execute(
        text(
            "SELECT pass_id FROM analysis_pass "
            "WHERE project_id = :pid AND mechanism = 'DomainDerivation' "
            "AND execution_status IN ('Completed', 'CompletedWithWarnings') "
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
                phase_id="PH003",
                pass_type="Universal",
                mechanism="DomainDerivation",
                evaluated_scope=f"Row {ROW_REF} for {PROJECT_ID}",
                confidence=1.0,
                pass_started_at=now,
                pass_completed_at=now,
                execution_status="Completed",
                mode_active="IM",
                declared_transformation_modes=["IM", "DM"],
                elapsed_ms=100,
                practitioner_id=PRACTITIONER_ID,
                project_id=PROJECT_ID,
                outputs={
                    "mechanism_data": {"row_ref": ROW_REF, "domain_count": 2},
                    "read_witness": {},
                },
            )
        )
        session.flush()


def seed_requirement_register(session: Session) -> None:
    """Ensure RequirementRegister row exists for the test project."""
    existing = session.execute(
        text(
            "SELECT register_id FROM register "
            "WHERE register_type = 'Requirement' AND project_id = :pid"
        ),
        {"pid": PROJECT_ID},
    ).fetchone()
    if not existing:
        session.execute(
            text(
                "INSERT INTO register "
                "(register_id, register_type, project_id, member_ids, completeness_rule) "
                "VALUES (:rid, 'Requirement', :pid, '[]', 'Test register')"
            ),
            {"rid": "RR-001", "pid": PROJECT_ID},
        )
        session.flush()


def seed_standard_test_dataset(session: Session) -> None:
    """
    Seed project, profile, ZachmanCells, CCIs, 2 Domains, 3c pass,
    and RequirementRegister.
    """
    seed_project(session)
    seed_project_profile(session)
    seed_requirement_register(session)

    cells = [
        ("ZC-R4-C-What", "What"),
        ("ZC-R4-C-How", "How"),
        ("ZC-R4-C-Where", "Where"),
    ]
    for cell_id, column in cells:
        seed_zachman_cell(session, cell_id, column)

    ccis = [
        ("CCI-ROW4-C-What-001", "ZC-R4-C-What", "What", "Component", "Auth service component"),
        ("CCI-ROW4-C-What-002", "ZC-R4-C-What", "What", "Component", "DB access layer"),
        ("CCI-ROW4-C-How-001", "ZC-R4-C-How", "How", "Process", "OAuth2 token validation"),
        ("CCI-ROW4-C-How-002", "ZC-R4-C-How", "How", "Process", "DB query execution"),
        ("CCI-ROW4-C-Where-001", "ZC-R4-C-Where", "Where", "Location", "Cloud deployment target"),
    ]
    for ci_id, cell_id, column, cls_type, desc in ccis:
        seed_cci(session, ci_id, cell_id, column, cls_type, desc)

    seed_domain(
        session,
        DOMAIN_A_ID,
        "Authentication Infrastructure",
        "Physical components realising authentication and token management",
        DOMAIN_A_CCIS,
    )
    seed_domain(
        session,
        DOMAIN_B_ID,
        "Data Access and Deployment Platform",
        "DB access layer components, query execution, and cloud deployment context",
        DOMAIN_B_CCIS,
    )
    seed_3c_pass(session)


# ---------------------------------------------------------------------------
# AI response builder helpers (for mock patch targets)
# ---------------------------------------------------------------------------


def make_derivation_response(proposals: list[dict]) -> str:
    """Build a valid RequirementDerivationResponse JSON string (list)."""
    return json.dumps(proposals)


def make_incremental_response(proposals: list[dict]) -> str:
    """Build a valid RequirementIncrementalResponse JSON string (list)."""
    return json.dumps(proposals)


def make_repair_response(proposals: list[dict]) -> str:
    """Build a valid RequirementRepairResponse JSON string (list)."""
    return json.dumps(proposals)
