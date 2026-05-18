"""
run_row1_cci_e2e.py — Phase 3b CCI Construction E2E runner for ROW1_E2E.

Runs CCI Construction for rows 1-5 sequentially with skip_deduplication=True,
then exports the row 5 ledger using the output naming convention.

Invocation (from workspace root):
    python -u sysengage/run_row1_cci_e2e.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import mechanisms.cci_construction as cci
from core.db import get_session
from core.output_naming import generate_filename
from mechanisms.ledger_export import run_ledger_export

PROJECT_ID = "ROW1_E2E"
PROJECT_CODE = "ROW1"
PRACTITIONER_ID = "SH001"
ROWS = [1, 2, 3, 4, 5]
OUT_DIR = Path(__file__).parent.parent / "verification_outputs"

print(f"[runner] Starting Phase 3b CCI Construction for {PROJECT_ID}", flush=True)
print(f"[runner] skip_deduplication=True  rows={ROWS}", flush=True)
print(flush=True)

results: dict[int, dict] = {}

for row in ROWS:
    print(f"[runner] --- Row {row} ---", flush=True)
    try:
        result = cci.run(
            project_id=PROJECT_ID,
            practitioner_id=PRACTITIONER_ID,
            row_ref=row,
            skip_deduplication=True,
        )
        cd = result["cci_data"]
        print(f"[runner]   pass_id={result['pass_id']}", flush=True)
        print(f"[runner]   ccis_created={cd['ccis_created']}  ccis_merged={cd['ccis_merged']}", flush=True)
        print(f"[runner]   status={result['execution_status']}", flush=True)
        results[row] = result
    except Exception as exc:
        print(f"[runner]   ERROR row {row}: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

print(flush=True)
print("[runner] All rows complete. Summary:", flush=True)
total = 0
for row, r in sorted(results.items()):
    n = r["cci_data"]["ccis_created"]
    total += n
    print(f"[runner]   R{row}: {n} CCIs  ({r['pass_id']}  {r['execution_status']})", flush=True)
print(f"[runner]   Total CCIs: {total}", flush=True)

print(flush=True)
print("[runner] Exporting row 5 ledger (naming convention)...", flush=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
basename = generate_filename(
    project_id=PROJECT_CODE,
    phase="03",
    pass_="3b",
    row="5",
    out_dir=str(OUT_DIR),
)
session = get_session()
try:
    export_result = run_ledger_export(project_id=PROJECT_ID, session=session)
finally:
    session.close()

json_path = OUT_DIR / basename
with open(json_path, "w", encoding="utf-8", newline="\n") as f:
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
print("[runner] Done.", flush=True)
