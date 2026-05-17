"""
Conftest for Row-Lens Source Re-Analysis tests.

Provides:
- project/stakeholder fixtures committed in isolated transactions (mirroring
  the ledger discipline of the mechanism itself)
- Source fixtures for stream 1
- Domain + Requirement fixtures for stream 2
- mock_ai_client fixture for AI-involving tests
- Mock AI response builders for classification and conflict sweep
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from core.db import get_session
from models import (
    ProjectModel,
    StakeholderModel,
    SourceModel,
    DomainModel,
    RequirementModel,
    ProjectProfileModel,
    SignalModel,
    ConcernModel,
    AnalysisPassModel,
)
from models.segment import SegmentModel
from models.source_atom import SourceAtomModel
from sqlalchemy import delete


PROJECT_ID = "TESTPROJ_RL"
PRACTITIONER_ID = "SH_RL_TEST"


def _commit(obj_or_list) -> None:
    session = get_session()
    try:
        items = obj_or_list if isinstance(obj_or_list, list) else [obj_or_list]
        for item in items:
            session.add(item)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _delete_test_data() -> None:
    """
    Clean up all test data for PROJECT_ID to ensure test isolation.

    Uses a single session but commits after each table's DELETE so that a
    failure on one table cannot roll back the others.  The connection stays
    open across all deletes (one round-trip overhead instead of eleven).
    Deletion order respects FK constraints: children before parents.
    Errors per table are silently absorbed — teardown is best-effort.
    """
    stmts = [
        delete(AnalysisPassModel).where(AnalysisPassModel.project_id == PROJECT_ID),
        delete(SignalModel).where(SignalModel.project_id == PROJECT_ID),
        delete(ConcernModel).where(ConcernModel.project_id == PROJECT_ID),
        delete(SourceAtomModel).where(SourceAtomModel.project_id == PROJECT_ID),
        delete(SourceModel).where(SourceModel.project_id == PROJECT_ID),
        delete(RequirementModel).where(RequirementModel.project_id == PROJECT_ID),
        delete(DomainModel).where(DomainModel.project_id == PROJECT_ID),
        delete(SegmentModel).where(SegmentModel.project_id == PROJECT_ID),
        delete(ProjectProfileModel).where(ProjectProfileModel.project_id == PROJECT_ID),
        delete(ProjectModel).where(ProjectModel.project_id == PROJECT_ID),
        delete(StakeholderModel).where(StakeholderModel.stakeholder_id == PRACTITIONER_ID),
    ]
    session = get_session()
    try:
        for stmt in stmts:
            try:
                session.execute(stmt)
                session.commit()
            except Exception:
                session.rollback()
    finally:
        session.close()


@pytest.fixture()
def test_project():
    """Create project + stakeholder records for tests.

    Commits Project and Stakeholder in separate transactions so that a
    pre-existing row for one (left over from a prior test's failed teardown)
    cannot prevent creation of the other.
    """
    _delete_test_data()
    _commit(
        ProjectModel(
            project_id=PROJECT_ID,
            name="Row Lens Test Project",
            created_at=datetime.now(timezone.utc),
        )
    )
    _commit(
        StakeholderModel(
            stakeholder_id=PRACTITIONER_ID,
            name="Test Practitioner",
            stakeholder_type="practitioner",
            created_at=datetime.now(timezone.utc),
        )
    )
    yield PROJECT_ID
    _delete_test_data()


@pytest.fixture()
def project_profile(test_project):
    """Create a default ProjectProfile for the test project."""
    _commit(
        ProjectProfileModel(
            project_id=PROJECT_ID,
            concern_threshold=0.65,
            chunk_match_threshold=0.6,
            residual_batch_size=50,
            created_at=datetime.now(timezone.utc),
        )
    )
    return PROJECT_ID


@pytest.fixture()
def sources_3(test_project):
    """
    Three Sources in stream 1 for testing.
    Content: pocket-money-style simple sentences for Row 1 lens.
    """
    src_data = [
        ("RLS901", "The pocket money app lets children track their savings."),
        ("RLS902", "Parents approve or reject spending requests from children."),
        ("RLS903", "The system sends weekly summaries to parents via email."),
    ]
    _commit(
        [
            SourceModel(
                source_id=sid,
                source_text=text,
                segmentation_context="paragraph",
                input_material_ref="test_doc.txt",
                confidence=1.0,
                project_id=PROJECT_ID,
                created_at=datetime.now(timezone.utc),
            )
            for sid, text in src_data
        ]
    )
    return [sid for sid, _ in src_data]


@pytest.fixture()
def stream2_domain_and_requirements(test_project):
    """
    One Domain + two Requirements at row_target="1" for Row 2 chunk assembly tests.
    """
    domain = DomainModel(
        domain_id="RLD901",
        name="User Management",
        row_target="1",
        project_id=PROJECT_ID,
        created_at=datetime.now(timezone.utc),
    )
    reqs = [
        RequirementModel(
            requirement_id="RLR901",
            statement="Children can manage their pocket money accounts.",
            row_target="1",
            domain_id="RLD901",
            project_id=PROJECT_ID,
            created_at=datetime.now(timezone.utc),
        ),
        RequirementModel(
            requirement_id="RLR902",
            statement="Parents oversee and approve child spending requests.",
            row_target="1",
            domain_id="RLD901",
            project_id=PROJECT_ID,
            created_at=datetime.now(timezone.utc),
        ),
    ]
    _commit([domain] + reqs)
    return {"domain_id": "RLD901", "requirement_ids": ["RLR901", "RLR902"]}


def make_classification_response(items: list[dict]) -> str:
    """
    Build a JSON string that the mock AI client will return for classification.
    Each item: {item_id, classification, signal_type, confidence, description}
    """
    return json.dumps({"items": items})


def make_conflict_sweep_response(conflicts: list[dict]) -> str:
    """
    Build a JSON string that the mock AI client will return for conflict sweep.
    Each conflict: {source_id, is_genuine_contradiction, rationale}
    """
    return json.dumps({"conflicts": conflicts})


def build_mock_message(content_text: str, model: str = "claude-sonnet-4-5") -> MagicMock:
    """Build a mock Anthropic message object."""
    msg = MagicMock()
    msg.model = model
    content_item = MagicMock()
    content_item.text = content_text
    msg.content = [content_item]
    return msg


@pytest.fixture()
def mock_ai_client():
    """
    Patch get_ai_client() across all mechanism modules so tests don't hit the real API.
    The fixture exposes the mock client so individual tests can configure responses.
    """
    mock_client = MagicMock()
    patch_targets = [
        "mechanisms.row_lens_source_reanalysis.stage2_chunk_classification.get_ai_client",
        "mechanisms.row_lens_source_reanalysis.stage2_residual_classification.get_ai_client",
        "mechanisms.row_lens_source_reanalysis.stage4_conflict_sweep.get_ai_client",
    ]
    with patch(patch_targets[0], return_value=mock_client), \
         patch(patch_targets[1], return_value=mock_client), \
         patch(patch_targets[2], return_value=mock_client):
        yield mock_client
