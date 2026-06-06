"""
run_pmt_rm_r2_3x_reexport.py — Re-export pass-3e ledger JSONs from the
snap_PMT_ph03_3e_R2_3x_YYYYMMDD snapshot with the corrected json_builder
that now includes refines_refs in Requirement payloads.

This script is idempotent and safe to re-run.  It clones a disposable
branch from the 3e snapshot, exports the three ledger JSONs, overwrites
the files in verification_outputs/, then deletes the temp branch.

Usage (from workspace root):
    python -u sysengage/run_pmt_rm_r2_3x_reexport.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SYSENGAGE_DIR = Path(__file__).parent
sys.path.insert(0, str(SYSENGAGE_DIR))
sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))

import branch_manager as bm

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECTS: list[tuple[str, int]] = [
    ("PMT_E2E_R11", 11),
    ("PMT_E2E_R12", 12),
    ("PMT_E2E_R13", 13),
]

PROJECT_CODE = "PMT"
ROW          = 2

OUT_DIR = SYSENGAGE_DIR.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_SNAP      = "snap_PMT_ph03_3e_R2_3x_20260606"
TEMP_BRANCH_NAME = "tmp_PMT_3e_R2_reexport"

SEP = "=" * 65


# ---------------------------------------------------------------------------
# Step 1 — Clone the 3e snapshot into a temp branch
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[reexport] Step 1 — Clone {SOURCE_SNAP} → {TEMP_BRANCH_NAME}", flush=True)
print(SEP, flush=True)

neon_project = bm._get_project_id()

source_branch = bm._find_branch_by_name(neon_project, SOURCE_SNAP)
if not source_branch:
    print(
        f"[reexport] ERROR: snapshot '{SOURCE_SNAP}' not found in Neon.",
        file=sys.stderr,
    )
    sys.exit(1)
source_branch_id = source_branch["id"]
print(f"[reexport]   Source : {SOURCE_SNAP} ({source_branch_id})", flush=True)

existing = bm._find_branch_by_name(neon_project, TEMP_BRANCH_NAME)
if existing:
    print(
        f"[reexport]   Temp branch already exists — deleting and re-creating.",
        flush=True,
    )
    bm._delete_branch(neon_project, existing["id"])

temp_branch_id, temp_branch_url = bm._create_branch(
    neon_project, TEMP_BRANCH_NAME, source_branch_id
)
print(f"[reexport]   Created temp branch: {temp_branch_id}", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Step 2 — Point NEON_DATABASE_URL at temp branch (before mechanism imports)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[reexport] Step 2 — Switch active DB to temp branch", flush=True)
print(SEP, flush=True)

os.environ["NEON_DATABASE_URL"] = temp_branch_url
print("[reexport]   NEON_DATABASE_URL → temp branch", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Deferred mechanism imports — engine binds to temp branch URL
# ---------------------------------------------------------------------------

from core.db import get_session
from core.output_naming import generate_filename
from mechanisms.ledger_export import run_ledger_export


# ---------------------------------------------------------------------------
# Step 3 — Re-export ledger JSON for each project
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[reexport] Step 3 — Ledger exports (pass 3e, with refines_refs)", flush=True)
print(SEP, flush=True)

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

    print(f"[reexport]   {_project_id} → {_basename}", flush=True)
    print(f"[reexport]     Elements={_n_el}  Registers={_n_reg}  Hash={_hash}...", flush=True)
    print(
        f"[reexport]     Row{ROW} reqs: {_reqs_with_refs}/{_row2_reqs} have refines_refs populated",
        flush=True,
    )

print(flush=True)


# ---------------------------------------------------------------------------
# Step 4 — Delete temp branch
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[reexport] Step 4 — Delete temp branch {TEMP_BRANCH_NAME}", flush=True)
print(SEP, flush=True)

bm._delete_branch(neon_project, temp_branch_id)
print(f"[reexport]   Deleted temp branch {temp_branch_id}", flush=True)
print(flush=True)

print(SEP, flush=True)
print("[reexport] Done — verification_outputs/ updated with refines_refs.", flush=True)
print(SEP, flush=True)
