# SysEngage Row 4 Mechanism: Row-Lens Source Re-Analysis

**Implementation specification — depth tier (i)+**

Filename: SysEngage_Row_4_Mechanism_Row_Lens_Source_Reanalysis_v0_2.md

Version: 0.2 (Reverted to SINGLE-STREAM per finding F83 — the dual-stream Pass-3a model is rejected. Realises Row 3 Reanalysis v0.4.)

Date: 03 June 2026

**Purpose.** Implementation specification for the Row-Lens Source Re-Analysis mechanism (Mechanism B). Translates the Row 3 Mechanism Specification (SysEngage_Row_3_Mechanism_Row_Lens_Source_Reanalysis_v0_4.md, single-stream) into Row 4 implementation detail consistent with the SysEngage v1 architectural commitments and canonical ledger spec v2.13. At depth tier (i)+ per Row 4 Understanding §8: architectural specification + verification criteria + test fixtures. Suitable for handoff to an implementation agent.

**Status.** v0.2 — single-stream. The dual-stream model (v0.1) is reverted per finding F83. F36 deferred (T1 empirical validation after verification).

**Changes from v0.1 (this version — SINGLE-STREAM REVERT, finding F83).** The dual-stream Pass-3a model is rejected and removed; this spec realises the single-stream Row 3 v0.4. Rationale (authoritative record in Issues Tracker F83/F93): a requirement atomises through Pass 3a → Signals → CCIs → Domains → Requirements; no requirement-level thread survives, so the stream-2 re-analysis of upstream Requirements gave only diffuse signal-level provenance. Cross-row «refine» traceability is now carried by `Requirement.refines_refs` (ledger v2.13, established by the Requirement Matching service). Concretely: (1) §1 operational location/applicability — four-stage dual-stream → two-stage single-stream. (2) §3 module structure / decisions / dependencies — chunk-assembly and stream-2 modules removed. (3) §4 — Stage 1 (Domain-driven chunk assembly), Stage 3 (chunk deduplication), Stage 4 (cross-chunk conflict sweep) removed; the mechanism is Stage 1 Source classification + Stage 2 contradiction sweep. (4) §5 Pydantic/SQLAlchemy — stream-2 / chunk fields removed. (5) §7 row_lens_data — stream2_* counts removed; invariant simplified. (6) §9/§10 fixtures and edge cases — stream-2 / chunk cases removed or reframed. (7) Ledger v2.12 → v2.13. F35's dual-stream portion reversed by F83 — see Tracker.

**Excludes.** Per Row 4 Understanding §8.1 depth tier (i)+: NO pseudo-code, NO function signatures, NO code-level interface definitions. The implementation agent derives these from the architectural specification + canonical schemas. The spec describes WHAT each stage does and WHAT correctness looks like.

---

## 1. Mechanism Identification

| **Mechanism name** | Row-Lens Source Re-Analysis |
| --- | --- |
| **Row 3 Mechanism Spec reference** | SysEngage_Row_3_Mechanism_Row_Lens_Source_Reanalysis_v0_4.md (single-stream) — all sections |
| **Operational location** | Phase 3 Pass 3a. Executes once per active row at Phase 3 entry. Two stages: Stage 1 (Source classification, IM+DM), Stage 2 (contradiction sweep, IM+DM). (Single-stream — finding F83.) |
| **Mechanism class** | AI-involving. IM for classification acts (Stage 1 classification, Stage 2 contradiction sweep). DM for entity production and AnalysisPass recording. LPM preservation constraint throughout. |
| **Module location** | `mechanisms/row_lens_source_reanalysis/` directory. See §3.1 for file structure. |
| **Row applicability** | Row-sequential. Single-stream at every row: the Source material is classified through the row's lens. (No stream-2 dependency on the row above — finding F83.) |
| **Mechanism Stakeholder** | None (D-B3, OQ-B3 dissolved). SH001 covers deterministic structural review. SG-01 covers all Concern disposition. SG-03 carries execution attribution via AnalysisPass. |

---

## 2. Cross-References

