"""
run_capture.py — Source Capture CLI verification utility.

TRANSITIONAL INFRASTRUCTURE: disposable single-file harness.
Not a mechanism. Not registered under mechanisms/. Purpose: allow a Practitioner
to submit real input material to the Source Capture mechanism and inspect the
resulting canonical ledger JSON without requiring pytest.

Invocation (from workspace root where sysengage/ is a package):
    python -m sysengage.tools.run_capture <input_file_path> <output_ledger_path>

Or from within sysengage/ with PYTHONPATH set to the workspace root:
    PYTHONPATH=.. python -m sysengage.tools.run_capture <input_file_path> <output_ledger_path>

Exit codes:
    0 — success
    1 — failure (error printed to stderr)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _ensure_sysengage_on_path() -> None:
    """
    Add the sysengage/ package directory to sys.path so that internal imports
    (mechanisms, core, models, schemas) resolve regardless of the working directory.
    Safe to call multiple times; only inserts if not already present.
    """
    sysengage_dir = str(Path(__file__).parent.parent.resolve())
    if sysengage_dir not in sys.path:
        sys.path.insert(0, sysengage_dir)


def export_ledger(
    pass_id: str,
    source_ids: list[str],
    segment_ids: list[str],
    atom_ids: list[str],
) -> dict:
    """
    Query the database for all entities produced by this Source Capture execution
    and assemble them into a canonical ledger JSON dict per spec v2.11.

    TRANSITIONAL UTILITY: this function is intentionally self-contained so it can
    be reused by tests or by a future proper Ledger Export mechanism. It is NOT
    part of the Source Capture mechanism itself. When a formal Ledger Export
    mechanism is built, this function should be superseded by that mechanism's
    export logic.

    Canonical attribute filtering (F24 resolution):
      Source payload: {source_id, source_text, segmentation_context,
                       input_material_ref, confidence, parent_source_ref}
      Segment payload: {segment_id, title, description, source_refs,
                        parent_segment_ref, confidence}
      SourceAtom payload: {atom_id, atom_text, source_ref, segment_ref,
                           parent_atom_ref, confidence, position}
      AnalysisPass payload: {pass_id, pass_type, mechanism, execution_status,
                              mode_active, declared_transformation_modes, outputs,
                              evaluated_scope, pass_started_at, pass_completed_at,
                              elapsed_ms, confidence}

    Non-canonical attributes stripped at export (F24):
      phase_id, practitioner_id, project_id, created_at, is_non_text,
      has_decoding_issues.

    Scoping strategy:
    - AnalysisPass: fetched by pass_id (exact).
    - project_id: sourced from the AnalysisPass row — used as additional scope
      guard for all entity queries.
    - Sources: fetched by source_ids filtered to ap_row.project_id.
    - Segments: fetched by segment_ids filtered to ap_row.project_id.
    - SourceAtoms: fetched by atom_ids filtered to ap_row.project_id.

    Args:
        pass_id:     The AnalysisPass identifier from this execution.
        source_ids:  List of Source identifiers produced by this execution.
        segment_ids: List of Segment identifiers produced by this execution.
        atom_ids:    List of SourceAtom identifiers produced by this execution.

    Returns:
        Canonical ledger dict conforming to sysengage_ledger_version 2.11.
    """
    _ensure_sysengage_on_path()

    from sqlalchemy import select
    from core.db import get_session
    from models.analysis_pass import AnalysisPassModel
    from models.source import SourceModel
    from models.segment import SegmentModel
    from models.source_atom import SourceAtomModel

    session = get_session()
    elements: list[dict] = []

    try:
        ap_row = session.execute(
            select(AnalysisPassModel).where(AnalysisPassModel.pass_id == pass_id)
        ).scalar_one_or_none()

        if ap_row is None:
            raise RuntimeError(f"AnalysisPass {pass_id} not found in database.")

        project_id: str = ap_row.project_id

        if source_ids:
            src_rows = (
                session.execute(
                    select(SourceModel).where(
                        SourceModel.source_id.in_(source_ids),
                        SourceModel.project_id == project_id,
                    )
                )
                .scalars()
                .all()
            )
        else:
            src_rows = []

        if segment_ids:
            seg_rows = (
                session.execute(
                    select(SegmentModel).where(
                        SegmentModel.segment_id.in_(segment_ids),
                        SegmentModel.project_id == project_id,
                    )
                )
                .scalars()
                .all()
            )
        else:
            seg_rows = []

        if atom_ids:
            atom_rows_db = (
                session.execute(
                    select(SourceAtomModel).where(
                        SourceAtomModel.atom_id.in_(atom_ids),
                        SourceAtomModel.project_id == project_id,
                    )
                )
                .scalars()
                .all()
            )
        else:
            atom_rows_db = []

        for src in src_rows:
            elements.append(
                {
                    "element_id": src.source_id,
                    "element_type": "Source",
                    "payload": {
                        "source_id": src.source_id,
                        "source_text": src.source_text,
                        "segmentation_context": src.segmentation_context,
                        "input_material_ref": src.input_material_ref,
                        "confidence": src.confidence,
                        "parent_source_ref": src.parent_source_ref,
                    },
                }
            )

        for seg in seg_rows:
            elements.append(
                {
                    "element_id": seg.segment_id,
                    "element_type": "Segment",
                    "payload": {
                        "segment_id": seg.segment_id,
                        "title": seg.title,
                        "description": seg.description,
                        "source_refs": list(seg.source_refs or []),
                        "parent_segment_ref": seg.parent_segment_ref,
                        "confidence": seg.confidence,
                    },
                }
            )

        for atom in atom_rows_db:
            elements.append(
                {
                    "element_id": atom.atom_id,
                    "element_type": "SourceAtom",
                    "payload": {
                        "atom_id": atom.atom_id,
                        "atom_text": atom.atom_text,
                        "source_ref": atom.source_ref,
                        "segment_ref": atom.segment_ref,
                        "parent_atom_ref": atom.parent_atom_ref,
                        "confidence": atom.confidence,
                        "position": atom.position,
                    },
                }
            )

        elements.append(
            {
                "element_id": ap_row.pass_id,
                "element_type": "AnalysisPass",
                "payload": {
                    "pass_id": ap_row.pass_id,
                    "pass_type": ap_row.pass_type,
                    "mechanism": ap_row.mechanism,
                    "execution_status": ap_row.execution_status,
                    "mode_active": ap_row.mode_active,
                    "declared_transformation_modes": ap_row.declared_transformation_modes,
                    "outputs": ap_row.outputs,
                    "evaluated_scope": ap_row.evaluated_scope,
                    "pass_started_at": ap_row.pass_started_at.isoformat(),
                    "pass_completed_at": (
                        ap_row.pass_completed_at.isoformat()
                        if ap_row.pass_completed_at
                        else None
                    ),
                    "elapsed_ms": ap_row.elapsed_ms,
                    "confidence": ap_row.confidence,
                },
            }
        )

    finally:
        session.close()

    return {
        "sysengage_ledger_version": "2.11",
        "schema_id": "sysengage.ledger.instance.v2_11",
        "row_target": None,
        "run_id": pass_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "sysengage_source_capture_v0.7",
        "elements": elements,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m sysengage.tools.run_capture",
        description=(
            "Submit an input file to the Source Capture mechanism and write "
            "the resulting canonical ledger JSON to an output file."
        ),
    )
    parser.add_argument(
        "input_file",
        help="Path to the input file (.txt, .md, .docx, .pdf)",
    )
    parser.add_argument(
        "output_ledger",
        help="Path where the canonical ledger JSON will be written",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_ledger)

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if not input_path.is_file():
        print(f"Error: input path is not a file: {input_path}", file=sys.stderr)
        sys.exit(1)

    _ensure_sysengage_on_path()

    try:
        from mechanisms.source_capture import run_source_capture
    except RuntimeError as exc:
        print(f"Error: database configuration problem — {exc}", file=sys.stderr)
        sys.exit(1)

    project_id = f"CLI_{uuid4().hex[:8].upper()}"
    practitioner_id = f"CLI_{uuid4().hex[:8].upper()}"

    try:
        result = run_source_capture(
            input_path,
            project_id=project_id,
            practitioner_id=practitioner_id,
        )
    except Exception as exc:
        print(f"Error: Source Capture mechanism failed — {exc}", file=sys.stderr)
        sys.exit(1)

    if result.execution_status not in ("Success", "PartialSuccess"):
        print(
            f"Error: mechanism returned status '{result.execution_status}': "
            f"{result.failure_reason}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        ledger = export_ledger(
            pass_id=result.pass_id,
            source_ids=result.source_ids,
            segment_ids=result.segment_ids,
            atom_ids=result.atom_ids,
        )
    except Exception as exc:
        print(f"Error: ledger export failed — {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(ledger, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"Error: could not write output file — {exc}", file=sys.stderr)
        sys.exit(1)

    print("Source Capture completed.")
    print(f"  AnalysisPass ID: {result.pass_id}")
    print(f"  Sources produced: {result.source_count}")
    print(f"  Segments produced: {result.segment_count}")
    print(f"  SourceAtoms produced: {result.source_atom_count}")
    print(f"Ledger written to: {output_path}")


if __name__ == "__main__":
    main()
