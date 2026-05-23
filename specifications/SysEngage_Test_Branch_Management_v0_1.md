# SysEngage Test Environment — Neon Branch Management Specification

**Version:** 0.1
**Date:** 16 May 2026
**Applies to:** All Pass-level mechanism testing in the SysEngage Replit implementation

---

## Purpose

This document specifies the Neon database branching strategy for SysEngage mechanism testing. It replaces ad-hoc table clearing as the mechanism for achieving a clean starting state between test runs.

The core principle: **never modify the parent branch during testing**. All test execution occurs on disposable child branches cloned from named snapshot branches. The snapshot branches represent stable, verified pipeline states at each phase boundary.

---

## Problem Statement

SysEngage mechanisms are stateful — each pass reads from and writes to the ledger. Testing a mechanism in isolation requires a known starting state. Previous approaches (manual table clearing, project_id isolation) have two failure modes:

- **Incomplete clearing:** Clearing one table while leaving dependent records (e.g. clearing CCIs but not AnalysisPasses) produces contaminated test state
- **Re-execution cost:** Using a fresh project_id for isolation requires re-running all upstream passes to recreate the starting state, which grows expensive as the pipeline deepens

Neon branch cloning solves both: a snapshot branch captures the complete, consistent ledger state at a phase boundary; a child branch cloned from it inherits that state exactly and can be discarded after the test run.

---

## Snapshot Branch Naming Convention

Snapshot branches are named using this format:

```
snap_{ProjectID}_{phase}_{pass}_R{row}
```

| **Field** | **Format** | **Example** |
| --- | --- | --- |
| `{ProjectID}` | Uppercase letters | `PMT`, `NQPS`, `ROW` |
| `{phase}` | `ph` + zero-padded 2-digit phase number | `ph01`, `ph03` |
| `{pass}` | Pass identifier | `0a`, `0b`, `3a`, `3b`, `3c`, `3d` |
| `R{row}` | `R` + row number | `R1`, `R5` |

The snapshot represents the state **after** the named pass has completed successfully and been verified. It is the correct starting state for testing the **next** pass.

**Examples:**

| **Snapshot name** | **State captured** | **Used to test** |
| --- | --- | --- |
| `snap_PMT_ph01_0a_R1` | Post-Source Capture, Row 1 | Pass 0b (Segment Capture) |
| `snap_PMT_ph03_3a_R1` | Post-Pass 3a (Signals committed), Row 1 | Pass 3b (CCI Construction) |
| `snap_PMT_ph03_3b_R1` | Post-Pass 3b (CCIs committed), Row 1 | Pass 3c (Domain Derivation) |
| `snap_PMT_ph03_3c_R1` | Post-Pass 3c (Domains committed), Row 1 | Pass 3d (Requirement Derivation) |
| `snap_NQPS_ph03_3a_R5` | Post-Pass 3a (Signals committed), all rows | Pass 3b, NQPS project |

---

## Test Branch Naming Convention

Test branches are short-lived, created for a single test run and deleted after analysis. They are named to describe the test scenario:

```
test_{ProjectID}_{phase}_{pass}_R{row}_{scenario}
```

| **Field** | **Format** | **Example** |
| --- | --- | --- |
| `{scenario}` | Short descriptor of what is being tested | `dedup_on`, `dedup_off`, `rerun`, `batchsize20` |

**Examples:**

| **Test branch** | **Cloned from** | **Tests** |
| --- | --- | --- |
| `test_PMT_ph03_3b_R1_dedup_off` | `snap_PMT_ph03_3a_R1` | Pass 3b, deduplication disabled |
| `test_PMT_ph03_3b_R1_dedup_on` | `snap_PMT_ph03_3a_R1` | Pass 3b, deduplication enabled |
| `test_PMT_ph03_3b_R1_rerun` | `snap_PMT_ph03_3a_R1` | Pass 3b re-run after Concern resolution |
| `test_ROW_ph03_3b_R1_batchsize20` | `snap_ROW_ph03_3a_R1` | Pass 3b with 223 signals, batch_size=20 |
| `test_NQPS_ph03_3c_R1_first` | `snap_NQPS_ph03_3b_R5` | Pass 3c first run |

---

## Workflow

### Creating a snapshot branch

A snapshot branch is created once, after a pass has been verified against its VER criteria. It is never modified after creation.

```
1. Run the mechanism on the main development branch to completion
2. Verify all VER-nn-nn criteria pass
3. Create Neon branch: snap_{ProjectID}_{phase}_{pass}_R{row}
   Source: current main branch state
4. Record the snapshot in the Snapshot Registry (see §6)
5. Mark the snapshot as VERIFIED
```

### Running a test scenario

```
1. Identify the correct snapshot branch for the test (the post-previous-pass state)
2. Create a test branch from the snapshot:
   test_{ProjectID}_{phase}_{pass}_R{row}_{scenario}
3. Point the test runner's DATABASE_URL to the test branch connection string
4. Run the mechanism under test
5. Export the ledger (using the standard naming convention)
6. Analyse the output
7. Delete the test branch
```

### Promoting a test result to a new snapshot

When a test run produces a verified output that should become the starting state for the next pass:

```
1. Confirm all VER criteria pass on the test branch
2. Create new snapshot branch from the test branch:
   snap_{ProjectID}_{phase}_{pass}_R{row}
   Source: the verified test branch
3. Record in Snapshot Registry
4. Delete the test branch (the snapshot now preserves the state)
```

---

## Implementation Requirements

### Environment variable management

The implementation must support switching DATABASE_URL between branches without code changes. The test runner reads DATABASE_URL from environment at startup. Two mechanisms are acceptable:

