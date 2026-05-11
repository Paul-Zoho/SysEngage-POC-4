"""
End-to-end mechanism tests for Source Capture.

Per Implementation Spec v0.4 §8.5, §9, and §10.

Tests:
  - Happy path end-to-end: AnalysisPass created, entities persisted
  - Canonical field assertions on AnalysisPass (F25/F27 resolution):
    pass_type, mechanism, evaluated_scope, confidence
  - Atomicity: on failure, no partial entity persistence
  - Determinism: re-run produces identical entity content
  - Phase 10 re-execution: same input skipped; new input appended
  - Edge cases: empty input, corrupt pdf, unsupported format
  - Large single sentence: exactly 1 Source, no error
  - AnalysisPass.outputs.read_witness populated correctly
  - AnalysisPass.outputs.mechanism_data populated correctly

Entity counts per v0.4 §9.1.x:
  §9.1.1 simple_paragraph.txt: 4 Sources, 0 Segments, 0 SourceAtoms
  §9.1.2 multi_section.md: 4 Sources, 2 Segments, 0 SourceAtoms
  §9.2.4 very_long_sentence: 1 Source, 0 Segments, 0 SourceAtoms
"""

from pathlib import Path

import pytest
from sqlalchemy import select

from core.db import get_session
from mechanisms.source_capture import run_source_capture, SourceCaptureResult
from models.analysis_pass import AnalysisPassModel
from models.source import SourceModel
from models.segment import SegmentModel
from models.source_atom import SourceAtomModel


