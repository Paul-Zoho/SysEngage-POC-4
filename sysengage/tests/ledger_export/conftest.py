"""
Test fixtures for ledger_export tests.

All fixtures use in-memory data — no database connection required.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from mechanisms.ledger_export.db_reader import ProjectData


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


# ── minimal model factories ──────────────────────────────────────────────────

def make_project(project_id="PROJ001", name="Test Project") -> SimpleNamespace:
    return SimpleNamespace(
        project_id=project_id,
        name=name,
    )


def make_source(
    source_id="S001",
    source_text="The system shall allow users to track expenses.",
    segmentation_context="normative statement",
    input_material_ref="test_doc.docx",
    confidence=1.0,
    parent_source_ref=None,
    project_id="PROJ001",
) -> SimpleNamespace:
    return SimpleNamespace(
        source_id=source_id,
        source_text=source_text,
        segmentation_context=segmentation_context,
        input_material_ref=input_material_ref,
        confidence=confidence,
        parent_source_ref=parent_source_ref,
        project_id=project_id,
    )


def make_segment(
    segment_id="SEG001",
    title="Introduction",
    description=None,
    source_refs=None,
    parent_segment_ref=None,
    confidence=1.0,
    project_id="PROJ001",
) -> SimpleNamespace:
    return SimpleNamespace(
        segment_id=segment_id,
        title=title,
        description=description,
        source_refs=source_refs or ["S001"],
        parent_segment_ref=parent_segment_ref,
        confidence=confidence,
        project_id=project_id,
    )


def make_source_atom(
    atom_id="SA001",
    atom_text="users to track expenses",
    source_ref="S001",
    segment_ref=None,
    parent_atom_ref=None,
    confidence=0.95,
    position=1,
    project_id="PROJ001",
) -> SimpleNamespace:
    return SimpleNamespace(
        atom_id=atom_id,
        atom_text=atom_text,
        source_ref=source_ref,
        segment_ref=segment_ref,
        parent_atom_ref=parent_atom_ref,
        confidence=confidence,
        position=position,
        project_id=project_id,
    )


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
) -> SimpleNamespace:
    return SimpleNamespace(
        signal_id=signal_id,
        signal_type=signal_type,
        row_target=row_target,
        description=description,
        source_refs=source_refs or ["S001"],
        sourceatom_refs=sourceatom_refs or [],
        confidence=confidence,
        derived_from_concern_id=derived_from_concern_id,
        project_id=project_id,
    )


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
) -> SimpleNamespace:
    return SimpleNamespace(
        concern_id=concern_id,
        source_refs=source_refs or ["S001"],
        description=description,
        state=state,
        produced_in_row=produced_in_row,
        practitioner_id=practitioner_id,
        dispositioned_with_outcome=dispositioned_with_outcome,
        disposition_rationale=disposition_rationale,
        confidence=confidence,
        project_id=project_id,
    )


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
) -> SimpleNamespace:
    return SimpleNamespace(
        pass_id=pass_id,
        pass_type=pass_type,
        mechanism=mechanism,
        evaluated_scope=evaluated_scope,
        execution_status=execution_status,
        mode_active=mode_active,
        declared_transformation_modes=declared_transformation_modes or ["LPM"],
        outputs=outputs or {
            "read_witness": {
                "input_hash": "abc123",
                "byte_count": 1024,
                "character_count": 512,
                "read_mode": "LPM",
                "read_completion_status": "Complete",
            },
            "mechanism_data": {"source_count": 1},
            "mode_violations": [],
        },
        pass_started_at=pass_started_at or _dt("2026-05-01T10:00:00"),
        pass_completed_at=pass_completed_at or _dt("2026-05-01T10:00:01"),
        elapsed_ms=elapsed_ms,
        confidence=confidence,
        practitioner_id=practitioner_id,
        project_id=project_id,
    )


def make_stakeholder(
    stakeholder_id="SH001",
    name="SysEngage",
    stakeholder_type="AutomatedAnalysisAgent",
) -> SimpleNamespace:
    return SimpleNamespace(
        stakeholder_id=stakeholder_id,
        name=name,
        stakeholder_type=stakeholder_type,
    )


def make_domain(
    domain_id="D001",
    name="Expense Tracking",
    row_target="1",
    description=None,
    classification_type=None,
    cell_content_item_refs=None,
    project_id="PROJ001",
) -> SimpleNamespace:
    return SimpleNamespace(
        domain_id=domain_id,
        name=name,
        row_target=row_target,
        description=description,
        classification_type=classification_type,
        cell_content_item_refs=cell_content_item_refs or [],
        project_id=project_id,
    )


def make_requirement(
    requirement_id="R001",
    statement="The system shall allow users to track household expenses.",
    requirement_type="Functional",
    row_target="1",
    domain_id="D001",
    confidence=1.0,
    cci_refs=None,
    domain_refs=None,
    answer_refs=None,
    rationale=None,
    fit_criteria=None,
    verification_method=None,
    priority=None,
    retired_at=None,
    project_id="PROJ001",
) -> SimpleNamespace:
    return SimpleNamespace(
        requirement_id=requirement_id,
        statement=statement,
        requirement_type=requirement_type,
        row_target=row_target,
        domain_id=domain_id,
        confidence=confidence,
        cci_refs=cci_refs or [],
        domain_refs=domain_refs or [],
        answer_refs=answer_refs or [],
        rationale=rationale,
        fit_criteria=fit_criteria,
        verification_method=verification_method,
        priority=priority,
        retired_at=retired_at,
        project_id=project_id,
    )


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
            make_requirement("R001", "The system shall track expenses.", row_target="1", domain_id="D001", project_id="FULL001"),
        ],
    )
