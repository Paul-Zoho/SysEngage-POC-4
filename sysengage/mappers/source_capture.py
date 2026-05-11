"""
Pydantic ↔ SQLAlchemy mappers for Source Capture entities.

Per Implementation Spec v0.4 §5.3: conversion functions for all four entity types.
Handles JSONB outputs serialisation for AnalysisPass.

Changes from v0.3:
  - source_pydantic_to_sqlalchemy: removed segment_id (no longer on Source, per F24).
  - source_sqlalchemy_to_pydantic: removed segment_id.
  - segment_pydantic_to_sqlalchemy: added source_refs (ARRAY column).
  - segment_sqlalchemy_to_pydantic: reads source_refs from ARRAY column (was ORM relation).
  - analysis_pass_sqlalchemy_to_pydantic: added pass_type, mechanism,
    evaluated_scope, confidence (F25/F27 resolution).
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
        is_non_text=model.is_non_text,
        has_decoding_issues=model.has_decoding_issues,
        project_id=model.project_id,
    )


def segment_pydantic_to_sqlalchemy(segment: Segment) -> SegmentModel:
    return SegmentModel(
        segment_id=segment.segment_id,
        title=segment.title,
        description=segment.description,
        source_refs=list(segment.source_refs),
        parent_segment_ref=segment.parent_segment_ref,
        confidence=segment.confidence,
        project_id=segment.project_id,
    )


def segment_sqlalchemy_to_pydantic(model: SegmentModel) -> Segment:
    return Segment(
        segment_id=model.segment_id,
        title=model.title,
        description=model.description,
        source_refs=list(model.source_refs or []),
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
        pass_type=model.pass_type,
        mechanism=model.mechanism,
        evaluated_scope=model.evaluated_scope,
        confidence=model.confidence,
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