- `.env.test` file with branch-specific connection string, loaded by the test runner
- Environment variable set in the Replit Secrets panel per test scenario

The main development branch connection string must be kept in a separate variable (`DATABASE_URL_MAIN`) so it is never accidentally overwritten during test branch operations.

### Branch creation utility

Implement a utility script `scripts/branch_manager.py` with the following operations:

**`create_snapshot`** — create a snapshot branch from the current main branch state:
```
python scripts/branch_manager.py create_snapshot --project PMT --phase ph03 --pass 3a --row R1
```
Creates `snap_PMT_ph03_3a_R1`. Records in snapshot registry. Outputs the branch connection string.

**`create_test_branch`** — create a test branch from a named snapshot:
```
python scripts/branch_manager.py create_test_branch --snapshot snap_PMT_ph03_3a_R1 --scenario dedup_on
```
Creates `test_PMT_ph03_3b_R1_dedup_on`. Outputs the branch connection string for use as DATABASE_URL.

**`delete_test_branch`** — delete a test branch after analysis:
```
python scripts/branch_manager.py delete_test_branch --branch test_PMT_ph03_3b_R1_dedup_on
```

**`promote_to_snapshot`** — create a snapshot from a verified test branch:
```
python scripts/branch_manager.py promote_to_snapshot --branch test_PMT_ph03_3b_R1_dedup_on --phase ph03 --pass 3b --row R1
```
Creates `snap_PMT_ph03_3b_R1`. Records in snapshot registry. Deletes the test branch.

**`list_snapshots`** — list all available snapshot branches with status:
```
python scripts/branch_manager.py list_snapshots
```

The utility uses the Neon API (branching endpoints) authenticated via `NEON_API_KEY` from environment.

### Snapshot registry

Maintain a simple JSON file `test_infrastructure/snapshot_registry.json` tracking all snapshot branches:

```json
{
  "snapshots": [
    {
      "name": "snap_PMT_ph03_3a_R1",
      "project_id": "PMT",
      "phase": "ph03",
      "pass": "3a",
      "row": "R1",
      "state_description": "Post-Pass 3a: 223 Row 1 Signals committed, 0 CCIs",
      "created_at": "2026-05-16T00:00:00Z",
      "status": "VERIFIED",
      "ver_criteria_passed": ["VER-3a-01", "VER-3a-02"],
      "neon_branch_id": "br-xxxx"
    }
  ]
}
```

The registry is version-controlled alongside the codebase. The `neon_branch_id` field allows the utility to manage branches by ID rather than name.

---

## Current Snapshot State

The following snapshots should be created immediately to support ongoing Pass 3b testing:

| **Snapshot** | **State** | **Priority** | **Status** |
| --- | --- | --- | --- |
| `snap_PMT_ph03_3a_R1` | PMT Row 1, 223 Signals committed, 0 CCIs | **Immediate** | To create |
| `snap_NQPS_ph03_3a_R5` | NQPS all rows, Signals committed, 0 CCIs | High | To create |
| `snap_ROW_ph03_3a_R1` | ROW project Row 1, 223 Signals committed, 0 CCIs | High | To create |

Once `snap_PMT_ph03_3a_R1` exists, the following test branches can be created and run independently without re-executing Pass 3a:

- `test_PMT_ph03_3b_R1_dedup_off` — baseline, no deduplication
- `test_PMT_ph03_3b_R1_dedup_on` — deduplication enabled, confirms merge behaviour
- `test_PMT_ph03_3b_R1_batchsize10` — batch size sensitivity test
- `test_PMT_ph03_3b_R1_batchsize20` — batch size sensitivity test

---

## Relationship to Output Document Naming

Each test branch run produces a ledger export. The output document naming convention (`SysEngage_Test_Output_Naming_Convention_v0_2.md`) determines the filename. The run number in the output filename corresponds to the test branch scenario iteration, not a global run counter.

When a test branch is created from a snapshot, the Run counter for that scenario starts at 1. If the same scenario is re-run on a new test branch from the same snapshot, the Run counter increments.

Example: three Pass 3b dedup-on tests from `snap_PMT_ph03_3a_R1` produce:
- `PMT_Ph03_3b_CCIConstruction_R1_Run1.json`
- `PMT_Ph03_3b_CCIConstruction_R1_Run2.json`
- `PMT_Ph03_3b_CCIConstruction_R1_Run3.json`

Each corresponds to a distinct `test_PMT_ph03_3b_R1_dedup_on` branch cloned fresh from the snapshot.

---

## Rules

1. **Snapshot branches are read-only.** No mechanism execution writes to a snapshot branch. Snapshot branches are only written to by the `create_snapshot` and `promote_to_snapshot` operations.

2. **Test branches are disposable.** Every test branch is deleted after the ledger export is produced and analysed. Test branches are never reused.

3. **A snapshot is only created from a VERIFIED state.** A pass must have all decidable VER criteria passing before its snapshot is created. Creating a snapshot from an unverified state propagates defects into all downstream tests.

4. **DATABASE_URL_MAIN is never pointed at a test branch.** Main development work runs against the main branch only. Test branch DATABASE_URL is always set explicitly via environment variable for the duration of the test run.

5. **Snapshot names are immutable.** Once a snapshot is created and recorded in the registry, its name does not change. If the snapshot needs to be rebuilt (e.g. after a schema migration), the old snapshot is deleted and a new one created with the same name from a fresh verified run.

---

## Document End

End of SysEngage Test Environment — Neon Branch Management Specification v0.1.
