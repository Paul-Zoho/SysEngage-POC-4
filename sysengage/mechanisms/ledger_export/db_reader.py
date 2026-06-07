"""
Ledger Export — DB Reader.

Reads all canonical ledger entities for a project from the database.
Returns a ProjectData dataclass containing ordered lists of each element type.
Isolated from source_capture and row_lens_source_reanalysis mechanisms.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.analysis_pass import AnalysisPassModel
from models.cell_content_item import CellContentItemModel
from models.concern import ConcernModel
from models.domain import DomainModel
from models.project import ProjectModel
from models.requirement import RequirementModel
from models.segment import SegmentModel
from models.signal import SignalModel
from models.source import SourceModel
from models.source_atom import SourceAtomModel
from models.stakeholder import StakeholderModel
from models.zachman_cell import ZachmanCellModel


@dataclass
class ProjectData:
    """All canonical ledger elements for one project, read from DB."""

    project: ProjectModel
    sources: list[SourceModel] = field(default_factory=list)
    segments: list[SegmentModel] = field(default_factory=list)
    source_atoms: list[SourceAtomModel] = field(default_factory=list)
    signals: list[SignalModel] = field(default_factory=list)
    concerns: list[ConcernModel] = field(default_factory=list)
    analysis_passes: list[AnalysisPassModel] = field(default_factory=list)
    stakeholders: list[StakeholderModel] = field(default_factory=list)
    domains: list[DomainModel] = field(default_factory=list)
    requirements: list[RequirementModel] = field(default_factory=list)
    zachman_cells: list[ZachmanCellModel] = field(default_factory=list)
    ccis: list[CellContentItemModel] = field(default_factory=list)
    data_dictionary_entries: list[dict] = field(default_factory=list)


def read_project_data(project_id: str, session: Session) -> ProjectData:
    """
    Read all canonical ledger entities for *project_id* from the DB.

    Raises ValueError if the project does not exist.
    All lists are ordered deterministically (by primary key) for stable output.
    """
    project = session.get(ProjectModel, project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id!r}")

    sources = (
        session.query(SourceModel)
        .filter(SourceModel.project_id == project_id)
        .order_by(SourceModel.source_id)
        .all()
    )

    segments = (
        session.query(SegmentModel)
        .filter(SegmentModel.project_id == project_id)
        .order_by(SegmentModel.segment_id)
        .all()
    )

    source_atoms = (
        session.query(SourceAtomModel)
        .filter(SourceAtomModel.project_id == project_id)
        .order_by(SourceAtomModel.atom_id)
        .all()
    )

    signals = (
        session.query(SignalModel)
        .filter(SignalModel.project_id == project_id)
        .order_by(SignalModel.signal_id)
        .all()
    )

    concerns = (
        session.query(ConcernModel)
        .filter(ConcernModel.project_id == project_id)
        .order_by(ConcernModel.concern_id)
        .all()
    )

    analysis_passes = (
        session.query(AnalysisPassModel)
        .filter(AnalysisPassModel.project_id == project_id)
        .order_by(AnalysisPassModel.pass_id)
        .all()
    )

    # Stakeholders scoped to this project via analysis_passes or concerns.
    # Collect all stakeholder_ids referenced, then load them (avoids a full
    # stakeholder table scan which is shared across all projects).
    stakeholder_ids: set[str] = set()
    for ap in analysis_passes:
        stakeholder_ids.add(ap.practitioner_id)
    for cn in concerns:
        stakeholder_ids.add(cn.practitioner_id)
    # Always include the reserved SH001 tool stakeholder.
    stakeholder_ids.add("SH001")

    stakeholders: list[StakeholderModel] = []
    if stakeholder_ids:
        stakeholders = (
            session.query(StakeholderModel)
            .filter(StakeholderModel.stakeholder_id.in_(stakeholder_ids))
            .order_by(StakeholderModel.stakeholder_id)
            .all()
        )

    domains = (
        session.query(DomainModel)
        .filter(DomainModel.project_id == project_id)
        .order_by(DomainModel.domain_id)
        .all()
    )

    requirements = (
        session.query(RequirementModel)
        .filter(RequirementModel.project_id == project_id)
        .order_by(RequirementModel.requirement_id)
        .all()
    )

    ccis = (
        session.query(CellContentItemModel)
        .filter(CellContentItemModel.project_id == project_id)
        .order_by(CellContentItemModel.ci_id)
        .all()
    )

    zachman_cells = (
        session.query(ZachmanCellModel)
        .filter(ZachmanCellModel.project_id == project_id)
        .order_by(ZachmanCellModel.cell_id)
        .all()
    )

    # DataDictionaryEntry rows have no project_id (the DD is project-wide).
    # Export all non-retired entries ordered by dd_id for stable output.
    dd_rows = session.execute(
        text(
            "SELECT dd_id, entry_kind, name, description, attributes, "
            "surface_term, resolves_to, from_ref, to_ref, cardinality, "
            "provenance_ref, confidence "
            "FROM data_dictionary_entry "
            "WHERE retired_at IS NULL "
            "ORDER BY dd_id"
        )
    ).mappings().all()
    data_dictionary_entries = [dict(r) for r in dd_rows]

    return ProjectData(
        project=project,
        sources=sources,
        segments=segments,
        source_atoms=source_atoms,
        signals=signals,
        concerns=concerns,
        analysis_passes=analysis_passes,
        stakeholders=stakeholders,
        domains=domains,
        requirements=requirements,
        zachman_cells=zachman_cells,
        ccis=ccis,
        data_dictionary_entries=data_dictionary_entries,
    )
