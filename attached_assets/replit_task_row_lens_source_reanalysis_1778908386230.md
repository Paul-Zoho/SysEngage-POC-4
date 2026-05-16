# Replit Agent Task — Implement Row-Lens Source Re-Analysis (Phase 3 Pass 3a)

**Task type:** New mechanism implementation + service architecture refactor
**Spec version:** SysEngage_Row_4_Mechanism_Row_Lens_Source_Reanalysis_v0_1.md
**Date:** 13 May 2026
**Tracker:** SysEngage_Issues_Tracker_v0_24.md — F35 Action-In-Progress

---

## Before You Start — Tell Me About The Current Implementation

Before writing any code, I need you to read the current codebase and answer the following questions. Do not proceed to implementation until you have answered all of them and I have confirmed the plan.

**Q1 — Current mechanism module structure:** What does `mechanisms/` currently look like? List all files and directories. Specifically: is `source_capture/` a flat directory (all Pass files at the same level) or does it have sub-directories? What are the exact filenames?

**Q2 — Current orchestration entry point:** How does the system currently invoke `source_capture/`? Is there an orchestrator or runner (e.g., `core/orchestrator.py`, `core/runner.py`, a FastAPI endpoint, or a direct function call from a route)? Show me the entry point.

**Q3 — Current AnalysisPass production:** How does Source Capture currently build and write its AnalysisPass record? Show me the relevant code. Specifically: where is `outputs.row_lens_data` currently handled (it should be absent from Source Capture — confirm this)?

**Q4 — Current ProjectProfile model:** Does a `ProjectProfile` model exist? Show me its current schema. Does it have a `concern_threshold` field? A `chunk_match_threshold` field? A `residual_batch_size` field?

**Q5 — Current ledger transaction pattern:** How does Source Capture wrap its entity writes in a Postgres transaction? Is there a shared transaction helper or does each mechanism manage its own session/commit?

