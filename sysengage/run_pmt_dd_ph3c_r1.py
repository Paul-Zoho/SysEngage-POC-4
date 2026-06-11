"""
run_pmt_dd_ph3c_r1.py — Pass 3c Domain Derivation for PMT_E2E, Row 1 only.

Runs Domain Derivation for Row 1 of the PMT_E2E project and exports the
full canonical ledger JSON.

Usage (main branch):
  python -u sysengage/run_pmt_dd_ph3c_r1.py

Usage (test branch — set NEON_DATABASE_URL before running):
  NEON_DATABASE_URL=<branch_conn_str> python -u sysengage/run_pmt_dd_ph3c_r1.py

Schema migration is applied automatically via alembic upgrade head before
the run — safe on both main branch (no-op if already at head) and on any
test branch cloned from a snapshot that predates recent migrations.

Per replit.md: project-specific runner — does not modify the canonical
all-rows runner (run_pmt_dd_ph3c.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

import mechanisms.domain_derivation as dd
from core.db import get_session
from core.output_naming import generate_filename
from mechanisms.ledger_export import run_ledger_export

PROJECT_ID = "PMT_E2E"
PROJECT_CODE = "PMT"
PRACTITIONER_ID = "SH001"
ROW = 1
OUT_DIR = Path(__file__).parent.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Schema migration — bring the target DB to the current migration head.
# Idempotent: no-op if already at head. Essential for test branches cloned
# from snapshots that pre-date recent migrations (e.g. snap_ph03_3b_AllProjects
# sits at migration 008; current head is 016+).
# ---------------------------------------------------------------------------
print("[runner] Applying schema migrations (alembic upgrade head)...", flush=True)
_alembic_cfg = AlembicConfig(str(Path(__file__).parent / "alembic.ini"))
alembic_command.upgrade(_alembic_cfg, "head")
print("[runner] Schema up to date.", flush=True)
print(flush=True)

# ---------------------------------------------------------------------------
# Domain Derivation run
# ---------------------------------------------------------------------------
print(f"[runner] Pass 3c Domain Derivation — {PROJECT_ID}  Row {ROW}", flush=True)
print(flush=True)

try:
    result = dd.run(
        project_id=PROJECT_ID,
        practitioner_id=PRACTITIONER_ID,
        row_ref=ROW,
    )
except Exception as exc:
    print(f"[runner] EXCEPTION: {exc}", file=sys.stderr, flush=True)
    sys.exit(1)

md = result["mechanism_data"]
status = result["execution_status"]
ok = status in ("Success", "PartialSuccess")

print(f"  pass_id               = {result['pass_id']}", flush=True)
print(f"  execution_status      = {status}", flush=True)
print(f"  scenario              = {md.get('scenario')}", flush=True)
print(f"  cci_count_input       = {md.get('cci_count_input')}", flush=True)
print(f"  domain_count_produced = {md.get('domain_count_produced')}", flush=True)
print(f"  domain_count_retired  = {md.get('domain_count_retired')}", flush=True)
print(f"  downstream_rerun_req  = {md.get('downstream_rerun_required')}", flush=True)
print(f"  large_cci_advisory    = {md.get('large_cci_set_advisory')}", flush=True)

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
        print(f"    {a.get('ci_id')}  appears in {a.get('domain_count')} domains", flush=True)

print(flush=True)
print("  Domains produced:", flush=True)
for d in md.get("domains_produced", []):
    print(
        f"    {d['domain_id']}  {d['name']!r}  "
        f"{d.get('cci_ref_count', '?')} CCIs  "
        f"cross-cutting={d.get('cross_cutting_cci_count', 0)}",
        flush=True,
    )
print(flush=True)

if not ok:
    print(f"[runner] Row {ROW} failed — skipping ledger export.", file=sys.stderr, flush=True)
    sys.exit(1)

# Export full ledger (covers all rows committed so far; named after Row 1 per convention)
print("[runner] Exporting ledger...", flush=True)
basename = generate_filename(
    project_id=PROJECT_CODE,
    phase=3,
    pass_="3c",
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

print(f"[runner] Ledger written : {basename}", flush=True)
print(f"[runner]   Elements     : {n_elements}", flush=True)
print(f"[runner]   Registers    : {n_registers}", flush=True)
print(f"[runner]   Hash         : {hash_prefix}...", flush=True)
print(flush=True)
print("[runner] Row 1 completed successfully.", flush=True)