def _query_sources(project_id: str) -> list[SourceModel]:
    session = get_session()
    try:
        return (
            session.execute(
                select(SourceModel).where(SourceModel.project_id == project_id)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()


def _query_segments(project_id: str) -> list[SegmentModel]:
    session = get_session()
    try:
        return (
            session.execute(
                select(SegmentModel).where(SegmentModel.project_id == project_id)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()


def _query_atoms(project_id: str) -> list[SourceAtomModel]:
    session = get_session()
    try:
        return (
            session.execute(
                select(SourceAtomModel).where(SourceAtomModel.project_id == project_id)
            )
            .scalars()
            .all()
        )
    finally:
        session.close()


def _query_pass(pass_id: str) -> AnalysisPassModel | None:
    session = get_session()
    try:
        return session.execute(
            select(AnalysisPassModel).where(AnalysisPassModel.pass_id == pass_id)
        ).scalar_one_or_none()
    finally:
        session.close()


class TestEndToEndHappyPath:
    def test_simple_paragraph_end_to_end(
        self,
        simple_paragraph_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        Full mechanism run for simple_paragraph.txt.
        Expected per §9.1.1 (v0.4): 4 Sources, 0 Segments, 0 SourceAtoms, Success.
        Sentence-level Source Capture (Pass 0A); Pass 0C no-op in v1.
        """
        result = run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        assert result.execution_status == "Success"
        assert result.pass_id.startswith("P")
        assert result.source_count == 4
        assert result.segment_count == 0
        assert result.source_atom_count == 0

    def test_simple_paragraph_entities_persisted(
        self,
        simple_paragraph_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """4 Sources persisted, 0 atoms. source_count matches DB query."""
        result = run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        sources = _query_sources(project_id)
        atoms = _query_atoms(project_id)

        assert len(sources) == 4
        assert len(atoms) == 0
        assert result.source_count == len(sources)

    def test_analysis_pass_record_created(
        self,
        simple_paragraph_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        AnalysisPass persisted with all canonical v2.11 attributes (F25/F27 resolution).
        Asserts: pass_type, mechanism, evaluated_scope, confidence, mode_active, phase_id.
        """
        result = run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        ap = _query_pass(result.pass_id)
        assert ap is not None
        assert ap.execution_status == "Success"
        assert ap.mode_active == "LPM"
        assert ap.phase_id == "PH001"
        assert ap.pass_type == "Universal"
        assert ap.mechanism == "SourceCapture"
        assert ap.evaluated_scope == "All input material in this project"
        assert ap.confidence == 1.0

    def test_read_witness_on_analysis_pass(
        self,
        simple_paragraph_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """Read Witness stored on AnalysisPass.outputs.read_witness per F10."""
        result = run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        ap = _query_pass(result.pass_id)
        assert ap is not None

        rw = ap.outputs.get("read_witness", {})
        assert "input_hash" in rw
        assert "byte_count" in rw
        assert rw["byte_count"] > 0
        assert rw["read_completion_status"] is True
        assert rw["read_mode"] == "Full"

    def test_mechanism_data_on_analysis_pass(
        self,
        simple_paragraph_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        mechanism_data sub-structure populated per §7.4.
        v0.4: source_count==4, segment_count==0, source_atom_count==0.
        """
        result = run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        ap = _query_pass(result.pass_id)
        md = ap.outputs.get("mechanism_data", {})

        assert md["source_count"] == 4
        assert md["segment_count"] == 0
        assert md["source_atom_count"] == 0
        assert len(md["source_ids"]) == 4

    def test_multi_section_end_to_end(
        self,
        multi_section_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        Full mechanism run for multi_section.md.
        Expected per §9.1.2 (v0.4): 4 Sources, 2 Segments, 0 SourceAtoms.
        Section One: 3 sentences → 3 Sources. Section Two: 1 sentence → 1 Source.
        """
        result = run_source_capture(
            multi_section_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        assert result.execution_status == "Success"
        assert result.source_count == 4
        assert result.segment_count == 2
        assert result.source_atom_count == 0

        segments = _query_segments(project_id)
        assert len(segments) == 2

    def test_multi_section_segments_have_source_refs(
        self,
        multi_section_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        Segments produced by multi_section.md must have non-empty source_refs
        (canonical v2.11 Segment → Source relation via ARRAY).
        """
        run_source_capture(
            multi_section_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        segments = _query_segments(project_id)
        for seg in segments:
            assert seg.source_refs is not None
            assert len(seg.source_refs) > 0, (
                f"Segment '{seg.title}' has empty source_refs (violates v2.11)"
            )

    def test_sources_have_no_segment_id(
        self,
        multi_section_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        Sources must NOT have a segment_id column (F24 fix).
        Verified by confirming the model has no segment_id attribute.
        """
        from models.source import SourceModel

        assert not hasattr(SourceModel, "segment_id"), (
            "SourceModel must not have segment_id column (F24 fix)"
        )

    def test_source_ids_match_canonical_format(
        self,
        simple_paragraph_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """Source IDs must match ^S\\d{3,}$ per canonical ledger spec v2.11."""
        import re

        result = run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        pattern = re.compile(r"^S\d{3,}$")
        for src_id in result.source_ids:
            assert pattern.match(src_id), f"Invalid source_id format: {src_id}"

    def test_pass_id_matches_canonical_format(
        self,
        simple_paragraph_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """pass_id must match ^P\\d{3,}$ per canonical ledger spec v2.11."""
        import re

        result = run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        pattern = re.compile(r"^P\d{3,}$")
        assert pattern.match(result.pass_id)

    def test_docx_fixture_end_to_end(
        self,
        simple_requirements_docx: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """Per §9.1.3: docx fixture produces expected entity structure."""
        result = run_source_capture(
            simple_requirements_docx,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        assert result.execution_status == "Success"
        assert result.segment_count >= 2
        assert result.source_count >= 5


class TestEdgeCases:
    def test_empty_input_fails_with_audit_trail(
        self,
        empty_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        Empty input: mechanism aborts; AnalysisPass failure record committed.
        No Sources/Segments/SourceAtoms persisted per §9.2.1.
        """
        result = run_source_capture(
            empty_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        assert result.execution_status == "Failed"
        assert result.source_count == 0
        assert result.segment_count == 0
        assert result.source_atom_count == 0

        ap = _query_pass(result.pass_id)
        assert ap is not None
        assert ap.execution_status == "Failed"
        assert "empty" in (ap.outputs.get("failure_reason") or "").lower()

        sources = _query_sources(project_id)
        assert len(sources) == 0

    def test_single_short_statement_zero_atoms(
        self,
        single_short_statement_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """Per §9.2.2: 1 Source, 0 Segments, 0 SourceAtoms for 'Hello'."""
        result = run_source_capture(
            single_short_statement_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        assert result.execution_status == "Success"
        assert result.source_count == 1
        assert result.segment_count == 0
        assert result.source_atom_count == 0

    def test_corrupt_pdf_partial_success(
        self,
        corrupt_pdf: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        Corrupt PDF: read_completion_status=False; PartialSuccess or Success
        with decoding issue flags. Per §9.2.5.
        """
        result = run_source_capture(
            corrupt_pdf,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        assert result.execution_status in ("PartialSuccess", "Success", "Failed")

        if result.execution_status != "Failed":
            ap = _query_pass(result.pass_id)
            rw = ap.outputs.get("read_witness", {})
            assert rw.get("read_completion_status") is False

    def test_unsupported_format_fails(
        self,
        unsupported_format_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """Per §9.2.6: UnsupportedFormatError → mechanism aborts; AnalysisPass.Failed."""
        result = run_source_capture(
            unsupported_format_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        assert result.execution_status == "Failed"
        assert result.source_count == 0

    def test_very_long_sentence_one_source(
        self,
        very_long_sentence: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        Per §9.2.4: >100KB SINGLE sentence → exactly 1 Source, no error.
        No internal sentence-ending punctuation → 1 Source from Pass 0A.
        Must complete within 10 seconds.
        """
        import time

        start = time.monotonic()
        result = run_source_capture(
            very_long_sentence,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )
        elapsed = time.monotonic() - start

        assert result.execution_status == "Success"
        assert result.source_count == 1
        assert elapsed < 10.0, f"Mechanism took {elapsed:.1f}s — exceeds 10s limit"


class TestAtomicity:
    def test_failed_execution_leaves_no_sources(
        self,
        empty_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        Atomicity: on failure (empty input), transaction rolls back.
        No partial entity persistence per Row 4 Applied §5.
        """
        run_source_capture(
            empty_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )

        sources = _query_sources(project_id)
        segments = _query_segments(project_id)
        atoms = _query_atoms(project_id)

        assert len(sources) == 0
        assert len(segments) == 0
        assert len(atoms) == 0


class TestDeterminism:
    """
    Determinism fixtures: re-running mechanism produces identical entity content.
    Per Implementation Spec v0.4 §9.3.
    Identifiers may differ (sequence-allocated); content must be bit-identical.
    """

    def test_source_content_identical_across_runs(
        self,
        simple_paragraph_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        import uuid

        project_id_2 = f"TEST_PROJ_{uuid.uuid4().hex[:8].upper()}"

        result1 = run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )
        result2 = run_source_capture(
            simple_paragraph_path,
            project_id=project_id_2,
            practitioner_id=practitioner_id,
        )

        assert result1.source_count == result2.source_count
        assert result1.segment_count == result2.segment_count
        assert result1.source_atom_count == result2.source_atom_count

        srcs1 = sorted(_query_sources(project_id), key=lambda s: s.source_id)
        srcs2 = sorted(_query_sources(project_id_2), key=lambda s: s.source_id)

        for s1, s2 in zip(srcs1, srcs2):
            assert s1.source_text == s2.source_text, (
                "Source content differs across runs (determinism violation)"
            )

        session = get_session()
        try:
            from sqlalchemy import delete
            from models.analysis_pass import AnalysisPassModel
            from models.source_atom import SourceAtomModel
            from models.source import SourceModel
            from models.segment import SegmentModel
            from models.project import ProjectModel

            session.execute(delete(AnalysisPassModel).where(AnalysisPassModel.project_id == project_id_2))
            session.execute(delete(SourceAtomModel).where(SourceAtomModel.project_id == project_id_2))
            session.execute(delete(SourceModel).where(SourceModel.project_id == project_id_2))
            session.execute(delete(SegmentModel).where(SegmentModel.project_id == project_id_2))
            session.execute(delete(ProjectModel).where(ProjectModel.project_id == project_id_2))
            session.commit()
        finally:
            session.close()

    def test_read_witness_identical_across_runs(
        self,
        simple_paragraph_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        import uuid

        project_id_2 = f"TEST_PROJ_{uuid.uuid4().hex[:8].upper()}"

        result1 = run_source_capture(
            simple_paragraph_path, project_id=project_id, practitioner_id=practitioner_id
        )
        result2 = run_source_capture(
            simple_paragraph_path, project_id=project_id_2, practitioner_id=practitioner_id
        )

        ap1 = _query_pass(result1.pass_id)
        ap2 = _query_pass(result2.pass_id)

        rw1 = ap1.outputs.get("read_witness", {})
        rw2 = ap2.outputs.get("read_witness", {})

        assert rw1["input_hash"] == rw2["input_hash"]
        assert rw1["byte_count"] == rw2["byte_count"]
        assert rw1["character_count"] == rw2["character_count"]

        session = get_session()
        try:
            from sqlalchemy import delete
            from models.analysis_pass import AnalysisPassModel
            from models.source_atom import SourceAtomModel
            from models.source import SourceModel
            from models.segment import SegmentModel
            from models.project import ProjectModel

            session.execute(delete(AnalysisPassModel).where(AnalysisPassModel.project_id == project_id_2))
            session.execute(delete(SourceAtomModel).where(SourceAtomModel.project_id == project_id_2))
            session.execute(delete(SourceModel).where(SourceModel.project_id == project_id_2))
            session.execute(delete(SegmentModel).where(SegmentModel.project_id == project_id_2))
            session.execute(delete(ProjectModel).where(ProjectModel.project_id == project_id_2))
            session.commit()
        finally:
            session.close()


class TestPhase10ReExecution:
    """
    Phase 10 re-execution fixtures per Implementation Spec v0.4 §9.4.
    Re-execution with same input: skipped (existing hash detected).
    Re-execution with new input: entities appended.
    """

    def test_reexecution_new_input_appends_entities(
        self,
        simple_paragraph_path: Path,
        multi_section_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        Run with simple_paragraph.txt (4 Sources), then multi_section.md (4 Sources).
        Total after second run: 8 Sources.
        Per Implementation Spec §9.4.1.
        """
        run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )
        sources_after_first = _query_sources(project_id)
        count_after_first = len(sources_after_first)

        run_source_capture(
            multi_section_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
            re_execution_context={},
        )

        sources_after_second = _query_sources(project_id)
        count_after_second = len(sources_after_second)

        assert count_after_second > count_after_first, (
            "Re-execution with new input should add new Sources"
        )

        assert all(
            s.source_id in {s2.source_id for s2 in sources_after_second}
            for s in sources_after_first
        ), "Original Sources must still be present after re-execution"

    def test_reexecution_same_input_skipped(
        self,
        simple_paragraph_path: Path,
        project_id: str,
        practitioner_id: str,
    ):
        """
        Re-execution with the same input (same hash) should be skipped.
        Per Implementation Spec v0.4 §10.4.
        """
        run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )
        sources_after_first = _query_sources(project_id)

        result2 = run_source_capture(
            simple_paragraph_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
            re_execution_context={},
        )

        sources_after_second = _query_sources(project_id)

        assert len(sources_after_second) == len(sources_after_first), (
            "Re-execution with same input should not add new Sources"
        )
        assert result2.execution_status == "Failed"
        assert result2.failure_reason == "already_captured"
