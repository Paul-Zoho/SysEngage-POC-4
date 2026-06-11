"""
run_row1_cci_e2e.py — Phase 3b CCI Construction E2E runner for ROW1_E2E.

Runs CCI Construction for rows 1-5 sequentially with skip_deduplication=True.
Idempotent: skips any row that already has a Completed/CompletedWithWarnings
pass to prevent double-runs caused by bash interrupt + subprocess survival.

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
from sqlalchemy import text

PROJECT_ID = "ROW1_E2E"
PROJECT_CODE = "ROW"
PRACTITIONER_ID = "SH001"
ROWS = [1]
OUT_DIR = Path(__file__).parent.parent / "verification_outputs"


def already_completed(project_id: str, row_ref: int) -> str | None:
    """
    Return existing pass_id if a Completed/CompletedWithWarnings CCIConstruction
    pass already exists for this project + row, or None if the row should run.
    """
    scope = f"All Row {row_ref} Signals"
    s = get_session()
    try:
        row = s.execute(
            text(
                """
                SELECT pass_id FROM analysis_pass
                WHERE project_id = :p
                  AND mechanism IN ('CCIConstruction', 'CellContentItemConstruction')
                  AND evaluated_scope = :scope
                  AND execution_status IN ('Completed', 'CompletedWithWarnings', 'Success', 'PartialSuccess')
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"p": project_id, "scope": scope},
        ).fetchone()
        return row[0] if row else None
    finally:
        s.close()


print(f"[runner] Starting Phase 3b CCI Construction for {PROJECT_ID}", flush=True)
print(f"[runner] skip_deduplication=True  rows={ROWS}", flush=True)
print(flush=True)

results: dict[int, dict] = {}

for row in ROWS:
    existing = already_completed(PROJECT_ID, row)
    if existing:
        print(f"[runner] --- Row {row} --- SKIP (pass {existing} already Completed)", flush=True)
        results[row] = {"skipped": True, "pass_id": existing}
        continue

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
for row_ref, r in sorted(results.items()):
    if r.get("skipped"):
        print(f"[runner]   R{row_ref}: skipped ({r['pass_id']})", flush=True)
    else:
        n = r["cci_data"]["ccis_created"]
        total += n
        print(f"[runner]   R{row_ref}: {n} CCIs  ({r['pass_id']}  {r['execution_status']})", flush=True)
print(f"[runner]   New CCIs this run: {total}", flush=True)

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
