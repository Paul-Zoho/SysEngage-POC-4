"""
run_pmt_rd_r5_rerun.py — Re-run RD Pass 3d Row 5 on the existing test branch.

Reuses branch test_PMT_ph03_3e_R5_Launcher_20260610_151452 (all upstream
SC → RLSRA → CCI → DD state intact).  Fetches the live connection string
from the Neon API, runs Requirement Derivation for PMT_E2E Row 5, and
exports a JSON ledger.

Architecture note:
  core/db.py reads NEON_DATABASE_URL at module import time.  NEON_DATABASE_URL
  must be set in os.environ BEFORE any db-dependent module is imported.
  Do not reorder Steps 1–3.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SYSENGAGE_DIR = Path(__file__).parent
sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))
import branch_manager as bm  # noqa: E402

BRANCH_NAME    = "test_PMT_ph03_3e_R3-4-5_Launcher_20260610_191708"
PROJECT_ID     = "PMT_E2E"
PROJECT_CODE   = "PMT"
PRACTITIONER_ID = "SH001"
ROW            = 5

OUT_DIR = SYSENGAGE_DIR.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEP = "=" * 65

# ── Step 1: Locate existing branch and obtain connection string ────────────────
print(SEP, flush=True)
print(f"[orchestrator] Re-run RD Row {ROW} on existing branch: {BRANCH_NAME}", flush=True)
print(SEP, flush=True)

neon_project = bm._get_project_id()
branch = bm._find_branch_by_name(neon_project, BRANCH_NAME)
if not branch:
    print(
        f"[orchestrator] ERROR: branch '{BRANCH_NAME}' not found in Neon.",
        file=sys.stderr, flush=True,
    )
    sys.exit(1)

branch_id = branch["id"]
print(f"[orchestrator] Branch found : id={branch_id}", flush=True)

# Get connection string via Neon API (avoids fragile regex reconstruction)
import requests  # noqa: E402
api_key = os.environ["NEON_API_KEY"]
headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

# Find the endpoint for this branch
ep_resp = requests.get(
    f"https://console.neon.tech/api/v2/projects/{neon_project}/endpoints",
    headers=headers,
)
ep_resp.raise_for_status()
endpoints = ep_resp.json().get("endpoints", [])
endpoint = next((e for e in endpoints if e.get("branch_id") == branch_id), None)
if not endpoint:
    print(
        f"[orchestrator] ERROR: no endpoint found for branch {branch_id}.",
        file=sys.stderr, flush=True,
    )
    sys.exit(1)

endpoint_id = endpoint["id"]
uri_resp = requests.get(
    f"https://console.neon.tech/api/v2/projects/{neon_project}/connection_uri",
    headers=headers,
    params={
        "branch_id": branch_id,
        "endpoint_id": endpoint_id,
        "database_name": "neondb",
        "role_name": "neondb_owner",
    },
)
uri_resp.raise_for_status()
conn_str = uri_resp.json()["uri"]

if not conn_str or not (
    conn_str.startswith("postgresql://") or conn_str.startswith("postgres://")
):
    print(
        f"[orchestrator] ERROR: invalid connection string: {conn_str!r}",
        file=sys.stderr, flush=True,
    )
    sys.exit(1)

print(f"[orchestrator] Connection   : {conn_str[:50]}…", flush=True)
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

# ── Step 5: Run Pass 3d Row 5 ─────────────────────────────────────────────────
print(SEP, flush=True)
print(f"[orchestrator] Pass 3d Requirement Derivation — {PROJECT_ID}  Row {ROW}", flush=True)
print(SEP, flush=True)

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
ok = status in ("Completed", "CompletedWithWarnings")

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
    print("  type_distribution:", flush=True)
    for rtype, count in sorted(type_dist.items()):
        print(f"    {rtype}: {count}", flush=True)

seed_cov = result.get("seed_coverage", {})
if seed_cov:
    print(f"  seed_coverage               = {seed_cov}", flush=True)

warnings = result.get("execution_warnings", [])
if warnings:
    from collections import Counter
    wtype_counts = Counter(w.get("type", "?") for w in warnings)
    print(f"  execution_warnings ({len(warnings)} total):", flush=True)
    for wtype, cnt in sorted(wtype_counts.items()):
        print(f"    {cnt:3d} x {wtype}", flush=True)

orphans = result.get("orphaned_ccis", [])
if orphans:
    print(f"  WARNING orphaned CCIs: {orphans}", flush=True)

print(flush=True)

if not ok:
    print(
        f"[orchestrator] Run FAILED with status {status!r} — skipping ledger export.",
        file=sys.stderr, flush=True,
    )
    sys.exit(1)

# ── Step 6: Export ledger ──────────────────────────────────────────────────────
print("[orchestrator] Exporting ledger…", flush=True)
basename = generate_filename(
    project_id=PROJECT_CODE,
    phase=3,
    pass_="3e",
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
print(SEP, flush=True)
print(f"[orchestrator] Pass 3d Row {ROW} re-run COMPLETE.", flush=True)
print(f"[orchestrator] Branch still alive: {BRANCH_NAME}", flush=True)
print("[orchestrator] Delete when done:", flush=True)
print(
    f"  python sysengage/scripts/branch_manager.py delete_test_branch "
    f"--branch {BRANCH_NAME}",
    flush=True,
)
print(SEP, flush=True)
