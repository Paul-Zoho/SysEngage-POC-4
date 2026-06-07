"""
run_pmt_3e_r2_dd_reexport.py — Re-export PMT_Ph03_3e_RequirementMatching_R2_Run4.json
with DataDictionaryEntry elements now included in the ledger export pipeline.

Source: test_PMT_ph03_3e_R2_Launcher_20260606_202235 (br-round-cell-abkyr073)
  — the Launcher branch from Run4, which contains the 17 DD entries written by
    the v0.7 §4.4.3a DD object-slot binding.

Project:  PMT_E2E  (the single-project form used by the Launcher runs)
Output:   verification_outputs/PMT_Ph03_3e_RequirementMatching_R2_Run4.json
          (overwrites in-place — Run4 file, not a new run number)

Steps:
  1. Clone source branch → tmp_PMT_3e_r2_dd_reexport (fresh URL from Neon API)
  2. Point NEON_DATABASE_URL at the temp branch
  3. Export PMT_E2E ledger → overwrite Run4 JSON
  4. Delete temp branch

Usage (from workspace root):
    python -u sysengage/run_pmt_3e_r2_dd_reexport.py
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

PROJECT_ID   = "PMT_E2E"
SOURCE_BRANCH = "test_PMT_ph03_3e_R2_Launcher_20260606_202235"
TEMP_BRANCH   = "tmp_PMT_3e_r2_dd_reexport"

OUT_DIR  = SYSENGAGE_DIR.parent / "verification_outputs"
RUN4_OUT = OUT_DIR / "PMT_Ph03_3e_RequirementMatching_R2_Run4.json"

SEP = "=" * 65


# ---------------------------------------------------------------------------
# Step 1 — Clone source branch → temp branch (URL from Neon API directly)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[dd-reexport] Step 1 — Clone {SOURCE_BRANCH} → {TEMP_BRANCH}", flush=True)
print(SEP, flush=True)

neon_project = bm._get_project_id()

source = bm._find_branch_by_name(neon_project, SOURCE_BRANCH)
if not source:
    print(f"[dd-reexport] ERROR: '{SOURCE_BRANCH}' not found in Neon.", file=sys.stderr)
    sys.exit(1)
source_id = source["id"]
print(f"[dd-reexport]   Source : {SOURCE_BRANCH} ({source_id})", flush=True)

existing = bm._find_branch_by_name(neon_project, TEMP_BRANCH)
if existing:
    print("[dd-reexport]   Stale temp branch found — deleting.", flush=True)
    bm._delete_branch(neon_project, existing["id"])

temp_id, temp_url = bm._create_branch(neon_project, TEMP_BRANCH, source_id)
print(f"[dd-reexport]   Created temp branch: {temp_id}", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Step 2 — Point active DB at temp branch (before mechanism imports)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[dd-reexport] Step 2 — Switch NEON_DATABASE_URL to temp branch", flush=True)
print(SEP, flush=True)

os.environ["NEON_DATABASE_URL"] = temp_url
print("[dd-reexport]   NEON_DATABASE_URL → temp branch", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Deferred imports — SQLAlchemy engine binds to temp_url
# ---------------------------------------------------------------------------

from core.db import get_session
from mechanisms.ledger_export import run_ledger_export


# ---------------------------------------------------------------------------
# Step 3 — Export and overwrite Run4
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[dd-reexport] Step 3 — Export {PROJECT_ID} → {RUN4_OUT.name}", flush=True)
print(SEP, flush=True)

session = get_session()
try:
    export = run_ledger_export(project_id=PROJECT_ID, session=session)
finally:
    session.close()

with open(RUN4_OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(export.json_str)

ledger  = export.ledger
n_el    = len(ledger.get("elements", []))
n_reg   = len(ledger.get("register_index", []))
chash   = ledger.get("content_hash", {}).get("hash", "")[:16]

dd_entries   = [e for e in ledger.get("elements", []) if e.get("element_type") == "DataDictionaryEntry"]
dd_canonical = sum(1 for e in dd_entries if e["payload"].get("entry_kind") == "canonical")
dd_synonym   = sum(1 for e in dd_entries if e["payload"].get("entry_kind") == "synonym")

reqs_r2       = [e for e in ledger.get("elements", [])
                 if e.get("element_type") == "Requirement"
                 and str(e.get("payload", {}).get("row_target", "")) == "2"]
reqs_with_refs = sum(1 for r in reqs_r2 if r.get("payload", {}).get("refines_refs"))

print(f"[dd-reexport]   Elements={n_el}  Registers={n_reg}  Hash={chash}...", flush=True)
print(f"[dd-reexport]   DD entries : {len(dd_entries)} total ({dd_canonical} canonical, {dd_synonym} synonym)", flush=True)
print(f"[dd-reexport]   Row2 reqs  : {reqs_with_refs}/{len(reqs_r2)} have refines_refs", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Step 4 — Delete temp branch
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[dd-reexport] Step 4 — Delete temp branch {TEMP_BRANCH}", flush=True)
print(SEP, flush=True)

bm._delete_branch(neon_project, temp_id)
print(f"[dd-reexport]   Deleted {temp_id}", flush=True)
print(flush=True)

print(SEP, flush=True)
print(f"[dd-reexport] Done — {RUN4_OUT.name} now includes {len(dd_entries)} DataDictionaryEntry elements.", flush=True)
print(SEP, flush=True)
