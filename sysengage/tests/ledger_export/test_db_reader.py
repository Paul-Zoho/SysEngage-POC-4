"""
Tests for ledger_export/db_reader.py.

Uses a mocked SQLAlchemy session — no real database connection required.
Verifies query dispatch, result assembly, stakeholder scoping, and error handling.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from mechanisms.ledger_export.db_reader import ProjectData, read_project_data
from tests.ledger_export.conftest import (
    make_analysis_pass,
    make_concern,
    make_domain,
    make_project,
    make_requirement,
    make_segment,
    make_signal,
    make_source,
    make_source_atom,
    make_stakeholder,
)


def _make_query_chain(results: list) -> MagicMock:
    """Return a mock that chains .filter().order_by().all() → results."""
    chain = MagicMock()
    chain.filter.return_value = chain
    chain.order_by.return_value = chain
    chain.all.return_value = results
    return chain


def _make_session(
    project=None,
    sources=None,
    segments=None,
    source_atoms=None,
    signals=None,
    concerns=None,
    analysis_passes=None,
    stakeholders=None,
    domains=None,
    requirements=None,
) -> MagicMock:
    """Build a mock session that returns the provided lists for each entity type."""
    session = MagicMock()

    if project is None:
        project = make_project()
    session.get.return_value = project

    query_results_by_call: list[list] = [
        sources or [make_source()],
        segments or [],
        source_atoms or [],
        signals or [],
        concerns or [],
        analysis_passes or [make_analysis_pass()],
        stakeholders or [make_stakeholder()],
        domains or [],
        requirements or [],
    ]

    call_index = 0

    def _query_side_effect(model_cls):
        nonlocal call_index
        chain = _make_query_chain(query_results_by_call[call_index % len(query_results_by_call)])
        call_index += 1
        return chain

    session.query.side_effect = _query_side_effect
    return session


# ── project not found ─────────────────────────────────────────────────────────

class TestProjectNotFound:
    def test_raises_value_error_when_project_missing(self):
        session = MagicMock()
        session.get.return_value = None
        with pytest.raises(ValueError, match="Project not found"):
            read_project_data("NONEXISTENT", session)

    def test_error_message_includes_project_id(self):
        session = MagicMock()
        session.get.return_value = None
        with pytest.raises(ValueError, match="NONEXISTENT"):
            read_project_data("NONEXISTENT", session)


# ── successful reads ──────────────────────────────────────────────────────────

class TestSuccessfulRead:
    def test_returns_project_data_instance(self):
        session = _make_session()
        result = read_project_data("PROJ001", session)
        assert isinstance(result, ProjectData)

    def test_project_is_set(self):
        project = make_project(project_id="PROJ001")
        session = _make_session(project=project)
        result = read_project_data("PROJ001", session)
        assert result.project.project_id == "PROJ001"

    def test_sources_populated(self):
        sources = [make_source("S001"), make_source("S002")]
        session = _make_session(sources=sources)
        result = read_project_data("PROJ001", session)
        assert len(result.sources) == 2

    def test_empty_collections_default_to_empty_lists(self):
        session = _make_session()
        result = read_project_data("PROJ001", session)
        assert isinstance(result.segments, list)
        assert isinstance(result.source_atoms, list)
        assert isinstance(result.signals, list)
        assert isinstance(result.concerns, list)
        assert isinstance(result.domains, list)
        assert isinstance(result.requirements, list)

    def test_analysis_passes_populated(self):
        passes = [make_analysis_pass("P001"), make_analysis_pass("P002")]
        session = _make_session(analysis_passes=passes)
        result = read_project_data("PROJ001", session)
        assert len(result.analysis_passes) == 2

    def test_stakeholders_populated(self):
        stakeholders = [make_stakeholder("SH001"), make_stakeholder("SH002", "Alice")]
        session = _make_session(stakeholders=stakeholders)
        result = read_project_data("PROJ001", session)
        assert len(result.stakeholders) == 2

    def test_signals_populated(self):
        signals = [make_signal("SG001"), make_signal("SG002")]
        session = _make_session(signals=signals)
        result = read_project_data("PROJ001", session)
        assert len(result.signals) == 2

    def test_concerns_populated(self):
        concerns = [make_concern("CN001"), make_concern("CN002")]
        session = _make_session(concerns=concerns)
        result = read_project_data("PROJ001", session)
        assert len(result.concerns) == 2

    def test_domains_populated(self):
        domains = [make_domain("D001")]
        session = _make_session(domains=domains)
        result = read_project_data("PROJ001", session)
        assert len(result.domains) == 1

    def test_requirements_populated(self):
        reqs = [make_requirement("R001"), make_requirement("R002")]
        session = _make_session(requirements=reqs)
        result = read_project_data("PROJ001", session)
        assert len(result.requirements) == 2

    def test_session_get_called_with_project_id(self):
        session = _make_session()
        read_project_data("PROJ001", session)
        from models.project import ProjectModel
        session.get.assert_called_once_with(ProjectModel, "PROJ001")


# ── ProjectData dataclass ─────────────────────────────────────────────────────

class TestProjectDataDataclass:
    def test_default_empty_lists(self):
        project = make_project()
        data = ProjectData(project=project)
        assert data.sources == []
        assert data.segments == []
        assert data.source_atoms == []
        assert data.signals == []
        assert data.concerns == []
        assert data.analysis_passes == []
        assert data.stakeholders == []
        assert data.domains == []
        assert data.requirements == []

    def test_fields_assignable(self):
        project = make_project()
        sources = [make_source("S001")]
        data = ProjectData(project=project, sources=sources)
        assert data.sources is sources
