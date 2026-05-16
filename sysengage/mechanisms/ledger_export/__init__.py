"""
Ledger Export mechanism — entry point.

Reads all canonical ledger elements for a project from the DB and produces:
  1. A canonical JSON ledger dict conforming to spec v2.12
  2. A human-readable Markdown projection (per spec Appendix A — Markdown is a
     view; the JSON ledger is the authoritative canonical artefact)

Usage:
    from mechanisms.ledger_export import run_ledger_export

    result = run_ledger_export(project_id="PMT_E2E", session=session)
    # result.json_str     — canonical JSON string (write to *.ledger.json)
    # result.markdown_str — Markdown projection (write to *.ledger.md)
    # result.ledger       — raw canonical ledger dict
    # result.project_data — ProjectData from DB

Isolated from:
  - mechanisms/source_capture
  - mechanisms/row_lens_source_reanalysis
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from mechanisms.ledger_export.db_reader import ProjectData, read_project_data
from mechanisms.ledger_export.json_builder import (
    build_canonical_ledger,
    ledger_to_json_str,
)
from mechanisms.ledger_export.markdown_renderer import render_markdown


@dataclass
class LedgerExportResult:
    """Result of a ledger export run."""

    project_data: ProjectData
    ledger: dict
    json_str: str
    markdown_str: str

    @property
    def project_id(self) -> str:
        return self.project_data.project.project_id

    @property
    def project_name(self) -> str:
        return self.project_data.project.name


def run_ledger_export(
    project_id: str,
    session: Session,
) -> LedgerExportResult:
    """
    Export the canonical ledger for *project_id*.

    Reads all entities from the DB, builds the canonical JSON structure, and
    renders the Markdown projection. Does NOT write to disk — the caller
    decides where to persist the output.

    Raises:
        ValueError: if the project does not exist in the DB.
    """
    project_data = read_project_data(project_id, session)
    ledger = build_canonical_ledger(project_data)
    json_str = ledger_to_json_str(ledger)
    markdown_str = render_markdown(project_data, ledger)

    return LedgerExportResult(
        project_data=project_data,
        ledger=ledger,
        json_str=json_str,
        markdown_str=markdown_str,
    )
