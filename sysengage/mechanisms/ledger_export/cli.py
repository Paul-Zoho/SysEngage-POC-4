"""
Ledger Export CLI.

Usage:
    python -m mechanisms.ledger_export.cli <project_id> [--out-dir <dir>]

Writes to --out-dir (default: verification_outputs at workspace root):
    <project_id>.ledger.json  — canonical JSON ledger (spec v2.12)
"""

from __future__ import annotations

import argparse
import os
import sys

# sysengage/ is three levels up from this file
_SYSENGAGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# workspace root is one level above sysengage/
_WORKSPACE_ROOT = os.path.dirname(_SYSENGAGE_ROOT)
_DEFAULT_OUT_DIR = os.path.join(_WORKSPACE_ROOT, "verification_outputs")

sys.path.insert(0, _SYSENGAGE_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a SysEngage project ledger to JSON + Markdown (spec v2.12)."
    )
    parser.add_argument("project_id", help="Project ID to export (e.g. PMT_E2E)")
    parser.add_argument(
        "--out-dir",
        default=_DEFAULT_OUT_DIR,
        help=f"Directory to write output files (default: {_DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--out-file",
        default=None,
        help="Override the output filename (basename only, written into --out-dir). "
             "Default: <project_id>.ledger.json",
    )
    args = parser.parse_args()

    project_id: str = args.project_id
    out_dir: str = args.out_dir

    os.makedirs(out_dir, exist_ok=True)

    from core.db import get_session
    from mechanisms.ledger_export import run_ledger_export

    print(f"[ledger-export] Loading project: {project_id!r}", flush=True)
    session = get_session()
    try:
        result = run_ledger_export(project_id=project_id, session=session)
    except ValueError as exc:
        print(f"[ledger-export] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()

    if args.out_file:
        json_path = os.path.join(out_dir, args.out_file)
    else:
        safe_id = project_id.replace("/", "_").replace("\\", "_")
        json_path = os.path.join(out_dir, f"{safe_id}.ledger.json")

    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(result.json_str)
    print(f"[ledger-export] JSON → {json_path}", flush=True)

    ledger = result.ledger
    n_elements = len(ledger.get("elements", []))
    n_registers = len(ledger.get("register_index", []))
    project_name = result.project_name
    hash_prefix = ledger.get("content_hash", {}).get("hash", "")[:16]

    print(
        f"\n[ledger-export] Export complete\n"
        f"  Project:   {project_name} ({project_id})\n"
        f"  Elements:  {n_elements}\n"
        f"  Registers: {n_registers}\n"
        f"  Hash:      {hash_prefix}...\n",
        flush=True,
    )


if __name__ == "__main__":
    main()
