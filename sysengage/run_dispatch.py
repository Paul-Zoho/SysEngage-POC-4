"""
run_dispatch.py — Generic parameterized dispatcher for SysEngage mechanism passes.

Accepts CLI arguments and runs the selected passes in correct numeric order
for the selected rows against the selected project.

Usage (from workspace root):
    python -u sysengage/run_dispatch.py \\
        --project PMT_E2E \\
        --rows 1,2 \\
        --passes 3b,3c,3d \\
        --snapshot snap_ph03_3a_AllProjects \\
        --source-doc "The Pocket Money Tracker System v1.docx"

Arguments
---------
--project     Project ID, e.g. PMT_E2E, NQPS_E2E, ROW_E2E
--rows        Comma-separated row numbers, e.g. 1,2,3
--passes      Comma-separated pass codes, e.g. 3a,3b,3c,3d,3e
--snapshot    (optional) Snapshot name to clone a test branch from.
              If omitted, runs against the current NEON_DATABASE_URL directly.
--source-doc  (optional) Filename within verification_inputs/ for pass 3a SC.
              Required when 3a is included.

Pass definitions
----------------
3a  Source Capture  +  Row-Lens Source Re-Analysis
3b  CCI Construction
3c  Domain Derivation
3d  Requirement Derivation
3e  Requirement Matching

Notes
-----
- Passes run in sorted numeric order regardless of the order supplied.
- If upstream state is missing (e.g. running 3c without 3b having run) the pass
  will produce nothing. This is by design — the caller is responsible for
  supplying the right snapshot.
- NEON_DATABASE_URL must be set before any mechanism imports (core.db binds the
  engine at import time). This script therefore defers all mechanism imports
  until after the URL is confirmed / injected.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SYSENGAGE_DIR = Path(__file__).parent
WORKSPACE_ROOT = SYSENGAGE_DIR.parent
VERIFICATION_INPUTS = WORKSPACE_ROOT / "verification_inputs"
VERIFICATION_OUTPUTS = WORKSPACE_ROOT / "verification_outputs"

sys.path.insert(0, str(SYSENGAGE_DIR))
sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))

PRACTITIONER_ID = "SH001"
SEP = "=" * 65

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="SysEngage mechanism dispatcher")
parser.add_argument("--project", required=True, help="Project ID, e.g. PMT_E2E")
parser.add_argument("--rows", required=True, help="Comma-separated row numbers, e.g. 1,2")
parser.add_argument("--passes", required=True, help="Comma-separated pass codes, e.g. 3b,3c")
parser.add_argument("--snapshot", default="", help="Snapshot name to clone test branch from")
parser.add_argument("--source-doc", default="", dest="source_doc",
                    help="Filename in verification_inputs/ for pass 3a")
args = parser.parse_args()

PROJECT_ID = args.project.strip()
try:
    ROWS = sorted(int(r.strip()) for r in args.rows.split(",") if r.strip())
except ValueError:
    print("[dispatch] ERROR: --rows must be comma-separated integers", file=sys.stderr, flush=True)
    sys.exit(1)

PASS_ORDER = {"3a": 0, "3b": 1, "3c": 2, "3d": 3, "3e": 4}
raw_passes = [p.strip().lower() for p in args.passes.split(",") if p.strip()]
invalid = [p for p in raw_passes if p not in PASS_ORDER]
if invalid:
    print(f"[dispatch] ERROR: unknown passes: {invalid}  valid: {list(PASS_ORDER)}", file=sys.stderr, flush=True)
    sys.exit(1)
PASSES = sorted(set(raw_passes), key=lambda p: PASS_ORDER[p])

SNAPSHOT = args.snapshot.strip()
SOURCE_DOC = args.source_doc.strip()

# Derive project code (first segment before _) for output naming
PROJECT_CODE = PROJECT_ID.split("_")[0]

print(SEP, flush=True)
print(f"[dispatch] Project  : {PROJECT_ID}", flush=True)
print(f"[dispatch] Rows     : {ROWS}", flush=True)
print(f"[dispatch] Passes   : {PASSES}", flush=True)
print(f"[dispatch] Snapshot : {SNAPSHOT or '(none — use current DB)'}", flush=True)
if SOURCE_DOC:
    print(f"[dispatch] Source   : {SOURCE_DOC}", flush=True)
print(SEP, flush=True)
print(flush=True)

# ---------------------------------------------------------------------------
# Step 1 — branch clone (if snapshot given)
# ---------------------------------------------------------------------------

import branch_manager as bm  # noqa: E402  (safe — does not import core.db)

neon_project = bm._get_project_id()
_last_pass = PASSES[-1]          # e.g. "3c"
_rows_seg  = "R" + "-".join(str(r) for r in ROWS)   # e.g. "R1", "R1-3"
_ts        = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
test_branch_name = f"test_{PROJECT_CODE}_ph03_{_last_pass}_{_rows_seg}_Launcher_{_ts}"

if SNAPSHOT:
    print(SEP, flush=True)
    print(f"[dispatch] Cloning snapshot {SNAPSHOT!r} → {test_branch_name}", flush=True)
    print(SEP, flush=True)

    parent_branch = bm._find_branch_by_name(neon_project, SNAPSHOT)
    if not parent_branch:
        print(f"[dispatch] ERROR: snapshot branch '{SNAPSHOT}' not found in Neon.", file=sys.stderr, flush=True)
        sys.exit(1)

    parent_label = f"snapshot '{SNAPSHOT}'"
else:
    print(SEP, flush=True)
    print(f"[dispatch] No snapshot selected — cloning from primary branch → {test_branch_name}", flush=True)
    print(SEP, flush=True)

    parent_branch = bm._get_primary_branch(neon_project)
    parent_label = f"primary branch '{parent_branch['name']}'"

test_branch_id, conn_str = bm._create_branch(neon_project, test_branch_name, parent_branch["id"])
print(f"[dispatch]   Parent         : {parent_label}", flush=True)
print(f"[dispatch]   Created branch : {test_branch_id}", flush=True)
print(f"[dispatch]   Branch name    : {test_branch_name}", flush=True)

if not conn_str or not (conn_str.startswith("postgresql://") or conn_str.startswith("postgres://")):
    print(f"[dispatch] ERROR: invalid connection string from Neon: {conn_str!r}", file=sys.stderr, flush=True)
    bm._delete_branch(neon_project, test_branch_id)
    sys.exit(1)

os.environ["NEON_DATABASE_URL"] = conn_str
print("[dispatch]   NEON_DATABASE_URL → test branch", flush=True)
print(flush=True)

# ---------------------------------------------------------------------------
# Step 2 — deferred mechanism imports (engine binds to URL set above)
# ---------------------------------------------------------------------------

from alembic import command as alembic_command       # noqa: E402
from alembic.config import Config as AlembicConfig   # noqa: E402

from core.db import get_session                      # noqa: E402
from core.output_naming import generate_filename     # noqa: E402
from mechanisms.ledger_export import run_ledger_export  # noqa: E402

# Only import mechanism modules for selected passes
if "3a" in PASSES:
    import mechanisms.source_capture as sc               # noqa: E402
    import mechanisms.row_lens_source_reanalysis as rlsra  # noqa: E402
if "3b" in PASSES:
    import mechanisms.cci_construction as cci            # noqa: E402
if "3c" in PASSES:
    import mechanisms.domain_derivation as dd            # noqa: E402
if "3d" in PASSES:
    import mechanisms.requirement_derivation as rd       # noqa: E402
if "3e" in PASSES:
    from mechanisms.requirement_matching.service import match_row  # noqa: E402

# ---------------------------------------------------------------------------
# Step 3 — schema migration (idempotent)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[dispatch] Applying schema migrations…", flush=True)
print(SEP, flush=True)

_cfg = AlembicConfig(str(SYSENGAGE_DIR / "alembic.ini"))
_cfg.set_main_option("script_location", str(SYSENGAGE_DIR / "alembic"))
alembic_command.upgrade(_cfg, "head")
print("[dispatch] Schema up to date.", flush=True)
print(flush=True)

# ---------------------------------------------------------------------------
# Step 4 — run passes in order
# ---------------------------------------------------------------------------

VERIFICATION_OUTPUTS.mkdir(parents=True, exist_ok=True)
all_ok = True

for pass_code in PASSES:
    print(SEP, flush=True)
    print(f"[dispatch] ──── Pass {pass_code} ────", flush=True)
    print(SEP, flush=True)

    # ── 3a: Source Capture + RLSRA ────────────────────────────────────────
    if pass_code == "3a":
        # SC runs once (all rows)
        if not SOURCE_DOC:
            print("[dispatch] ERROR: pass 3a requires --source-doc.", file=sys.stderr, flush=True)
            all_ok = False
        else:
            doc_path = VERIFICATION_INPUTS / SOURCE_DOC
            if not doc_path.exists():
                print(f"[dispatch] ERROR: source doc not found: {doc_path}", file=sys.stderr, flush=True)
                all_ok = False
            else:
                print(f"[dispatch] SC — {doc_path.name}", flush=True)
                try:
                    sc_result = sc.run_source_capture(
                        doc_path,
                        project_id=PROJECT_ID,
                        practitioner_id=PRACTITIONER_ID,
                        read_mode="Full",
                        segmentation_policy="default",
                    )
                    print(f"[dispatch]   SC status   = {sc_result.execution_status}", flush=True)
                    print(f"[dispatch]   sources     = {sc_result.source_count}", flush=True)
                    print(f"[dispatch]   segments    = {sc_result.segment_count}", flush=True)
                    if sc_result.execution_status not in (
                        "Completed", "CompletedWithWarnings", "Success", "PartialSuccess"
                    ):
                        print(f"[dispatch]   SC FAILED: {sc_result.failure_reason}", file=sys.stderr, flush=True)
                        all_ok = False
                except Exception as exc:
                    import traceback
                    print(f"[dispatch] SC EXCEPTION: {exc}", file=sys.stderr, flush=True)
                    traceback.print_exc()
                    all_ok = False

        if not all_ok:
            print(flush=True)
            continue

        # RLSRA runs per row
        for row in ROWS:
            print(f"[dispatch] RLSRA Row {row}…", flush=True)
            try:
                r = rlsra.run(project_id=PROJECT_ID, practitioner_id=PRACTITIONER_ID, row_ref=row)
                rld = r.get("row_lens_data", {})
                print(f"[dispatch]   status   = {r['execution_status']}", flush=True)
                print(f"[dispatch]   signals  = {rld.get('signal_count','?')}", flush=True)
                if r["execution_status"] not in (
                    "Completed", "CompletedWithWarnings", "Success", "PartialSuccess"
                ):
                    all_ok = False
            except Exception as exc:
                import traceback
                print(f"[dispatch] RLSRA Row {row} EXCEPTION: {exc}", file=sys.stderr, flush=True)
                traceback.print_exc()
                all_ok = False

    # ── 3b: CCI Construction ───────────────────────────────────────────────
    elif pass_code == "3b":
        for row in ROWS:
            print(f"[dispatch] CCI Row {row}…", flush=True)
            try:
                r = cci.run(project_id=PROJECT_ID, practitioner_id=PRACTITIONER_ID,
                            row_ref=row, skip_deduplication=False)
                cd = r["cci_data"]
                print(f"[dispatch]   status       = {r['execution_status']}", flush=True)
                print(f"[dispatch]   ccis_created = {cd['ccis_created']}", flush=True)
                print(f"[dispatch]   ccis_merged  = {cd['ccis_merged']}", flush=True)
                if r["execution_status"] not in (
                    "Completed", "CompletedWithWarnings", "Success", "PartialSuccess"
                ):
                    all_ok = False
            except Exception as exc:
                import traceback
                print(f"[dispatch] CCI Row {row} EXCEPTION: {exc}", file=sys.stderr, flush=True)
                traceback.print_exc()
                all_ok = False

    # ── 3c: Domain Derivation ──────────────────────────────────────────────
    elif pass_code == "3c":
        for row in ROWS:
            print(f"[dispatch] DD Row {row}…", flush=True)
            try:
                r = dd.run(project_id=PROJECT_ID, practitioner_id=PRACTITIONER_ID, row_ref=row)
                md = r["mechanism_data"]
                print(f"[dispatch]   status          = {r['execution_status']}", flush=True)
                print(f"[dispatch]   domains_produced= {md.get('domain_count_produced','?')}", flush=True)
                if r["execution_status"] not in (
                    "Completed", "CompletedWithWarnings", "Success", "PartialSuccess"
                ):
                    all_ok = False
            except Exception as exc:
                import traceback
                print(f"[dispatch] DD Row {row} EXCEPTION: {exc}", file=sys.stderr, flush=True)
                traceback.print_exc()
                all_ok = False

    # ── 3d: Requirement Derivation ─────────────────────────────────────────
    elif pass_code == "3d":
        for row in ROWS:
            print(f"[dispatch] RD Row {row}…", flush=True)
            try:
                r = rd.run_requirement_derivation(
                    project_id=PROJECT_ID, practitioner_id=PRACTITIONER_ID, row_ref=row)
                print(f"[dispatch]   status                    = {r['execution_status']}", flush=True)
                print(f"[dispatch]   requirement_count_produced= {r.get('requirement_count_produced','?')}", flush=True)
                if r["execution_status"] not in (
                    "Completed", "CompletedWithWarnings", "Success", "PartialSuccess"
                ):
                    all_ok = False
            except Exception as exc:
                import traceback
                print(f"[dispatch] RD Row {row} EXCEPTION: {exc}", file=sys.stderr, flush=True)
                traceback.print_exc()
                all_ok = False

    # ── 3e: Requirement Matching ───────────────────────────────────────────
    elif pass_code == "3e":
        for row in ROWS:
            if row == 1:
                print(f"[dispatch] RM Row 1 SKIP — Row 1 has no parent row to match against.", flush=True)
                continue
            print(f"[dispatch] RM Row {row}…", flush=True)
            try:
                r = match_row(row, PROJECT_ID)
                print(f"[dispatch]   refine_count    = {r.get('refine_count','?')}", flush=True)
                print(f"[dispatch]   no_match_count  = {r.get('no_match_count','?')}", flush=True)
                print(f"[dispatch]   flagged_count   = {r.get('flagged_count','?')}", flush=True)
            except Exception as exc:
                import traceback
                print(f"[dispatch] RM Row {row} EXCEPTION: {exc}", file=sys.stderr, flush=True)
                traceback.print_exc()
                all_ok = False

    print(flush=True)

# ---------------------------------------------------------------------------
# Step 5 — ledger export
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[dispatch] Exporting ledger…", flush=True)
print(SEP, flush=True)

max_pass = PASSES[-1]
max_row = max(ROWS)
basename = generate_filename(
    project_id=PROJECT_CODE,
    phase=3,
    pass_=max_pass.replace("3", "3"),  # e.g. "3c"
    row=max_row,
    out_dir=str(VERIFICATION_OUTPUTS),
)
session = get_session()
try:
    export_result = run_ledger_export(project_id=PROJECT_ID, session=session)
finally:
    session.close()

ledger_path = VERIFICATION_OUTPUTS / basename
with open(ledger_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(export_result.json_str)

ledger = export_result.ledger
n_elements  = len(ledger.get("elements", []))
n_registers = len(ledger.get("register_index", []))
hash_prefix = ledger.get("content_hash", {}).get("hash", "")[:16]

print(f"[dispatch] Ledger written : {basename}", flush=True)
print(f"[dispatch]   Elements    : {n_elements}", flush=True)
print(f"[dispatch]   Registers   : {n_registers}", flush=True)
print(f"[dispatch]   Hash        : {hash_prefix}…", flush=True)
print(flush=True)

# ---------------------------------------------------------------------------
# Step 6 — clean up test branch (leave alive — user can inspect / snapshot)
# ---------------------------------------------------------------------------

if test_branch_name:
    print(SEP, flush=True)
    print(f"[dispatch] Test branch still alive: {test_branch_name}", flush=True)
    print("[dispatch] To delete:", flush=True)
    print(f"  python sysengage/scripts/branch_manager.py delete_test_branch --branch {test_branch_name}", flush=True)
    print(SEP, flush=True)

print(flush=True)
print(f"[dispatch] {'COMPLETE' if all_ok else 'COMPLETE WITH ERRORS'} — {PROJECT_ID}  passes={PASSES}  rows={ROWS}", flush=True)

if not all_ok:
    sys.exit(1)
