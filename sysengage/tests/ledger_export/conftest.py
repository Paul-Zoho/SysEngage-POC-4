"""
Test fixtures for ledger_export tests.

All fixtures use in-memory data — no database connection required.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from mechanisms.ledger_export.db_reader import ProjectData


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


# ── minimal model factories ──────────────────────────────────────────────────

def make_project(project_id="PROJ001", name="Test Project") -> MagicMock:
    p = MagicMock()
    p.project_id = project_id
    p.name = name
    return p


def make_source(
    source_id="S001",
    source_text="The system shall allow users to track expenses.",
    segmentation_context="normative statement",
    input_material_ref="test_doc.docx",
    confidence=1.0,
    parent_source_ref=None,
    project_id="PROJ001",
) -> MagicMock:
    s = MagicMock()
    s.source_id = source_id
    s.source_text = source_text
    s.segmentation_context = segmentation_context
    s.input_material_ref = input_material_ref
    s.confidence = confidence
    s.parent_source_ref = parent_source_ref
    s.project_id = project_id
    return s


def make_segment(
    segment_id="SEG001",
    title="Introduction",
    description=None,
    source_refs=None,
    parent_segment_ref=None,
    confidence=1.0,
    project_id="PROJ001",
) -> MagicMock:
    seg = MagicMock()
    seg.segment_id = segment_id
    seg.title = title
    seg.description = description
    seg.source_refs = source_refs or ["S001"]
    seg.parent_segment_ref = parent_segment_ref
    seg.confidence = confidence
    seg.project_id = project_id
    return seg


def make_source_atom(
    atom_id="SA001",
    atom_text="users to track expenses",
    source_ref="S001",
    segment_ref=None,
    parent_atom_ref=None,
    confidence=0.95,
    position=1,
    project_id="PROJ001",
) -> MagicMock:
    a = MagicMock()
    a.atom_id = atom_id
    a.atom_text = atom_text
    a.source_ref = source_ref
    a.segment_ref = segment_ref
    a.parent_atom_ref = parent_atom_ref
    a.confidence = confidence
    a.position = position
    a.project_id = project_id
    return a


def make_signal(
    signal_id="SG001",
    signal_type="Intent",
    row_target="1",
    description="Users intend to track household expenses.",
    source_refs=None,
    sourceatom_refs=None,
    confidence=0.9,
    derived_from_concern_id=None,
    project_id="PROJ001",
) -> MagicMock:
    sig = MagicMock()
    sig.signal_id = signal_id
    sig.signal_type = signal_type
    sig.row_target = row_target
    sig.description = description
    sig.source_refs = source_refs or ["S001"]
    sig.sourceatom_refs = sourceatom_refs or []
    sig.confidence = confidence
    sig.derived_from_concern_id = derived_from_concern_id
    sig.project_id = project_id
    return sig


def make_concern(
    concern_id="CN001",
    source_refs=None,
    description="Ambiguous: it is unclear whether 'users' refers to individuals or households.",
    state="Open",
    produced_in_row="1",
    practitioner_id="SH001",
    dispositioned_with_outcome=None,
    disposition_rationale=None,
    confidence=0.75,
    project_id="PROJ001",
) -> MagicMock:
    cn = MagicMock()
    cn.concern_id = concern_id
    cn.source_refs = source_refs or ["S001"]
    cn.description = description
    cn.state = state
    cn.produced_in_row = produced_in_row
    cn.practitioner_id = practitioner_id
    cn.dispositioned_with_outcome = dispositioned_with_outcome
    cn.disposition_rationale = disposition_rationale
    cn.confidence = confidence
    cn.project_id = project_id
    return cn


def make_analysis_pass(
    pass_id="P001",
    pass_type="Universal",
    mechanism="SourceCapture",
    evaluated_scope="All input material",
    execution_status="Completed",
    mode_active="LPM",
    declared_transformation_modes=None,
    outputs=None,
    pass_started_at=None,
    pass_completed_at=None,
    elapsed_ms=1234,
    confidence=1.0,
    practitioner_id="SH001",
    project_id="PROJ001",
) -> MagicMock:
    ap = MagicMock()
    ap.pass_id = pass_id
    ap.pass_type = pass_type
    ap.mechanism = mechanism
    ap.evaluated_scope = evaluated_scope
    ap.execution_status = execution_status
    ap.mode_active = mode_active
    ap.declared_transformation_modes = declared_transformation_modes or ["LPM"]
    ap.outputs = outputs or {
        "read_witness": {
            "input_hash": "abc123",
            "byte_count": 1024,
            "character_count": 512,
            "read_mode": "LPM",
            "read_completion_status": "Complete",
        },
        "mechanism_data": {"source_count": 1},
        "mode_violations": [],
    }
    ap.pass_started_at = pass_started_at or _dt("2026-05-01T10:00:00")
    ap.pass_completed_at = pass_completed_at or _dt("2026-05-01T10:00:01")
    ap.elapsed_ms = elapsed_ms
    ap.confidence = confidence
    ap.practitioner_id = practitioner_id
    ap.project_id = project_id
    return ap


def make_stakeholder(
    stakeholder_id="SH001",
    name="SysEngage",
    stakeholder_type="AutomatedAnalysisAgent",
) -> MagicMock:
    sh = MagicMock()
    sh.stakeholder_id = stakeholder_id
    sh.name = name
    sh.stakeholder_type = stakeholder_type
    return sh


def make_domain(
    domain_id="D001",
    name="Expense Tracking",
    row_target="1",
    project_id="PROJ001",
) -> MagicMock:
    d = MagicMock()
    d.domain_id = domain_id
    d.name = name
    d.row_target = row_target
    d.project_id = project_id
    return d


def make_requirement(
    requirement_id="R001",
    statement="The system shall allow users to track household expenses.",
    row_target="1",
    domain_id="D001",
    project_id="PROJ001",
) -> MagicMock:
    r = MagicMock()
    r.requirement_id = requirement_id
    r.statement = statement
    r.row_target = row_target
    r.domain_id = domain_id
    r.project_id = project_id
    return r


# ── assembled fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def minimal_project_data() -> ProjectData:
    """Minimal project with one source, one analysis pass, and SH001."""
    return ProjectData(
        project=make_project(),
        sources=[make_source()],
        segments=[],
        source_atoms=[],
        signals=[],
        concerns=[],
        analysis_passes=[make_analysis_pass()],
        stakeholders=[make_stakeholder()],
        domains=[],
        requirements=[],
    )


@pytest.fixture
def full_project_data() -> ProjectData:
    """Full project exercising every element type the module handles."""
    return ProjectData(
        project=make_project(project_id="FULL001", name="Full Test Project"),
        sources=[
            make_source("S001", "The system shall allow users to track expenses."),
            make_source("S002", "Budget categories shall be configurable.", project_id="FULL001"),
        ],
        segments=[
            make_segment("SEG001", "Requirements Section", source_refs=["S001", "S002"]),
        ],
        source_atoms=[
            make_source_atom("SA001", "track expenses", source_ref="S001"),
            make_source_atom("SA002", "configurable", source_ref="S002"),
        ],
        signals=[
            make_signal(
                "SG001",
                "Intent",
                "1",
                "Users intend to track household expenses.",
                source_refs=["S001"],
                project_id="FULL001",
            ),
            make_signal(
                "SG002",
                "Normative",
                "1",
                "Budget categories shall be configurable.",
                source_refs=["S002"],
                project_id="FULL001",
            ),
        ],
        concerns=[
            make_concern(
                "CN001",
                source_refs=["S001"],
                description="Ambiguous: 'users' scope unclear.",
                project_id="FULL001",
            ),
        ],
        analysis_passes=[
            make_analysis_pass("P001", project_id="FULL001"),
        ],
        stakeholders=[
            make_stakeholder("SH001", "SysEngage", "AutomatedAnalysisAgent"),
            make_stakeholder("SH002", "Alice", "Engineer"),
        ],
        domains=[
            make_domain("D001", "Expense Tracking", "1", project_id="FULL001"),
        ],
        requirements=[
            make_requirement("R001", "The system shall track expenses.", "1", "D001", project_id="FULL001"),
        ],
    )
