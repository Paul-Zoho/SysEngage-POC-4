"""
run_pmt_dd_ph3c.py — Pass 3c Domain Derivation for PMT_E2E, all rows.

Runs Domain Derivation for rows 1–5 of the PMT_E2E project in order.
Each row is an independent dd.run() call; the orchestrator builds on
committed state from the prior row automatically.

After all rows complete, exports the full canonical ledger for the project
(same pattern as run_pmt_cci_r1.py / run_row1_cci_e2e.py).

Usage:
  NEON_DATABASE_URL="<branch-url>" python -u sysengage/run_pmt_dd_ph3c.py

Expects NEON_DATABASE_URL to point at the correct branch (test or main).
Per replit.md: project-specific runner — does not modify the canonical E2E runner.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import mechanisms.domain_derivation as dd
from core.db import get_session
from core.output_naming import generate_filename
from mechanisms.ledger_export import run_ledger_export

PROJECT_ID = "PMT_E2E"
PROJECT_CODE = "PMT"
PRACTITIONER_ID = "SH001"
ROWS = [1, 2, 3, 4, 5]
OUT_DIR = Path(__file__).parent.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(
    f"[runner] Pass 3c Domain Derivation — {PROJECT_ID}  rows {ROWS}",
    flush=True,
)
print(flush=True)

all_ok = True

for row in ROWS:
    print(f"{'='*60}", flush=True)
    print(f"[runner] Row {row}", flush=True)
    print(f"{'='*60}", flush=True)

    try:
        result = dd.run(
            project_id=PROJECT_ID,
            practitioner_id=PRACTITIONER_ID,
            row_ref=row,
        )
    except Exception as exc:
        print(f"[runner] Row {row} EXCEPTION: {exc}", file=sys.stderr, flush=True)
        all_ok = False
        continue

    md = result["mechanism_data"]
    status = result["execution_status"]
    ok = status in ("Completed", "CompletedWithWarnings")
    if not ok:
        all_ok = False

    print(f"  pass_id              = {result['pass_id']}", flush=True)
    print(f"  execution_status     = {status}", flush=True)
    print(f"  scenario             = {md.get('scenario')}", flush=True)
    print(f"  cci_count_input      = {md.get('cci_count_input')}", flush=True)
    print(f"  domain_count_produced= {md.get('domain_count_produced')}", flush=True)
    print(f"  domain_count_retired = {md.get('domain_count_retired')}", flush=True)
    print(
        f"  downstream_rerun_req = {md.get('downstream_rerun_required')}",
        flush=True,
    )

    orphans = md.get("orphaned_ccis_after_repair", [])
    if orphans:
        print(f"  WARNING orphaned CCIs: {orphans}", flush=True)

    for d in md.get("domains_produced", []):
        print(
            f"    {d['domain_id']}  {d['name']!r}  "
            f"{d['cci_ref_count']} CCIs  "
            f"cross-cutting={d.get('cross_cutting_cci_count', 0)}",
            flush=True,
        )
    print(flush=True)

if not all_ok:
    print(
        "[runner] One or more rows failed — skipping ledger export.",
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)

# Full ledger export — one canonical file covering all rows (row 5 naming convention)
print("[runner] Exporting full ledger...", flush=True)
basename = generate_filename(
    project_id=PROJECT_CODE,
    phase=3,
    pass_="3c",
    row=5,
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

print(f"[runner] Ledger written: {basename}", flush=True)
print(f"[runner]   Elements:  {n_elements}", flush=True)
print(f"[runner]   Registers: {n_registers}", flush=True)
print(f"[runner]   Hash:      {hash_prefix}...", flush=True)
print(flush=True)
print("[runner] All rows completed successfully.", flush=True)
