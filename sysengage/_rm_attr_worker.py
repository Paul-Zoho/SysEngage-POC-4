"""
_rm_attr_worker.py — Attribution branch worker (Task #37 Step B).

Called by run_pmt_attr_r2.py via subprocess with NEON_DATABASE_URL set to a test branch.
Not intended to be run directly.

Modes
-----
rerun       Reset PMT_E2E_R11 Row 2 matching state and re-run match_row.
            Used for the R11 baseline (R11's Row 2 vs R11's Row 1).

substitute  Delete target project's Row 2 requirements, insert R11's active Row 2
            requirements under the target project_id, then run match_row.
            Used for R12 and R13 baselines (R11's Row 2 vs R12/R13 Row 1).

Usage
-----
    python -u sysengage/_rm_attr_worker.py \\
        --mode rerun|substitute \\
        --target-project PMT_E2E_R11|PMT_E2E_R12|PMT_E2E_R13 \\
        --source-reqs-json /tmp/r11_row2_reqs.json \\
        --out-file /tmp/attr_R11.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SYSENGAGE_DIR = Path(__file__).parent
sys.path.insert(0, str(SYSENGAGE_DIR))

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from core.db import get_session
from core.output_naming import generate_filename
from mechanisms.ledger_export import run_ledger_export
from mechanisms.requirement_matching.service import match_row
from sqlalchemy import text

ROW     = 2
OUT_DIR = SYSENGAGE_DIR.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SEP     = "=" * 65


def _apply_migrations() -> None:
    cfg = AlembicConfig(str(SYSENGAGE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(SYSENGAGE_DIR / "alembic"))
    alembic_command.upgrade(cfg, "head")
    print("[attr-worker]   Schema up to date.", flush=True)


def _reset_matching_state(project_id: str) -> None:
    """
    Clear Row 2 matching state for project_id:
      - refines_refs → [] on all Row 2 requirements
      - requirement_matching_log rows for project_id
      - requirement_gap_record rows whose requirement_id belongs to project_id Row 2
    """
    s = get_session()
    try:
        s.execute(
            text(
                "UPDATE requirement SET refines_refs = '[]'::jsonb "
                "WHERE project_id = :pid AND row_target = '2'"
            ),
            {"pid": project_id},
        )
        s.execute(
            text("DELETE FROM requirement_matching_log WHERE project_id = :pid"),
            {"pid": project_id},
        )
        s.execute(
            text(
                "DELETE FROM requirement_gap_record "
                "WHERE requirement_id IN ("
                "  SELECT requirement_id FROM requirement "
                "  WHERE project_id = :pid AND row_target = '2'"
                ")"
            ),
            {"pid": project_id},
        )
        s.commit()
        print(f"[attr-worker]   Reset matching state for {project_id}.", flush=True)
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def _substitute_row2_reqs(
    target_project_id: str, source_reqs: list[dict]
) -> dict[str, str]:
    """
    Replace target project's Row 2 requirements with R11's Row 2 requirements.

    To avoid primary-key conflicts (R11's Row 2 IDs can overlap with the target
    project's Row 1 IDs), source IDs are remapped to the next available IDs in
    the global requirement table (irrespective of project).  E.g. if the highest
    existing ID across all projects is R042, the substituted reqs become R043,
    R044, …  Gaps within a project are intentional and inconsequential.

    Returns id_map: {db_id: original_r11_id} so callers can normalize results
    back to R11 IDs for cross-baseline comparison.
    """
    sorted_source = sorted(source_reqs, key=lambda r: r["requirement_id"])

    s = get_session()
    try:
        # Collect existing Row 2 requirement IDs before deleting (so gap cleanup can use them)
        existing_row2_ids: list[str] = [
            row[0]
            for row in s.execute(
                text(
                    "SELECT requirement_id FROM requirement "
                    "WHERE project_id = :pid AND row_target = '2'"
                ),
                {"pid": target_project_id},
            ).fetchall()
        ]

        # Delete gap records: rows with project_id match OR rows with matching requirement_id
        # (handles pre-fix rows that have project_id = NULL in the 3e snapshot)
        if existing_row2_ids:
            placeholders = ", ".join(f":rid{i}" for i in range(len(existing_row2_ids)))
            rid_params = {f"rid{i}": v for i, v in enumerate(existing_row2_ids)}
            s.execute(
                text(
                    f"DELETE FROM requirement_gap_record "
                    f"WHERE project_id = :pid OR requirement_id IN ({placeholders})"
                ),
                {"pid": target_project_id, **rid_params},
            )
        else:
            s.execute(
                text("DELETE FROM requirement_gap_record WHERE project_id = :pid"),
                {"pid": target_project_id},
            )

        # Delete matching log + Row 2 requirements
        s.execute(
            text("DELETE FROM requirement_matching_log WHERE project_id = :pid"),
            {"pid": target_project_id},
        )
        s.execute(
            text(
                "DELETE FROM requirement "
                "WHERE project_id = :pid AND row_target = '2'"
            ),
            {"pid": target_project_id},
        )
        s.flush()

        # Find the next available ID globally across the whole requirement table.
        # Using global max means IDs are unique table-wide; gaps within a project are fine.
        row = s.execute(
            text(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(requirement_id FROM 2) AS INTEGER)), 0) "
                "FROM requirement "
                "WHERE requirement_id ~ '^R[0-9]+$'"
            )
        ).fetchone()
        next_num = (row[0] if row else 0) + 1

        # Build id_map now that we know the safe starting number
        id_map: dict[str, str] = {}  # db_id → original_r11_id
        for i, req in enumerate(sorted_source):
            new_id = f"R{next_num + i:03d}"
            id_map[new_id] = req["requirement_id"]

        # Insert R11's active Row 2 requirements under target project_id using remapped IDs
        inserted = 0
        reverse_map = {v: k for k, v in id_map.items()}  # original_r11_id → db_id
        for req in sorted_source:
            db_id = reverse_map[req["requirement_id"]]
            s.execute(
                text(
                    "INSERT INTO requirement ("
                    "  requirement_id, project_id, statement, requirement_type, row_target,"
                    "  cci_refs, domain_refs, answer_refs, refines_refs, confidence,"
                    "  rationale, verification_method, priority, fit_criteria, created_at"
                    ") VALUES ("
                    "  :rid, :pid, :stmt, :rtype, '2',"
                    "  CAST(:cci AS jsonb), CAST(:dom AS jsonb), '[]'::jsonb, '[]'::jsonb, :conf,"
                    "  :rationale, :vm, :priority, :fit, :now"
                    ")"
                ),
                {
                    "rid":        db_id,
                    "pid":        target_project_id,
                    "stmt":       req["statement"],
                    "rtype":      req["requirement_type"],
                    "cci":        json.dumps(req.get("cci_refs") or []),
                    "dom":        json.dumps(req.get("domain_refs") or []),
                    "conf":       float(req.get("confidence", 0.9)),
                    "rationale":  req.get("rationale"),
                    "vm":         req.get("verification_method"),
                    "priority":   req.get("priority"),
                    "fit":        req.get("fit_criteria"),
                    "now":        datetime.now(timezone.utc),
                },
            )
            inserted += 1

        s.commit()
        last_id = f"R{next_num + inserted - 1:03d}"
        print(
            f"[attr-worker]   Substituted {inserted} R11 Row 2 requirements into "
            f"{target_project_id} (IDs R{next_num:03d}–{last_id}).",
            flush=True,
        )
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()

    return id_map


def _read_refines_refs(project_id: str) -> dict[str, list[str]]:
    """Read committed refines_refs per active Row 2 requirement."""
    s = get_session()
    try:
        rows = s.execute(
            text(
                "SELECT requirement_id, refines_refs "
                "FROM requirement "
                "WHERE project_id = :pid AND row_target = '2' AND retired_at IS NULL "
                "ORDER BY requirement_id"
            ),
            {"pid": project_id},
        ).fetchall()
        return {row[0]: sorted(row[1] or []) for row in rows}
    finally:
        s.close()


def _run_matching_and_capture(project_id: str) -> dict[str, Any]:
    """Run match_row and return results + per-req refines_refs."""
    print(SEP, flush=True)
    print(f"[attr-worker] match_row({ROW}, {project_id!r})", flush=True)
    print(SEP, flush=True)
    try:
        result = match_row(ROW, project_id)
    except Exception as exc:
        print(f"[attr-worker] FAILED: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)

    print(
        f"[attr-worker]   total={result['total']}  refine={result['refine_count']}"
        f"  no_match={result['no_match_count']}  flagged={result['flagged_count']}",
        flush=True,
    )
    for r in result.get("results", []):
        rid   = r.get("requirement_id", "?")
        out   = r.get("outcome", "?")
        pids  = r.get("matched_parent_ids", [])
        conf  = r.get("confidence")
        c_str = f" conf={conf:.2f}" if conf is not None else ""
        p_str = f" → {pids}" if pids else ""
        print(f"[attr-worker]     {rid}  {out}{c_str}{p_str}", flush=True)

    refines = _read_refines_refs(project_id)
    return {
        "match_result": result,
        "refines_refs": refines,
    }


def _export_ledger(project_id: str) -> str:
    """Export ledger JSON; return the filename."""
    basename = generate_filename(
        project_id="PMT",
        phase=3,
        pass_="3e",
        row=ROW,
        out_dir=str(OUT_DIR),
    )
    s = get_session()
    try:
        export = run_ledger_export(project_id=project_id, session=s)
    finally:
        s.close()

    path = OUT_DIR / basename
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(export.json_str)
    print(f"[attr-worker]   Ledger exported: {basename}", flush=True)
    return basename


def main() -> None:
    parser = argparse.ArgumentParser(description="Attribution branch worker")
    parser.add_argument("--mode", required=True, choices=["rerun", "substitute"])
    parser.add_argument("--target-project", required=True)
    parser.add_argument("--source-reqs-json", required=True)
    parser.add_argument("--out-file", required=True)
    args = parser.parse_args()

    target_project  = args.target_project
    mode            = args.mode
    source_reqs_json = Path(args.source_reqs_json)
    out_file        = Path(args.out_file)

    print(SEP, flush=True)
    print(f"[attr-worker] mode={mode}  target={target_project}", flush=True)
    print(SEP, flush=True)

    _apply_migrations()

    with open(source_reqs_json) as f:
        source_reqs: list[dict] = json.load(f)

    id_map: dict[str, str] = {}  # db_id → original_r11_id (empty for rerun mode)

    if mode == "rerun":
        # R11 baseline: reset and re-run matching on R11's own data
        _reset_matching_state(target_project)
    else:
        # substitute: delete target's Row 2 reqs, copy R11's in with remapped IDs, run matching
        id_map = _substitute_row2_reqs(target_project, source_reqs)

    capture = _run_matching_and_capture(target_project)
    ledger_basename = _export_ledger(target_project)

    # Build refines_refs_by_source_id: keyed by original R11 requirement IDs.
    # For rerun mode id_map is empty → DB IDs ARE the original R11 IDs.
    # For substitute mode id_map maps db_id → original_r11_id.
    raw_refines = capture["refines_refs"]  # {db_id: [parent_ids]}
    if id_map:
        refines_by_source = {
            id_map[db_id]: parents
            for db_id, parents in raw_refines.items()
            if db_id in id_map
        }
    else:
        refines_by_source = dict(raw_refines)

    # per_requirement_by_source_id: normalized to original R11 IDs
    raw_per_req = capture["match_result"].get("results", [])
    if id_map:
        per_req_normalized = [
            {
                "requirement_id":     id_map.get(r.get("requirement_id", ""),
                                                  r.get("requirement_id")),
                "db_requirement_id":  r.get("requirement_id"),
                "outcome":            r.get("outcome"),
                "matched_parent_ids": r.get("matched_parent_ids", []),
                "confidence":         r.get("confidence"),
            }
            for r in raw_per_req
        ]
    else:
        per_req_normalized = [
            {
                "requirement_id":    r.get("requirement_id"),
                "outcome":           r.get("outcome"),
                "matched_parent_ids": r.get("matched_parent_ids", []),
                "confidence":        r.get("confidence"),
            }
            for r in raw_per_req
        ]

    result: dict[str, Any] = {
        "target_project": target_project,
        "row1_baseline": target_project,
        "mode": mode,
        "row": ROW,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "ledger_basename": ledger_basename,
        "match_summary": {
            "total":          capture["match_result"]["total"],
            "refine":         capture["match_result"]["refine_count"],
            "no_match":       capture["match_result"]["no_match_count"],
            "flagged":        capture["match_result"]["flagged_count"],
            "duplicate":      capture["match_result"]["duplicate_count"],
            "downward_gaps":  capture["match_result"]["downward_gap_count"],
        },
        "per_requirement": per_req_normalized,
        "refines_refs": raw_refines,
        "refines_refs_by_source_id": refines_by_source,
        "id_map": id_map,
    }

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=2)
    print(f"[attr-worker]   Results written: {out_file}", flush=True)


if __name__ == "__main__":
    main()
