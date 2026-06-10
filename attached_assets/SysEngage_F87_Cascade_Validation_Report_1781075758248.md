# SysEngage — F87 Refinement-Driven Derivation: Cascade Validation Report

**Date:** 2026-06-10
**Scope:** PMT rows 1–5, Pass 3d (Requirement Derivation) + Pass 3e (Matching), under the refinement-driven cascade (RD Row 3 v0.13 / Row 4 v0.17, Matching v0.6, ledger v2.16).
**Runs reviewed:** R3_Run4, R3_Run5 (two Row-3 runs on the same Row 2); R4_Run5 (adds Row 4); R5_Run1 (adds Row 5).

---

## 1. Headline

Refinement-driven derivation (F87) is **validated at three of the four descents** and **fails at one**:

| Descent | Seed coverage | Path R | Verdict |
|---|---|---|---|
| Row 1 → 2 | 11/11 (Run19, prior) | live | ✅ validated |
| Row 2 → 3 | **19/19** (both R3_Run4 and R3_Run5) | live (path_r 12–19) | ✅ validated, reproducible |
| Row 3 → 4 | **0/24** | **path_r = 0** | ❌ **fails — Path R produces nothing** |
| Row 4 → 5 | **4/4** (R5_Run1) | live (path_r = 9) | ✅ validated |

The mechanism works (business→logical, physical→component); it is **specifically the Row 3 → Row 4 (logical → physical) descent that fails**, and the failure is genuine, not an artifact.

---

## 2. What works — and is now reproducible

- **Row 2 → 3 = 19/19 across two independent runs** (R3_Run4, R3_Run5) on the same Row 2. Every Row 2 seed is elaborated into Row 3. This is the descent that was 0/27 (R4_Run3) and 24/27 (R4_Run4) before the fixes; it is now full and stable. The provenance-blind seed-set fix (RD v0.13/v0.14) and BUG-2/BUG-3 fixes hold.
- **Row 4 → 5 = 4/4** (R5_Run1): all 4 Row 4 requirements elaborated into Row 5, path_r = 9. Path R works at the physical→component jump.
- **VER-3d-21 clean** in all runs — no `seed_set_size_mismatch`; the provenance-filter guard confirms no filtering crept back in.
- **Matching healthy** where rows are populated: D-rm-8 provenance-blind handling working (Row 3 pass: 20 `pre_linked`, 1 `refine_link`, 3 `no_candidates`, 8 `duplicate_merge`); 0 `no_match` anomalies; the row-native platform constraints land as `no_candidates` correctly.

---

## 3. The failure — Row 3 → Row 4, Path R produces zero

**Symptom.** At Row 4 derivation (R4_Run5 and R5_Run1, identical): `total_seeds = 24`, `path_r_count = 0`, `unrefined_count = 24`, 24 `elaboration_gaps`. None of the 24 Row 3 logical-design requirements is elaborated into a Row 4 physical requirement. The only Row 4 requirements (4 of them) are row-native platform constraints (R052–R055), which land as `no_candidates` in matching.

**It is NOT an idempotency false-skip.** The Row 4 derivation pass reports `idempotent = False`, `run_scenario = FirstRun` — Stage 2 ran fresh, assembled all 24 seeds, and Path R still returned nothing. (This rules out the BUG-3-style stale-cache hypothesis: seed assembly works — 24 seeds loaded — but Path R refined none of them.)

**Two root-cause candidates (need build-side confirmation):**

1. **Path R cannot elaborate logical → physical specifically.** Row 3→4 is the logical-design → physical jump — a different transformation from business→logical (Row 2→3, works) and physical→component (Row 4→5, works). The Path-R refinement prompt, the Row 4 ROW_GUIDANCE, or the response schema may fail on Row 3-style logical statements as input, returning zero usable children. The fact that the *adjacent* descents both work points at something specific to this row's input/guidance.

2. **CHK-3d-10 detects but does not enforce at Row 4 (the more serious finding).** 24 unrefined seeds were recorded as `elaboration_gaps`, yet the pass reports `execution_status = PartialSuccess` with `downstream_rerun_required = False`, and the pipeline proceeded to build Row 5. Per spec (RD v0.13 §CHK-3d-10), an unrefined seed is **extinction** — the check is a hard Non-Loss assertion that must re-prompt and, on persistent failure, record a **hard failure**, not a quiet PartialSuccess that lets downstream rows build on an incompletely-elaborated parent row. The guard *detected* the loss (24 gaps) but did not *enforce* it. This is the exact failure mode that removing the "terminal" exit and hardening CHK-3d-10 was meant to prevent.

**Consequence.** Row 5 (R5_Run1) was derived on top of a Row 4 that elaborated none of its parents. Row 4→5 reports 4/4, but that 4 is only the 4 row-native platform constraints — the 24 logical obligations that should have produced physical requirements are absent from Row 4 entirely, so they cannot propagate to Row 5. The design is silently incomplete below Row 3.

---

## 4. Secondary findings (non-blocking)

- **`seed_coverage.refined_count` is mis-reported.** At Row 3, runs report `refined_count: 11` while actual coverage is 19/19 (`unrefined_count: 0`, all 19 seeds appear in Row 3 `refines_refs`). The `unrefined_count` / `unrefined_seed_ids` are correct (so VER-3d-21 and CHK-3d-10 are not fooled), but `refined_count` itself undercounts. Because `seed_coverage` is the F87 acceptance metric, this field must be trustworthy — flag to the build. Metric bug, not a derivation bug.

- **Row 3 derivation is materially non-deterministic between runs.** Same Row 2 input → R3_Run4: 30 Row 3 reqs (5 row-native, types 13F/11S/6C); R3_Run5: 32 (11 row-native, 17F/12S/3C). Seed coverage is stable (always 19/19) but the *shape* of the Row 3 design varies run to run. Not a defect (both are valid, complete elaborations); a reproducibility watch-item — same class as the Row 2 subject-mix variance, one row down, somewhat larger.

---

## 5. Status against F87

F87's decisive test — does interrogative elaboration of R(n−1) generate the full child set on built output — **passes at Row 1→2, Row 2→3 (reproducibly), and Row 4→5; fails at Row 3→4.** F87 stays Open. It cannot close until the Row 3→4 descent reaches full seed coverage with `path_r > 0` at Row 4, and until CHK-3d-10 enforces (hard-fails) rather than merely detecting extinction.

---

## 6. Recommended actions

| # | Action | Owner | Priority |
|---|---|---|---|
| 1 | Diagnose why Path R returns 0 at Row 4 (logical→physical) — inspect the refinement prompt/response on Row 3 logical input and the Row 4 ROW_GUIDANCE | build | **High** |
| 2 | Fix CHK-3d-10 enforcement at Row 4: unrefined seeds must re-prompt and, on persistent failure, record a hard failure — not PartialSuccess with `downstream_rerun_required=False`. Downstream rows must not build on a row with extinct seeds | build | **High** |
| 3 | Fix `seed_coverage.refined_count` mis-count (undercounts vs actual coverage) | build | Medium |
| 4 | Row 3 (and lower) derivation non-determinism — record as watch-item; act only if a reproducibility requirement emerges | spec/tracker | Low (watch) |
| 5 | Re-run rows 1–5 after #1/#2; acceptance = seed coverage full at every descent, `path_r > 0` at every row ≥ 2, CHK-3d-10 hard-fails on any residual gap | build | gating for F87 closure |
