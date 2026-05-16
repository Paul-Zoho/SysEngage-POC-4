"""
Tests for ledger_export/markdown_renderer.py.

Verifies Markdown projection structure, YAML front matter, element sections,
projection disclaimer, and correct handling of empty/populated element groups.
"""

from __future__ import annotations

import pytest

from mechanisms.ledger_export.json_builder import build_canonical_ledger
from mechanisms.ledger_export.markdown_renderer import render_markdown
from tests.ledger_export.conftest import (
    ProjectData,
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


def _render(data: ProjectData) -> str:
    ledger = build_canonical_ledger(data)
    return render_markdown(data, ledger)


# ── YAML front matter ─────────────────────────────────────────────────────────

class TestYAMLFrontMatter:
    def test_opens_with_yaml_fence(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert md.startswith("---\n")

    def test_contains_spec_version(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert 'sysengage_ledger_version: "2.12"' in md

    def test_contains_project_id(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert 'project_id: "PROJ001"' in md

    def test_contains_project_name(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert 'project_name: "Test Project"' in md

    def test_contains_run_id(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "run_id:" in md

    def test_contains_generator_line(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "generator:" in md

    def test_contains_content_hash(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "content_hash:" in md


# ── heading and disclaimer ────────────────────────────────────────────────────

class TestHeadingAndDisclaimer:
    def test_main_heading_contains_project_name(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "# SysEngage Canonical Ledger — Test Project" in md

    def test_projection_disclaimer_present(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "Markdown projection" in md
        assert ".ledger.json" in md

    def test_summary_table_present(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "## Summary" in md
        assert "| Element Type | Count |" in md


# ── summary table counts ─────────────────────────────────────────────────────

class TestSummaryTableCounts:
    def test_source_count_in_summary(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "| Source | 1 |" in md

    def test_zero_signals_in_summary(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "| Signal | 0 |" in md

    def test_full_data_counts(self, full_project_data):
        md = _render(full_project_data)
        assert "| Source | 2 |" in md
        assert "| Signal | 2 |" in md
        assert "| Concern | 1 |" in md
        assert "| Segment | 1 |" in md
        assert "| SourceAtom | 2 |" in md
        assert "| Domain | 1 |" in md
        assert "| Requirement | 1 |" in md


# ── element sections ──────────────────────────────────────────────────────────

class TestElementSections:
    def test_sources_section_present_when_sources_exist(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "## Sources (1)" in md

    def test_sources_section_absent_when_no_sources(self):
        data = ProjectData(
            project=make_project(),
            sources=[],
            segments=[],
            source_atoms=[],
            signals=[],
            concerns=[],
            analysis_passes=[make_analysis_pass()],
            stakeholders=[make_stakeholder()],
            domains=[],
            requirements=[],
        )
        md = _render(data)
        assert "## Sources" not in md

    def test_source_text_rendered_as_blockquote(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "> The system shall allow users to track expenses." in md

    def test_source_id_heading(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "### S001" in md

    def test_analysis_passes_section_present(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "## Analysis Passes (1)" in md

    def test_analysis_pass_heading_contains_mechanism(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "### P001 — SourceCapture" in md

    def test_analysis_pass_execution_status_shown(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "Execution Status" in md

    def test_segments_section_present_when_segments_exist(self, full_project_data):
        md = _render(full_project_data)
        assert "## Segments (1)" in md

    def test_segments_section_absent_when_no_segments(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "## Segments" not in md

    def test_segment_heading_has_title(self, full_project_data):
        md = _render(full_project_data)
        assert "### SEG001 — Requirements Section" in md

    def test_source_atoms_section_present_when_atoms_exist(self, full_project_data):
        md = _render(full_project_data)
        assert "## Source Atoms (2)" in md

    def test_signals_section_present_when_signals_exist(self, full_project_data):
        md = _render(full_project_data)
        assert "## Signals (2)" in md

    def test_signals_grouped_by_row(self, full_project_data):
        md = _render(full_project_data)
        assert "### Row 1 Signals (2)" in md

    def test_signal_type_shown_in_heading(self, full_project_data):
        md = _render(full_project_data)
        assert "SG001" in md
        assert "`Intent`" in md

    def test_signal_description_as_blockquote(self, full_project_data):
        md = _render(full_project_data)
        assert "> Users intend to track household expenses." in md

    def test_concerns_section_present_when_concerns_exist(self, full_project_data):
        md = _render(full_project_data)
        assert "## Concerns (1)" in md

    def test_concerns_grouped_by_row(self, full_project_data):
        md = _render(full_project_data)
        assert "### Row 1 Concerns (1)" in md

    def test_concern_heading_includes_state(self, full_project_data):
        md = _render(full_project_data)
        assert "CN001" in md
        assert "Open" in md

    def test_concern_description_as_blockquote(self, full_project_data):
        md = _render(full_project_data)
        assert "> Ambiguous: 'users' scope unclear." in md

    def test_stakeholders_table_present(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "## Stakeholders (1)" in md
        assert "| ID | Name | Role / Kind |" in md

    def test_sh001_shown_in_stakeholders_table(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "`SH001`" in md
        assert "SysEngage" in md
        assert "Automated" in md

    def test_domains_section_present_when_domains_exist(self, full_project_data):
        md = _render(full_project_data)
        assert "## Domains (1)" in md
        assert "### D001 — Expense Tracking" in md

    def test_domains_section_absent_when_no_domains(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "## Domains" not in md

    def test_requirements_section_present_when_requirements_exist(self, full_project_data):
        md = _render(full_project_data)
        assert "## Requirements (1)" in md

    def test_requirements_grouped_by_row(self, full_project_data):
        md = _render(full_project_data)
        assert "### Row 1 Requirements (1)" in md

    def test_requirement_statement_as_blockquote(self, full_project_data):
        md = _render(full_project_data)
        assert "> The system shall track expenses." in md


# ── registers section ─────────────────────────────────────────────────────────

class TestRegistersSection:
    def test_registers_section_always_present(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "## Registers" in md

    def test_source_register_row_in_table(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "SOURCE_REG001" in md

    def test_concern_register_row_present_when_concerns_exist(self, full_project_data):
        md = _render(full_project_data)
        assert "CONCERN_REG001" in md

    def test_segment_register_row_absent_when_no_segments(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "SEGMENT_REG001" not in md


# ── ledger provenance footer ──────────────────────────────────────────────────

class TestLedgerProvenanceFooter:
    def test_provenance_section_present(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "## Ledger Provenance" in md

    def test_content_hash_in_provenance(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "Content Hash (sha256)" in md

    def test_run_id_in_provenance(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "Run ID" in md


# ── read_witness in analysis pass ─────────────────────────────────────────────

class TestReadWitnessRendering:
    def test_read_witness_table_rendered(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "Read Witness" in md
        assert "`input_hash`" in md
        assert "`byte_count`" in md

    def test_mechanism_data_rendered(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "Mechanism Data" in md
        assert "source_count" in md

    def test_mode_violations_none_shown(self, minimal_project_data):
        md = _render(minimal_project_data)
        assert "Mode Violations" in md
        assert "_none_" in md
