"""
run_pmt_dd_ph3c.py — Pass 3c Domain Derivation for PMT_E2E, all rows.

Runs Domain Derivation for rows 1–5 of the PMT_E2E project in order.
Each row is an independent dd.run() call; the orchestrator builds on
committed state from the prior row automatically.

Usage:
  python -u sysengage/run_pmt_dd_ph3c.py

Expects NEON_DATABASE_URL to point at the correct branch (test or main).
Per replit.md: project-specific runner — does not modify the canonical E2E runner.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import mechanisms.domain_derivation as dd
from core.output_naming import generate_filename

PROJECT_ID = "PMT_E2E"
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

    out_path = OUT_DIR / generate_filename(
        project_id="PMT",
        phase=3,
        pass_="3c",
        row=row,
        out_dir=str(OUT_DIR),
        ext="json",
    )
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  output → {out_path.name}", flush=True)
    print(flush=True)

print(flush=True)
if all_ok:
    print("[runner] All rows completed successfully.", flush=True)
else:
    print("[runner] One or more rows failed — check output above.", file=sys.stderr, flush=True)
    sys.exit(1)
