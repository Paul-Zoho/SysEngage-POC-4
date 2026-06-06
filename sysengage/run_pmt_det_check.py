"""
run_pmt_det_check.py — Matching determinism check for PMT Row 2 (Task #37 Step A).

Workflow
--------
1.  Clone snap_PMT_ph03_3e_R2_3x_YYYYMMDD → tmp_PMT_det_check.
2.  Set NEON_DATABASE_URL to test branch (before deferred imports).
3.  Apply schema migrations (idempotent).
4.  Snapshot retired_at state for all Row 2 reqs (baseline for full reset).
5.  Reset state: clear refines_refs, matching log, gaps; restore retired_at.
6.  Run match_row(2, "PMT_E2E_R11") — capture per-req refines_refs → run1.
7.  Reset state again (same baseline).
8.  Run match_row(2, "PMT_E2E_R11") — capture per-req refines_refs → run2.
9.  Compare run1 vs run2.
10. Write verification_outputs/PMT_Matching_Determinism_Check.json.
11. Delete temp branch.

State reset fully restores retired_at so both runs start from the same initial
state (same active / retired split as the snapshot). This means duplicate merges
committed by Run 1 are undone before Run 2.

Invocation (from workspace root):
    python -u sysengage/run_pmt_det_check.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SYSENGAGE_DIR = Path(__file__).parent
sys.path.insert(0, str(SYSENGAGE_DIR))
sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))

import branch_manager as bm

PROJECT_ID   = "PMT_E2E_R11"
ROW          = 2
SOURCE_SNAP  = "snap_PMT_ph03_3e_R2_3x_20260606"
BRANCH_NAME  = "tmp_PMT_det_check"
OUT_DIR      = SYSENGAGE_DIR.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE     = OUT_DIR / "PMT_Matching_Determinism_Check.json"
SEP          = "=" * 65


# ---------------------------------------------------------------------------
# Step 1 — Clone / reuse test branch
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[det] Step 1 — Clone {SOURCE_SNAP} → {BRANCH_NAME}", flush=True)
print(SEP, flush=True)

neon_project = bm._get_project_id()

source_branch = bm._find_branch_by_name(neon_project, SOURCE_SNAP)
if not source_branch:
    print(f"[det] ERROR: source snapshot '{SOURCE_SNAP}' not found.", file=sys.stderr)
    sys.exit(1)

existing = bm._find_branch_by_name(neon_project, BRANCH_NAME)
if existing:
    bm._delete_branch(neon_project, existing["id"])
    print(f"[det]   Removed stale {BRANCH_NAME}", flush=True)

test_branch_id, test_branch_url = bm._create_branch(neon_project, BRANCH_NAME, source_branch["id"])
print(f"[det]   Created {BRANCH_NAME} ({test_branch_id})", flush=True)


# ---------------------------------------------------------------------------
# Step 2 — Point active DB at test branch (BEFORE any core.db import)
# ---------------------------------------------------------------------------

os.environ["NEON_DATABASE_URL"] = test_branch_url
print("[det] Step 2 — NEON_DATABASE_URL → test branch", flush=True)


# ---------------------------------------------------------------------------
# Deferred imports — engine binds here
# ---------------------------------------------------------------------------

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from core.db import get_session
from mechanisms.requirement_matching.service import match_row
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Step 3 — Migrations (idempotent)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[det] Step 3 — Schema migrations", flush=True)
print(SEP, flush=True)

_alembic_cfg = AlembicConfig(str(SYSENGAGE_DIR / "alembic.ini"))
_alembic_cfg.set_main_option("script_location", str(SYSENGAGE_DIR / "alembic"))
alembic_command.upgrade(_alembic_cfg, "head")
print("[det]   Schema up to date.", flush=True)


# ---------------------------------------------------------------------------
# Step 4 — Snapshot initial retired_at state
#
# We capture which Row 2 requirements are already retired in the source
# snapshot. This lets the reset function restore the exact same active/retired
# split before each run — so both runs start from identical initial state,
# undoing any duplicate merges committed by a previous run.
# ---------------------------------------------------------------------------

def _snapshot_retired_state() -> dict[str, Any]:
    """
    Return {requirement_id: retired_at_isostring_or_None} for all Row 2 reqs.
    """
    s = get_session()
    try:
        rows = s.execute(
            text(
                "SELECT requirement_id, retired_at "
                "FROM requirement "
                "WHERE project_id = :pid AND row_target = '2' "
                "ORDER BY requirement_id"
            ),
            {"pid": PROJECT_ID},
        ).fetchall()
        return {
            row[0]: row[1].isoformat() if row[1] else None
            for row in rows
        }
    finally:
        s.close()


print(SEP, flush=True)
print("[det] Step 4 — Snapshot initial retired_at state", flush=True)
_initial_retired = _snapshot_retired_state()
_n_active   = sum(1 for v in _initial_retired.values() if v is None)
_n_retired  = sum(1 for v in _initial_retired.values() if v is not None)
print(f"[det]   Row 2 reqs: {len(_initial_retired)} total  "
      f"({_n_active} active, {_n_retired} retired in snapshot)", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_r11_row2(label: str) -> None:
    """
    Reset PMT_E2E_R11 Row 2 matching state to the initial snapshot.

    Restores:
      - retired_at to the value it had in the source snapshot (undoes merge retirements)
      - refines_refs → [] on ALL Row 2 requirements
      - requirement_matching_log entries deleted
      - requirement_gap_record entries for Row 2 reqs deleted
    """
    s = get_session()
    try:
        # 1. Restore retired_at to initial snapshot values (undo any merges)
        for rid, retired_iso in _initial_retired.items():
            if retired_iso is None:
                s.execute(
                    text(
                        "UPDATE requirement SET retired_at = NULL "
                        "WHERE project_id = :pid AND requirement_id = :rid AND row_target = '2'"
                    ),
                    {"pid": PROJECT_ID, "rid": rid},
                )
            else:
                s.execute(
                    text(
                        "UPDATE requirement SET retired_at = CAST(:ts AS timestamptz) "
                        "WHERE project_id = :pid AND requirement_id = :rid AND row_target = '2'"
                    ),
                    {"pid": PROJECT_ID, "rid": rid, "ts": retired_iso},
                )

        # 2. Clear refines_refs on all Row 2 reqs (active and retired)
        s.execute(
            text(
                "UPDATE requirement SET refines_refs = '[]'::jsonb "
                "WHERE project_id = :pid AND row_target = '2'"
            ),
            {"pid": PROJECT_ID},
        )

        # 3. Delete matching log for this project
        s.execute(
            text("DELETE FROM requirement_matching_log WHERE project_id = :pid"),
            {"pid": PROJECT_ID},
        )

        # 4. Delete gap records for this project's Row 2 reqs
        if _initial_retired:
            placeholders = ", ".join(f":rid{i}" for i in range(len(_initial_retired)))
            rid_params = {f"rid{i}": v for i, v in enumerate(_initial_retired.keys())}
            s.execute(
                text(
                    f"DELETE FROM requirement_gap_record "
                    f"WHERE project_id = :pid OR requirement_id IN ({placeholders})"
                ),
                {"pid": PROJECT_ID, **rid_params},
            )
        else:
            s.execute(
                text("DELETE FROM requirement_gap_record WHERE project_id = :pid"),
                {"pid": PROJECT_ID},
            )

        s.commit()

        n_active = sum(1 for v in _initial_retired.values() if v is None)
        print(f"[det]   Reset for {label}: {n_active} active reqs ready.", flush=True)
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def _read_refines_refs() -> dict[str, list[str]]:
    """
    Read current refines_refs from DB for PMT_E2E_R11 active Row 2 requirements.
    Returns {requirement_id: [parent_id, ...]} in sorted order.
    """
    s = get_session()
    try:
        rows = s.execute(
            text(
                "SELECT requirement_id, refines_refs "
                "FROM requirement "
                "WHERE project_id = :pid AND row_target = '2' AND retired_at IS NULL "
                "ORDER BY requirement_id"
            ),
            {"pid": PROJECT_ID},
        ).fetchall()
        return {row[0]: sorted(row[1] or []) for row in rows}
    finally:
        s.close()


def _run_matching(run_label: str) -> dict[str, Any]:
    print(SEP, flush=True)
    print(f"[det] {run_label} — match_row(2, {PROJECT_ID!r})", flush=True)
    print(SEP, flush=True)
    try:
        result = match_row(ROW, PROJECT_ID)
    except Exception as exc:
        print(f"[det] FAILED: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)

    print(f"[det]   total={result['total']}  refine={result['refine_count']}"
          f"  no_match={result['no_match_count']}  flagged={result['flagged_count']}"
          f"  duplicate={result['duplicate_count']}", flush=True)
    for r in result.get("results", []):
        rid    = r.get("requirement_id", "?")
        out    = r.get("outcome", "?")
        pids   = r.get("matched_parent_ids", [])
        conf   = r.get("confidence")
        c_str  = f" conf={conf:.2f}" if conf is not None else ""
        p_str  = f" → {pids}" if pids else ""
        print(f"[det]     {rid}  {out}{c_str}{p_str}", flush=True)
    return result


# ---------------------------------------------------------------------------
# Steps 5 & 6 — Run 1
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[det] Step 5 — Reset state (before run 1)", flush=True)
_reset_r11_row2("run1-reset")

run1_result = _run_matching("Run 1")
run1_refs   = _read_refines_refs()
print(f"[det]   Run 1 active reqs after matching: {len(run1_refs)}", flush=True)


# ---------------------------------------------------------------------------
# Steps 7 & 8 — Run 2
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[det] Step 7 — Reset state (before run 2)", flush=True)
_reset_r11_row2("run2-reset")

run2_result = _run_matching("Run 2")
run2_refs   = _read_refines_refs()
print(f"[det]   Run 2 active reqs after matching: {len(run2_refs)}", flush=True)


# ---------------------------------------------------------------------------
# Step 9 — Compare
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[det] Step 9 — Compare run1 vs run2", flush=True)
print(SEP, flush=True)

all_req_ids = sorted(set(run1_refs) | set(run2_refs))
diffs: list[dict[str, Any]] = []

for rid in all_req_ids:
    r1 = run1_refs.get(rid, [])
    r2 = run2_refs.get(rid, [])
    if r1 != r2:
        diffs.append({"requirement_id": rid, "run1": r1, "run2": r2})
        print(f"[det]   DIFF  {rid}: run1={r1}  run2={r2}", flush=True)
    else:
        print(f"[det]   MATCH {rid}: {r1}", flush=True)

determinism_passed = len(diffs) == 0
print(flush=True)
if determinism_passed:
    print("[det]   DETERMINISM PASSED — both runs produced identical refines_refs", flush=True)
else:
    print(f"[det]   DETERMINISM FAILED — {len(diffs)} requirement(s) differ", flush=True)


# ---------------------------------------------------------------------------
# Step 10 — Write output JSON
# ---------------------------------------------------------------------------

output: dict[str, Any] = {
    "experiment": "PMT_Matching_Determinism_Check",
    "project_id": PROJECT_ID,
    "row": ROW,
    "source_snapshot": SOURCE_SNAP,
    "test_branch_id": test_branch_id,
    "ran_at": datetime.now(timezone.utc).isoformat(),
    "temperature_fix_applied": True,
    "determinism_passed": determinism_passed,
    "diff_count": len(diffs),
    "diffs": diffs,
    "initial_active_count": _n_active,
    "initial_retired_count": _n_retired,
    "run1_summary": {
        "total": run1_result["total"],
        "refine": run1_result["refine_count"],
        "no_match": run1_result["no_match_count"],
        "flagged": run1_result["flagged_count"],
        "duplicate": run1_result["duplicate_count"],
        "downward_gaps": run1_result["downward_gap_count"],
    },
    "run2_summary": {
        "total": run2_result["total"],
        "refine": run2_result["refine_count"],
        "no_match": run2_result["no_match_count"],
        "flagged": run2_result["flagged_count"],
        "duplicate": run2_result["duplicate_count"],
        "downward_gaps": run2_result["downward_gap_count"],
    },
    "per_requirement": {
        rid: {"run1": run1_refs.get(rid, []), "run2": run2_refs.get(rid, [])}
        for rid in all_req_ids
    },
}

with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
    json.dump(output, f, indent=2)
print(f"[det]   Written: {OUT_FILE.name}", flush=True)


# ---------------------------------------------------------------------------
# Step 11 — Delete temp branch
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[det] Step 11 — Delete temp branch {BRANCH_NAME}", flush=True)
bm._delete_branch(neon_project, test_branch_id)
print(f"[det]   Deleted {test_branch_id}", flush=True)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(SEP, flush=True)
if determinism_passed:
    print("[det] DETERMINISM CHECK PASSED", flush=True)
else:
    print(f"[det] DETERMINISM CHECK FAILED — {len(diffs)} diff(s)", flush=True)
    for d in diffs:
        print(f"[det]   {d['requirement_id']}: run1={d['run1']}  run2={d['run2']}", flush=True)
    sys.exit(2)
print(SEP, flush=True)
print(f"[det]   Output: {OUT_FILE.name}", flush=True)