| **Source** | **Reference** | **What this provides** |
| --- | --- | --- |
| **Row 4 Understanding** | §10 Mechanism B Framework | Implementation framework: module structure, entity production patterns, AnalysisPass population, prompt template management (the chunk-assembly portion is superseded by the single-stream revert, F83) |
| **Row 4 Understanding v0.2** | §9.4 Prompt Architecture Pattern | Prompt template registry, parameterisation contract, response schema, lens definition locus |
| **Row 4 Understanding v0.2** | §9.5 Non-Determinism Handling | Decidable vs plausibility split; re-run semantics; AI model fingerprinting |
| **Row 4 Understanding v0.2** | §9.6 OutOfScope Classification Framework | Relevance gate separation; out_of_scope_refs recording; OS-1/OS-2 validation |
| **Row 4 Applied v0.2** | All sections | Common architectural commitments: Python 3.12+, FastAPI, Neon PostgreSQL via SQLAlchemy + Alembic, Pydantic v2, Claude Sonnet via Anthropic API, pytest, transactional discipline |
| **Row 3 Mechanism Spec v0.4** | All sections | Architectural spec (single-stream): two-stage pass structure, three classification outcomes, row-specific lens definitions (§5), verification criteria (§9), edge cases (§10) |
| **Canonical Ledger v2.13** | Signal, Concern, AnalysisPass element types | Authoritative schemas. Pydantic models in schemas/ mirror these. Concern identifier CN-NNN; nine attributes; source_refs list. |
| **Tracker (current)** | F35, F36, F83, F93 | Architectural decision history; F83 = single-stream revert (reverses F35's dual-stream portion) |

---

## 3. Architectural Approach

### 3.1 Module structure

```
mechanisms/row_lens_source_reanalysis/
  __init__.py                              # Orchestration entry point
  stage1_source_classification.py         # IM+DM: Source AI classification + entity production
  stage2_contradiction_sweep.py           # IM+DM: contradiction sweep AI invocation + Concern production
  entity_production.py                    # DM: Shared Signal/Concern/OutOfScope recording
  analysis_pass_production.py             # DM: AnalysisPass record construction + commit
  prompts/
    source_classification_prompt.py       # Template: row-lens Source classification
    contradiction_sweep_prompt.py         # Template: contradiction sweep
    lens_definitions.py                    # Row-specific lens content (from Row 3 Spec §5.2)
  schemas/
    classification_response_schema.py     # Pydantic: AI response validation for classification
    contradiction_sweep_response_schema.py # Pydantic: AI response validation for contradiction sweep
```

### 3.2 Major design decisions

- **Single transactional ledger write** — all entities produced by the mechanism (Signals, Concerns, AnalysisPass) committed atomically in one Postgres transaction at the end of the mechanism execution. If any stage fails, the entire transaction rolls back. Per Row 4 Applied §5 transactional discipline.

- **AI invocations outside the transaction** — AI API calls are made before the Postgres transaction opens. Results are held in memory. The transaction writes only the validated, deterministic entity set. This separates non-deterministic AI I/O from deterministic ledger writes.

- **Prompt templates as separate modules** — lens content and prompt structure live in `prompts/` and can be updated independently of classification logic. The `lens_definitions.py` file is the single source of truth for row-specific lens content; it mirrors Row 3 Mechanism Spec §5.2 verbatim.

- **Pydantic validation at AI response boundary** — AI responses are immediately parsed against the response schema (`classification_response_schema.py`). Validation failure at this boundary produces a PartialSuccess execution status; valid items proceed to entity production; invalid items recorded in AnalysisPass failure detail.

- **concern_threshold from ProjectProfile** — T1 is read from `ProjectProfile.concern_threshold` at mechanism invocation. Default 0.65 (provisional, F36). Not hard-coded. Per-row override read from `ProjectProfile.concern_threshold_overrides[row_ref]` if present.

- **Single-stream classification** — the mechanism classifies the Source set directly through the row's lens; there is no Domain-chunk assembly from the row above (finding F83). Large Source sets are processed in sub-batches (`ProjectProfile.source_batch_size`, default 50). No NLP subject/object extraction and no fuzzy-match threshold are required (those served the now-removed chunk assembly).

### 3.3 Dependencies

- **Claude Sonnet via Anthropic API** — per Row 4 Applied AI Model commitment
- **SQLAlchemy 2.x** — ORM for entity persistence
- **Pydantic v2** — entity validation and AI response schema validation
- **anthropic Python SDK** — API client for Claude invocations
- **Standard library** — typing, dataclasses, uuid for support

(spaCy is no longer required — it served the removed Stage 1 chunk-assembly subject/object extraction; single-stream classification needs no NLP pre-processing.)

---

## 4. Stage-by-Stage Implementation

### 4.1 Stage 1 — Source Classification

**Mode:** IM (AI invocation) + DM (entity production). LPM preservation constraint: Source.source_text is never modified.

**Input handling:**
- Read all Source entities from ledger (the classification input)
- Read all SourceAtom entities (where present)
- Batch Sources into sub-batches of configurable size (`ProjectProfile.source_batch_size`, default 50) if the set is large. Each sub-batch is one AI invocation.

**Per-batch AI invocation:**
- Construct prompt from `source_classification_prompt.py` template with parameters: `{row_ref}`, `{lens_content}` (from `lens_definitions.py[row_ref]`), `{sources}` (list of source_id + source_text), `{concern_threshold}`.
- Call Claude Sonnet API. Record AI model version fingerprint.
- Parse response against `classification_response_schema.py`. Schema: `{items: [{item_id: string, classification: "Signal"|"Concern"|"OutOfScope", confidence: float, signal_type: string, description: string}]}`.
- Validation failure: record malformed items in AnalysisPass failure detail; proceed with valid items (PartialSuccess).

**Three-step classification prompt structure:** the `source_classification_prompt.py` instructs the AI to evaluate each item in two steps:
1. Relevance gate: is this item relevant to the row's analytical abstraction level? (Yes/No)
2. If Yes: assess confidence that it classifies clearly (Signal) vs ambiguously (Concern). Return confidence score.
3. If No: classify as OutOfScope.

The concern_threshold is passed to the prompt as context but the DM entity-production step applies it — the AI returns the confidence score; the implementation decides Signal vs Concern based on whether confidence ≥ T1.

**Entity production (DM) — for each valid AI response item:**
- Classification = "OutOfScope": append source_id to out_of_scope_refs. No entity produced.
- Classification = "Signal" (confidence ≥ concern_threshold): produce Signal entity. source_refs = [item_id] (a Source.source_id or SourceAtom.atom_id). signal_type from AI. row_target = str(row_ref). description from AI. confidence from AI. derived_from_concern_id = null.
- Classification = "Concern" (confidence < concern_threshold, or AI explicitly classified as Concern): produce Concern entity. concern_id = next CN-NNN. source_refs = [item_id] (Source/SourceAtom id only). description from AI. state = Open. produced_in_row = str(row_ref). practitioner_id from invocation context. confidence from AI.

### 4.2 Stage 2 — Contradiction Sweep

**Mode:** IM (AI invocation) + DM (Concern production). LPM constraint throughout.

**Input handling:**
- Receives all Signals and Concerns produced in Stage 1.
- The sweep looks for items in mutual contradiction across the classified Source set (two or more Sources whose classified content conflicts at this row's lens). If the produced set is large, the sweep is sub-batched; cross-batch contradictions are captured by presenting batch summaries in a final reconciliation invocation.

**AI invocation:**
- Construct prompt from `contradiction_sweep_prompt.py` with parameters: `{row_ref}`, `{lens_content}`, `{signals}` and `{concerns}` (id + description), `{sources}` (id + source_text for the referenced items).
- Call Claude Sonnet API. Record AI model version fingerprint.
- Parse response against `contradiction_sweep_response_schema.py`. Schema: `{contradictions: [{source_ids: [string], is_genuine_contradiction: bool, rationale: string}]}`.

**Entity production (DM):**
- For each contradiction where `is_genuine_contradiction = true`: produce one new Concern entity. source_refs = the conflicting source_ids. description = AI rationale string. state = Open. concern_id = next CN-NNN. produced_in_row = str(row_ref).
- For each where `is_genuine_contradiction = false`: no new entity.
- Existing Signals from Stage 1 are NEVER removed by Stage 2, regardless of outcome.

### 4.3 AnalysisPass Record Production

**Mode:** DM. Fully deterministic. Runs after both stages complete.

**AnalysisPass attributes:**
- pass_id: next available P### in sequence
- pass_type: "Per-row"
- mechanism: "RowLensSourceReanalysis" (exact string)
- execution_status: "Completed" (or "Failed"/"PartialSuccess" — see §10.4)
- mode_active: "IM"
- declared_transformation_modes: ["IM", "DM", "LPM"]
- outputs.row_lens_data: (see §7.2 for full sub-structure)
- outputs.mode_violations: [] on clean run
- pass_started_at: timestamp recorded at mechanism invocation entry
- pass_completed_at: timestamp recorded at AnalysisPass commit
- elapsed_ms: derived from timestamps
- confidence: mean of all AI invocation confidence scores for this run
- ai_model_fingerprints: list of AI model versions used across all invocations (one entry per invocation)

**Invariant enforcement (before commit):**
`stream1_source_count = signal_count_produced + concern_count_produced + out_of_scope_count`

If invariant fails: set execution_status = "Failed"; populate failure_reason with count discrepancy detail; commit AnalysisPass with Failed status; roll back Signal/Concern entity writes; raise mechanism execution error.

---

## 5. Schema and Validation

### 5.1 Pydantic models (in-memory)

**SignalModel** — mirrors canonical ledger spec v2.13 Signal attributes:
- signal_id (str, pattern `^SG\d{3}$`)
- signal_type (Literal["Normative","Intent","Actor","Concern","Ambiguity","Quality"])
- row_target (Literal["1","2","3","4","5","6"])
- description (str, min_length=1)
- source_refs (list[str], min_length=1) — each entry references Source.source_id or SourceAtom.atom_id (single-stream: Source content only, finding F83)
- sourceatom_refs (list[str], optional)
- confidence (float, ge=0.0, le=1.0)
- derived_from_concern_id (str | None, pattern `^CN-\d{3}$` when present)

**ConcernModel** — mirrors canonical ledger spec v2.13 Concern attributes:
- concern_id (str, pattern `^CN-\d{3}$`)
- source_refs (list[str], min_length=1)
- description (str, min_length=1)
- state (Literal["Open","Resolved","Dispositioned"])
- produced_in_row (Literal["1","2","3","4","5","6"])
- practitioner_id (str, min_length=1)
- dispositioned_with_outcome (Literal["NotApplicable","Indeterminate"] | None)
- disposition_rationale (str | None)
- confidence (float, ge=0.0, le=1.0)

**AnalysisPassModel** — extends base AnalysisPass with row_lens_data:
- All base AnalysisPass attributes per canonical ledger spec v2.13
- outputs.row_lens_data: RowLensDataModel (see §7.2)

**ClassificationResponseItemModel** — validates per-item AI response:
- item_id (str)
- classification (Literal["Signal","Concern","OutOfScope"])
- confidence (float, ge=0.0, le=1.0)
- description (str)

**ContradictionSweepResponseItemModel** — validates per-contradiction AI response:
- source_ids (list[str])
- is_genuine_contradiction (bool)
- rationale (str)

### 5.2 SQLAlchemy models (persistence)

Signal, Concern, AnalysisPass tables follow the canonical ledger spec v2.13 attribute set. No non-canonical attributes at persistence layer. The `outputs` field on AnalysisPass is a PostgreSQL JSONB column; `row_lens_data` sub-structure is stored within it.

Concern table: `concern_id` column uses the `^CN-\d{3}$` pattern enforced by Postgres CHECK constraint (consistent with Source Capture approach for S###, SEG###, SA###).

### 5.3 Identifier assignment strategy

- Signal: sequential SG### starting from max existing SG### in ledger + 1. Thread-safe via Postgres sequence.
- Concern: sequential CN-NNN starting from max existing CN-NNN in ledger + 1. Postgres sequence on the numeric portion.
- AnalysisPass: sequential P### per existing pattern.

### 5.4 Referential integrity checks

Before AnalysisPass commit, run referential integrity sweep:
- Every Signal.source_refs entry references an existing Source.source_id or SourceAtom.atom_id. Failure → remove Signal from commit set; record in AnalysisPass failure detail.
- Every Concern.source_refs entry references an existing Source.source_id or SourceAtom.atom_id. Failure → remove Concern from commit set; record in failure detail.
- No source_id appears in both Signal.source_refs and Concern.source_refs (mutual exclusivity). Failure → record in failure detail; Concern takes precedence (more conservative). (Single-stream: source_refs reference Source content only — finding F83.)

### 5.5 Non-canonical attributes

No non-canonical attributes are introduced. (The v0.1 `chunk_assignment` audit entry is removed with the dual-stream revert — there is no chunk assignment in single-stream classification.)

---

## 6. Mode Discipline Realisation

### 6.1 Mode declarations

| **Stage** | **Mode declaration** | **Enforcement** |
| --- | --- | --- |
| Stage 1 (classification AI act) | IM | Source text read-only; any attempt to modify source_text raises LPM violation |
| Stage 1 (entity production) | DM | Entities constructed from AI response + configuration; no re-interpretation |
| Stage 2 (contradiction sweep AI act) | IM | Source text read-only |
| Stage 2 (contradiction Concern production) | DM | Entities constructed from AI response |
| AnalysisPass production | DM | Count aggregation; no AI calls |

Mode declarations recorded on AnalysisPass: `mode_active="IM"`, `declared_transformation_modes=["IM","DM","LPM"]`.

### 6.2 LPM preservation specifics

LPM is the preservation constraint throughout — it governs what the mechanism may not do:
- `Source.source_text` is read-only. Any modification attempt raises a mode violation and records `mode_violations` entry on AnalysisPass.
- `Requirement.requirement_text` is read-only. Same constraint.
- Signal descriptions and Concern descriptions are AI-generated characterisations — they reference the content but do not replace or rewrite it. The originating text remains verbatim in the Source/Requirement entity.
- SourceAtom splitting is not performed by this mechanism (already done by Source Capture).

### 6.3 Mode metadata recording

AnalysisPass.outputs.mode_violations: array of violation records. Each entry: `{stage: string, item_id: string, violation_type: string, detail: string}`. Empty array on clean execution.

---

## 7. Audit Trail Population

### 7.1 AnalysisPass record creation

One AnalysisPass created per mechanism run. Created at the end of the mechanism after both stages complete. Written in the same Postgres transaction as Signal and Concern entities.

### 7.2 outputs.row_lens_data sub-structure

```json
{
  "row_ref": 3,
  "stream1_source_count": 272,
  "signal_count_produced": 285,
  "concern_count_produced": 12,
  "out_of_scope_count": 20,
  "out_of_scope_refs": ["S001", "S017", "..."],
  "ai_model_fingerprints": [
    "claude-sonnet-4-20250514 (classification batch 1)",
    "claude-sonnet-4-20250514 (classification batch 2)",
    "claude-sonnet-4-20250514 (contradiction sweep)"
  ],
  "concern_threshold_used": 0.65
}
```

Invariant: `stream1_source_count = signal_count_produced + concern_count_produced + out_of_scope_count`

### 7.3 Failure recording

On PartialSuccess or Failed execution:
- `outputs.failure_reason`: human-readable description of what failed
- `outputs.failure_detail`: structured list of failed items with item_id and reason
- `outputs.failure_pass`: which stage failed ("Stage1"/"Stage2"/"AnalysisPassProduction")

---

## 8. Verification Criteria

### 8.1 Decidable criteria (automated — must pass on every run)

| **Criterion** | **Check** | **Failure action** |
| --- | --- | --- |
| CN-1 Concern identifier format | Every Concern.concern_id matches `^CN-\d{3}$` | Reject run |
| CN-2 Concern source_refs non-empty | Every Concern.source_refs has ≥ 1 entry | Reject run |
| CN-3 Concern referential integrity | Every Concern.source_refs entry references existing Source/SourceAtom | Reject run |
| CN-5 Concern state at production | Every Concern.state = "Open" | Reject run |
| CN-6 Concern produced_in_row | Every Concern.produced_in_row = str(row_ref) | Reject run |
| SG-1 Signal referential integrity | Every Signal.source_refs entry references existing Source or SourceAtom | Reject run |
| SG-3 Signal row_target | Every Signal.row_target = str(row_ref) | Reject run |
| ME-1 Mutual exclusivity | No source_id appears in both Signal.source_refs and Concern.source_refs | Reject run |
| OS-1 OutOfScope recorded | Every OutOfScope item's id in out_of_scope_refs | Reject run |
| OS-2 OutOfScope no entity | No id in out_of_scope_refs appears in any Signal/Concern source_refs | Reject run |
| INV-1 Invariant | stream1_source_count = signals + concerns + out_of_scope | Reject run |
| SR-1 Source-only refs | No Signal or Concern source_refs entry is a Requirement id (single-stream — finding F83) | Reject run |
| AP-1 AnalysisPass exists | Phase 3 AnalysisPass with mechanism="RowLensSourceReanalysis" exists post-execution | Reject run |
| AP-2 AnalysisPass status | execution_status ∈ {Completed, CompletedWithWarnings} | Reject run |
| AP-3 AnalysisPass mode | mode_active="IM"; "LPM" ∈ declared_transformation_modes | Reject run |

### 8.2 Non-loss reconstruction check

Sum of `len(source.source_text)` for all Sources in stream 1 = `stream1_source_count` × average source length is not directly verifiable (Source Capture's Read Witness handles the byte-level check). For Row-Lens, the non-loss check is: every source_id in the Source set appears in exactly one of: Signal.source_refs, Concern.source_refs, or out_of_scope_refs. Every source is accounted for in exactly one outcome category. This is a stronger form of INV-1.

### 8.3 End-to-end mechanism verification

After a complete run: query ledger for all Signals and Concerns with row_target = str(row_ref) and produced by this AnalysisPass. Verify counts match AnalysisPass.outputs.row_lens_data values. Verify no Concerns are in state Resolved or Dispositioned (should be Open at production time).

---

## 9. Test Fixtures

### 9.1 Happy-path fixtures

**Fixture 1 — Pocket Money × Row 2**

Input: Pocket Money document (existing Source Capture fixture — Sources already in ledger from prior Source Capture run). Row_ref = 2.

Expected postconditions:
- INV-1 satisfied (stream1_source_count = signals + concerns + out_of_scope)
- All Signals have row_target = "2"
- All Concerns have produced_in_row = "2", state = "Open"
- AnalysisPass exists with mechanism = "RowLensSourceReanalysis", execution_status ∈ {Completed, CompletedWithWarnings}
- No source_id appears in both Signal.source_refs and Concern.source_refs
- No Requirement id appears in any Signal/Concern source_refs (SR-1, single-stream)

Content expectations (plausibility, Practitioner review):
- Pocket Money content is simple; expect mostly Signals, few Concerns, possibly some OutOfScope (any content that's clearly implementation-level at Row 2)
- The Row 2 conceptual lens applied to the Sources should surface business-level analytical content

**Fixture 2 — Pocket Money × Row 1**

Same Pocket Money Sources. Row_ref = 1.

Expected postconditions:
- No Requirement ids in any Signal/Concern source_refs (SR-1)
- All Sources processed (signal + concern + out_of_scope count = stream1_source_count)
- All Signals have row_target = "1"; the Row 1 contextual lens applied to the Sources

**Fixture 3 — Row 1 Understanding v1.2 × Row 2 (stress test)**

Input: Row 1 Understanding v1.2 (272 Sources from Source Capture stress test TST-010). Row_ref = 2.

Expected postconditions:
- INV-1 satisfied across 272 Sources
- AnalysisPass.outputs.row_lens_data.stream1_source_count = 272
- No run-terminating invariant failures
- Concerns produced (Row 1 Understanding v1.2 contains complex content; expect at least some Concerns from Row 2 lens)
- Plausibility: content about SysEngage process (which is conceptual/business content) should classify as Signal at Row 2; content about implementation specifics should be OutOfScope or Signal with Ambiguity type

**Fixture 4 — Row 1 Understanding v1.2 × Row 3 (row-lens difference validation)**

Same input as Fixture 3. Row_ref = 3.

Key validation: Signal/Concern/OutOfScope distributions from Fixture 3 (Row 2) and Fixture 4 (Row 3) MUST be materially different. If distributions are substantially identical, the row-lens parameterisation is not functioning (Row 2 conceptual lens vs Row 3 logical-design lens must produce visibly different analytical outputs on the same source material).

### 9.2 Edge-case fixtures

**EC-1 — Empty Source set**

Row_ref = 2 but no Sources exist in ledger (Phase 1 produced nothing). Expected behaviour: mechanism fails the Phase 1 precondition (a project with zero Sources cannot reach Phase 3). AnalysisPass.execution_status = Failed; failure_reason = "no_sources".

**EC-2 — All Sources classified OutOfScope**

Construct a small test ledger with Sources that are clearly implementation-detail (e.g., "The system is implemented in Python 3.12") reviewed at Row 2 (conceptual). Expected: all Sources OutOfScope; signal_count = 0; concern_count = 0; out_of_scope_count = stream1_source_count; INV-1 satisfied; AnalysisPass Completed.

**EC-3 — Source contradiction**

Construct two Sources whose content conflicts at the Row 2 lens (e.g., one says "users manage their own accounts", another says "accounts are managed centrally, not by users"). Both produce Signals in Stage 1; the Stage 2 contradiction sweep produces a Concern referencing both source_ids.

**EC-4 — Large Source set (sub-batching)**

Construct a scenario with 80+ Sources. Verify: the Source set is processed in sub-batches (`source_batch_size`, default 50); each sub-batch is one AI invocation; the Stage 2 contradiction sweep reconciles across batches; INV-1 still satisfied.

**EC-5 — concern_threshold at extremes**

Run Fixture 1 with concern_threshold = 0.0 (everything that passes the relevance gate becomes a Concern) and concern_threshold = 1.0 (everything that passes becomes a Signal). Verify: at 0.0, concern_count_produced ≈ stream1_source_count - out_of_scope_count; at 1.0, signal_count_produced ≈ stream1_source_count - out_of_scope_count. INV-1 must hold in both cases.

### 9.3 Non-determinism fixtures

**ND-1 — Repeated run, identical input**

Run Fixture 1 twice on the same input without modifying the ledger between runs (Phase 10 re-run scenario). Expected:
- Both runs produce structurally valid output (all decidable criteria pass on both runs)
- Signal/Concern counts MAY differ between runs (AI judgment variation)
- Signal/Concern descriptions WILL differ between runs
- Both AnalysisPass records exist in ledger (second run creates new P### with new pass_id)
- stream1_source_count is identical across both runs (deterministic input counting)

**ND-2 — Row 2 vs Row 3 lens difference**

Fixtures 3 and 4 together constitute the lens difference validation (see §9.1 Fixture 4 notes). This is the primary non-determinism-adjacent check: we cannot require identical outputs, but we CAN require that Row 2 and Row 3 produce meaningfully different outputs on the same input. Documented as a Practitioner review step, not an automated assertion.

---

## 10. Edge Cases (Implementation-Level)

### 10.1 Source material not available

If no Source entities exist in the ledger (Phase 1 Source Capture did not complete or produced nothing): mechanism fails with a clear error before Stage 1. This is a precondition violation. AnalysisPass.execution_status = Failed; failure_reason = "no_sources". (Single-stream: there is no Row N-1 stream-2 precondition — each row re-analyses the Source material independently, finding F83.)

### 10.2 AI API failure

If a Claude API call fails (network error, rate limit, API error):
- Retry up to 3 times with exponential backoff (1s, 2s, 4s delays)
- If all retries fail: the classification sub-batch that failed produces no Signals/Concerns. Records the failure in AnalysisPass.outputs.failure_detail. Continues to next sub-batch.
- If all sub-batches fail: execution_status = Failed.
- If some sub-batches succeed and some fail: execution_status = PartialSuccess. INV-1 is checked against the successfully processed Sources only; unprocessed Sources are noted in failure_detail.

### 10.3 AI response schema validation failure

If the AI response does not parse against `classification_response_schema.py`:
- Log the raw response to failure_detail
- Attempt partial extraction: if individual items within the response are valid, extract them; discard malformed items
- If no items can be extracted: the sub-batch produces no entities; recorded as a batch-level failure in failure_detail
- execution_status = PartialSuccess if other sub-batches succeeded

### 10.4 Concern threshold effect on invariant

The concern_threshold is applied at the DM entity-production step, not in the AI prompt. The AI returns a confidence score for every in-scope item. Whether that item becomes a Signal or Concern depends on the threshold comparison. The invariant (stream1_source_count = signals + concerns + out_of_scope) holds regardless of threshold value — every in-scope item becomes either a Signal or a Concern.

### 10.5 Phase 10 re-execution

When Phase 10 triggers Phase 3 re-execution:
- Mechanism re-runs with the current Source set (which may have changed since the original run)
- Prior Signals and Concerns produced by the previous run are invalidated (deleted from ledger or marked superseded — per Row 4 Applied re-execution policy)
- Resolved or Dispositioned Concerns from prior Phase 10 cycles are reviewed by Practitioner before re-run; the mechanism does not automatically re-open them
- New AnalysisPass produced with new pass_id; prior AnalysisPass retained for audit
- (No stream-2 dependency on amended upstream Requirements — single-stream, finding F83; cross-row relationships are re-established by the Requirement Matching service.)

### 10.6 Identifier sequence continuity

Signal identifiers (SG###) and Concern identifiers (CN-NNN) continue from the ledger's current maximum. If a prior run produced SG001–SG050 and Phase 10 re-execution invalidates them, the new run starts from SG051 (not SG001). This ensures ledger identifier uniqueness across re-runs and preserves the audit trail.

---

## 11. Cross-Mechanism Interactions

### 11.1 Upstream

| **Mechanism** | **What this mechanism consumes** | **Dependency type** |
| --- | --- | --- |
| **Source Capture (MECH-R3-002)** | Source, Segment, SourceAtom entities; Phase 1 AnalysisPass (precondition check for execution_status) | Hard prerequisite — Source Capture MUST be Completed before this mechanism runs |
| **Phase 2 completion** | ProjectProfile (for concern_threshold, source_batch_size); Stakeholder entities; mechanism activation state | Soft prerequisite — Phase 2 MUST be complete per phase sequencing |

### 11.2 Downstream

| **Mechanism** | **What this mechanism produces for it** | **Dependency type** |
| --- | --- | --- |
| **Phase 3 Pass 3b (CCI construction)** | Signal entities — the Signal set is the sole input. Concern-blocked content and OutOfScope items excluded. | Hard dependency — Pass 3b cannot begin until Pass 3a (this mechanism) has completed with status ∈ {Completed, CompletedWithWarnings} |
| **Phase 9 Row-Lens Re-Analysis Completion Check** | AnalysisPass with mechanism="RowLensSourceReanalysis" | Hard gate — row close blocked if absent or Failed |
| **Phase 9 Concern Resolution Check** | Concern entities in state Open | Hard gate — row close blocked if any Concern is Open |
| **Phase 10 Concern resolution** | Concern entities — each drives a Phase 9 Question and Phase 10 Answer cycle | Lifecycle dependency |

### 11.3 Coordination via ledger

Per Row 4 Applied §13: mechanisms coordinate via ledger reads, not direct calls. This mechanism reads Sources (and SourceAtoms where present) from the ledger at invocation time; writes Signals, Concerns, and AnalysisPass in one atomic transaction at completion. (Single-stream: it does not read Row N-1 Requirements/Domains — finding F83.)

---

## 12. Build Notes

### 12.1 Findings and decisions

| **Reference** | **Status** | **Relevance** |
| --- | --- | --- |
| **F35 / F83** | F35 partially reversed | F35 decisions D1 (Phase 3 placement), D2 (RSSF retired), D3 (single unified prompt) remain operationalised. F35's dual-stream/Domain-chunking portion is REVERSED by finding F83 (single-stream revert, v0.2). Authoritative rationale in Tracker F83/F93. |
| **F36** | Deferred | T1=0.65 default (D-B2c). After verification runs all fixtures, compare Concern rates at T1=0.55/0.65/0.75 and update ProjectProfile default if evidence warrants. |
| **OQ-B1** | MOOT (F83) | Concerned dual-stream Domain-driven chunking — removed by the single-stream revert. |
| **OQ-B2** | Resolved | Three-step classification; T1 from ProjectProfile; relevance gate for OutOfScope (§4.1, §5.1) |
| **OQ-B3** | Dissolved | No Mechanism Stakeholder; SH001/SG-01/SG-03 cover review (§1) |

### 12.2 Open questions for Replit Agent build

| **OQ** | **Question** | **Recommended default** |
| --- | --- | --- |
| **RA-1** | ~~spaCy model size~~ — MOOT (F83): subject/object extraction served the removed Stage 1 chunk assembly; single-stream classification needs no NLP. | n/a |
| **RA-2** | Source classification sub-batch size — `ProjectProfile.source_batch_size` default value? | 50 Sources per sub-batch. Adjust after verification if context pressure observed. |
| **RA-3** | AI retry backoff parameters — 3 retries, 1s/2s/4s delays. Sufficient? | Yes for v1. Configurable via `ProjectProfile.ai_retry_config` if needed. |
| **RA-4** | ~~Stage 1 chunk_assignment audit storage~~ — MOOT (F83): no chunk assignment in single-stream classification. | n/a |
| **RA-5** | How are Phase 10 re-run prior Signals/Concerns invalidated — deleted or soft-deleted (status flag)? | Per Row 4 Applied re-execution policy — check Applied §10 for the established pattern from Source Capture. Consistent approach required. |

### 12.3 Replit Agent task structure

The implementation-agent handoff should include:
- This Implementation Spec (primary input)
- Row 3 Mechanism Spec v0.4 (single-stream architectural reference)
- Row 4 Applied (common foundations reference — technology stack, persistence, mode discipline decorator pattern)
- Canonical Ledger v2.13 (entity schemas)
- Existing Source Capture implementation as a reference for established patterns (transactional discipline, mode decorator, AnalysisPass population, identifier assignment)

The agent should implement mechanisms/row_lens_source_reanalysis/ following the established pattern of mechanisms/source_capture/ and then implement the AI-specific additions (prompt templates, response schemas, three-step classification, Stage 1–2 orchestration).

---

## Document End

End of SysEngage Row 4 Mechanism: Row-Lens Source Re-Analysis v0.2.

**Single-stream revert (finding F83).** The dual-stream Pass-3a model (v0.1) is removed: the mechanism classifies the Source material directly through each row's Zachman lens (Stage 1) and sweeps the classified set for contradictions (Stage 2). The four-stage Domain-chunking structure (chunk assembly / per-chunk classification / chunk deduplication / cross-chunk conflict sweep) is gone — it served only the now-rejected stream-2 re-analysis of upstream Requirements. spaCy/NLP extraction and the chunk-match threshold are removed. Cross-row requirement traceability relocates to `Requirement.refines_refs` (ledger v2.13), established by the Requirement Matching service. F35's dual-stream portion is reversed by F83 — authoritative rationale in the Issues Tracker.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Row_Lens_Source_Reanalysis_v0_4.md — Row 3 single-stream architectural authority
- sysengage_minimal_ledger_spec_v2_13.md — Signal / Concern / AnalysisPass schema authority
- SysEngage_Row_3_Mechanism_Requirement_Matching_v0_1.md — carries the cross-row «refine» trace (refines_refs)
- SysEngage_Issues_Tracker (current) — F83 / F93 / F35 authoritative rationale
