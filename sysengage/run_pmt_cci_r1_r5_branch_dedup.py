"""
run_pmt_cci_r1_r5_branch_dedup.py — Branch-isolated CCI Construction, PMT Rows 1-5, dedup ON.

Workflow:
  1. Clone a fresh test branch from snap_PMT_ph03_3a_R1 (scenario Ph3b_Dedup_On)
  2. Run CCI Construction rows 1-5 with skip_deduplication=False against the branch
  3. Export one JSON ledger
  4. Delete the test branch

The runner subprocess (run_pmt_cci_r1_r5_dedup.py) is invoked with NEON_DATABASE_URL
set to the test branch connection string — the parent environment is never mutated.

Invocation (from workspace root):
    python -u sysengage/run_pmt_cci_r1_r5_branch_dedup.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SYSENGAGE = Path(__file__).parent
ROOT = SYSENGAGE.parent
sys.path.insert(0, str(SYSENGAGE))

from scripts.branch_manager import (
    _create_branch,
    _delete_branch,
    _find_branch_by_name,
    _get_project_id,
    _registry_get,
)

SNAP_NAME = "snap_PMT_ph03_3a_R1"
SCENARIO = "Ph3b_Dedup_On"
BRANCH_NAME = f"test_PMT_ph03_3a_R1_{SCENARIO}"
RUNNER = str(SYSENGAGE / "run_pmt_cci_r1_r5_dedup.py")


def banner(msg: str) -> None:
    print(f"\n{'─' * 60}", flush=True)
    print(f"  {msg}", flush=True)
    print(f"{'─' * 60}", flush=True)


def main() -> None:
    banner("PMT Rows 1-5  •  dedup ON  •  branch-isolated")
    print(f"[orchestrator] Snapshot : {SNAP_NAME}", flush=True)
    print(f"[orchestrator] Branch   : {BRANCH_NAME}", flush=True)
    print(f"[orchestrator] Runner   : {Path(RUNNER).name}", flush=True)

    neon_project = _get_project_id()
    print(f"[orchestrator] Neon project: {neon_project}", flush=True)

    # ── resolve snapshot branch ID ─────────────────────────────────────────────
    snap = _registry_get(SNAP_NAME)
    if snap:
        snap_branch_id = snap["neon_branch_id"]
        print(f"[orchestrator] Snapshot branch ID (registry): {snap_branch_id}", flush=True)
    else:
        neon_snap = _find_branch_by_name(neon_project, SNAP_NAME)
        if not neon_snap:
            print(
                f"ERROR: Snapshot '{SNAP_NAME}' not found in registry or Neon.",
                file=sys.stderr,
            )
            sys.exit(1)
        snap_branch_id = neon_snap["id"]
        print(f"[orchestrator] Snapshot branch ID (Neon lookup): {snap_branch_id}", flush=True)

    # ── create fresh test branch ───────────────────────────────────────────────
    banner(f"Creating test branch: {BRANCH_NAME}")
    existing = _find_branch_by_name(neon_project, BRANCH_NAME)
    if existing:
        print(f"[orchestrator] Branch already exists — deleting first ({existing['id']})", flush=True)
        _delete_branch(neon_project, existing["id"])

    branch_id, conn_uri = _create_branch(neon_project, BRANCH_NAME, snap_branch_id)
    print(f"[orchestrator] Test branch ready: id={branch_id}", flush=True)

    env = {**os.environ, "NEON_DATABASE_URL": conn_uri}

    # ── apply pending migrations to test branch ────────────────────────────────
    banner("Applying migrations to test branch (alembic upgrade head)")
    alembic_dir = str(SYSENGAGE)
    mig_result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env,
        cwd=alembic_dir,
        capture_output=False,
    )
    if mig_result.returncode != 0:
        print(
            f"[orchestrator] ERROR: alembic upgrade failed (code {mig_result.returncode})",
            file=sys.stderr,
            flush=True,
        )
        _delete_branch(neon_project, branch_id)
        sys.exit(mig_result.returncode)
    print(f"[orchestrator] Migrations applied.", flush=True)

    # ── run rows 1-5 dedup ON against test branch ──────────────────────────────
    banner("Running CCI Construction  rows 1-5  skip_dedup=False")


    result = subprocess.run(
        [sys.executable, "-u", RUNNER],
        env=env,
        capture_output=False,
    )

    if result.returncode != 0:
        print(
            f"[orchestrator] ERROR: runner exited with code {result.returncode}",
            file=sys.stderr,
            flush=True,
        )
        print(f"[orchestrator] Cleaning up test branch: {BRANCH_NAME}", flush=True)
        _delete_branch(neon_project, branch_id)
        sys.exit(result.returncode)

    # ── clean up test branch ───────────────────────────────────────────────────
    banner("Cleanup")
    print(f"[orchestrator] Deleting test branch: {BRANCH_NAME}", flush=True)
    _delete_branch(neon_project, branch_id)
    print(f"[orchestrator] Test branch deleted.", flush=True)

    banner("DONE")
    print("[orchestrator] JSON ledger written by runner above (see path in output).", flush=True)


if __name__ == "__main__":
    main()
