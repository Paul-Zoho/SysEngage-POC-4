"""
run_pmt_cci_r1.py — Phase 3b CCI Construction for PMT_E2E, Row 1, no deduplication.

Fresh run — no idempotency skip guard (intentional for test purposes).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import mechanisms.cci_construction as cci
from core.db import get_session
from core.output_naming import generate_filename
from mechanisms.ledger_export import run_ledger_export

PROJECT_ID = "PMT_E2E"
PROJECT_CODE = "PMT"
PRACTITIONER_ID = "SH001"
ROW = 1
OUT_DIR = Path(__file__).parent.parent / "verification_outputs"

print(f"[runner] Phase 3b CCI Construction — {PROJECT_ID}  Row {ROW}  skip_dedup=False", flush=True)
print(flush=True)

try:
    result = cci.run(
        project_id=PROJECT_ID,
        practitioner_id=PRACTITIONER_ID,
        row_ref=ROW,
        skip_deduplication=False,
    )
except Exception as exc:
    print(f"[runner] FAILED: {exc}", file=sys.stderr, flush=True)
    sys.exit(1)

cd = result["cci_data"]
print(f"[runner] pass_id          = {result['pass_id']}", flush=True)
print(f"[runner] execution_status = {result['execution_status']}", flush=True)
print(f"[runner] ccis_created     = {cd['ccis_created']}", flush=True)
print(f"[runner] ccis_merged      = {cd['ccis_merged']}", flush=True)
print(f"[runner] batches_processed= {cd['batches_processed']}", flush=True)
print(f"[runner] batches_failed   = {cd['batches_failed']}", flush=True)
print(flush=True)

print("[runner] Exporting ledger...", flush=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
basename = generate_filename(
    project_id=PROJECT_CODE,
    phase="03",
    pass_="3b",
    row=str(ROW),
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