**Q6 — Current identifier sequence pattern:** How are Source IDs (S###), Segment IDs (SEG###), SourceAtom IDs (SA###), and AnalysisPass IDs (P###) currently assigned? Is there a shared sequence helper, a Postgres sequence, or max+1 logic per entity?

**Q7 — Current test structure:** Where do existing tests for Source Capture live? What test fixtures exist? Are there shared test helpers (e.g., a ledger factory, a test project setup)?

**Q8 — Current AI API integration:** Is there any existing AI (Claude/Anthropic) API client code in the codebase? If yes, show me the client setup. If no, confirm it does not exist yet.

Wait for my confirmation before proceeding.

---

## Context — What This Task Is Building

SysEngage is a structured requirements analysis tool built on the Zachman Enterprise Architecture Framework. Analysis proceeds row by row (Row 1 through Row 6). Each row re-analyses the original source material through its own analytical lens.

**Phase 1 (already implemented):** Source Capture — reads input documents, produces Source/Segment/SourceAtom entities. Deterministic, LPM-only.

**Phase 3 (this task):** Row-Lens Source Re-Analysis — for each active row, reads all Sources (stream 1) and the prior row's Domains + Requirements (stream 2, empty at Row 1), applies the row's Zachman analytical lens, and classifies every item as:
- **Signal** — content is clear and classifiable from this row's lens
- **Concern** — content is ambiguous from this row's lens; requires Practitioner clarification
- **OutOfScope** — content has no analytical relevance at this row's abstraction level

This is the first AI-involving mechanism in the system. It calls Claude Sonnet via the Anthropic API.

**The primary spec document for this task is:** `SysEngage_Row_4_Mechanism_Row_Lens_Source_Reanalysis_v0_1.md`

Read the full spec before writing any code. Every implementation decision in the spec is intentional.

---

## Service Architecture Requirement — Read This Carefully

**This is the most important architectural requirement in this task.** Before building the mechanism, restructure the codebase so that mechanisms are isolated services.

### Why service isolation matters

Source Capture was built as a mechanism module. Row-Lens Source Re-Analysis is a different mechanism with different dependencies, a different mode profile (AI-involving vs LPM-only), and different configuration. Future mechanisms will differ again. If mechanisms share code without explicit boundaries, changes to one mechanism will risk breaking others. At scale, this becomes unmanageable.

The goal is: **changing, replacing, or improving one mechanism should not require touching any other mechanism's code.**

### The service isolation pattern to implement

Each mechanism is an isolated service with three characteristics:

**1. A single public contract.** Each mechanism exposes exactly one public function (the orchestration entry point). Everything else is private to the mechanism. The orchestrator calls the public function; it does not reach into mechanism internals.

```
# Public contract — the ONLY thing the orchestrator calls
mechanisms/row_lens_source_reanalysis/__init__.py

def run(
    project_id: str,
    row_ref: int,
    practitioner_id: str,
    config: MechanismConfig
) -> MechanismResult:
    ...
```

No other file in `mechanisms/row_lens_source_reanalysis/` is imported from outside the directory.

**2. All dependencies injected, nothing imported from other mechanisms.** The mechanism receives its inputs (ledger session, configuration, AI client) as arguments to `run()`. It does NOT import from `mechanisms/source_capture/` or any other mechanism. It reads from the ledger via the injected session. Cross-mechanism coordination happens via the ledger, not via direct code dependencies.

**3. Shared infrastructure in a common layer, not in any mechanism.** If both Source Capture and Row-Lens Source Re-Analysis need the same thing (e.g., AnalysisPass construction, identifier sequence logic, Pydantic models that mirror the canonical ledger schema), that shared logic lives in a `core/` or `shared/` layer — NOT duplicated in each mechanism and NOT in one mechanism that another imports.

### Specific shared infrastructure to extract

After answering the pre-start questions, identify which of the following currently live inside `mechanisms/source_capture/` and need to be moved to `core/` before adding the new mechanism:

- **Identifier sequence logic** (the pattern for generating S###, SEG###, P### etc.) → `core/identifiers.py`
- **AnalysisPass construction and commit** (the pattern for building and writing the AnalysisPass record) → `core/analysis_pass.py`
- **Ledger transaction wrapper** (the single-transaction commit pattern) → `core/ledger.py` or existing session management
- **Pydantic models mirroring canonical ledger schemas** (Signal, Concern, AnalysisPass, Source, etc.) → `schemas/` (if not already there)
- **Mode discipline decorator** (the `@pass_mode("LPM")` pattern) → `core/mode_discipline.py` (if not already there)

Do NOT copy these into the new mechanism. Extract them to shared infrastructure first, update Source Capture to use the shared versions, confirm Source Capture tests still pass, then build the new mechanism using the shared infrastructure.

### What isolation looks like in practice

**Before (coupled):**
```
mechanisms/
  source_capture/
    __init__.py         # contains identifier logic, analysispass construction, etc.
    pass_0_read_witness.py
    ...
```

**After (isolated services with shared infrastructure):**
```
core/
  identifiers.py          # shared identifier sequence logic
  analysis_pass.py        # shared AnalysisPass construction + commit
  mode_discipline.py      # shared mode decorator
  ledger.py               # shared session/transaction management

schemas/
  signal.py               # Pydantic: Signal model (canonical v2.12)
  concern.py              # Pydantic: Concern model (canonical v2.12)  
  analysis_pass.py        # Pydantic: AnalysisPass model (canonical v2.12)
  source.py               # Pydantic: Source model (already exists)
  ...

mechanisms/
  source_capture/
    __init__.py           # public contract: run(project_id, ...) -> MechanismResult
    pass_0_read_witness.py
    pass_0a_source_capture.py
    pass_0b_segment_construction.py
    pass_0c_sourceatom_splitting.py
    # NO identifier logic here — uses core/identifiers.py
    # NO AnalysisPass construction here — uses core/analysis_pass.py

  row_lens_source_reanalysis/
    __init__.py           # public contract: run(project_id, row_ref, ...) -> MechanismResult
    stage1_chunk_assembly.py
    stage2_chunk_classification.py
    stage2_residual_classification.py
    stage3_deduplication.py
    stage4_conflict_sweep.py
    entity_production.py
    analysis_pass_production.py
    prompts/
      chunk_classification_prompt.py
      residual_classification_prompt.py
      conflict_sweep_prompt.py
      lens_definitions.py
    schemas/
      classification_response_schema.py
      conflict_sweep_response_schema.py
```

### Phase 1 refactor — may require Source Capture restructuring

If the pre-start questions reveal that Source Capture currently contains logic that should be in shared infrastructure (identifier sequences, AnalysisPass construction, mode discipline), refactor Source Capture first before adding the new mechanism. The steps are:

1. Extract shared logic to `core/` and `schemas/`
2. Update Source Capture to import from `core/` and `schemas/`
3. Run existing Source Capture tests — all must pass before proceeding
4. Only then build the new mechanism

If Source Capture is already well-structured and the shared infrastructure is already separate, confirm this in your pre-start answers and proceed directly to mechanism implementation.

---

## What To Build — The Row-Lens Source Re-Analysis Mechanism

Read `SysEngage_Row_4_Mechanism_Row_Lens_Source_Reanalysis_v0_1.md` in full. The implementation must follow the spec exactly. Key points:

### Four stages (§4 in the Row 4 Mechanism Spec)

**Stage 1 — Domain-driven chunk assembly (DM, no AI)**
- For each Row N-1 Domain: extract subject/object noun phrases from its Requirements using spaCy (`en_core_web_sm`)
- Fuzzy-match Sources against Domain vocabulary (token overlap ≥ `concern_threshold` from ProjectProfile, default 0.6)
- Build chunk list + residual list
- Record `chunk_assignment` audit: `{source_id: [domain_id, ...]}`
- At Row 1: skip entirely; all Sources are residual

**Stage 2 — Per-chunk + residual classification (IM+DM, AI-involving)**
- For each Domain chunk: one Claude Sonnet API call using `chunk_classification_prompt`
- For residual Sources: one or more API calls (batched at `residual_batch_size`, default 50) using `residual_classification_prompt`
- Three-step classification in the prompt: (1) relevance gate → OutOfScope if irrelevant; (2) confidence score → Signal if ≥ T1, Concern if < T1
- T1 = `ProjectProfile.concern_threshold` (default 0.65)
- Validate AI response against `ClassificationResponseItemModel`
- Produce Signal, Concern, or OutOfScope entry per item

**Stage 3 — Deduplication (DM, no AI)**
- For Sources assigned to multiple chunks: resolve cross-chunk classification conflicts by rule (see Row 4 Mechanism Spec §4.3 for all rules)
- Flag genuine conflicts for Stage 4

**Stage 4 — Cross-chunk conflict sweep (IM+DM, AI-involving)**
- One Claude Sonnet API call presenting all conflict flags
- AI determines: genuine contradiction → new Concern; complementary classification → no new entity
- Existing Signals are NEVER removed
- Skip if no conflicts

### The three classification outcomes

Every item in the classification queue (Source or Requirement) produces exactly one of:
- **Signal entity** (SG###) — written to ledger
- **Concern entity** (CN-NNN) — written to ledger, state = Open
- **OutOfScope** — NOT a ledger entity; id recorded in `AnalysisPass.outputs.row_lens_data.out_of_scope_refs`

The invariant MUST hold:
```
stream1_source_count + stream2_requirement_count
    = signal_count_produced + concern_count_produced + out_of_scope_count
```

If the invariant fails: set `execution_status = "Failed"`, populate `failure_reason`, do NOT commit Signal/Concern entities.

### AnalysisPass population (§7 in the Row 4 Mechanism Spec)

The `outputs.row_lens_data` sub-structure must be fully populated:
```json
{
  "row_ref": 3,
  "stream1_source_count": 272,
  "stream2_requirement_count": 45,
  "stream2_domain_count": 8,
  "signal_count_produced": 285,
  "concern_count_produced": 12,
  "out_of_scope_count": 20,
  "out_of_scope_refs": ["S001", "S017"],
  "chunk_assignment": {"S003": ["D001", "D003"]},
  "ai_model_fingerprints": ["claude-sonnet-4-20250514 (chunk D001)", "..."],
  "concern_threshold_used": 0.65,
  "chunk_match_threshold_used": 0.6
}
```

### Prompt templates (§10.5 in Row 4 Understanding v0.2, §9.4)

Prompts live in `prompts/` within the mechanism directory. They are NOT inline strings in the classification code. The row-lens content for each row (Row 1 through Row 6) lives in `prompts/lens_definitions.py` as a dictionary keyed by row_ref integer — content verbatim from Row 4 Mechanism Spec §3.1 and §4.2 Stage 2 (lens_definitions are fully specified there).

All AI invocations request structured JSON output. Response schemas are Pydantic models in `schemas/` within the mechanism directory.

### Canonical entity schemas

Signal and Concern Pydantic models must mirror canonical ledger spec v2.12 exactly:

**Signal (SG###):**
- signal_id: str, pattern `^SG\d{3}$`
- signal_type: Literal["Normative","Intent","Actor","Concern","Ambiguity","Quality"]
- row_target: Literal["1","2","3","4","5","6"]
- description: str (min_length=1)
- source_refs: list[str] (min_length=1) — Source.source_id or Requirement.requirement_id
- confidence: float (0.0–1.0)
- derived_from_concern_id: str | None (pattern `^CN-\d{3}$` when present, null at production time)

**Concern (CN-NNN):**
- concern_id: str, pattern `^CN-\d{3}$`
- source_refs: list[str] (min_length=1)
- description: str (min_length=1)
- state: Literal["Open","Resolved","Dispositioned"] — always "Open" at production
- produced_in_row: Literal["1","2","3","4","5","6"]
- practitioner_id: str
- dispositioned_with_outcome: Literal["NotApplicable","Indeterminate"] | None — null at production
- disposition_rationale: str | None — null at production
- confidence: float (0.0–1.0)

---

## What NOT To Build

- No Practitioner UI for Concern review or Signal review (Phase 9/10 UI is out of scope for this task)
- No Phase 9 Question generation (separate mechanism, future task)
- No Phase 10 Concern resolution (separate mechanism, future task)
- No ZachmanCell, CellContentItem, Domain, or Requirement production (Phase 3 Passes 3b–3d, future tasks)
- No replit.md update (Replit Agent maintains; note any needed updates in a comment)

---

## Verification Criteria (Automated — Must Pass)

After implementation, run verification against the decidable criteria from Row 4 Mechanism Spec §8.1. All 17 criteria must pass:

| Criterion | Check |
|---|---|
| CN-1 | Every Concern.concern_id matches `^CN-\d{3}$` |
| CN-2 | Every Concern.source_refs has ≥ 1 entry |
| CN-3 | Every Concern.source_refs entry references existing Source/SourceAtom/Requirement |
| CN-4 | Any Requirement in Concern.source_refs has row_target < Concern.produced_in_row |
| CN-5 | Every Concern.state = "Open" at production |
| CN-6 | Every Concern.produced_in_row = str(row_ref) |
| SG-1 | Every Signal.source_refs entry references existing Source or Requirement |
| SG-2 | Any Requirement in Signal.source_refs has row_target < Signal.row_target |
| SG-3 | Every Signal.row_target = str(row_ref) |
| ME-1 | No source_id in both Signal.source_refs and Concern.source_refs (per chunk) |
| OS-1 | Every OutOfScope item's id appears in out_of_scope_refs |
| OS-2 | No id in out_of_scope_refs appears in any Signal/Concern source_refs |
| INV-1 | stream1 + stream2 = signals + concerns + out_of_scope |
| R1-1 | At row_ref=1: stream2_count=0, no Requirement ids in Signal/Concern source_refs |
| AP-1 | Phase 3 AnalysisPass with mechanism="RowLensSourceReanalysis" exists |
| AP-2 | execution_status ∈ {Completed, CompletedWithWarnings} |
| AP-3 | mode_active="IM"; "LPM" ∈ declared_transformation_modes |

---

## Test Fixtures To Run

After implementation run these fixtures in order:

**Fixture 1 — Row 1, stream 2 empty (simplest case)**
- Input: Pocket Money document Sources (already in ledger from Source Capture)
- row_ref = 1
- Expected: stream2_requirement_count = 0; R1-1 criterion passes; INV-1 holds; AnalysisPass Completed

**Fixture 2 — Row 2, stream 2 active**
- Input: same Pocket Money Sources + Row 1 Requirements and Domains (requires Row 1 Phase 3d to have run — if not yet implemented, mock 2–3 synthetic Requirements and 1 Domain for this fixture)
- row_ref = 2
- Expected: INV-1 holds; all Concerns have produced_in_row="2" and state="Open"; AnalysisPass Completed

**Fixture 3 — Row 1 Understanding v1.2 stress test (272 Sources)**
- Input: Row 1 Understanding v1.2 Sources (from existing stress test TST-010, 272 Sources)
- row_ref = 2
- Expected: stream1_source_count = 272; INV-1 holds; no run-terminating invariant failures; AnalysisPass Completed or CompletedWithWarnings

Report results from all three fixtures before marking the task complete.

---

## Implementation Order

1. **Answer pre-start questions** — read codebase, answer Q1–Q8 above
2. **Confirm plan with me** — I will review your pre-start answers and confirm the service isolation refactor scope before you write any code
3. **Extract shared infrastructure** (if needed) — move shared logic to `core/` and `schemas/`; confirm Source Capture tests pass
4. **Add ProjectProfile fields** — `concern_threshold` (float, default 0.65), `chunk_match_threshold` (float, default 0.6), `residual_batch_size` (int, default 50)
5. **Build mechanism module** — `mechanisms/row_lens_source_reanalysis/` per the module structure in Row 4 Mechanism Spec §3.1
6. **Write prompt templates** — `prompts/lens_definitions.py` (row-lens content from Row 3 Spec §5.2), `prompts/chunk_classification_prompt.py`, `prompts/residual_classification_prompt.py`, `prompts/conflict_sweep_prompt.py`
7. **Write response schemas** — Pydantic models for AI response validation
8. **Add Concern SQLAlchemy model** — table for Concern entities per canonical v2.12 schema; CN-NNN identifier constraint
9. **Add Signal.derived_from_concern_id column** — nullable, FK to Concern, if not already present
10. **Wire orchestration** — `mechanisms/row_lens_source_reanalysis/__init__.py` orchestrates Stage 1 → 2 → 3 → 4 → AnalysisPass production in one transaction
11. **Add API endpoint** (if applicable) — endpoint to invoke Phase 3 Pass 3a for a given project_id and row_ref; consistent with existing Source Capture endpoint pattern
12. **Write tests** — pytest tests covering all 17 decidable criteria + 3 fixtures above
13. **Run verification** — report fixture results

---

## References

- `SysEngage_Row_4_Mechanism_Row_Lens_Source_Reanalysis_v0_1.md` — **primary spec** (read this first)
- `SysEngage_Row_4_Understanding_v0_2.md` — framework (§9.4 prompt architecture, §9.5 non-determinism, §9.6 OutOfScope, §10 Mechanism B implementation patterns)
- `SysEngage_Row_4_Applied_to_SysEngage_v0_2.docx` — technology stack commitments (Python 3.12+, FastAPI, Neon PostgreSQL, Pydantic v2, Claude Sonnet, pytest)
- `sysengage_minimal_ledger_spec_v2_12.md` — canonical entity schemas (Signal, Concern, AnalysisPass — authoritative)
- `SysEngage_Issues_Tracker_v0_24.md` — F35 (current active finding), F36 (deferred threshold validation)

---

## A Note on Non-Determinism

This mechanism calls Claude Sonnet. The AI's Signal/Concern descriptions will vary between runs on identical input — this is expected and acceptable. The 17 decidable verification criteria (structural conformance) must pass on every run. The content of descriptions is not automated-verifiable and does not need to be.

When writing tests: test structural properties, not description text. Do not assert that a specific Source produced a specific Signal description. Do assert that every Signal.source_refs entry references a real Source or Requirement.

---

*End of Replit Agent Task — Row-Lens Source Re-Analysis (Phase 3 Pass 3a)*
