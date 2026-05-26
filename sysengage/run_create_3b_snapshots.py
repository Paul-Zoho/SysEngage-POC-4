"""
run_create_3b_snapshots.py — Create post-Phase-3b baseline snapshots for PMT and NQPS.

Workflow (for each project):
  1. Clone a fresh test branch from the post-3a snapshot.
  2. Apply pending Alembic migrations.
  3. Run CCI Construction rows 1-5 with dedup ON against the test branch.
  4. Promote the test branch to a new snapshot (snap_{PROJECT}_ph03_3b_R5).

Snapshots produced:
  snap_PMT_ph03_3b_R5   — PMT post-3b, dedup enabled, all rows
  snap_NQPS_ph03_3b_R5  — NQPS post-3b, dedup enabled, all rows

These snapshots serve as clean test inputs for Phase 3c (Domain Derivation).

Invocation (from workspace root):
    python -u sysengage/run_create_3b_snapshots.py
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
    _neon_request,
    _registry_get,
    _registry_add_snapshot,
)
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Project configurations
# ---------------------------------------------------------------------------

PROJECTS = [
    {
        "label": "PMT",
        "source_snap": "snap_PMT_ph03_3a_R1",
        "test_branch": "test_PMT_ph03_3a_R1_Ph3b_Baseline",
        "target_snap": "snap_PMT_ph03_3b_R5",
        "target_phase": "ph03",
        "target_pass": "3b",
        "target_row": "R5",
        "runner": str(SYSENGAGE / "run_pmt_cci_r1_r5_dedup.py"),
        "description": "Post-3b dedup: PMT all rows, CCIs committed, dedup ON — Phase 3c input baseline",
    },
    {
        "label": "NQPS",
        "source_snap": "snap_NQPS_ph03_3a_R5",
        "test_branch": "test_NQPS_ph03_3a_R5_Ph3b_Baseline",
        "target_snap": "snap_NQPS_ph03_3b_R5",
        "target_phase": "ph03",
        "target_pass": "3b",
        "target_row": "R5",
        "runner": str(SYSENGAGE / "run_nqps_cci_r1_r5_dedup.py"),
        "description": "Post-3b dedup: NQPS all rows, CCIs committed, dedup ON — Phase 3c input baseline",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def banner(msg: str) -> None:
    print(f"\n{'═' * 60}", flush=True)
    print(f"  {msg}", flush=True)
    print(f"{'═' * 60}", flush=True)


def section(msg: str) -> None:
    print(f"\n{'─' * 60}", flush=True)
    print(f"  {msg}", flush=True)
    print(f"{'─' * 60}", flush=True)


# ---------------------------------------------------------------------------
# Per-project snapshot creation
# ---------------------------------------------------------------------------

def create_snapshot_for_project(cfg: dict, neon_project: str) -> None:
    label = cfg["label"]
    source_snap = cfg["source_snap"]
    test_branch_name = cfg["test_branch"]
    target_snap = cfg["target_snap"]

    banner(f"{label}  •  {source_snap}  →  {target_snap}")

    # ── guard: skip if target snapshot already exists ──────────────────────
    existing_snap = _find_branch_by_name(neon_project, target_snap)
    if existing_snap:
        print(
            f"[{label}] Snapshot '{target_snap}' already exists in Neon "
            f"(id={existing_snap['id']}) — skipping.",
            flush=True,
        )
        registry_entry = _registry_get(target_snap)
        if not registry_entry:
            print(f"[{label}] WARNING: snapshot exists in Neon but not in registry — please register manually.", flush=True)
        return

    # ── resolve source snapshot branch ID ─────────────────────────────────
    snap = _registry_get(source_snap)
    if snap:
        snap_branch_id = snap["neon_branch_id"]
        print(f"[{label}] Source snapshot branch (registry): {snap_branch_id}", flush=True)
    else:
        neon_snap = _find_branch_by_name(neon_project, source_snap)
        if not neon_snap:
            print(
                f"ERROR [{label}]: source snapshot '{source_snap}' not found in registry or Neon.",
                file=sys.stderr,
            )
            sys.exit(1)
        snap_branch_id = neon_snap["id"]
        print(f"[{label}] Source snapshot branch (Neon lookup): {snap_branch_id}", flush=True)

    # ── create test branch ─────────────────────────────────────────────────
    section(f"[{label}] Creating test branch: {test_branch_name}")
    existing_test = _find_branch_by_name(neon_project, test_branch_name)
    if existing_test:
        print(f"[{label}] Test branch already exists — deleting first ({existing_test['id']})", flush=True)
        _delete_branch(neon_project, existing_test["id"])

    branch_id, conn_uri = _create_branch(neon_project, test_branch_name, snap_branch_id)
    print(f"[{label}] Test branch ready: id={branch_id}", flush=True)

    env = {**os.environ, "NEON_DATABASE_URL": conn_uri}

    # ── apply migrations ───────────────────────────────────────────────────
    section(f"[{label}] Applying migrations")
    mig_result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env,
        cwd=str(SYSENGAGE),
        capture_output=False,
    )
    if mig_result.returncode != 0:
        print(f"ERROR [{label}]: alembic upgrade failed (code {mig_result.returncode})", file=sys.stderr, flush=True)
        _delete_branch(neon_project, branch_id)
        sys.exit(mig_result.returncode)
    print(f"[{label}] Migrations applied.", flush=True)

    # ── run CCI construction ───────────────────────────────────────────────
    section(f"[{label}] Running CCI Construction rows 1-5  dedup ON")
    run_result = subprocess.run(
        [sys.executable, "-u", cfg["runner"]],
        env=env,
        capture_output=False,
    )
    if run_result.returncode != 0:
        print(f"ERROR [{label}]: runner exited with code {run_result.returncode}", file=sys.stderr, flush=True)
        print(f"[{label}] Cleaning up test branch: {test_branch_name}", flush=True)
        _delete_branch(neon_project, branch_id)
        sys.exit(run_result.returncode)

    # ── promote test branch to snapshot (rename in-place) ──────────────────
    # NOTE: Do NOT create a new child branch then delete the parent — Neon
    # refuses to delete a branch that has children.  Instead, rename the test
    # branch directly to the snapshot name.  The branch ID is unchanged.
    section(f"[{label}] Promoting test branch → {target_snap}")

    _neon_request(
        "PATCH",
        f"/projects/{neon_project}/branches/{branch_id}",
        body={"branch": {"name": target_snap}},
    )
    print(f"[{label}] Test branch renamed to: {target_snap}", flush=True)

    entry = {
        "name": target_snap,
        "project_id": cfg["label"],
        "phase": cfg["target_phase"],
        "pass": cfg["target_pass"],
        "row": cfg["target_row"],
        "state_description": cfg["description"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "VERIFIED",
        "ver_criteria_passed": [],
        "neon_branch_id": branch_id,
        "neon_project_id": neon_project,
    }
    _registry_add_snapshot(entry)
    print(f"[{label}] Snapshot registered: {target_snap}  (branch id={branch_id})", flush=True)

    print(f"\n[{label}] ✓  Snapshot ready: {target_snap}", flush=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    banner("Phase 3b baseline snapshot creation  •  PMT + NQPS")

    neon_project = _get_project_id()
    print(f"[orchestrator] Neon project: {neon_project}", flush=True)
    print(f"[orchestrator] Targets: snap_PMT_ph03_3b_R5  +  snap_NQPS_ph03_3b_R5", flush=True)

    for cfg in PROJECTS:
        create_snapshot_for_project(cfg, neon_project)

    banner("ALL DONE")
    print("[orchestrator] Both post-3b baseline snapshots are registered and ready.", flush=True)
    print("[orchestrator] Registry: sysengage/test_infrastructure/snapshot_registry.json", flush=True)


if __name__ == "__main__":
    main()
