"""
run_pmt_rd_ph3d_allrows_branch.py — PMT Pass 3d Requirement Derivation, Rows 1–5.

Creates one disposable test branch from snap_ph03_3c_AllProjects, applies
schema migrations, runs Requirement Derivation for PMT_E2E Rows 1–5 in
sequence, then exports a single project-wide JSON ledger.

Delete when done:
  python sysengage/scripts/branch_manager.py delete_test_branch \\
    --branch test_ALL_ph03_3c_Ph3d_RD_PMT_R1toR5
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SYSENGAGE_DIR = Path(__file__).parent

sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))
import branch_manager as bm  # noqa: E402

SNAPSHOT = "snap_ph03_3c_AllProjects"
TEST_BRANCH_NAME = "test_ALL_ph03_3c_Ph3d_RD_PMT_R1toR5"

PROJECT_ID = "PMT_E2E"
PROJECT_CODE = "PMT"
PRACTITIONER_ID = "SH001"
ROWS = [1, 2, 3, 4, 5]

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
from mechanisms.ledger_export import run_ledger_export  # noqa: E402

# ── Step 4: Schema migration ───────────────────────────────────────────────────
print("[orchestrator] Applying schema migrations (alembic upgrade head)…", flush=True)
_alembic_cfg = AlembicConfig(str(SYSENGAGE_DIR / "alembic.ini"))
_alembic_cfg.set_main_option("script_location", str(SYSENGAGE_DIR / "alembic"))
alembic_command.upgrade(_alembic_cfg, "head")
print("[orchestrator] Schema up to date.", flush=True)
print(flush=True)

# ── Step 5: Run Pass 3d Rows 1–5 in sequence ──────────────────────────────────
row_summaries: list[dict] = []
failed_rows: list[int] = []

for row in ROWS:
    print("=" * 60, flush=True)
    print(f"[orchestrator] Pass 3d — {PROJECT_ID}  Row {row}", flush=True)
    print("=" * 60, flush=True)

    try:
        result = rd.run_requirement_derivation(
            project_id=PROJECT_ID,
            practitioner_id=PRACTITIONER_ID,
            row_ref=row,
        )
    except Exception as exc:
        print(f"[orchestrator] EXCEPTION row {row}: {exc}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        failed_rows.append(row)
        continue

    status = result["execution_status"]
    ok = status in ("Success", "PartialSuccess", "Skipped")

    print(f"  execution_status           = {status}", flush=True)
    print(f"  scenario                   = {result.get('scenario')}", flush=True)
    print(f"  cci_count_input            = {result.get('cci_count_input')}", flush=True)
    print(f"  requirement_count_produced = {result.get('requirement_count_produced')}", flush=True)

    type_dist = result.get("requirement_type_distribution", {})
    if type_dist and any(v for v in type_dist.values()):
        parts = ", ".join(f"{t}: {c}" for t, c in sorted(type_dist.items()) if c)
        print(f"  type_distribution          = {{{parts}}}", flush=True)

    orphans = result.get("orphaned_ccis", [])
    if orphans:
        print(f"  WARNING orphaned CCIs: {orphans}", flush=True)

    print(flush=True)

    row_summaries.append({"row": row, "status": status, "result": result})
    if not ok:
        print(
            f"[orchestrator] Row {row} failed with status {status!r} — continuing.",
            file=sys.stderr,
            flush=True,
        )
        failed_rows.append(row)

# ── Step 6: Export combined project ledger ────────────────────────────────────
# Count existing all-rows files to derive run number.
prefix = f"{PROJECT_CODE}_Ph03_3d_RequirementDerivation_AllRows_Run"
existing_runs = [
    f for f in OUT_DIR.iterdir()
    if f.name.startswith(prefix) and f.suffix == ".json"
]
run_n = len(existing_runs) + 1
basename = f"{prefix}{run_n}.json"

print("[orchestrator] Exporting project ledger…", flush=True)
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
print(f"[orchestrator] Pass 3d Rows 1–5 complete — {PROJECT_ID}", flush=True)
for s in row_summaries:
    req = s["result"].get("requirement_count_produced", 0)
    print(f"  Row {s['row']}: {s['status']}  requirements={req}", flush=True)
if failed_rows:
    print(f"  FAILED rows: {failed_rows}", flush=True)
print(f"[orchestrator] Test branch still alive: {TEST_BRANCH_NAME}", flush=True)
print("[orchestrator] Delete when done:", flush=True)
print(
    f"  python sysengage/scripts/branch_manager.py delete_test_branch "
    f"--branch {TEST_BRANCH_NAME}",
    flush=True,
)
