"""
run_capture.py — Source Capture CLI verification utility.

TRANSITIONAL INFRASTRUCTURE: disposable single-file harness.
Not a mechanism. Not registered under mechanisms/. Purpose: allow a Practitioner
to submit real input material to the Source Capture mechanism and inspect the
resulting canonical ledger JSON without requiring pytest.

Invocation (from workspace root or sysengage/ directory):
    python -m sysengage.tools.run_capture <input_file_path> <output_ledger_path>

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


def export_ledger(
    pass_id: str,
    source_ids: list[str],
    project_id: str,
) -> dict:
    """
    Query the database for all entities produced by this Source Capture execution
    and assemble them into a canonical ledger JSON dict.

    TRANSITIONAL UTILITY: this function is intentionally self-contained so it can
    be reused by tests or by a future proper Ledger Export mechanism.  It is NOT
    part of the Source Capture mechanism itself.  When a formal Ledger Export
    mechanism is built, this function should be superseded by that mechanism's
    export logic.

    Scoping strategy:
    - AnalysisPass: fetched by pass_id (exact).
    - Sources: fetched by source_ids (returned by the orchestrator).
    - Segments: fetched by project_id filtered to those referenced by the Sources.
    - SourceAtoms: fetched by source_ref in source_ids.

    Args:
        pass_id:    The AnalysisPass identifier from this execution.
        source_ids: List of Source identifiers produced by this execution.
        project_id: The project identifier used for this execution.

    Returns:
        Canonical ledger dict conforming to sysengage_ledger_version 2.10.
    """
    import sys
    import os

    sys.path.insert(0, str(Path(__file__).parent.parent))
    os.chdir(Path(__file__).parent.parent)

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

        if source_ids:
            src_rows = (
                session.execute(
                    select(SourceModel).where(SourceModel.source_id.in_(source_ids))
                )
                .scalars()
                .all()
            )
        else:
            src_rows = []

        segment_ids = list(
            {r.segment_id for r in src_rows if r.segment_id is not None}
        )
        if segment_ids:
            seg_rows = (
                session.execute(
                    select(SegmentModel).where(
                        SegmentModel.segment_id.in_(segment_ids)
                    )
                )
                .scalars()
                .all()
            )
        else:
            seg_rows = []

        if source_ids:
            atom_rows = (
                session.execute(
                    select(SourceAtomModel).where(
                        SourceAtomModel.source_ref.in_(source_ids)
                    )
                )
                .scalars()
                .all()
            )
        else:
            atom_rows = []

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
                        "segment_id": src.segment_id,
                        "parent_source_ref": src.parent_source_ref,
                        "is_non_text": src.is_non_text,
                        "has_decoding_issues": src.has_decoding_issues,
                        "project_id": src.project_id,
                        "created_at": src.created_at.isoformat(),
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
                        "parent_segment_ref": seg.parent_segment_ref,
                        "confidence": seg.confidence,
                        "project_id": seg.project_id,
                        "created_at": seg.created_at.isoformat(),
                    },
                }
            )

        for atom in atom_rows:
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
                        "project_id": atom.project_id,
                        "created_at": atom.created_at.isoformat(),
                    },
                }
            )

        elements.append(
            {
                "element_id": ap_row.pass_id,
                "element_type": "AnalysisPass",
                "payload": {
                    "pass_id": ap_row.pass_id,
                    "phase_id": ap_row.phase_id,
                    "execution_status": ap_row.execution_status,
                    "mode_active": ap_row.mode_active,
                    "declared_transformation_modes": ap_row.declared_transformation_modes,
                    "pass_started_at": ap_row.pass_started_at.isoformat(),
                    "pass_completed_at": (
                        ap_row.pass_completed_at.isoformat()
                        if ap_row.pass_completed_at
                        else None
                    ),
                    "elapsed_ms": ap_row.elapsed_ms,
                    "practitioner_id": ap_row.practitioner_id,
                    "project_id": ap_row.project_id,
                    "outputs": ap_row.outputs,
                    "created_at": ap_row.created_at.isoformat(),
                },
            }
        )

    finally:
        session.close()

    return {
        "sysengage_ledger_version": "2.10",
        "schema_id": "sysengage.ledger.instance.v2_10",
        "row_target": None,
        "run_id": pass_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "sysengage_source_capture_v0.1",
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
    parser.add_argument("input_file", help="Path to the input file (.txt, .md, .docx, .pdf)")
    parser.add_argument("output_ledger", help="Path where the canonical ledger JSON will be written")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_ledger)

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if not input_path.is_file():
        print(f"Error: input path is not a file: {input_path}", file=sys.stderr)
        sys.exit(1)

    import os
    sysengage_dir = Path(__file__).parent.parent
    os.chdir(sysengage_dir)
    sys.path.insert(0, str(sysengage_dir))

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
            project_id=project_id,
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
