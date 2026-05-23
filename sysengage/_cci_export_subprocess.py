"""
_cci_export_subprocess.py — Ledger export subprocess worker.

Called by run_pmt_cci_r1_branch_test.py with NEON_DATABASE_URL set to a test branch.
Not intended to be run directly.

Usage:
    python -u sysengage/_cci_export_subprocess.py --out /path/to/output.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.db import get_session
from mechanisms.ledger_export import run_ledger_export

PROJECT_ID = "PMT_E2E"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output JSON file path")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[export-worker] Exporting ledger for {PROJECT_ID}...", flush=True)

    session = get_session()
    try:
        export_result = run_ledger_export(project_id=PROJECT_ID, session=session)
    finally:
        session.close()

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(export_result.json_str)

    ledger = export_result.ledger
    n_elements = len(ledger.get("elements", []))
    n_registers = len(ledger.get("register_index", []))
    hash_prefix = ledger.get("content_hash", {}).get("hash", "")[:16]

    print(f"[export-worker] Written: {out_path.name}", flush=True)
    print(f"[export-worker]   Elements:  {n_elements}", flush=True)
    print(f"[export-worker]   Registers: {n_registers}", flush=True)
    print(f"[export-worker]   Hash:      {hash_prefix}...", flush=True)


if __name__ == "__main__":
    main()
