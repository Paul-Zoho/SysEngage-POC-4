"""
run_pmt_e2e_r1_main.py — PMT Row 1 full pipeline on a disposable test branch.

Workflow
--------
1.  Clone a disposable test branch from the (empty) production main branch.
2.  Set NEON_DATABASE_URL to the test branch connection string — ALL mechanism
    writes go to the test branch; production is never touched.
3.  Run SC → RLSRA → CCI → DD → RD on the test branch.
4.  Export the ledger.
5.  Rename the test branch to snap_PMT_ph03_3d_R1_<YYYYMMDD> — the rename IS
    the snapshot; no separate clone is needed.
6.  Register the snapshot.

The production (main) branch remains empty throughout.

Key design note
---------------
core/db.py builds the SQLAlchemy engine at *module import time* from
NEON_DATABASE_URL.  Therefore all mechanism imports must happen AFTER
os.environ["NEON_DATABASE_URL"] has been set to the test branch URL.
The imports at the top of this file are deliberately limited to stdlib and
branch_manager (which does not import core.db).

Idempotency
-----------
Each pass is skipped if a Completed / CompletedWithWarnings pass already exists
for that mechanism + scope on the active branch.  Re-running the script after a
partial failure resumes from the first incomplete step.

Invocation (from workspace root):
    python -u sysengage/run_pmt_e2e_r1_main.py
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SYSENGAGE_DIR = Path(__file__).parent
sys.path.insert(0, str(SYSENGAGE_DIR))
sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))

# branch_manager is safe to import early — it does NOT import core.db
import branch_manager as bm

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ID      = "PMT_E2E"
PROJECT_CODE    = "PMT"
PRACTITIONER_ID = "SH001"
ROW             = 1

INPUT_DOC = (
    SYSENGAGE_DIR.parent / "verification_inputs" / "The Pocket Money Tracker System v1.docx"
)
OUT_DIR = SYSENGAGE_DIR.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PRODUCTION_BRANCH_ID = "br-still-base-abca1uh3"   # Neon production (root) — always empty
TEST_BRANCH_NAME     = "test_PMT_ph03_3d_R1_run"

SNAP_DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
SNAP_NAME = f"snap_PMT_ph03_3d_R1_{SNAP_DATE}"

SEP = "=" * 65


# ---------------------------------------------------------------------------
# Step 1 — Create test branch from production (empty)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[E2E] Step 1 — Create test branch from production", flush=True)
print(SEP, flush=True)

neon_project = bm._get_project_id()

# Reuse an existing test branch if this is a resumed run
existing = bm._find_branch_by_name(neon_project, TEST_BRANCH_NAME)
if existing:
    test_branch_id = existing["id"]
    print(f"[E2E]   Reusing existing test branch: {test_branch_id}", flush=True)
    # Reconstruct the connection URL by swapping the host
    ep_data = bm._neon_request("GET", f"/projects/{neon_project}/branches/{test_branch_id}/endpoints")
    endpoints = ep_data.get("endpoints", [])
    if not endpoints:
        print("[E2E] ERROR: test branch has no endpoint.", file=sys.stderr)
        sys.exit(1)
    test_host = endpoints[0]["host"]
    base_url = os.environ.get("NEON_DATABASE_URL", "")
    test_branch_url = re.sub(r"@[^/?]+", f"@{test_host}", base_url)
    test_branch_url = test_branch_url.replace("channel_binding=require", "channel_binding=prefer")
else:
    test_branch_id, test_branch_url = bm._create_branch(
        neon_project, TEST_BRANCH_NAME, PRODUCTION_BRANCH_ID
    )
    print(f"[E2E]   Created test branch: {test_branch_id}", flush=True)

print(f"[E2E]   Branch ID : {test_branch_id}", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Step 2 — Point NEON_DATABASE_URL at the test branch
#           (must happen BEFORE any mechanism imports, which bind core.db engine)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[E2E] Step 2 — Switch active DB to test branch", flush=True)
print(SEP, flush=True)

os.environ["NEON_DATABASE_URL"] = test_branch_url
print("[E2E]   NEON_DATABASE_URL → test branch", flush=True)
print(flush=True)

# ---------------------------------------------------------------------------
# Deferred mechanism imports — engine binds to test branch URL from here on
# ---------------------------------------------------------------------------

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

import mechanisms.source_capture as sc
import mechanisms.row_lens_source_reanalysis as rlsra
import mechanisms.cci_construction as cci
import mechanisms.domain_derivation as dd
import mechanisms.requirement_derivation as rd
from core.db import get_session
from core.output_naming import generate_filename
from mechanisms.ledger_export import run_ledger_export
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Idempotency helper
# ---------------------------------------------------------------------------

def _pass_already_done(mechanism: str, scope: str) -> str | None:
    """Return pass_id if a terminal-success pass exists on the active branch."""
    s = get_session()
    try:
        row = s.execute(
            text(
                "SELECT pass_id FROM analysis_pass "
                "WHERE project_id = :p "
                "  AND mechanism = :m "
                "  AND evaluated_scope = :scope "
                "  AND execution_status IN ('Completed','CompletedWithWarnings') "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"p": PROJECT_ID, "m": mechanism, "scope": scope},
        ).fetchone()
        return row[0] if row else None
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Step 3 — Schema migrations (idempotent, against test branch)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[E2E] Step 3 — Schema migrations (test branch)", flush=True)
print(SEP, flush=True)

_alembic_cfg = AlembicConfig(str(SYSENGAGE_DIR / "alembic.ini"))
_alembic_cfg.set_main_option("script_location", str(SYSENGAGE_DIR / "alembic"))
alembic_command.upgrade(_alembic_cfg, "head")
print("[E2E]   Schema up to date.", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Step 4 — Source Capture
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[E2E] Step 4 — Source Capture", flush=True)
print(SEP, flush=True)

_sc_done = _pass_already_done("SourceCapture", "All input material in this project")
if _sc_done:
    print(f"[E2E]   SKIP — pass {_sc_done} already Completed.", flush=True)
else:
    if not INPUT_DOC.exists():
        print(f"[E2E] ERROR: input document not found: {INPUT_DOC}", file=sys.stderr)
        sys.exit(1)

    print(f"[E2E]   Input: {INPUT_DOC.name}", flush=True)
    sc_result = sc.run_source_capture(
        INPUT_DOC,
        project_id=PROJECT_ID,
        practitioner_id=PRACTITIONER_ID,
        read_mode="Full",
        segmentation_policy="default",
    )

    print(f"[E2E]   pass_id          = {sc_result.pass_id}", flush=True)
    print(f"[E2E]   execution_status = {sc_result.execution_status}", flush=True)
    print(f"[E2E]   sources          = {sc_result.source_count}", flush=True)
    print(f"[E2E]   segments         = {sc_result.segment_count}", flush=True)
    print(f"[E2E]   source_atoms     = {sc_result.source_atom_count}", flush=True)

    if sc_result.execution_status not in ("Completed", "CompletedWithWarnings"):
        print(f"[E2E] Source Capture failed: {sc_result.failure_reason}", file=sys.stderr)
        sys.exit(1)

print(flush=True)


# ---------------------------------------------------------------------------
# Step 5 — Row-Lens Source Re-Analysis (3a), Row 1  → produces Signals
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[E2E] Step 5 — RLSRA 3a  Row 1  (signal extraction)", flush=True)
print(SEP, flush=True)

_rlsra_done = _pass_already_done("RowLensSourceReanalysis", f"All Sources (Row {ROW})")
if _rlsra_done:
    print(f"[E2E]   SKIP — pass {_rlsra_done} already Completed.", flush=True)
else:
    try:
        rlsra_result = rlsra.run(
            project_id=PROJECT_ID,
            practitioner_id=PRACTITIONER_ID,
            row_ref=ROW,
        )
    except Exception as exc:
        print(f"[E2E] RLSRA failed: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)

    status = rlsra_result["execution_status"]
    rld = rlsra_result.get("row_lens_data", {})
    print(f"[E2E]   pass_id          = {rlsra_result['pass_id']}", flush=True)
    print(f"[E2E]   execution_status = {status}", flush=True)
    print(f"[E2E]   signals_produced = {rld.get('signal_count', '?')}", flush=True)
    print(f"[E2E]   concerns_raised  = {rld.get('concern_count', '?')}", flush=True)
    print(f"[E2E]   out_of_scope     = {rld.get('out_of_scope_count', '?')}", flush=True)

    if status not in ("Completed", "CompletedWithWarnings"):
        print(f"[E2E] RLSRA failed with status {status!r}", file=sys.stderr)
        sys.exit(1)

print(flush=True)


# ---------------------------------------------------------------------------
# Step 6 — CCI Construction (3b), Row 1, dedup ON
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[E2E] Step 6 — CCI Construction 3b  Row 1  dedup=ON", flush=True)
print(SEP, flush=True)

_cci_done = _pass_already_done("CellContentItemConstruction", f"All Row {ROW} Signals")
if _cci_done:
    print(f"[E2E]   SKIP — pass {_cci_done} already Completed.", flush=True)
else:
    try:
        cci_result = cci.run(
            project_id=PROJECT_ID,
            practitioner_id=PRACTITIONER_ID,
            row_ref=ROW,
            skip_deduplication=False,
        )
    except Exception as exc:
        print(f"[E2E] CCI failed: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)

    cd = cci_result["cci_data"]
    print(f"[E2E]   pass_id          = {cci_result['pass_id']}", flush=True)
    print(f"[E2E]   execution_status = {cci_result['execution_status']}", flush=True)
    print(f"[E2E]   ccis_created     = {cd['ccis_created']}", flush=True)
    print(f"[E2E]   ccis_merged      = {cd['ccis_merged']}", flush=True)
    print(f"[E2E]   batches_processed= {cd['batches_processed']}", flush=True)
    print(f"[E2E]   batches_failed   = {cd['batches_failed']}", flush=True)

    if cci_result["execution_status"] not in ("Completed", "CompletedWithWarnings"):
        print(f"[E2E] CCI ended with status {cci_result['execution_status']!r}", file=sys.stderr)
        sys.exit(1)

print(flush=True)


# ---------------------------------------------------------------------------
# Step 7 — Domain Derivation (3c), Row 1
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[E2E] Step 7 — Domain Derivation 3c  Row 1", flush=True)
print(SEP, flush=True)

_dd_done = _pass_already_done("DomainDerivation", f"Row {ROW} CCIs for project {PROJECT_ID}")
if _dd_done:
    print(f"[E2E]   SKIP — pass {_dd_done} already Completed.", flush=True)
else:
    try:
        dd_result = dd.run(
            project_id=PROJECT_ID,
            practitioner_id=PRACTITIONER_ID,
            row_ref=ROW,
        )
    except Exception as exc:
        print(f"[E2E] DD failed: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)

    md = dd_result["mechanism_data"]
    status = dd_result["execution_status"]
    print(f"[E2E]   pass_id               = {dd_result['pass_id']}", flush=True)
    print(f"[E2E]   execution_status      = {status}", flush=True)
    print(f"[E2E]   scenario              = {md.get('scenario')}", flush=True)
    print(f"[E2E]   cci_count_input       = {md.get('cci_count_input')}", flush=True)
    print(f"[E2E]   domain_count_produced = {md.get('domain_count_produced')}", flush=True)
    for d in md.get("domains_produced", []):
        print(
            f"[E2E]     {d['domain_id']}  {d['name']!r}  {d.get('cci_ref_count','?')} CCIs",
            flush=True,
        )

    if status not in ("Completed", "CompletedWithWarnings"):
        print(f"[E2E] DD ended with status {status!r}", file=sys.stderr)
        sys.exit(1)

print(flush=True)


# ---------------------------------------------------------------------------
# Step 8 — Requirement Derivation (3d), Row 1
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[E2E] Step 8 — Requirement Derivation 3d  Row 1", flush=True)
print(SEP, flush=True)

_rd_done = _pass_already_done("RequirementDerivation", f"Row {ROW} for {PROJECT_ID}")
if _rd_done:
    print(f"[E2E]   SKIP — pass {_rd_done} already Completed.", flush=True)
else:
    try:
        rd_result = rd.run_requirement_derivation(
            project_id=PROJECT_ID,
            practitioner_id=PRACTITIONER_ID,
            row_ref=ROW,
        )
    except Exception as exc:
        print(f"[E2E] RD failed: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)

    status = rd_result["execution_status"]
    print(f"[E2E]   pass_id                    = {rd_result.get('pass_id')}", flush=True)
    print(f"[E2E]   execution_status           = {status}", flush=True)
    print(f"[E2E]   scenario                   = {rd_result.get('scenario')}", flush=True)
    print(f"[E2E]   cci_count_input            = {rd_result.get('cci_count_input')}", flush=True)
    print(f"[E2E]   domain_count               = {rd_result.get('domain_count')}", flush=True)
    print(f"[E2E]   requirement_count_produced = {rd_result.get('requirement_count_produced')}", flush=True)
    print(f"[E2E]   requirement_count_retired  = {rd_result.get('requirement_count_retired')}", flush=True)

    type_dist = rd_result.get("requirement_type_distribution", {})
    if type_dist:
        print("[E2E]   type_distribution:", flush=True)
        for rtype, count in sorted(type_dist.items()):
            print(f"[E2E]     {rtype}: {count}", flush=True)

    if status not in ("Completed", "CompletedWithWarnings"):
        print(f"[E2E] RD ended with status {status!r}", file=sys.stderr)
        sys.exit(1)

print(flush=True)


# ---------------------------------------------------------------------------
# Step 9 — Ledger export (written locally; test branch data)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[E2E] Step 9 — Ledger export", flush=True)
print(SEP, flush=True)

basename = generate_filename(
    project_id=PROJECT_CODE,
    phase=3,
    pass_="3d",
    row=ROW,
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
n_elements  = len(ledger.get("elements", []))
n_registers = len(ledger.get("register_index", []))
hash_prefix = ledger.get("content_hash", {}).get("hash", "")[:16]

print(f"[E2E]   Ledger written : {basename}", flush=True)
print(f"[E2E]   Elements       : {n_elements}", flush=True)
print(f"[E2E]   Registers      : {n_registers}", flush=True)
print(f"[E2E]   Hash           : {hash_prefix}...", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Step 10 — Count rows for snapshot metadata
# ---------------------------------------------------------------------------

session2 = get_session()
try:
    req_count    = session2.execute(text("SELECT count(*) FROM requirement       WHERE project_id = :p"), {"p": PROJECT_ID}).scalar()
    domain_count = session2.execute(text("SELECT count(*) FROM domain            WHERE project_id = :p"), {"p": PROJECT_ID}).scalar()
    cci_count    = session2.execute(text("SELECT count(*) FROM cell_content_item WHERE project_id = :p"), {"p": PROJECT_ID}).scalar()
    source_count = session2.execute(text("SELECT count(*) FROM source            WHERE project_id = :p"), {"p": PROJECT_ID}).scalar()
finally:
    session2.close()


# ---------------------------------------------------------------------------
# Step 10 — Promote test branch → snapshot (rename in place)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[E2E] Step 10 — Promote test branch → {SNAP_NAME}", flush=True)
print(SEP, flush=True)

# Delete a same-named snapshot if this is a repeated run on the same date
old = bm._find_branch_by_name(neon_project, SNAP_NAME)
if old:
    print(f"[E2E]   Removing stale same-date snapshot ({old['id']}) …", flush=True)
    bm._delete_branch(neon_project, old["id"])

bm._neon_request(
    "PATCH",
    f"/projects/{neon_project}/branches/{test_branch_id}",
    body={"branch": {"name": SNAP_NAME}},
)
print(f"[E2E]   Renamed {TEST_BRANCH_NAME} → {SNAP_NAME}", flush=True)

state_desc = (
    f"PMT_E2E Row 1 full pipeline (SC+RLSRA+CCI+DD+RD). "
    f"Sources={source_count}, CCIs={cci_count}, "
    f"Domains={domain_count}, Requirements={req_count}. "
    f"Production branch was untouched throughout."
)

entry = {
    "name": SNAP_NAME,
    "project_id": "PMT",
    "phase": "ph03",
    "pass": "3d",
    "row": "R1",
    "state_description": state_desc,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "status": "VERIFIED",
    "ver_criteria_passed": [],
    "neon_branch_id": test_branch_id,
    "neon_project_id": neon_project,
}
bm._registry_add_snapshot(entry)
print(f"[E2E]   Snapshot registered in registry.", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[E2E] PMT Row 1 pipeline COMPLETE — production branch untouched", flush=True)
print(SEP, flush=True)
print(f"[E2E]   Sources      : {source_count}", flush=True)
print(f"[E2E]   CCIs         : {cci_count}", flush=True)
print(f"[E2E]   Domains      : {domain_count}", flush=True)
print(f"[E2E]   Requirements : {req_count}", flush=True)
print(f"[E2E]   Ledger       : {basename}", flush=True)
print(f"[E2E]   Snapshot     : {SNAP_NAME}  ({test_branch_id})", flush=True)
print(flush=True)
print("[E2E] To clone a test branch from this snapshot:", flush=True)
print(
    f"  python sysengage/scripts/branch_manager.py create_test_branch "
    f"--snapshot {SNAP_NAME} --scenario <name>",
    flush=True,
)
