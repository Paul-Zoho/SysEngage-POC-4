# Bug Report — Stage 4a Enumeration Split Group Protection: Incorrect Scoping

**Date:** 16 May 2026
**Severity:** Medium — no analytical harm, but causes unnecessary Stage 4b AI calls and spurious execution_warnings entries
**Spec reference:** Row 3 Mechanism Spec v0.16 §4 Stage 4a Step 1; Row 4 Mechanism Spec v0.17 §4.4 Step 1
**Confirmed in:** PMT Run 17 (R1-How, member_count=4), NQPS Run 2 (6 false-positive warnings across R1 and R2)

---

## Description

Stage 4a's enumeration split group protection is firing for candidates that were NOT split by Stage 3a-pre. The protection should apply only to sub-signals from confirmed Stage 3a-pre splits — candidates whose source Signal appears in the current run's `enumeration_splits` record. Instead, it is applying to any candidate where `len(signal_refs)==1`, regardless of whether that Signal was split.

---

## Observed Behaviour

**PMT Run 17:**
- Row 1 produced zero enumeration splits (`splits=0` in AnalysisPass)
- SG049 was not split by Stage 3a-pre
- Stage 3a (AI) derived two Process CCIs from SG049 in a single derivation pass — normal AI behaviour
- Stage 4a incorrectly treated both as split sub-signals and routed them to Stage 4b as a protected group
- Warning fired: `stage4a_named_instance_routed` for ZC-R1-C-How, `member_count=4`

**NQPS Run 2:**
- Zero enumeration splits across all rows
- Six false-positive `stage4a_named_instance_routed` warnings:
  - ZC-R1-C-Why | Constraint | member_count=5
  - ZC-R2-C-How | Process | member_count=7
  - ZC-R2-C-How | Function | member_count=3
  - ZC-R2-C-Why | Goal | member_count=8
  - ZC-R2-C-Why | Constraint | member_count=2
  - ZC-R5-C-What | Attribute | member_count=2
- In every case the AI correctly returned Distinct (no merges resulted)
- NQPS shows higher false-positive rate than PMT because policy document Signals frequently produce multiple CCIs from a single Signal — the pattern `len(signal_refs)==1` is common

---

## Root Cause

The implementation's Stage 4a group protection check uses only one condition:

```python
# Current (incorrect) — checks only signal_refs length
if len(candidate.signal_refs) == 1:
    signal_id = candidate.signal_refs[0]
    if signal_id not in protected_groups:
        protected_groups[signal_id] = []
    protected_groups[signal_id].append(candidate)
```

The second condition — checking that the Signal id appears in `enumeration_splits` — is not being evaluated. This means any candidate produced by the AI from a single Signal enters the protection path, regardless of whether Stage 3a-pre split that Signal.

---

## Expected Behaviour

Per Row 4 Mechanism Spec v0.17 §4.4 Stage 4a Step 1:

> "A candidate is a confirmed split sub-signal if and only if BOTH of the following are true:
> - Its `signal_refs` contains exactly one Signal id, AND
> - That Signal id appears in the current run's `enumeration_splits` buffer"

Implementation check pattern from spec:

```python
split_signal_ids = {s['original_signal_id'] for s in enumeration_splits_buffer}

# Correct — both conditions required
if len(candidate.signal_refs) == 1 and candidate.signal_refs[0] in split_signal_ids:
    signal_id = candidate.signal_refs[0]
    # add to protected group
```

---

## Fix Required

In `step4_deduplication.py`, Stage 4a Step 1:

Add the `enumeration_splits_buffer` check as a second mandatory condition before adding a candidate to a protected group. The `enumeration_splits_buffer` is populated by `step3_cci_derivation.py` (Stage 3a-pre) and passed into the deduplication step.

```python
# Build the set of Signal ids that were actually split this run
split_signal_ids = {s['original_signal_id'] for s in enumeration_splits_buffer}

# Stage 4a Step 1 — identify confirmed split sub-signals only
protected_groups = defaultdict(list)
non_protected = []

for candidate in new_candidates:
    if (len(candidate.signal_refs) == 1
            and candidate.signal_refs[0] in split_signal_ids):
        # Confirmed split sub-signal — add to protected group
        protected_groups[candidate.signal_refs[0]].append(candidate)
    else:
        # Not a split sub-signal — normal pairwise evaluation
        non_protected.append(candidate)
```

---

## Impact if Not Fixed

- **Analytical correctness:** No impact — the AI correctly returns Distinct for false-positive groups in every observed case. No incorrect merges have been observed.
- **Performance:** Unnecessary Stage 4b AI calls for every false-positive group. On NQPS Run 2 this produced 6 unnecessary calls. On a dense policy document with many single-Signal CCIs, this could add significant latency.
- **Audit trail:** Spurious `stage4a_named_instance_routed` entries in `execution_warnings` make the run record misleading — a Practitioner reading the warnings would expect named-instance splits to be present, and finding none would create confusion.

---

## Verification

After applying the fix, run against:

1. **NQPS clean snapshot** — `execution_warnings` should contain zero `stage4a_named_instance_routed` entries (NQPS has no SG splits)
2. **PMT clean snapshot** — `execution_warnings` should contain exactly two `stage4a_named_instance_routed` entries, both for ZC-R5-C-Where (SG545 split, double-fire is expected and acceptable)
3. **Row 1 check** — no routing warnings for any Row 1 cell

---

## Related Spec Sections

- Row 3 Mechanism Spec v0.16 §4 Stage 4a Step 1 — "A candidate is a confirmed split sub-signal if and only if BOTH..."
- Row 4 Mechanism Spec v0.17 §4.4 Stage 4a Step 1 — implementation check pattern: `candidate.signal_refs[0] in {s['original_signal_id'] for s in enumeration_splits_buffer}`
- Row 3 Mechanism Spec v0.16 §11.2 OQ-3b-11 — resolved; this bug is a separate scoping issue in the implementation of the fix for OQ-3b-11
