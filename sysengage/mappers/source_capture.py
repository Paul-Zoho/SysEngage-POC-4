"""
Pydantic ↔ SQLAlchemy mappers for Source Capture entities.

Per Implementation Spec §5.3: conversion functions for all four entity types.
Handles JSONB outputs serialisation for AnalysisPass.
"""

from schemas.source import Source
from schemas.segment import Segment
from schemas.source_atom import SourceAtom
from schemas.analysis_pass import AnalysisPass
from models.source import SourceModel
from models.segment import SegmentModel
from models.source_atom import SourceAtomModel
from models.analysis_pass import AnalysisPassModel


def source_pydantic_to_sqlalchemy(source: Source) -> SourceModel:
    return SourceModel(
        source_id=source.source_id,
        source_text=source.source_text,
        segmentation_context=source.segmentation_context,
        parent_source_ref=source.parent_source_ref,
        input_material_ref=source.input_material_ref,
        confidence=source.confidence,
        segment_id=source.segment_id,
        is_non_text=source.is_non_text,
        has_decoding_issues=source.has_decoding_issues,
        project_id=source.project_id,
    )


def source_sqlalchemy_to_pydantic(model: SourceModel) -> Source:
    return Source(
        source_id=model.source_id,
        source_text=model.source_text,
        segmentation_context=model.segmentation_context,
        parent_source_ref=model.parent_source_ref,
        input_material_ref=model.input_material_ref,
        confidence=model.confidence,
        segment_id=model.segment_id,
        is_non_text=model.is_non_text,
        has_decoding_issues=model.has_decoding_issues,
        project_id=model.project_id,
    )


def segment_pydantic_to_sqlalchemy(segment: Segment) -> SegmentModel:
    return SegmentModel(
        segment_id=segment.segment_id,
        title=segment.title,
        description=segment.description,
        parent_segment_ref=segment.parent_segment_ref,
        confidence=segment.confidence,
        project_id=segment.project_id,
    )


def segment_sqlalchemy_to_pydantic(model: SegmentModel) -> Segment:
    source_refs = [s.source_id for s in (model.sources or [])]
    return Segment(
        segment_id=model.segment_id,
        title=model.title,
        description=model.description,
        source_refs=source_refs,
        parent_segment_ref=model.parent_segment_ref,
        confidence=model.confidence,
        project_id=model.project_id,
    )


def source_atom_pydantic_to_sqlalchemy(atom: SourceAtom) -> SourceAtomModel:
    return SourceAtomModel(
        atom_id=atom.atom_id,
        atom_text=atom.atom_text,
        source_ref=atom.source_ref,
        segment_ref=atom.segment_ref,
        parent_atom_ref=atom.parent_atom_ref,
        confidence=atom.confidence,
        position=atom.position,
        project_id=atom.project_id,
    )


def source_atom_sqlalchemy_to_pydantic(model: SourceAtomModel) -> SourceAtom:
    return SourceAtom(
        atom_id=model.atom_id,
        atom_text=model.atom_text,
        source_ref=model.source_ref,
        segment_ref=model.segment_ref,
        parent_atom_ref=model.parent_atom_ref,
        confidence=model.confidence,
        position=model.position,
        project_id=model.project_id,
    )


def analysis_pass_sqlalchemy_to_pydantic(model: AnalysisPassModel) -> AnalysisPass:
    return AnalysisPass(
        pass_id=model.pass_id,
        phase_id=model.phase_id,
        pass_started_at=model.pass_started_at,
        pass_completed_at=model.pass_completed_at,
        execution_status=model.execution_status,
        mode_active=model.mode_active,
        declared_transformation_modes=model.declared_transformation_modes or ["LPM"],
        elapsed_ms=model.elapsed_ms,
        practitioner_id=model.practitioner_id,
        project_id=model.project_id,
        outputs=model.outputs or {},
    )
