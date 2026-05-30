"""
run_create_3b_allprojects.py — Create snap_ph03_3b_AllProjects

Merges PMT_3b and NQPS_3b data into a fresh branch cloned from
snap_ph03_3a_AllProjects so that, after promotion, both source 3b
branches and their structural parent chains can be deleted.

What gets copied
----------------
The 3a_AllProjects branch already inherited all sources, signals,
source_atoms, segments, zachman_cells, and base analysis_passes from
production — those are identical across all branches and need no
copying.  The only branch-specific data added by the 3b CCI
Construction runs is:

  1. cell_content_item rows for PMT_E2E  (from snap_PMT_ph03_3b_R5)
  2. cell_content_item rows for NQPS_E2E (from snap_NQPS_ph03_3b_R5)
  3. Extra analysis_pass rows for PMT_E2E (5 passes not in 3a baseline)
  4. Extra analysis_pass rows for NQPS_E2E (5 passes not in 3a baseline)

Pass ID conflict resolution
---------------------------
Both 3b runs started from the same sequence state and consumed
sequence values P1474–P1478 for their 5 extra passes.  The script
inserts PMT extras first (original IDs), then fetches 5 new IDs from
p_id_seq for the NQPS extras so there is no PK collision.

Post-run cleanup (run after verifying the new snapshot)
--------------------------------------------------------
  python sysengage/scripts/branch_manager.py delete_snapshot \\
      --snapshot snap_PMT_ph03_3b_R5
  python sysengage/scripts/branch_manager.py delete_test_branch \\
      --branch test_PMT_ph03_3a_R1_Ph3b_Baseline
  python sysengage/scripts/branch_manager.py delete_snapshot \\
      --snapshot snap_PMT_ph03_3a_R1 --force
  python sysengage/scripts/branch_manager.py delete_snapshot \\
      --snapshot snap_NQPS_ph03_3b_R5
  python sysengage/scripts/branch_manager.py delete_snapshot \\
      --snapshot snap_NQPS_ph03_3a_R5 --force
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from scripts.branch_manager import (
    _create_branch,
    _get_project_id,
    _neon_request,
    _registry_add_snapshot,
    _delete_branch,
    _find_branch_by_name,
    REGISTRY_PATH,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SNAP_3A_BRANCH_ID = "br-patient-wind-ab22nov1"   # snap_ph03_3a_AllProjects
PMT_3B_BRANCH_ID  = "br-wild-snow-ab8c02ma"       # snap_PMT_ph03_3b_R5
NQPS_3B_BRANCH_ID = "br-dark-moon-abirq78k"       # snap_NQPS_ph03_3b_R5

PMT_3B_HOST  = "ep-empty-fog-ab4xd2kl.eu-west-2.aws.neon.tech"
NQPS_3B_HOST = "ep-young-term-abd89wvw.eu-west-2.aws.neon.tech"
SNAP_3A_HOST = "ep-autumn-pine-abhzr2ka.eu-west-2.aws.neon.tech"

NEW_SNAP_NAME = "snap_ph03_3b_AllProjects"
TEST_BRANCH_NAME = "test_ph03_3b_AllProjects_Merge"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _sanitise(url: str) -> str:
    return url.replace("channel_binding=require", "channel_binding=prefer")


def engine_for(host: str):
    base = os.environ["NEON_DATABASE_URL"]
    url = re.sub(r"@[^/?]+", f"@{host}", base)
    return create_engine(
        _sanitise(url),
        pool_size=1,
        max_overflow=0,
        connect_args={"connect_timeout": 30},
    )


def warm_up(eng) -> None:
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

def get_extra_passes(src_conn, dest_conn, project_id: str) -> list[dict]:
    """
    Return analysis_pass rows for *project_id* that are in src but not in dest.
    """
    existing = {
        r[0]
        for r in dest_conn.execute(
            text("SELECT pass_id FROM analysis_pass WHERE project_id = :p"),
            {"p": project_id},
        ).fetchall()
    }
    rows = src_conn.execute(
        text(
            "SELECT pass_id, phase_id, pass_type, mechanism, evaluated_scope, "
            "confidence, pass_started_at, pass_completed_at, execution_status, "
            "mode_active, declared_transformation_modes, elapsed_ms, "
            "practitioner_id, project_id, outputs, created_at "
            "FROM analysis_pass WHERE project_id = :p"
        ),
        {"p": project_id},
    ).fetchall()
    return [dict(r._mapping) for r in rows if r.pass_id not in existing]


def _jsonb(val) -> str | None:
    """Serialise a Python value to a JSON string for psycopg2 JSONB binding."""
    if val is None:
        return None
    if isinstance(val, str):
        return val  # already a string (shouldn't happen for JSONB, but guard)
    return json.dumps(val)


def insert_passes(dest_conn, passes: list[dict], id_override: dict | None = None) -> None:
    """
    Insert analysis_pass rows.  id_override maps old pass_id → new pass_id.
    """
    if not passes:
        print("  (no extra passes to insert)")
        return
    for row in passes:
        pid = (id_override or {}).get(row["pass_id"], row["pass_id"])
        dest_conn.execute(
            text(
                "INSERT INTO analysis_pass "
                "(pass_id, phase_id, pass_type, mechanism, evaluated_scope, "
                "confidence, pass_started_at, pass_completed_at, execution_status, "
                "mode_active, declared_transformation_modes, elapsed_ms, "
                "practitioner_id, project_id, outputs, created_at) "
                "VALUES (:pass_id, :phase_id, :pass_type, :mechanism, :evaluated_scope, "
                ":confidence, :pass_started_at, :pass_completed_at, :execution_status, "
                ":mode_active, CAST(:declared_transformation_modes AS JSONB), :elapsed_ms, "
                ":practitioner_id, :project_id, CAST(:outputs AS JSONB), :created_at)"
            ),
            {
                **row,
                "pass_id": pid,
                "declared_transformation_modes": _jsonb(row["declared_transformation_modes"]),
                "outputs": _jsonb(row["outputs"]),
            },
        )
    print(f"  Inserted {len(passes)} analysis_pass rows")


def get_new_pass_ids(dest_conn, n: int) -> list[str]:
    """Fetch n new pass_ids from p_id_seq."""
    rows = dest_conn.execute(
        text("SELECT nextval('p_id_seq') FROM generate_series(1, :n)"),
        {"n": n},
    ).fetchall()
    vals = [r[0] for r in rows]
    return [f"P{v:03d}" for v in vals]


def copy_ccis(src_conn, dest_conn, project_id: str) -> int:
    """Copy all cell_content_item rows for project_id from src to dest."""
    rows = src_conn.execute(
        text(
            "SELECT ci_id, cell_id, classification_type, signal_refs, "
            "description, trigger_condition, justification, confidence, "
            "project_id, created_at, updated_at "
            "FROM cell_content_item WHERE project_id = :p"
        ),
        {"p": project_id},
    ).fetchall()
    if not rows:
        print(f"  No CCIs found for {project_id}")
        return 0
    for row in rows:
        m = dict(row._mapping)
        dest_conn.execute(
            text(
                "INSERT INTO cell_content_item "
                "(ci_id, cell_id, classification_type, signal_refs, "
                "description, trigger_condition, justification, confidence, "
                "project_id, created_at, updated_at) "
                "VALUES (:ci_id, :cell_id, :classification_type, CAST(:signal_refs AS JSONB), "
                ":description, :trigger_condition, :justification, :confidence, "
                ":project_id, :created_at, :updated_at)"
            ),
            {**m, "signal_refs": _jsonb(m["signal_refs"])},
        )
    print(f"  Copied {len(rows)} cell_content_items for {project_id}")
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    neon_proj = _get_project_id()

    # -- 1. Create test branch from snap_ph03_3a_AllProjects ----------------
    print(f"\n[1] Creating test branch '{TEST_BRANCH_NAME}' from snap_ph03_3a_AllProjects …")

    existing = _find_branch_by_name(neon_proj, TEST_BRANCH_NAME)
    if existing:
        print(f"  Branch already exists ({existing['id']}) — reusing.")
        test_branch_id = existing["id"]
    else:
        test_branch_id, _conn_uri = _create_branch(
            neon_proj, TEST_BRANCH_NAME, SNAP_3A_BRANCH_ID
        )
        print(f"  Created: {test_branch_id}")

    # Get the endpoint host for the new branch
    ep_data = _neon_request("GET", f"/projects/{neon_proj}/branches/{test_branch_id}/endpoints")
    endpoints = ep_data.get("endpoints", [])
    if not endpoints:
        print("ERROR: new branch has no endpoint — cannot connect.", file=sys.stderr)
        sys.exit(1)
    new_host = endpoints[0]["host"]
    print(f"  Endpoint: {new_host}")

    # -- 2. Connect to all three branches ------------------------------------
    print("\n[2] Connecting to all branches …")
    eng_pmt  = engine_for(PMT_3B_HOST)
    eng_nqps = engine_for(NQPS_3B_HOST)
    eng_new  = engine_for(new_host)

    for label, eng in [("PMT_3b", eng_pmt), ("NQPS_3b", eng_nqps), ("combined", eng_new)]:
        warm_up(eng)
        print(f"  {label}: OK")

    # -- 3. Copy data -------------------------------------------------------
    print("\n[3] Copying data into combined branch …")

    with eng_pmt.connect() as src_pmt, \
         eng_nqps.connect() as src_nqps, \
         eng_new.connect() as dest:

        with dest.begin():

            # 3a. Extra analysis_passes for PMT_E2E
            print("\n  [3a] Extra PMT_E2E analysis_passes:")
            extra_pmt = get_extra_passes(src_pmt, dest, "PMT_E2E")
            print(f"  Found {len(extra_pmt)} extra passes")
            insert_passes(dest, extra_pmt)

            # Advance sequence past any explicitly-inserted IDs so nextval gives fresh values
            dest.execute(text(
                "SELECT setval('p_id_seq', "
                "(SELECT max(cast(substring(pass_id from 2) as integer)) FROM analysis_pass))"
            ))

            # 3b. Extra analysis_passes for NQPS_E2E (may need new IDs)
            print("\n  [3b] Extra NQPS_E2E analysis_passes:")
            extra_nqps = get_extra_passes(src_nqps, dest, "NQPS_E2E")
            print(f"  Found {len(extra_nqps)} extra passes")
            if extra_nqps:
                # Check which pass_ids already exist in dest (from 3a step above)
                existing_ids = {
                    r[0] for r in dest.execute(text("SELECT pass_id FROM analysis_pass")).fetchall()
                }
                conflicting = [row for row in extra_nqps if row["pass_id"] in existing_ids]
                non_conflicting = [row for row in extra_nqps if row["pass_id"] not in existing_ids]

                # Insert non-conflicting with original IDs
                insert_passes(dest, non_conflicting)

                # Assign new IDs for conflicting NQPS passes
                if conflicting:
                    new_ids = get_new_pass_ids(dest, len(conflicting))
                    id_map = {old["pass_id"]: new_id for old, new_id in zip(conflicting, new_ids)}
                    print(f"  Reassigning {len(conflicting)} conflicting pass IDs: {id_map}")
                    insert_passes(dest, conflicting, id_override=id_map)

            # 3c. CCIs for PMT_E2E
            print("\n  [3c] cell_content_items for PMT_E2E:")
            n_pmt_ccis = copy_ccis(src_pmt, dest, "PMT_E2E")

            # 3d. CCIs for NQPS_E2E
            print("\n  [3d] cell_content_items for NQPS_E2E:")
            n_nqps_ccis = copy_ccis(src_nqps, dest, "NQPS_E2E")

    # -- 4. Verify ----------------------------------------------------------
    print("\n[4] Verification …")
    with eng_new.connect() as conn:
        cci_counts = dict(conn.execute(
            text("SELECT project_id, count(*) FROM cell_content_item GROUP BY project_id")
        ).fetchall())
        ap_counts = dict(conn.execute(
            text("SELECT project_id, count(*) FROM analysis_pass GROUP BY project_id")
        ).fetchall())

    with eng_pmt.connect() as conn:
        pmt_cci_expected = conn.execute(
            text("SELECT count(*) FROM cell_content_item WHERE project_id='PMT_E2E'")
        ).scalar()
        pmt_ap_expected = conn.execute(
            text("SELECT count(*) FROM analysis_pass WHERE project_id='PMT_E2E'")
        ).scalar()

    with eng_nqps.connect() as conn:
        nqps_cci_expected = conn.execute(
            text("SELECT count(*) FROM cell_content_item WHERE project_id='NQPS_E2E'")
        ).scalar()
        nqps_ap_expected = conn.execute(
            text("SELECT count(*) FROM analysis_pass WHERE project_id='NQPS_E2E'")
        ).scalar()

    print(f"  cell_content_item counts: {cci_counts}")
    print(f"  analysis_pass counts (sample): PMT_E2E={ap_counts.get('PMT_E2E')}, NQPS_E2E={ap_counts.get('NQPS_E2E')}")

    errors = []
    if cci_counts.get("PMT_E2E", 0) != pmt_cci_expected:
        errors.append(f"PMT CCIs: got {cci_counts.get('PMT_E2E')}, expected {pmt_cci_expected}")
    if cci_counts.get("NQPS_E2E", 0) != nqps_cci_expected:
        errors.append(f"NQPS CCIs: got {cci_counts.get('NQPS_E2E')}, expected {nqps_cci_expected}")
    if ap_counts.get("PMT_E2E", 0) != pmt_ap_expected:
        errors.append(f"PMT analysis_passes: got {ap_counts.get('PMT_E2E')}, expected {pmt_ap_expected}")
    if ap_counts.get("NQPS_E2E", 0) != nqps_ap_expected:
        errors.append(f"NQPS analysis_passes: got {ap_counts.get('NQPS_E2E')}, expected {nqps_ap_expected}")

    if errors:
        print("\nVERIFICATION FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("\nTest branch NOT promoted — fix issues and rerun.", file=sys.stderr)
        sys.exit(1)

    print("\n  All counts match. Verification PASSED.")

    # -- 5. Rename test branch → snap_ph03_3b_AllProjects -------------------
    print(f"\n[5] Renaming '{TEST_BRANCH_NAME}' → '{NEW_SNAP_NAME}' in Neon …")
    _neon_request(
        "PATCH",
        f"/projects/{neon_proj}/branches/{test_branch_id}",
        body={"branch": {"name": NEW_SNAP_NAME}},
    )
    print("  Done.")

    # -- 6. Register in snapshot registry -----------------------------------
    print(f"\n[6] Registering '{NEW_SNAP_NAME}' in snapshot registry …")
    entry = {
        "name": NEW_SNAP_NAME,
        "project_id": "ALL",
        "phase": "ph03",
        "pass": "3b",
        "row": "R5",
        "state_description": (
            "Post-3b dedup: PMT and NQPS all rows, CCIs committed, dedup ON — "
            f"PMT_E2E={n_pmt_ccis} CCIs, NQPS_E2E={n_nqps_ccis} CCIs. "
            "Phase 3c input baseline."
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "VERIFIED",
        "ver_criteria_passed": [],
        "neon_branch_id": test_branch_id,
        "neon_project_id": neon_proj,
    }
    _registry_add_snapshot(entry)
    print(f"  Registry updated: {REGISTRY_PATH}")

    # -- 7. Summary ---------------------------------------------------------
    print(f"""
========================================================
  snap_ph03_3b_AllProjects created successfully
  Branch ID: {test_branch_id}
  PMT CCIs:  {n_pmt_ccis}
  NQPS CCIs: {n_nqps_ccis}
========================================================

Next: run the cleanup commands to free the old branches:

  python sysengage/scripts/branch_manager.py delete_snapshot \\
      --snapshot snap_PMT_ph03_3b_R5
  python sysengage/scripts/branch_manager.py delete_test_branch \\
      --branch test_PMT_ph03_3a_R1_Ph3b_Baseline
  python sysengage/scripts/branch_manager.py delete_snapshot \\
      --snapshot snap_PMT_ph03_3a_R1 --force
  python sysengage/scripts/branch_manager.py delete_snapshot \\
      --snapshot snap_NQPS_ph03_3b_R5
  python sysengage/scripts/branch_manager.py delete_snapshot \\
      --snapshot snap_NQPS_ph03_3a_R5 --force
""")

    for eng in (eng_pmt, eng_nqps, eng_new):
        eng.dispose()


if __name__ == "__main__":
    main()
