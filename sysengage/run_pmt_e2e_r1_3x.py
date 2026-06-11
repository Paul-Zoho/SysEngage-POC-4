"""
run_pmt_e2e_r1_3x.py — PMT Row 1 triple-run pipeline on a single test branch.

Workflow
--------
1.  Clone one disposable test branch from the (empty) production main branch.
2.  Set NEON_DATABASE_URL to the test branch connection string.
3.  Apply schema migrations once (idempotent).
4-8. For each of PMT_E2E_R11, PMT_E2E_R12, PMT_E2E_R13 in sequence:
       SC → RLSRA (3a) → CCI (3b, dedup=ON) → DD (3c) → RD (3d)
9.  Export one ledger JSON per project (Run11, Run12, Run13).
10. Rename the test branch → snap_PMT_ph03_3d_R1_3x_YYYYMMDD and register.

Design notes
------------
- All three projects live on the same Neon branch, reducing branch count from 3
  to 1 for this run set.  Row 2 testing can clone from this single snapshot and
  iterate over all three project IDs in one test branch.
- Idempotency: each pass is guarded by (mechanism, project_id, evaluated_scope).
  Restarting after a partial failure resumes from the first incomplete step.
- core/db.py binds the engine at import time.  All mechanism imports are deferred
  until AFTER os.environ["NEON_DATABASE_URL"] is set to the test branch URL.
- The snapshot name carries the _3x_ infix to distinguish it from the
  single-project snap_PMT_ph03_3d_R1_YYYYMMDD produced by run_pmt_e2e_r1_main.py.

Invocation (from workspace root):
    python -u sysengage/run_pmt_e2e_r1_3x.py
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SYSENGAGE_DIR = Path(__file__).parent
sys.path.insert(0, str(SYSENGAGE_DIR))
sys.path.insert(0, str(SYSENGAGE_DIR / "scripts"))

# branch_manager is safe to import early — it does NOT import core.db
import branch_manager as bm

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECTS: list[tuple[str, int]] = [
    ("PMT_E2E_R11", 11),
    ("PMT_E2E_R12", 12),
    ("PMT_E2E_R13", 13),
]

PROJECT_CODE    = "PMT"
PRACTITIONER_ID = "SH001"
ROW             = 1

INPUT_DOC = (
    SYSENGAGE_DIR.parent / "verification_inputs" / "The Pocket Money Tracker System v1.docx"
)
OUT_DIR = SYSENGAGE_DIR.parent / "verification_outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PRODUCTION_BRANCH_ID = "br-still-base-abca1uh3"
TEST_BRANCH_NAME     = "test_PMT_ph03_3d_R1_3x"

SNAP_DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
SNAP_NAME = f"snap_PMT_ph03_3d_R1_3x_{SNAP_DATE}"

SEP = "=" * 65


# ---------------------------------------------------------------------------
# Step 1 — Create test branch from production (empty)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[3x] Step 1 — Create test branch from production", flush=True)
print(SEP, flush=True)

neon_project = bm._get_project_id()

existing = bm._find_branch_by_name(neon_project, TEST_BRANCH_NAME)
if existing:
    test_branch_id = existing["id"]
    print(f"[3x]   Reusing existing test branch: {test_branch_id}", flush=True)
    ep_data = bm._neon_request(
        "GET",
        f"/projects/{neon_project}/branches/{test_branch_id}/endpoints",
    )
    endpoints = ep_data.get("endpoints", [])
    if not endpoints:
        print("[3x] ERROR: test branch has no endpoint.", file=sys.stderr)
        sys.exit(1)
    test_host = endpoints[0]["host"]
    base_url = os.environ.get("NEON_DATABASE_URL", "")
    test_branch_url = re.sub(r"@[^/?]+", f"@{test_host}", base_url)
    test_branch_url = test_branch_url.replace(
        "channel_binding=require", "channel_binding=prefer"
    )
else:
    test_branch_id, test_branch_url = bm._create_branch(
        neon_project, TEST_BRANCH_NAME, PRODUCTION_BRANCH_ID
    )
    print(f"[3x]   Created test branch: {test_branch_id}", flush=True)

print(f"[3x]   Branch ID : {test_branch_id}", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Step 2 — Point NEON_DATABASE_URL at the test branch
#           (must happen BEFORE any mechanism imports, which bind core.db engine)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[3x] Step 2 — Switch active DB to test branch", flush=True)
print(SEP, flush=True)

os.environ["NEON_DATABASE_URL"] = test_branch_url
print("[3x]   NEON_DATABASE_URL → test branch", flush=True)
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
# Idempotency helper (project_id-parameterised)
# ---------------------------------------------------------------------------

def _pass_already_done(project_id: str, mechanism: str, scope: str) -> str | None:
    """Return pass_id if a terminal-success pass exists for this project on the active branch."""
    s = get_session()
    try:
        row = s.execute(
            text(
                "SELECT pass_id FROM analysis_pass "
                "WHERE project_id = :p "
                "  AND mechanism = :m "
                "  AND evaluated_scope = :scope "
                "  AND execution_status IN ('Completed','CompletedWithWarnings','Success') "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"p": project_id, "m": mechanism, "scope": scope},
        ).fetchone()
        return row[0] if row else None
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Step 3 — Schema migrations (once, idempotent)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[3x] Step 3 — Schema migrations (test branch)", flush=True)
print(SEP, flush=True)

_alembic_cfg = AlembicConfig(str(SYSENGAGE_DIR / "alembic.ini"))
_alembic_cfg.set_main_option("script_location", str(SYSENGAGE_DIR / "alembic"))
alembic_command.upgrade(_alembic_cfg, "head")
print("[3x]   Schema up to date.", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Per-project pipeline runner
# ---------------------------------------------------------------------------

def _run_one_pipeline(project_id: str, run_label: int) -> None:
    """
    Run the full SC → RLSRA → CCI → DD → RD pipeline for one project_id.
    Idempotent: skips any step already completed on this branch.
    Exits the process on hard failure.
    """
    tag = f"[{project_id}]"
    print(flush=True)
    print(SEP, flush=True)
    print(f"{tag}  Run {run_label} — Row {ROW}", flush=True)
    print(SEP, flush=True)

    # ── Step 4: Source Capture ──────────────────────────────────────────────
    _sc_tag = f"[{project_id}/SC]"
    _sc_done = _pass_already_done(project_id, "SourceCapture", "All input material in this project")
    if _sc_done:
        print(f"{_sc_tag}   SKIP — pass {_sc_done} already Completed.", flush=True)
    else:
        if not INPUT_DOC.exists():
            print(f"{_sc_tag} ERROR: input document not found: {INPUT_DOC}", file=sys.stderr)
            sys.exit(1)
        sc_result = sc.run_source_capture(
            INPUT_DOC,
            project_id=project_id,
            practitioner_id=PRACTITIONER_ID,
            read_mode="Full",
            segmentation_policy="default",
        )
        print(f"{_sc_tag}   pass_id          = {sc_result.pass_id}", flush=True)
        print(f"{_sc_tag}   execution_status = {sc_result.execution_status}", flush=True)
        print(f"{_sc_tag}   sources          = {sc_result.source_count}", flush=True)
        if sc_result.execution_status not in ("Success", "PartialSuccess"):
            print(f"{_sc_tag} FAILED: {sc_result.failure_reason}", file=sys.stderr)
            sys.exit(1)

    # ── Step 5: RLSRA 3a ───────────────────────────────────────────────────
    _rlsra_tag = f"[{project_id}/RLSRA]"
    _rlsra_done = _pass_already_done(project_id, "RowLensSourceReanalysis", f"All Sources (Row {ROW})")
    if _rlsra_done:
        print(f"{_rlsra_tag}   SKIP — pass {_rlsra_done} already Completed.", flush=True)
    else:
        try:
            rlsra_result = rlsra.run(
                project_id=project_id,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW,
            )
        except Exception as exc:
            print(f"{_rlsra_tag} FAILED: {exc}", file=sys.stderr)
            import traceback; traceback.print_exc()
            sys.exit(1)
        status = rlsra_result["execution_status"]
        rld = rlsra_result.get("row_lens_data", {})
        print(f"{_rlsra_tag}   pass_id          = {rlsra_result['pass_id']}", flush=True)
        print(f"{_rlsra_tag}   execution_status = {status}", flush=True)
        print(f"{_rlsra_tag}   signals_produced = {rld.get('signal_count', '?')}", flush=True)
        print(f"{_rlsra_tag}   out_of_scope     = {rld.get('out_of_scope_count', '?')}", flush=True)
        if status not in ("Success", "PartialSuccess"):
            print(f"{_rlsra_tag} FAILED with status {status!r}", file=sys.stderr)
            sys.exit(1)

    # ── Step 6: CCI Construction 3b ────────────────────────────────────────
    _cci_tag = f"[{project_id}/CCI]"
    _cci_done = _pass_already_done(project_id, "CellContentItemConstruction", f"All Row {ROW} Signals")
    if _cci_done:
        print(f"{_cci_tag}   SKIP — pass {_cci_done} already Completed.", flush=True)
    else:
        try:
            cci_result = cci.run(
                project_id=project_id,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW,
                skip_deduplication=False,
            )
        except Exception as exc:
            print(f"{_cci_tag} FAILED: {exc}", file=sys.stderr)
            import traceback; traceback.print_exc()
            sys.exit(1)
        cd = cci_result["cci_data"]
        print(f"{_cci_tag}   pass_id          = {cci_result['pass_id']}", flush=True)
        print(f"{_cci_tag}   execution_status = {cci_result['execution_status']}", flush=True)
        print(f"{_cci_tag}   ccis_created     = {cd['ccis_created']}", flush=True)
        print(f"{_cci_tag}   ccis_merged      = {cd['ccis_merged']}", flush=True)
        if cci_result["execution_status"] not in ("Success", "PartialSuccess"):
            print(f"{_cci_tag} FAILED with status {cci_result['execution_status']!r}", file=sys.stderr)
            sys.exit(1)

    # ── Step 7: Domain Derivation 3c ───────────────────────────────────────
    _dd_tag = f"[{project_id}/DD]"
    _dd_done = _pass_already_done(project_id, "DomainDerivation", f"Row {ROW} CCIs for project {project_id}")
    if _dd_done:
        print(f"{_dd_tag}   SKIP — pass {_dd_done} already Completed.", flush=True)
    else:
        try:
            dd_result = dd.run(
                project_id=project_id,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW,
            )
        except Exception as exc:
            print(f"{_dd_tag} FAILED: {exc}", file=sys.stderr)
            import traceback; traceback.print_exc()
            sys.exit(1)
        md = dd_result["mechanism_data"]
        status = dd_result["execution_status"]
        print(f"{_dd_tag}   pass_id               = {dd_result['pass_id']}", flush=True)
        print(f"{_dd_tag}   execution_status      = {status}", flush=True)
        print(f"{_dd_tag}   domain_count_produced = {md.get('domain_count_produced')}", flush=True)
        for d in md.get("domains_produced", []):
            print(
                f"{_dd_tag}     {d['domain_id']}  {d['name']!r}  {d.get('cci_ref_count','?')} CCIs",
                flush=True,
            )
        if status not in ("Success", "PartialSuccess"):
            print(f"{_dd_tag} FAILED with status {status!r}", file=sys.stderr)
            sys.exit(1)

    # ── Step 8: Requirement Derivation 3d ──────────────────────────────────
    _rd_tag = f"[{project_id}/RD]"
    _rd_done = _pass_already_done(project_id, "RequirementDerivation", f"Row {ROW} for {project_id}")
    if _rd_done:
        print(f"{_rd_tag}   SKIP — pass {_rd_done} already Completed.", flush=True)
    else:
        try:
            rd_result = rd.run_requirement_derivation(
                project_id=project_id,
                practitioner_id=PRACTITIONER_ID,
                row_ref=ROW,
            )
        except Exception as exc:
            print(f"{_rd_tag} FAILED: {exc}", file=sys.stderr)
            import traceback; traceback.print_exc()
            sys.exit(1)
        status = rd_result["execution_status"]
        print(f"{_rd_tag}   pass_id                    = {rd_result.get('pass_id')}", flush=True)
        print(f"{_rd_tag}   execution_status           = {status}", flush=True)
        if rd_result.get("failure_reason"):
            print(f"{_rd_tag}   failure_reason             = {rd_result['failure_reason']}", flush=True)
        print(f"{_rd_tag}   scenario                   = {rd_result.get('scenario')}", flush=True)
        print(f"{_rd_tag}   cci_count_input            = {rd_result.get('cci_count_input')}", flush=True)
        print(f"{_rd_tag}   domain_count               = {rd_result.get('domain_count')}", flush=True)
        print(f"{_rd_tag}   requirement_count_produced = {rd_result.get('requirement_count_produced')}", flush=True)
        type_dist = rd_result.get("requirement_type_distribution", {})
        if type_dist:
            for rtype, count in sorted(type_dist.items()):
                print(f"{_rd_tag}     {rtype}: {count}", flush=True)
        if status not in ("Success", "PartialSuccess"):
            print(f"{_rd_tag} FAILED with status {status!r}", file=sys.stderr)
            sys.exit(1)

    print(f"{tag}  Run {run_label} pipeline complete.", flush=True)


# ---------------------------------------------------------------------------
# Steps 4-8: Run all three project pipelines
# ---------------------------------------------------------------------------

for _project_id, _run_number in PROJECTS:
    _run_one_pipeline(_project_id, _run_number)

print(flush=True)


# ---------------------------------------------------------------------------
# Step 9 — Ledger export (one per project)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[3x] Step 9 — Ledger exports", flush=True)
print(SEP, flush=True)

ledger_results: list[dict[str, Any]] = []

for _project_id, _run_number in PROJECTS:
    _basename = generate_filename(
        project_id=PROJECT_CODE,
        phase=3,
        pass_="3d",
        row=ROW,
        out_dir=str(OUT_DIR),
    )
    _session = get_session()
    try:
        _export = run_ledger_export(project_id=_project_id, session=_session)
    finally:
        _session.close()

    _path = OUT_DIR / _basename
    with open(_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_export.json_str)

    _ledger = _export.ledger
    _n_el   = len(_ledger.get("elements", []))
    _n_reg  = len(_ledger.get("register_index", []))
    _hash   = _ledger.get("content_hash", {}).get("hash", "")[:16]

    print(f"[3x]   {_project_id} → {_basename}", flush=True)
    print(f"[3x]     Elements={_n_el}  Registers={_n_reg}  Hash={_hash}...", flush=True)

    ledger_results.append({
        "project_id": _project_id,
        "run_number": _run_number,
        "basename": _basename,
        "n_elements": _n_el,
        "n_registers": _n_reg,
    })

print(flush=True)


# ---------------------------------------------------------------------------
# Step 10 — Count rows for snapshot metadata
# ---------------------------------------------------------------------------

_session3 = get_session()
try:
    _totals: dict[str, dict[str, int]] = {}
    for _project_id, _ in PROJECTS:
        _totals[_project_id] = {
            "sources":      _session3.execute(text("SELECT count(*) FROM source            WHERE project_id=:p"), {"p": _project_id}).scalar() or 0,
            "ccis":         _session3.execute(text("SELECT count(*) FROM cell_content_item WHERE project_id=:p"), {"p": _project_id}).scalar() or 0,
            "domains":      _session3.execute(text("SELECT count(*) FROM domain            WHERE project_id=:p"), {"p": _project_id}).scalar() or 0,
            "requirements": _session3.execute(text("SELECT count(*) FROM requirement       WHERE project_id=:p"), {"p": _project_id}).scalar() or 0,
        }
finally:
    _session3.close()


# ---------------------------------------------------------------------------
# Step 10 — Promote test branch → combined snapshot (rename in place)
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print(f"[3x] Step 10 — Promote test branch → {SNAP_NAME}", flush=True)
print(SEP, flush=True)

old = bm._find_branch_by_name(neon_project, SNAP_NAME)
if old:
    print(f"[3x]   Removing stale same-date snapshot ({old['id']}) …", flush=True)
    bm._delete_branch(neon_project, old["id"])

bm._neon_request(
    "PATCH",
    f"/projects/{neon_project}/branches/{test_branch_id}",
    body={"branch": {"name": SNAP_NAME}},
)
print(f"[3x]   Renamed {TEST_BRANCH_NAME} → {SNAP_NAME}", flush=True)

_parts = []
for _pid, _t in _totals.items():
    _parts.append(
        f"{_pid}: Sources={_t['sources']}, CCIs={_t['ccis']}, "
        f"Domains={_t['domains']}, Requirements={_t['requirements']}"
    )
_state_desc = (
    f"PMT Row 1 triple-run (Runs 11-13). "
    + " | ".join(_parts)
    + ". Production branch was untouched throughout."
)

_entry = {
    "name": SNAP_NAME,
    "project_id": "PMT_3x",
    "phase": "ph03",
    "pass": "3d",
    "row": "R1",
    "state_description": _state_desc,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "status": "VERIFIED",
    "ver_criteria_passed": [],
    "neon_branch_id": test_branch_id,
    "neon_project_id": neon_project,
}
bm._registry_add_snapshot(_entry)
print(f"[3x]   Snapshot registered in registry.", flush=True)
print(flush=True)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(SEP, flush=True)
print("[3x] PMT Row 1 triple-run COMPLETE — production branch untouched", flush=True)
print(SEP, flush=True)
print(f"[3x]   Branch    : {SNAP_NAME}  ({test_branch_id})", flush=True)
for lr in ledger_results:
    t = _totals[lr["project_id"]]
    print(
        f"[3x]   Run {lr['run_number']:2d}  {lr['project_id']}"
        f"  Src={t['sources']}  CCI={t['ccis']}  Dom={t['domains']}  Req={t['requirements']}"
        f"  → {lr['basename']}",
        flush=True,
    )
print(flush=True)
print("[3x] To clone a test branch for Row 2 from this snapshot:", flush=True)
print(
    f"  python sysengage/scripts/branch_manager.py create_test_branch "
    f"--snapshot {SNAP_NAME} --scenario <name>",
    flush=True,
)
