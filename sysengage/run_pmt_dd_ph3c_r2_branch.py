"""
run_pmt_dd_ph3c_r2_branch.py — Self-contained PMT Pass 3c Row 1 + Row 2 test run.

Creates (or reuses) a disposable test branch from snap_ph03_3b_AllProjects,
applies schema migrations, runs Domain Derivation for Row 1 then Row 2, and
exports the ledger.  The test branch is left alive after the run for analysis;
delete it when done:

  python sysengage/scripts/branch_manager.py delete_test_branch \
    --branch test_ALL_ph03_3b_R5_Ph3c_DD_R1R2

This runner validates the v0.19 ROW_GUIDANCE["2"] structured guidance block
against PMT_E2E's Row 2 CCIs.

Architecture note:
  core/db.py reads NEON_DATABASE_URL at module import time.  This orchestrator
  imports branch_manager directly (no subprocess) to get the connection string
  as a Python string, then sets os.environ["NEON_DATABASE_URL"] BEFORE importing
  any db-dependent module.  Do not reorder those sections.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SYSENGAGE_DIR = Path(__file__).parent

# branch_manager lives in sysengage/scripts/
sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))
import branch_manager as bm  # noqa: E402

SNAPSHOT = "snap_ph03_3b_AllProjects"
SCENARIO = "Ph3c_DD_R1R2"
# Branch name produced by branch_manager naming convention:
# test_{project_code}_{phase}_{pass_}_R{row_num}_{scenario}
# snap_ph03_3b_AllProjects → project_id=ALL, phase=ph03, pass=3b, row=R5
TEST_BRANCH_NAME = f"test_ALL_ph03_3b_R5_{SCENARIO}"

PROJECT_ID = "PMT_E2E"
PROJECT_CODE = "PMT"
PRACTITIONER_ID = "SH001"
OUT_DIR = SYSENGAGE_DIR.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Step 1: Create a fresh test branch ────────────────────────────────────────
# Always delete-and-recreate so we get the connection URI directly from the
# Neon API response (reliable).  _build_conn_uri_for_branch uses a regex
# host-substitution on DATABASE_URL_MAIN that is fragile; the create-branch
# API path returns connection_uris[0].connection_uri directly.
print(f"[orchestrator] Preparing test branch: {TEST_BRANCH_NAME}", flush=True)
neon_project = bm._get_project_id()

existing = bm._find_branch_by_name(neon_project, TEST_BRANCH_NAME)
if existing:
    print(f"[orchestrator] Branch exists (id={existing['id']}) — deleting for clean run…",
          flush=True)
    bm._delete_branch(neon_project, existing["id"])
    print(f"[orchestrator] Deleted.", flush=True)

print(f"[orchestrator] Creating branch from snapshot {SNAPSHOT!r}…", flush=True)
snap_branch = bm._find_branch_by_name(neon_project, SNAPSHOT)
if not snap_branch:
    print(f"[orchestrator] ERROR: snapshot branch '{SNAPSHOT}' not found in Neon.",
          file=sys.stderr, flush=True)
    sys.exit(1)
branch_id, conn_str = bm._create_branch(neon_project, TEST_BRANCH_NAME, snap_branch["id"])
print(f"[orchestrator] Branch created: id={branch_id}", flush=True)

print(f"[orchestrator] Test branch : {TEST_BRANCH_NAME}", flush=True)

if not conn_str or not (conn_str.startswith("postgresql://") or conn_str.startswith("postgres://")):
    print(f"[orchestrator] ERROR: invalid connection string: {conn_str!r}",
          file=sys.stderr, flush=True)
    sys.exit(1)

print(f"[orchestrator] Connection  : {conn_str[:50]}…", flush=True)
print(flush=True)

# ── Step 2: Inject URL BEFORE any db import ───────────────────────────────────
os.environ["NEON_DATABASE_URL"] = conn_str

# ── Step 3: Now import db-dependent modules ───────────────────────────────────
sys.path.insert(0, str(SYSENGAGE_DIR))

from alembic import command as alembic_command          # noqa: E402
from alembic.config import Config as AlembicConfig      # noqa: E402
import mechanisms.domain_derivation as dd               # noqa: E402
from core.db import get_session                          # noqa: E402
from core.output_naming import generate_filename        # noqa: E402
from mechanisms.ledger_export import run_ledger_export  # noqa: E402

# ── Step 4: Schema migration ───────────────────────────────────────────────────
print("[orchestrator] Applying schema migrations (alembic upgrade head)…", flush=True)
_alembic_cfg = AlembicConfig(str(SYSENGAGE_DIR / "alembic.ini"))
_alembic_cfg.set_main_option("script_location", str(SYSENGAGE_DIR / "alembic"))
alembic_command.upgrade(_alembic_cfg, "head")
print("[orchestrator] Schema up to date.", flush=True)
print(flush=True)

# ── Step 5: Run Domain Derivation — Row 1, then Row 2 ─────────────────────────
all_ok = True

for row in [1, 2]:
    print(f"{'='*60}", flush=True)
    print(f"[orchestrator] Pass 3c Domain Derivation — {PROJECT_ID}  Row {row}", flush=True)
    print(f"{'='*60}", flush=True)

    try:
        result = dd.run(
            project_id=PROJECT_ID,
            practitioner_id=PRACTITIONER_ID,
            row_ref=row,
        )
    except Exception as exc:
        print(f"[orchestrator] Row {row} EXCEPTION: {exc}", file=sys.stderr, flush=True)
        all_ok = False
        continue

    md = result["mechanism_data"]
    status = result["execution_status"]
    ok = status in ("Completed", "CompletedWithWarnings")
    if not ok:
        all_ok = False

    print(f"  pass_id               = {result['pass_id']}", flush=True)
    print(f"  execution_status      = {status}", flush=True)
    print(f"  scenario              = {md.get('scenario')}", flush=True)
    print(f"  cci_count_input       = {md.get('cci_count_input')}", flush=True)
    print(f"  domain_count_produced = {md.get('domain_count_produced')}", flush=True)
    print(f"  domain_count_retired  = {md.get('domain_count_retired')}", flush=True)
    print(f"  downstream_rerun_req  = {md.get('downstream_rerun_required')}", flush=True)

    orphans = md.get("orphaned_ccis", [])
    if orphans:
        print(f"  WARNING orphaned CCIs : {orphans}", flush=True)

    repair = md.get("repair_prompt_issued")
    if repair:
        print(f"  repair_prompt_issued  = {repair}", flush=True)

    absorption = md.get("single_cci_absorption_issued")
    if absorption:
        print(f"  absorption_issued     = {absorption}", flush=True)
        for ab in md.get("absorptions", []):
            print(
                f"    absorbed {ab['ci_id']} from \"{ab['absorbed_from_domain_name']}\" "
                f"→ \"{ab['absorbed_into_domain_name']}\"",
                flush=True,
            )

    cc_advisories = md.get("cross_cutting_advisories", [])
    if cc_advisories:
        print(f"  cross_cutting_advisories ({len(cc_advisories)}):", flush=True)
        for a in cc_advisories:
            print(f"    {a.get('ci_id')}  appears in {a.get('domain_count')} domains",
                  flush=True)

    print(flush=True)
    print(f"  Domains produced:", flush=True)
    for d in md.get("domains_produced", []):
        print(
            f"    {d['domain_id']}  {d['name']!r}  "
            f"{d.get('cci_ref_count', '?')} CCIs  "
            f"cross-cutting={d.get('cross_cutting_cci_count', 0)}",
            flush=True,
        )
    print(flush=True)

if not all_ok:
    print("[orchestrator] One or more rows failed — skipping ledger export.",
          file=sys.stderr, flush=True)
    sys.exit(1)

# ── Step 6: Ledger export ──────────────────────────────────────────────────────
print("[orchestrator] Exporting ledger…", flush=True)
basename = generate_filename(
    project_id=PROJECT_CODE,
    phase=3,
    pass_="3c",
    row=2,
    out_dir=str(OUT_DIR),
)
session = get_session()
try:
    export_result = run_ledger_export(project_id=PROJECT_ID, session=session)
finally:
    session.close()

ledger_path = OUT_DIR / basename
with open(ledger_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(export_result.json_str)

ledger = export_result.ledger
n_elements = len(ledger.get("elements", []))
n_registers = len(ledger.get("register_index", []))
hash_prefix = ledger.get("content_hash", {}).get("hash", "")[:16]

print(f"[orchestrator] Ledger written  : {basename}", flush=True)
print(f"[orchestrator]   Elements      : {n_elements}", flush=True)
print(f"[orchestrator]   Registers     : {n_registers}", flush=True)
print(f"[orchestrator]   Hash          : {hash_prefix}…", flush=True)
print(flush=True)
print(f"[orchestrator] Test branch still alive: {TEST_BRANCH_NAME}", flush=True)
print( "[orchestrator] Delete when done:", flush=True)
print(f"  python sysengage/scripts/branch_manager.py delete_test_branch "
      f"--branch {TEST_BRANCH_NAME}", flush=True)
print(flush=True)
print("[orchestrator] Rows 1–2 completed successfully.", flush=True)
