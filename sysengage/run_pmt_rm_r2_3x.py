"""
run_pmt_rm_r2_3x.py — PMT Row 2 Requirement Matching runner (triple-run).

Workflow
--------
1.  Clone one disposable test branch from snap_PMT_ph03_3d_R2_3x_YYYYMMDD
    (which already holds Row 1+2 complete pipelines for R11/R12/R13, with
    refines_refs=[] on all Row 2 requirements).
2.  Set NEON_DATABASE_URL to the test branch connection string.
3.  Apply schema migrations once (idempotent).
4.  For each of PMT_E2E_R11, PMT_E2E_R12, PMT_E2E_R13 in sequence:
      SC/RLSRA/CCI/DD/RD — all SKIP via idempotency (already done).
      RM  — run match_row(2, project_id) to populate refines_refs.
5.  Export one ledger JSON per project (pass 3e, Row 2).
6.  Rename the test branch → snap_PMT_ph03_3e_R2_3x_YYYYMMDD and register.

Design notes
------------
- Matching is a standalone service — idempotency is checked against
  analysis_pass (mechanism='RequirementMatching'; v0.2 AnalysisPass provenance).
- candidates.py falls back to the full same-row / parent-row pool when
  object_term is absent (acceptable; DD pre-filter is an optimisation).
- Row 1 is a no-op per VER-rm-02: match_row skips it automatically.
- Source snapshot is resolved by name at runtime; no branch ID hardcoded.

Invocation (from workspace root):
    python -u sysengage/run_pmt_rm_r2_3x.py
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SYSENGAGE_DIR = Path(__file__).parent
sys.path.insert(0, str(SYSENGAGE_DIR))
sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))

# branch_manager is safe to import early — it does NOT import core.db
import branch_manager as bm

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECTS: list[tuple[str, int]] = [
    ("PMT_E2E_R11", 11),
    ("PMT_E2E_R12", 12),
    ("PMT_E2E_R13", 13),
]

PROJECT_CODE    = "PMT"
PRACTITIONER_ID = "SH001"
ROW             = 2

OUT_DIR = SYSENGAGE_DIR.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_SNAP      = "snap_PMT_ph03_3d_R2_3x_20260606"
TEST_BRANCH_NAME = "test_PMT_ph03_3e_R2_3x"

SNAP_DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
SNAP_NAME = f"snap_PMT_ph03_3e_R2_3x_{SNAP_DATE}"

SEP = "=" * 65


# ---------------------------------------------------------------------------
# Step 1 — Create test branch from Row 2 combined snapshot
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[3x] Step 1 — Create test branch from {SOURCE_SNAP}", flush=True)
print(SEP, flush=True)

neon_project = bm._get_project_id()

source_branch = bm._find_branch_by_name(neon_project, SOURCE_SNAP)
if not source_branch:
    print(f"[3x] ERROR: source snapshot branch '{SOURCE_SNAP}' not found in Neon.", file=sys.stderr)
    print("[3x]   The Neon branch for this snapshot was deleted.", file=sys.stderr)
    print("[3x]   To rebuild it:", file=sys.stderr)
    print("[3x]     1. Clone snap_ph03_3c_AllProjects (still alive).", file=sys.stderr)
    print("[3x]     2. Run DD+RD for PMT_E2E_R11/R12/R13 rows 1+2 on that clone.", file=sys.stderr)
    print("[3x]     3. Promote the clone to snap_PMT_ph03_3d_R2_3x_YYYYMMDD.", file=sys.stderr)
    print("[3x]     4. Update SOURCE_SNAP in this file to the new date suffix.", file=sys.stderr)
    print("[3x]     5. Re-run this script.", file=sys.stderr)
    sys.exit(1)
source_branch_id = source_branch["id"]
print(f"[3x]   Source snapshot : {SOURCE_SNAP} ({source_branch_id})", flush=True)

existing = bm._find_branch_by_name(neon_project, TEST_BRANCH_NAME)
if existing:
    test_branch_id = existing["id"]
    print(f"[3x]   Reusing existing test branch: {test_branch_id}", flush=True)
    ep_data = bm._neon_request(
        "GET",
        f"/projects/{neon_project}/branches/{test_branch_id}/endpoints",
    )
    endpoints = ep_data.get("endpoints", [])
    if not endpoints:
        print("[3x] ERROR: test branch has no endpoint.", file=sys.stderr)
        sys.exit(1)
    test_host = endpoints[0]["host"]
    base_url = os.environ.get("NEON_DATABASE_URL", "")
    test_branch_url = re.sub(r"@[^/?]+", f"@{test_host}", base_url)
    test_branch_url = test_branch_url.replace(
        "channel_binding=require", "channel_binding=prefer"
    )
else:
    test_branch_id, test_branch_url = bm._create_branch(
        neon_project, TEST_BRANCH_NAME, source_branch_id
    )
    print(f"[3x]   Created test branch: {test_branch_id}", flush=True)

print(f"[3x]   Branch ID : {test_branch_id}", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Step 2 — Point NEON_DATABASE_URL at the test branch
#           (must happen BEFORE any mechanism imports, which bind core.db engine)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[3x] Step 2 — Switch active DB to test branch", flush=True)
print(SEP, flush=True)

os.environ["NEON_DATABASE_URL"] = test_branch_url
print("[3x]   NEON_DATABASE_URL → test branch", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Deferred mechanism imports — engine binds to test branch URL from here on
# ---------------------------------------------------------------------------

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

from core.db import get_session
from core.output_naming import generate_filename
from mechanisms.ledger_export import run_ledger_export
from mechanisms.requirement_matching.service import match_row
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Step 3 — Schema migrations (once, idempotent)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[3x] Step 3 — Schema migrations (test branch)", flush=True)
print(SEP, flush=True)

_alembic_cfg = AlembicConfig(str(SYSENGAGE_DIR / "alembic.ini"))
_alembic_cfg.set_main_option("script_location", str(SYSENGAGE_DIR / "alembic"))
alembic_command.upgrade(_alembic_cfg, "head")
print("[3x]   Schema up to date.", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Idempotency helper for Matching
# ---------------------------------------------------------------------------

def _matching_already_done(project_id: str, row_n: int) -> bool:
    """
    Return True if a completed RequirementMatching AnalysisPass exists for
    this project / row (v0.2: provenance in analysis_pass, not service-log tables).
    """
    s = get_session()
    try:
        scope = f"Row {row_n} requirements matched against Row {row_n - 1}"
        row = s.execute(
            text(
                "SELECT pass_id FROM analysis_pass "
                "WHERE project_id = :pid AND mechanism = 'RequirementMatching' "
                "AND evaluated_scope = :scope "
                "AND execution_status IN ('Completed','CompletedWithWarnings') "
                "LIMIT 1"
            ),
            {"pid": project_id, "scope": scope},
        ).fetchone()
        return row is not None
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Per-project Matching runner
# ---------------------------------------------------------------------------

def _run_matching(project_id: str, run_label: int) -> dict[str, Any]:
    """
    Run Requirement Matching for Row n on project_id.

    All upstream passes (SC/RLSRA/CCI/DD/RD) are already complete on this
    branch — idempotency check gates them silently. Only the RM step runs.

    Returns the match_row summary dict.
    """
    tag = f"[{project_id}]"
    rm_tag = f"[{project_id}/RM]"

    print(flush=True)
    print(SEP, flush=True)
    print(f"{tag}  Run {run_label} — Row {ROW} Matching", flush=True)
    print(SEP, flush=True)

    if _matching_already_done(project_id, ROW):
        print(
            f"{rm_tag}   SKIP — RequirementMatching AnalysisPass already exists for Row {ROW}.",
            flush=True,
        )
        # Read counts from the existing AnalysisPass mechanism_data (v0.2)
        s = get_session()
        try:
            scope = f"Row {ROW} requirements matched against Row {ROW - 1}"
            row = s.execute(
                text(
                    "SELECT outputs->'mechanism_data'->'counts' AS counts "
                    "FROM analysis_pass "
                    "WHERE project_id = :pid AND mechanism = 'RequirementMatching' "
                    "AND evaluated_scope = :scope "
                    "AND execution_status IN ('Completed','CompletedWithWarnings') "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"pid": project_id, "scope": scope},
            ).fetchone()
        finally:
            s.close()
        counts = dict(row[0]) if row and row[0] else {}
        total       = counts.get("processed", 0)
        refine_count    = counts.get("refine_link", 0)
        no_match_count  = counts.get("no_match", 0)
        flagged_count   = counts.get("flagged", 0)
        duplicate_count = counts.get("duplicate_merge", 0)
        deferred_count  = counts.get("deferred", 0)
        print(
            f"{rm_tag}   (existing)  total={total}  refine={refine_count}"
            f"  no_match={no_match_count}  flagged={flagged_count}",
            flush=True,
        )
        return {
            "row_matched": ROW,
            "total": total,
            "refine_count": refine_count,
            "no_match_count": no_match_count,
            "flagged_count": flagged_count,
            "duplicate_count": duplicate_count,
            "deferred_count": deferred_count,
            "downward_gap_count": 0,
            "_skipped": True,
        }

    try:
        rm_result = match_row(ROW, project_id)
    except Exception as exc:
        print(f"{rm_tag} FAILED: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)

    print(f"{rm_tag}   row_matched        = {rm_result['row_matched']}", flush=True)
    print(f"{rm_tag}   total              = {rm_result['total']}", flush=True)
    print(f"{rm_tag}   refine_count       = {rm_result['refine_count']}", flush=True)
    print(f"{rm_tag}   no_match_count     = {rm_result['no_match_count']}", flush=True)
    print(f"{rm_tag}   flagged_count      = {rm_result['flagged_count']}", flush=True)
    print(f"{rm_tag}   duplicate_count    = {rm_result['duplicate_count']}", flush=True)
    print(f"{rm_tag}   deferred_count     = {rm_result['deferred_count']}", flush=True)
    print(f"{rm_tag}   downward_gap_count = {rm_result['downward_gap_count']}", flush=True)

    # Per-requirement detail (concise)
    for r in rm_result.get("results", []):
        outcome = r.get("outcome", "?")
        rid = r.get("requirement_id", "?")
        parents = r.get("matched_parent_ids", [])
        conf = r.get("confidence")
        conf_str = f" conf={conf:.2f}" if conf is not None else ""
        parents_str = f" → {parents}" if parents else ""
        print(f"{rm_tag}     {rid}  {outcome}{conf_str}{parents_str}", flush=True)

    print(f"{tag}  Run {run_label} Matching complete.", flush=True)
    return rm_result


# ---------------------------------------------------------------------------
# Steps 4: Run Matching for all three projects
# ---------------------------------------------------------------------------

rm_summaries: dict[str, dict[str, Any]] = {}
for _project_id, _run_number in PROJECTS:
    rm_summaries[_project_id] = _run_matching(_project_id, _run_number)

print(flush=True)


# ---------------------------------------------------------------------------
# Step 5 — Ledger export (one per project, pass 3e)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[3x] Step 5 — Ledger exports (pass 3e — with refines_refs)", flush=True)
print(SEP, flush=True)

ledger_results: list[dict[str, Any]] = []

for _project_id, _run_number in PROJECTS:
    _basename = generate_filename(
        project_id=PROJECT_CODE,
        phase=3,
        pass_="3e",
        row=ROW,
        out_dir=str(OUT_DIR),
    )
    _session = get_session()
    try:
        _export = run_ledger_export(project_id=_project_id, session=_session)
    finally:
        _session.close()

    _path = OUT_DIR / _basename
    with open(_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_export.json_str)

    _ledger = _export.ledger
    _n_el   = len(_ledger.get("elements", []))
    _n_reg  = len(_ledger.get("register_index", []))
    _hash   = _ledger.get("content_hash", {}).get("hash", "")[:16]

    # Count non-empty refines_refs on Row 2 requirements (fields live in payload)
    _reqs_with_refs = sum(
        1 for el in _ledger.get("elements", [])
        if el.get("element_type") == "Requirement"
        and str(el.get("payload", {}).get("row_target", "")) == str(ROW)
        and el.get("payload", {}).get("refines_refs")
    )
    _row2_reqs = sum(
        1 for el in _ledger.get("elements", [])
        if el.get("element_type") == "Requirement"
        and str(el.get("payload", {}).get("row_target", "")) == str(ROW)
    )

    print(f"[3x]   {_project_id} → {_basename}", flush=True)
    print(f"[3x]     Elements={_n_el}  Registers={_n_reg}  Hash={_hash}...", flush=True)
    print(
        f"[3x]     Row{ROW} reqs: {_reqs_with_refs}/{_row2_reqs} have refines_refs populated",
        flush=True,
    )

    rm = rm_summaries[_project_id]
    print(
        f"[3x]     Matching: refine={rm['refine_count']}  no_match={rm['no_match_count']}"
        f"  flagged={rm['flagged_count']}  downward_gaps={rm['downward_gap_count']}",
        flush=True,
    )

    ledger_results.append({
        "project_id": _project_id,
        "run_number": _run_number,
        "basename": _basename,
        "n_elements": _n_el,
        "n_registers": _n_reg,
        "row2_reqs_total": _row2_reqs,
        "row2_reqs_with_refs": _reqs_with_refs,
    })

print(flush=True)


# ---------------------------------------------------------------------------
# Step 6 — Count rows for snapshot metadata
# ---------------------------------------------------------------------------

_session3 = get_session()
try:
    _totals: dict[str, dict[str, int]] = {}
    for _project_id, _ in PROJECTS:
        _totals[_project_id] = {
            "sources":      _session3.execute(text("SELECT count(*) FROM source            WHERE project_id=:p"), {"p": _project_id}).scalar() or 0,
            "ccis":         _session3.execute(text("SELECT count(*) FROM cell_content_item WHERE project_id=:p"), {"p": _project_id}).scalar() or 0,
            "domains":      _session3.execute(text("SELECT count(*) FROM domain            WHERE project_id=:p"), {"p": _project_id}).scalar() or 0,
            "requirements": _session3.execute(text("SELECT count(*) FROM requirement       WHERE project_id=:p"), {"p": _project_id}).scalar() or 0,
        }
finally:
    _session3.close()


# ---------------------------------------------------------------------------
# Step 6 — Promote test branch → combined snapshot (rename in place)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[3x] Step 6 — Promote test branch → {SNAP_NAME}", flush=True)
print(SEP, flush=True)

old = bm._find_branch_by_name(neon_project, SNAP_NAME)
if old:
    print(f"[3x]   Removing stale same-date snapshot ({old['id']}) …", flush=True)
    bm._delete_branch(neon_project, old["id"])

bm._neon_request(
    "PATCH",
    f"/projects/{neon_project}/branches/{test_branch_id}",
    body={"branch": {"name": SNAP_NAME}},
)
print(f"[3x]   Renamed {TEST_BRANCH_NAME} → {SNAP_NAME}", flush=True)

_parts = []
for _pid, _t in _totals.items():
    rm = rm_summaries[_pid]
    _parts.append(
        f"{_pid}: Sources={_t['sources']}, CCIs={_t['ccis']}, "
        f"Domains={_t['domains']}, Requirements={_t['requirements']}, "
        f"Matching(refine={rm['refine_count']},no_match={rm['no_match_count']},flagged={rm['flagged_count']})"
    )
_state_desc = (
    f"PMT Row 2 triple-run with Requirement Matching (Runs 11-13, pass 3e). "
    + " | ".join(_parts)
    + ". Cloned from snap_PMT_ph03_3d_R2_3x. refines_refs populated on Row 2 requirements. Production branch untouched."
)

_entry = {
    "name": SNAP_NAME,
    "project_id": "PMT_3x",
    "phase": "ph03",
    "pass": "3e",
    "row": "R2",
    "state_description": _state_desc,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "status": "VERIFIED",
    "ver_criteria_passed": [],
    "neon_branch_id": test_branch_id,
    "neon_project_id": neon_project,
}
bm._registry_add_snapshot(_entry)
print(f"[3x]   Snapshot registered in registry.", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[3x] PMT Row 2 Matching COMPLETE — production branch untouched", flush=True)
print(SEP, flush=True)
print(f"[3x]   Branch : {SNAP_NAME}  ({test_branch_id})", flush=True)
for lr in ledger_results:
    t = _totals[lr["project_id"]]
    rm = rm_summaries[lr["project_id"]]
    print(
        f"[3x]   Run {lr['run_number']:2d}  {lr['project_id']}"
        f"  Req={t['requirements']}"
        f"  refine={rm['refine_count']}  no_match={rm['no_match_count']}"
        f"  flagged={rm['flagged_count']}  dgaps={rm['downward_gap_count']}"
        f"  → {lr['basename']}",
        flush=True,
    )
print(flush=True)
print("[3x] To clone a test branch for determinism check from this snapshot:", flush=True)
print(
    f"  python sysengage/scripts/branch_manager.py create_test_branch "
    f"--snapshot {SNAP_NAME} --scenario <name>",
    flush=True,
)
