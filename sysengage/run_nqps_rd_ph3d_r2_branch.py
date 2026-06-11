"""
run_nqps_rd_ph3d_r2_branch.py — NQPS Pass 3d Requirement Derivation, Row 2.

Creates a disposable test branch from snap_ph03_3c_AllProjects, applies
schema migrations, runs Requirement Derivation for NQPS_E2E Row 2, exports
a JSON ledger, and leaves the branch alive for analysis.

Delete when done:
  python sysengage/scripts/branch_manager.py delete_test_branch \\
    --branch test_ALL_ph03_3c_R2_Ph3d_RD_NQPS_R2
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SYSENGAGE_DIR = Path(__file__).parent

sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))
import branch_manager as bm  # noqa: E402

SNAPSHOT = "snap_ph03_3c_AllProjects"
TEST_BRANCH_NAME = "test_ALL_ph03_3c_R2_Ph3d_RD_NQPS_R2"

PROJECT_ID = "NQPS_E2E"
PROJECT_CODE = "NQPS"
PRACTITIONER_ID = "SH001"
ROW = 2

OUT_DIR = SYSENGAGE_DIR.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Step 1: Create (or reuse) test branch ─────────────────────────────────────
print(f"[orchestrator] Preparing test branch: {TEST_BRANCH_NAME}", flush=True)
neon_project = bm._get_project_id()

existing = bm._find_branch_by_name(neon_project, TEST_BRANCH_NAME)
if existing:
    print(
        f"[orchestrator] Branch exists (id={existing['id']}) — deleting for clean run…",
        flush=True,
    )
    bm._delete_branch(neon_project, existing["id"])
    print("[orchestrator] Deleted.", flush=True)

print(f"[orchestrator] Creating branch from snapshot {SNAPSHOT!r}…", flush=True)
snap_branch = bm._find_branch_by_name(neon_project, SNAPSHOT)
if not snap_branch:
    print(
        f"[orchestrator] ERROR: snapshot branch '{SNAPSHOT}' not found in Neon.",
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)

branch_id, conn_str = bm._create_branch(neon_project, TEST_BRANCH_NAME, snap_branch["id"])
print(f"[orchestrator] Branch created : id={branch_id}", flush=True)
print(f"[orchestrator] Test branch    : {TEST_BRANCH_NAME}", flush=True)

if not conn_str or not (
    conn_str.startswith("postgresql://") or conn_str.startswith("postgres://")
):
    print(
        f"[orchestrator] ERROR: invalid connection string: {conn_str!r}",
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)

print(f"[orchestrator] Connection     : {conn_str[:50]}…", flush=True)
print(flush=True)

# ── Step 2: Inject URL BEFORE any db import ───────────────────────────────────
os.environ["NEON_DATABASE_URL"] = conn_str

# ── Step 3: Now import db-dependent modules ───────────────────────────────────
sys.path.insert(0, str(SYSENGAGE_DIR))

from alembic import command as alembic_command          # noqa: E402
from alembic.config import Config as AlembicConfig      # noqa: E402
import mechanisms.requirement_derivation as rd           # noqa: E402
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

# ── Step 5: Run Pass 3d Row 2 ─────────────────────────────────────────────────
print("=" * 60, flush=True)
print(f"[orchestrator] Pass 3d Requirement Derivation — {PROJECT_ID}  Row {ROW}", flush=True)
print("=" * 60, flush=True)

try:
    result = rd.run_requirement_derivation(
        project_id=PROJECT_ID,
        practitioner_id=PRACTITIONER_ID,
        row_ref=ROW,
    )
except Exception as exc:
    print(f"[orchestrator] EXCEPTION: {exc}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

status = result["execution_status"]
ok = status in ("Success", "PartialSuccess")

print(f"  pass_id                     = {result.get('pass_id')}", flush=True)
print(f"  execution_status            = {status}", flush=True)
print(f"  scenario                    = {result.get('scenario')}", flush=True)
print(f"  cci_count_input             = {result.get('cci_count_input')}", flush=True)
print(f"  domain_count                = {result.get('domain_count')}", flush=True)
print(f"  requirement_count_produced  = {result.get('requirement_count_produced')}", flush=True)
print(f"  requirement_count_retired   = {result.get('requirement_count_retired')}", flush=True)
print(f"  downstream_rerun_required   = {result.get('downstream_rerun_required')}", flush=True)

type_dist = result.get("requirement_type_distribution", {})
if type_dist:
    print(f"  type_distribution:", flush=True)
    for rtype, count in sorted(type_dist.items()):
        print(f"    {rtype}: {count}", flush=True)

orphans = result.get("orphaned_ccis", [])
if orphans:
    print(f"  WARNING orphaned CCIs: {orphans}", flush=True)

print(flush=True)

if not ok:
    print(
        f"[orchestrator] Run failed with status {status!r} — skipping ledger export.",
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)

# ── Step 6: Export ledger ──────────────────────────────────────────────────────
print("[orchestrator] Exporting ledger…", flush=True)
basename = generate_filename(
    project_id=PROJECT_CODE,
    phase=3,
    pass_="3d",
    row=ROW,
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

# ── Step 7: Summary ────────────────────────────────────────────────────────────
print("=" * 60, flush=True)
print("[orchestrator] Pass 3d Row 2 completed successfully.", flush=True)
print(f"[orchestrator] Test branch still alive: {TEST_BRANCH_NAME}", flush=True)
print("[orchestrator] Delete when done:", flush=True)
print(
    f"  python sysengage/scripts/branch_manager.py delete_test_branch "
    f"--branch {TEST_BRANCH_NAME}",
    flush=True,
)
