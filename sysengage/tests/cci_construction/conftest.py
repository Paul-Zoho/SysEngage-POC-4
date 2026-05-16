"""
Conftest for CCI Construction tests.

Provides:
- project/stakeholder fixtures committed in isolated transactions
- Signal fixtures for testing (row_target="2")
- ZachmanCell + CellContentItem cleanup helpers
- mock_ai_client fixture patching both Step 3 and Step 4 AI call sites
- Response builder helpers for derivation and dedup responses
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from core.db import get_session
from models import (
    AnalysisPassModel,
    ConcernModel,
    DomainModel,
    ProjectModel,
    ProjectProfileModel,
    RequirementModel,
    SignalModel,
    StakeholderModel,
)
from models.cell_content_item import CellContentItemModel
from models.zachman_cell import ZachmanCellModel
from sqlalchemy import delete

PROJECT_ID = "TESTPROJ_CCI"
PRACTITIONER_ID = "SH_CCI_TEST"
ROW_REF = 2


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
    """Clean up all test data for PROJECT_ID."""
    session = get_session()
    try:
        session.execute(
            delete(AnalysisPassModel).where(
                AnalysisPassModel.project_id == PROJECT_ID
            )
        )
        session.execute(
            delete(CellContentItemModel).where(
                CellContentItemModel.project_id == PROJECT_ID
            )
        )
        session.execute(
            delete(ZachmanCellModel).where(
                ZachmanCellModel.project_id == PROJECT_ID
            )
        )
        session.execute(
            delete(SignalModel).where(SignalModel.project_id == PROJECT_ID)
        )
        session.execute(
            delete(ConcernModel).where(ConcernModel.project_id == PROJECT_ID)
        )
        session.execute(
            delete(RequirementModel).where(
                RequirementModel.project_id == PROJECT_ID
            )
        )
        session.execute(
            delete(DomainModel).where(DomainModel.project_id == PROJECT_ID)
        )
        session.execute(
            delete(ProjectProfileModel).where(
                ProjectProfileModel.project_id == PROJECT_ID
            )
        )
        session.execute(
            delete(ProjectModel).where(ProjectModel.project_id == PROJECT_ID)
        )
        session.execute(
            delete(StakeholderModel).where(
                StakeholderModel.stakeholder_id == PRACTITIONER_ID
            )
        )
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@pytest.fixture()
def test_project():
    """Create project + stakeholder records for CCI tests."""
    _delete_test_data()
    _commit(
        [
            ProjectModel(
                project_id=PROJECT_ID,
                name="CCI Construction Test Project",
                created_at=datetime.now(timezone.utc),
            ),
            StakeholderModel(
                stakeholder_id=PRACTITIONER_ID,
                name="CCI Test Practitioner",
                stakeholder_type="practitioner",
                created_at=datetime.now(timezone.utc),
            ),
        ]
    )
    yield PROJECT_ID
    _delete_test_data()


@pytest.fixture()
def project_profile(test_project):
    """Create a ProjectProfile with CCI config for the test project."""
    _commit(
        ProjectProfileModel(
            project_id=PROJECT_ID,
            concern_threshold=0.65,
            chunk_match_threshold=0.6,
            residual_batch_size=50,
            cci_consolidation_threshold=0.80,
            cci_batch_size=20,
            created_at=datetime.now(timezone.utc),
        )
    )
    return PROJECT_ID


@pytest.fixture()
def signals_3(test_project):
    """
    Three Signals at row_target="2" for CCI tests.
    Content: pocket-money domain signals.
    """
    sig_data = [
        ("SG901", "Normative", "Children maintain pocket money accounts tracking savings and spending history."),
        ("SG902", "Actor", "Parents act as financial guardians approving or rejecting child spending requests."),
        ("SG903", "Normative", "The system transmits weekly financial summaries to parents via email notification."),
    ]
    _commit(
        [
            SignalModel(
                signal_id=sid,
                signal_type=stype,
                row_target="2",
                description=desc,
                source_refs=[f"SRC_{sid}"],
                sourceatom_refs=[],
                confidence=0.85,
                derived_from_concern_id=None,
                project_id=PROJECT_ID,
                created_at=datetime.now(timezone.utc),
            )
            for sid, stype, desc in sig_data
        ]
    )
    return [sid for sid, _, _ in sig_data]


def make_derivation_response(items: list[dict]) -> str:
    """Build a JSON string for Stage 3a AI derivation response."""
    return json.dumps({"items": items})


def make_dedup_response(verdicts: list[dict]) -> str:
    """Build a JSON string for Stage 4b AI dedup response."""
    return json.dumps({"verdicts": verdicts})


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
    Patch get_ai_client() across both AI-invoking step modules.
    Exposes the mock client so individual tests can configure responses.
    """
    mock_client = MagicMock()
    patch_targets = [
        "mechanisms.cci_construction.step3_cci_derivation.get_ai_client",
        "mechanisms.cci_construction.step4_deduplication.get_ai_client",
    ]
    with patch(patch_targets[0], return_value=mock_client), \
         patch(patch_targets[1], return_value=mock_client):
        yield mock_client
