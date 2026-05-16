# SysEngage Row 4 Mechanism: Row-Lens Source Re-Analysis

**Implementation specification — depth tier (i)+**

Filename: SysEngage_Row_4_Mechanism_Row_Lens_Source_Reanalysis_v0_1.md

Version: 0.1 (Initial — Mechanism B implementation spec)

Date: 13 May 2026

**Purpose.** Implementation specification for the Row-Lens Source Re-Analysis mechanism (Mechanism B). Translates the Row 3 Mechanism Specification (SysEngage_Row_3_Mechanism_Row_Lens_Source_Reanalysis_v0_3.md) into Row 4 implementation detail consistent with the SysEngage v1 architectural commitments (SysEngage_Row_4_Applied_to_SysEngage_v0_2.docx) and canonical ledger spec v2.12. At depth tier (i)+ per Row 4 Understanding §8: architectural specification + verification criteria + test fixtures. Suitable for handoff to Replit Agent for implementation generation.

**Status.** v0.1 — initial implementation specification. All Row 3 open questions resolved or dissolved (OQ-B1: Domain-driven chunking; OQ-B2: three-step classification with T1=0.65; OQ-B3: no dedicated Mechanism Stakeholder). F36 deferred (T1 empirical validation after Step 7 verification).

**Excludes.** Per Row 4 Understanding §8.1 depth tier (i)+: NO pseudo-code, NO function signatures, NO code-level interface definitions. Replit Agent derives these from the architectural specification + canonical schemas. The spec describes WHAT each stage does and WHAT correctness looks like; Agent decides HOW to write the code.

---

## 1. Mechanism Identification

| **Mechanism name** | Row-Lens Source Re-Analysis |
| --- | --- |
| **Row 3 Mechanism Spec reference** | SysEngage_Row_3_Mechanism_Row_Lens_Source_Reanalysis_v0_3.md — all sections |
| **Operational location** | Phase 3 Pass 3a. Executes once per active row at Phase 3 entry. Four stages: Stage 1 (Domain-driven chunk assembly, DM), Stage 2 (per-chunk + residual classification, IM+DM), Stage 3 (deduplication, DM), Stage 4 (conflict sweep, IM+DM). |
| **Mechanism class** | AI-involving. IM for classification acts (Stages 2, 4). DM for assembly, deduplication, entity production, AnalysisPass recording. LPM preservation constraint throughout. |
| **Module location** | `mechanisms/row_lens_source_reanalysis/` directory. See §3.1 for file structure. |
| **Row applicability** | Row-sequential. Row 1: stream 2 empty; Stages 1 skipped; all Sources processed as residual. Row 2+: full dual-stream processing. |
| **Mechanism Stakeholder** | None (D-B3, OQ-B3 dissolved). SH001 covers deterministic structural review. SG-01 covers all Concern disposition. SG-03 carries execution attribution via AnalysisPass. |

---

## 2. Cross-References

| **Source** | **Reference** | **What this provides** |
| --- | --- | --- |
| **Row 4 Understanding v0.2** | §10 Mechanism B Framework | Implementation framework: module structure, chunk assembly, entity production patterns, AnalysisPass population, prompt template management |
| **Row 4 Understanding v0.2** | §9.4 Prompt Architecture Pattern | Prompt template registry, parameterisation contract, response schema, lens definition locus |
| **Row 4 Understanding v0.2** | §9.5 Non-Determinism Handling | Decidable vs plausibility split; re-run semantics; AI model fingerprinting |
| **Row 4 Understanding v0.2** | §9.6 OutOfScope Classification Framework | Relevance gate separation; out_of_scope_refs recording; OS-1/OS-2 validation |
| **Row 4 Applied v0.2** | All sections | Common architectural commitments: Python 3.12+, FastAPI, Neon PostgreSQL via SQLAlchemy + Alembic, Pydantic v2, Claude Sonnet via Anthropic API, pytest, transactional discipline |
| **Row 3 Mechanism Spec v0.3** | All sections | Architectural spec: four-stage pass structure, three classification outcomes, dual-stream model, row-specific lens definitions (§5), verification criteria (§9), edge cases (§10) |
| **Canonical Ledger v2.12** | Signal, Concern, AnalysisPass element types | Authoritative schemas. Pydantic models in schemas/ mirror these. Concern identifier CN-NNN; nine attributes; source_refs list. |
| **Tracker v0.24** | F35, F36, OQ-B1/B2/B3 | Architectural decision history |

---

## 3. Architectural Approach

### 3.1 Module structure

```
mechanisms/row_lens_source_reanalysis/
  __init__.py                              # Orchestration entry point
  stage1_chunk_assembly.py                # DM: Domain-driven chunk assembly
  stage2_chunk_classification.py          # IM+DM: Per-chunk AI classification + entity production
  stage2_residual_classification.py       # IM+DM: Residual Sources AI classification + entity production
  stage3_deduplication.py                # DM: Cross-chunk deduplication + conflict flagging
  stage4_conflict_sweep.py               # IM+DM: Conflict sweep AI invocation + Concern production
  entity_production.py                   # DM: Shared Signal/Concern/OutOfScope recording
  analysis_pass_production.py            # DM: AnalysisPass record construction + commit
  prompts/
    chunk_classification_prompt.py       # Template: row-lens chunk classification
    residual_classification_prompt.py    # Template: residual Sources classification
    conflict_sweep_prompt.py             # Template: conflict sweep
    lens_definitions.py                  # Row-specific lens content (from Row 3 Spec §5.2)
  schemas/
    classification_response_schema.py    # Pydantic: AI response validation for classification
    conflict_sweep_response_schema.py    # Pydantic: AI response validation for conflict sweep
```

### 3.2 Major design decisions

- **Single transactional ledger write** — all entities produced by the mechanism (Signals, Concerns, AnalysisPass) committed atomically in one Postgres transaction at the end of the mechanism execution. If any stage fails, the entire transaction rolls back. Per Row 4 Applied §5 transactional discipline.

- **AI invocations outside the transaction** — AI API calls are made before the Postgres transaction opens. Results are held in memory. The transaction writes only the validated, deterministic entity set. This separates non-deterministic AI I/O from deterministic ledger writes.

- **Prompt templates as separate modules** — lens content and prompt structure live in `prompts/` and can be updated independently of classification logic. The `lens_definitions.py` file is the single source of truth for row-specific lens content; it mirrors Row 3 Mechanism Spec §5.2 verbatim.

- **Pydantic validation at AI response boundary** — AI responses are immediately parsed against the response schema (`classification_response_schema.py`). Validation failure at this boundary produces a PartialSuccess execution status; valid items proceed to entity production; invalid items recorded in AnalysisPass failure detail.

- **concern_threshold from ProjectProfile** — T1 is read from `ProjectProfile.concern_threshold` at mechanism invocation. Default 0.65 (provisional, F36). Not hard-coded. Per-row override read from `ProjectProfile.concern_threshold_overrides[row_ref]` if present.

- **NLP for Stage 1** — subject/object extraction uses spaCy (declared in Row 4 Applied §3 common dependencies). The lightweight `en_core_web_sm` model is sufficient for noun phrase extraction. Extraction is deterministic — no AI involvement in Stage 1.

- **chunk_match_threshold from ProjectProfile** — fuzzy match threshold (default 0.6) read from `ProjectProfile.chunk_match_threshold`. Per-mechanism configuration parameter.

### 3.3 Dependencies

- **Claude Sonnet via Anthropic API** — per Row 4 Applied AI Model commitment
- **spaCy + en_core_web_sm** — for deterministic subject/object extraction in Stage 1
- **SQLAlchemy 2.x** — ORM for entity persistence
- **Pydantic v2** — entity validation and AI response schema validation
- **anthropic Python SDK** — API client for Claude invocations
- **Standard library** — typing, dataclasses, uuid for support

---

## 4. Stage-by-Stage Implementation

### 4.1 Stage 1 — Domain-Driven Chunk Assembly

**Mode:** DM. No AI involvement. Fully deterministic.

**Input handling:**
- Read all Domain entities from ledger where `Domain.row_target = str(row_ref - 1)` (stream 2 Domains)
- Read all Requirement entities where `Requirement.row_target = str(row_ref - 1)` and `Requirement.domain_refs` references a stream 2 Domain (stream 2 Requirements)
- Read all Source entities from ledger (stream 1)
- Read all SourceAtom entities (stream 1, where present)
- At Row 1: return empty chunk list immediately. All Sources enter residual set.

**Processing logic:**
- For each Domain D in stream 2 Domains (ordered by domain_id for determinism):
  - For each Requirement R in D: extract subject noun phrases and object noun phrases from `R.requirement_text` using spaCy noun chunk extraction. Normalise extracted phrases (lowercase, singular canonical form via spaCy lemmatisation).
  - Build Domain vocabulary set: union of all subject and object noun phrases from all Requirements in D.
  - Scan Sources: for each Source S, compute token overlap score between S.source_text tokens and the Domain vocabulary set. If score ≥ `chunk_match_threshold`: assign S to chunk D. Record in chunk_assignment: `{source_id: [domain_id, ...]}`.
- Collect residual Sources: Sources not assigned to any Domain chunk.

**Output:**
- Chunk list: `[{domain_id, domain_name, requirements: [Requirement], sources: [Source]}]`
- Residual list: `[Source]`
- Chunk assignment audit: `{source_id: [domain_id]}` — stored in AnalysisPass outputs

**Edge cases:**
- No stream 2 Domains (Row 1, or Row N>1 where prior row produced no Domains): all Sources are residual; chunk list is empty.
- All Sources match multiple Domains: permitted. Sources are duplicated across chunks. Stage 3 deduplication handles cross-chunk Signal/Concern consistency.
- No Sources match any Domain (all residual): Stage 2 chunk loop has nothing to process; all Sources processed in residual pass.
- Very large Domain vocabulary (Domain with many Requirements): no special handling — vocabulary set may be large but match is O(|tokens| × |vocabulary|), deterministic.

### 4.2 Stage 2 — Per-Chunk Classification

**Mode:** IM (AI invocation) + DM (entity production). LPM preservation constraint: Source.source_text and Requirement.requirement_text are never modified.

**Per-chunk AI invocation:**
- For each Domain chunk assembled in Stage 1:
  - Construct prompt from `chunk_classification_prompt.py` template with parameters: `{row_ref}`, `{lens_content}` (from `lens_definitions.py[row_ref]`), `{domain_name}`, `{requirements}` (list of requirement_id + requirement_text), `{sources}` (list of source_id + source_text), `{concern_threshold}`.
  - Call Claude Sonnet API. Record AI model version fingerprint.
  - Parse response against `classification_response_schema.py`. Schema: `{items: [{item_id: string, classification: "Signal"|"Concern"|"OutOfScope", confidence: float, description: string}]}`.
  - Validation failure: record malformed items in AnalysisPass failure detail; proceed with valid items (PartialSuccess).

**Per-chunk entity production (DM) — for each valid AI response item:**
- Classification = "OutOfScope": append source_id to out_of_scope_refs. No entity produced.
- Classification = "Signal" (confidence ≥ concern_threshold from AI): produce Signal entity. source_refs = [item_id]. signal_type from AI classification. row_target = str(row_ref). description from AI. confidence from AI. derived_from_concern_id = null.
- Classification = "Concern" (confidence < concern_threshold, or AI explicitly classified as Concern): produce Concern entity. concern_id = next CN-NNN. source_refs = [item_id]. description from AI. state = Open. produced_in_row = str(row_ref). practitioner_id from invocation context. confidence from AI.

**Note on three-step classification prompt structure:**

The `chunk_classification_prompt.py` instructs the AI to evaluate each item in two steps:
1. Relevance gate: is this item relevant to the row's analytical abstraction level? (Yes/No)
2. If Yes: assess confidence that it classifies clearly (Signal) vs ambiguously (Concern). Return confidence score.
3. If No: classify as OutOfScope.

The concern_threshold is passed to the prompt as context but the DM entity-production step applies it — the AI returns the confidence score; the implementation decides Signal vs Concern based on whether confidence ≥ T1.

**Residual Sources classification:**
- Same pattern as per-chunk, using `residual_classification_prompt.py` (same structure, no domain_name or requirements parameters).
- Batch residual Sources into sub-batches of configurable size (`ProjectProfile.residual_batch_size`, default 50) if residual set is large.
- Each sub-batch is one AI invocation.

### 4.3 Stage 3 — Chunk Deduplication

**Mode:** DM. No AI involvement. Fully deterministic.

**Processing logic:**
- For each source_id that appears in multiple chunk outputs (identified from chunk_assignment):
  - Collect all Signal/Concern/OutOfScope classifications for this source_id across chunks.
  - If all classifications are OutOfScope: the source_id is OutOfScope (deduplicated to one out_of_scope_refs entry).
  - If all classifications are Signal with the same signal_type: deduplicate to one Signal. Retain the Signal with highest confidence; discard others.
  - If all classifications are Signal but with different signal_type values: flag as cross-chunk conflict for Stage 4. Retain all Signals (do not discard).
  - If classifications mix Signal and Concern: flag as cross-chunk conflict for Stage 4. Retain Signal(s) and Concern(s).
  - If all classifications are Concern: deduplicate to one Concern (retain highest confidence; merge descriptions if meaningfully different).
  - If classifications mix anything with OutOfScope: the non-OutOfScope classification wins; OutOfScope is discarded for this source_id.

**Output:**
- Deduplicated Signal list (source_ids with consistent classification resolved)
- Deduplicated Concern list
- Cross-chunk conflict list: `[{source_id, classifications_by_chunk: [{domain_id, classification, signal_type, confidence}]}]`

### 4.4 Stage 4 — Cross-Chunk Conflict Sweep

**Mode:** IM (AI invocation) + DM (Concern production). LPM constraint throughout.

**Input handling:**
- Receives cross-chunk conflict list from Stage 3.
- If conflict list is empty: Stage 4 produces no output. Proceed to AnalysisPass production.

**AI invocation:**
- Construct prompt from `conflict_sweep_prompt.py` with parameters: `{row_ref}`, `{lens_content}`, `{conflicts}` (list of source_id, source_text, classifications_by_chunk).
- Call Claude Sonnet API. Record AI model version fingerprint.
- Parse response against `conflict_sweep_response_schema.py`. Schema: `{conflicts: [{source_id: string, is_genuine_contradiction: bool, rationale: string}]}`.

**Entity production (DM):**
- For each conflict where `is_genuine_contradiction = true`: produce one new Concern entity. source_refs = [source_id]. description = AI rationale string. state = Open. concern_id = next CN-NNN. produced_in_row = str(row_ref).
- For each conflict where `is_genuine_contradiction = false`: no new entity. All existing Signals for this source_id are retained. The complementary classification is valid — the same Source contributes to two different Domain analyses legitimately.
- Existing Signals from Stage 2/3 are NEVER removed by Stage 4, regardless of conflict outcome.

### 4.5 AnalysisPass Record Production

**Mode:** DM. Fully deterministic. Runs after all four stages complete.

**AnalysisPass attributes:**
- pass_id: next available P### in sequence
- pass_type: "Per-row"
- mechanism: "RowLensSourceReanalysis" (exact string)
- execution_status: "Completed" (or "Failed"/"PartialSuccess" — see §10.5)
- mode_active: "IM"
- declared_transformation_modes: ["IM", "DM", "LPM"]
- outputs.row_lens_data: (see §7.2 for full sub-structure)
- outputs.mode_violations: [] on clean run
- pass_started_at: timestamp recorded at mechanism invocation entry
- pass_completed_at: timestamp recorded at AnalysisPass commit
- elapsed_ms: derived from timestamps
- confidence: mean of all AI invocation confidence scores for this run
- ai_model_fingerprints: list of AI model versions used across all invocations (one entry per invocation; typically multiple entries for one mechanism run)

**Invariant enforcement (before commit):**
`stream1_source_count + stream2_requirement_count = signal_count_produced + concern_count_produced + out_of_scope_count`

If invariant fails: set execution_status = "Failed"; populate failure_reason with count discrepancy detail; commit AnalysisPass with Failed status; roll back Signal/Concern entity writes; raise mechanism execution error.

---

## 5. Schema and Validation

### 5.1 Pydantic models (in-memory)

**SignalModel** — mirrors canonical ledger spec v2.12 Signal attributes:
- signal_id (str, pattern `^SG\d{3}$`)
- signal_type (Literal["Normative","Intent","Actor","Concern","Ambiguity","Quality"])
- row_target (Literal["1","2","3","4","5","6"])
- description (str, min_length=1)
- source_refs (list[str], min_length=1) — each entry references Source.source_id or Requirement.requirement_id
- sourceatom_refs (list[str], optional)
- confidence (float, ge=0.0, le=1.0)
- derived_from_concern_id (str | None, pattern `^CN-\d{3}$` when present)

**ConcernModel** — mirrors canonical ledger spec v2.12 Concern attributes:
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
- All base AnalysisPass attributes per canonical ledger spec v2.12
- outputs.row_lens_data: RowLensDataModel (see §7.2)

**ClassificationResponseItemModel** — validates per-item AI response:
- item_id (str)
- classification (Literal["Signal","Concern","OutOfScope"])
- confidence (float, ge=0.0, le=1.0)
- description (str)

**ConflictSweepResponseItemModel** — validates per-conflict AI response:
- source_id (str)
- is_genuine_contradiction (bool)
- rationale (str)

### 5.2 SQLAlchemy models (persistence)

Signal, Concern, AnalysisPass tables follow the canonical ledger spec v2.12 attribute set. No non-canonical attributes at persistence layer. The `outputs` field on AnalysisPass is a PostgreSQL JSONB column; `row_lens_data` sub-structure is stored within it.

Concern table: `concern_id` column uses the `^CN-\d{3}$` pattern enforced by Postgres CHECK constraint (consistent with Source Capture approach for S###, SEG###, SA###).

### 5.3 Identifier assignment strategy

- Signal: sequential SG### starting from max existing SG### in ledger + 1. Thread-safe via Postgres sequence.
- Concern: sequential CN-NNN starting from max existing CN-NNN in ledger + 1. Postgres sequence on the numeric portion.
- AnalysisPass: sequential P### per existing pattern.

### 5.4 Referential integrity checks

Before AnalysisPass commit, run referential integrity sweep:
- Every Signal.source_refs entry references an existing Source.source_id or Requirement.requirement_id. Failure → remove Signal from commit set; record in AnalysisPass failure detail.
- Every Concern.source_refs entry references an existing Source.source_id, SourceAtom.atom_id, or Requirement.requirement_id. Failure → remove Concern from commit set; record in failure detail.
- Any Requirement in source_refs has row_target strictly less than Signal/Concern produced_in_row. Failure → remove entity; record in failure detail.
- No source_id appears in both Signal.source_refs and Concern.source_refs (mutual exclusivity, per chunk). Failure → record in failure detail; Concern takes precedence (more conservative).

### 5.5 Non-canonical attributes

The `chunk_assignment` audit entry (`{source_id: [domain_id]}`) is stored in `AnalysisPass.outputs.row_lens_data` as part of the JSONB outputs field. It is implementation-specific audit data — not a canonical entity attribute. Not exported in the canonical ledger JSON export.

---

## 6. Mode Discipline Realisation

### 6.1 Mode declarations

| **Stage** | **Mode declaration** | **Enforcement** |
| --- | --- | --- |
| Stage 1 (chunk assembly) | DM | No AI calls permitted; spaCy extraction is deterministic; mode_violations populated if AI call attempted |
| Stage 2 (classification AI act) | IM | Source/Requirement text read-only; any attempt to modify source_text raises LPM violation |
| Stage 2 (entity production) | DM | Entities constructed from AI response + configuration; no re-interpretation |
| Stage 3 (deduplication) | DM | Pure in-memory computation; no AI calls |
| Stage 4 (conflict sweep AI act) | IM | Source text read-only |
| Stage 4 (conflict Concern production) | DM | Entities constructed from AI response |
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

One AnalysisPass created per mechanism run. Created at the end of the mechanism after all four stages complete. Written in the same Postgres transaction as Signal and Concern entities.

### 7.2 outputs.row_lens_data sub-structure

```json
{
  "row_ref": 3,
  "stream1_source_count": 272,
  "stream2_requirement_count": 45,
  "stream2_domain_count": 8,
  "signal_count_produced": 285,
  "concern_count_produced": 12,
  "out_of_scope_count": 20,
  "out_of_scope_refs": ["S001", "S017", "..."],
  "chunk_assignment": {"S003": ["D001", "D003"], "S007": ["D002"]},
  "ai_model_fingerprints": [
    "claude-sonnet-4-20250514 (chunk D001)",
    "claude-sonnet-4-20250514 (chunk D002)",
    "claude-sonnet-4-20250514 (residual batch 1)",
    "claude-sonnet-4-20250514 (conflict sweep)"
  ],
  "concern_threshold_used": 0.65,
  "chunk_match_threshold_used": 0.6
}
```

Invariant: `stream1_source_count + stream2_requirement_count = signal_count_produced + concern_count_produced + out_of_scope_count`

### 7.3 Failure recording

On PartialSuccess or Failed execution:
- `outputs.failure_reason`: human-readable description of what failed
- `outputs.failure_detail`: structured list of failed items with item_id and reason
- `outputs.failure_pass`: which stage failed ("Stage1"/"Stage2"/"Stage3"/"Stage4"/"AnalysisPassProduction")

---

## 8. Verification Criteria

### 8.1 Decidable criteria (automated — must pass on every run)

| **Criterion** | **Check** | **Failure action** |
| --- | --- | --- |
| CN-1 Concern identifier format | Every Concern.concern_id matches `^CN-\d{3}$` | Reject run |
| CN-2 Concern source_refs non-empty | Every Concern.source_refs has ≥ 1 entry | Reject run |
| CN-3 Concern referential integrity | Every Concern.source_refs entry references existing Source/SourceAtom/Requirement | Reject run |
| CN-4 Concern upstream row constraint | Any Requirement in Concern.source_refs has row_target < Concern.produced_in_row | Reject run |
| CN-5 Concern state at production | Every Concern.state = "Open" | Reject run |
| CN-6 Concern produced_in_row | Every Concern.produced_in_row = str(row_ref) | Reject run |
| SG-1 Signal referential integrity | Every Signal.source_refs entry references existing Source or Requirement | Reject run |
| SG-2 Signal upstream row constraint | Any Requirement in Signal.source_refs has row_target < Signal.row_target | Reject run |
| SG-3 Signal row_target | Every Signal.row_target = str(row_ref) | Reject run |
| ME-1 Mutual exclusivity | No source_id appears in both Signal.source_refs and Concern.source_refs (per chunk output, pre-Stage 3) | Reject run |
| OS-1 OutOfScope recorded | Every OutOfScope item's id in out_of_scope_refs | Reject run |
| OS-2 OutOfScope no entity | No id in out_of_scope_refs appears in any Signal/Concern source_refs | Reject run |
| INV-1 Invariant | stream1 + stream2 = signals + concerns + out_of_scope | Reject run |
| R1-1 Row 1 stream 2 | At row_ref=1: stream2_requirement_count=0, stream2_domain_count=0, no Requirement ids in Signal/Concern source_refs | Reject run |
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

**Fixture 1 — Pocket Money × Row 2 (stream 2 active)**

Input: Pocket Money document (existing Source Capture fixture — Sources already in ledger from prior Source Capture run). Stream 2: Row 1 Requirements (from prior Row 1 Phase 3d — these must exist in ledger for this fixture to run; if not, use fixture 3 first). Row_ref = 2.

Expected postconditions:
- stream2_domain_count ≥ 1 (Row 1 produced at least one Domain)
- stream2_requirement_count ≥ 1
- INV-1 satisfied
- All Signals have row_target = "2"
- All Concerns have produced_in_row = "2", state = "Open"
- AnalysisPass exists with mechanism = "RowLensSourceReanalysis", execution_status ∈ {Completed, CompletedWithWarnings}
- No source_id appears in both Signal.source_refs and Concern.source_refs

Content expectations (plausibility, Practitioner review):
- Pocket Money content is simple; expect mostly Signals, few Concerns, possibly some OutOfScope (any content that's clearly implementation-level at Row 2)
- Stream 2 Signals should represent elaboration of Row 1 content through Row 2 conceptual lens

**Fixture 2 — Pocket Money × Row 1 (stream 2 empty)**

Same Pocket Money Sources. Row_ref = 1.

Expected postconditions:
- stream2_requirement_count = 0
- stream2_domain_count = 0
- No Requirement ids in any Signal/Concern source_refs
- R1-1 criterion passes
- All Sources in stream 1 processed (signal + concern + out_of_scope count = stream1_source_count)

**Fixture 3 — Row 1 Understanding v1.2 × Row 2 (stress test)**

Input: Row 1 Understanding v1.2 (272 Sources from Source Capture stress test TST-010). Row_ref = 2. Row 1 Requirements must exist in ledger (requires prior Row 1 Phase 3d run on this input).

Expected postconditions:
- INV-1 satisfied across 272 stream 1 Sources + stream 2 Requirements
- AnalysisPass.outputs.row_lens_data.stream1_source_count = 272
- No run-terminating invariant failures
- Concerns produced (Row 1 Understanding v1.2 contains complex content; expect at least some Concerns from Row 2 lens)
- Plausibility: content about SysEngage process (which is conceptual/business content) should classify as Signal at Row 2; content about implementation specifics should be OutOfScope or Signal with Ambiguity type

**Fixture 4 — Row 1 Understanding v1.2 × Row 3 (row-lens difference validation)**

Same input as Fixture 3. Row_ref = 3. Row 2 Requirements must exist in ledger.

Key validation: Signal/Concern/OutOfScope distributions from Fixture 3 (Row 2) and Fixture 4 (Row 3) MUST be materially different. If distributions are substantially identical, the row-lens parameterisation is not functioning (Row 2 conceptual lens vs Row 3 logical-design lens must produce visibly different analytical outputs on the same source material).

### 9.2 Edge-case fixtures

**EC-1 — Row 1 with no prior Requirements (stream 2 empty by design)**

Row_ref = 2 but no Row N-1 Requirements exist in ledger (prior row not yet run). Expected behaviour: stream2_requirement_count = 0 (graceful empty stream 2); all Sources processed as residual; run completes successfully.

**EC-2 — All Sources classified OutOfScope**

Construct a small test ledger with Sources that are clearly implementation-detail (e.g., "The system is implemented in Python 3.12") reviewed at Row 2 (conceptual). Expected: all Sources OutOfScope; signal_count = 0; concern_count = 0; out_of_scope_count = stream1_source_count; INV-1 satisfied; AnalysisPass Completed.

**EC-3 — Cross-stream contradiction**

Construct a Source ("users manage accounts") and a Row 1 Requirement that contradicts it ("account management is not in scope"). At Row 2 lens, the Source produces a Signal; the Requirement should produce a Concern or be OutOfScope. Verify that the mechanism handles the contradiction and the cross-chunk conflict sweep produces a Concern referencing both items' source_refs.

**EC-4 — Large chunk (many Sources matching one Domain)**

Construct a scenario where a single Domain has 80+ Sources assigned by the fuzzy matcher (word "system" appears in all Sources; Domain vocabulary includes "system"). Verify: the chunk is processed as one AI invocation; if context limit is approached, the implementation gracefully sub-batches (PartialSuccess status if sub-batching is needed); INV-1 still satisfied.

**EC-5 — concern_threshold at extremes**

Run Fixture 1 with concern_threshold = 0.0 (everything that passes the relevance gate becomes a Concern) and concern_threshold = 1.0 (everything that passes becomes a Signal). Verify: at 0.0, concern_count_produced ≈ stream1_source_count + stream2_requirement_count - out_of_scope_count; at 1.0, signal_count_produced ≈ stream1_source_count + stream2_requirement_count - out_of_scope_count. INV-1 must hold in both cases.

### 9.3 Non-determinism fixtures

**ND-1 — Repeated run, identical input**

Run Fixture 1 twice on the same input without modifying the ledger between runs (Phase 10 re-run scenario). Expected:
- Both runs produce structurally valid output (all decidable criteria pass on both runs)
- Signal/Concern counts MAY differ between runs (AI judgment variation)
- Signal/Concern descriptions WILL differ between runs
- Both AnalysisPass records exist in ledger (second run creates new P### with new pass_id)
- stream1_source_count and stream2_requirement_count are identical across both runs (deterministic input counting)

**ND-2 — Row 2 vs Row 3 lens difference**

Fixtures 3 and 4 together constitute the lens difference validation (see §9.1 Fixture 4 notes). This is the primary non-determinism-adjacent check: we cannot require identical outputs, but we CAN require that Row 2 and Row 3 produce meaningfully different outputs on the same input. Documented as a Practitioner review step, not an automated assertion.

---

## 10. Edge Cases (Implementation-Level)

### 10.1 Stream 2 not available (prior row not completed)

If row_ref > 1 but Row N-1 Phase 3d has not completed (no Requirements with row_target = str(row_ref-1) in ledger): mechanism should fail with a clear error before Stage 1. This is a precondition violation, not a graceful degradation — the mechanism requires stream 2 to be available at Row 2+. AnalysisPass.execution_status = Failed; failure_reason = "stream2_not_available".

### 10.2 AI API failure

If a Claude API call fails (network error, rate limit, API error):
- Retry up to 3 times with exponential backoff (1s, 2s, 4s delays)
- If all retries fail: the chunk that failed produces no Signals/Concerns from that chunk. Records the failure in AnalysisPass.outputs.failure_detail. Continues to next chunk.
- If critical stages fail (e.g., all chunks fail): execution_status = Failed.
- If some chunks succeed and some fail: execution_status = PartialSuccess. INV-1 is checked against the successfully processed Sources only; unprocessed Sources are noted in failure_detail.

### 10.3 AI response schema validation failure

If the AI response does not parse against `classification_response_schema.py`:
- Log the raw response to failure_detail
- Attempt partial extraction: if individual items within the response are valid, extract them; discard malformed items
- If no items can be extracted: the chunk produces no entities; recorded as chunk-level failure in failure_detail
- execution_status = PartialSuccess if other chunks succeeded

### 10.4 Concern threshold effect on invariant

The concern_threshold is applied at the DM entity-production step, not in the AI prompt. The AI returns a confidence score for every in-scope item. Whether that item becomes a Signal or Concern depends on the threshold comparison. The invariant holds regardless of threshold value — every in-scope item (confidence score returned) becomes either a Signal or a Concern.

### 10.5 Phase 10 re-execution

When Phase 10 triggers Phase 3 re-execution:
- Mechanism re-runs with the current Source set and current Row N-1 Requirements (which may have changed since the original run)
- Prior Signals and Concerns produced by the previous run are invalidated (deleted from ledger or marked superseded — per Row 4 Applied re-execution policy)
- Resolved or Dispositioned Concerns from prior Phase 10 cycles are reviewed by Practitioner before re-run; the mechanism does not automatically re-open them
- New AnalysisPass produced with new pass_id; prior AnalysisPass retained for audit

### 10.6 Identifier sequence continuity

Signal identifiers (SG###) and Concern identifiers (CN-NNN) continue from the ledger's current maximum. If a prior run produced SG001–SG050 and Phase 10 re-execution invalidates them, the new run starts from SG051 (not SG001). This ensures ledger identifier uniqueness across re-runs and preserves the audit trail.

---

## 11. Cross-Mechanism Interactions

### 11.1 Upstream

| **Mechanism** | **What this mechanism consumes** | **Dependency type** |
| --- | --- | --- |
| **Source Capture (MECH-R3-002)** | Source, Segment, SourceAtom entities; Phase 1 AnalysisPass (precondition check for execution_status) | Hard prerequisite — Source Capture MUST be Completed before this mechanism runs |
| **Phase 2 completion** | ProjectProfile (for concern_threshold, chunk_match_threshold, residual_batch_size); Stakeholder entities; mechanism activation state | Soft prerequisite — Phase 2 MUST be complete per phase sequencing |
| **Row N-1 Phase 3d (for Row N>1)** | Domain entities (row_target = str(row_ref-1)); Requirement entities (row_target = str(row_ref-1)) | Hard prerequisite at Row 2+ — Row N-1 Phase 3d MUST be completed |

### 11.2 Downstream

| **Mechanism** | **What this mechanism produces for it** | **Dependency type** |
| --- | --- | --- |
| **Phase 3 Pass 3b (CCI construction)** | Signal entities — the Signal set is the sole input. Concern-blocked content and OutOfScope items excluded. | Hard dependency — Pass 3b cannot begin until Pass 3a (this mechanism) has completed with status ∈ {Completed, CompletedWithWarnings} |
| **Phase 9 Row-Lens Re-Analysis Completion Check** | AnalysisPass with mechanism="RowLensSourceReanalysis" | Hard gate — row close blocked if absent or Failed |
| **Phase 9 Concern Resolution Check** | Concern entities in state Open | Hard gate — row close blocked if any Concern is Open |
| **Phase 10 Concern resolution** | Concern entities — each drives a Phase 9 Question and Phase 10 Answer cycle | Lifecycle dependency |

### 11.3 Coordination via ledger

Per Row 4 Applied §13: mechanisms coordinate via ledger reads, not direct calls. This mechanism reads Sources, Requirements, and Domains from the ledger at invocation time; writes Signals, Concerns, and AnalysisPass in one atomic transaction at completion.

---

## 12. Build Notes

### 12.1 Findings and decisions

| **Reference** | **Status** | **Relevance** |
| --- | --- | --- |
| **F35** | Action-In-Progress | Architectural decisions (D1 Phase 3 placement, D2 RSSF retired, D3 single unified prompt) all operationalised in this spec. F35 closes when Step 7 verification completes. |
| **F36** | Deferred | T1=0.65 default (D-B2c). After Step 7 verification runs all fixtures, compare Concern rates at T1=0.55/0.65/0.75 and update ProjectProfile default if evidence warrants. |
| **OQ-B1** | Resolved | Domain-driven chunking (§3, §4) |
| **OQ-B2** | Resolved | Three-step classification; T1 from ProjectProfile; relevance gate for OutOfScope (§4.2, §5.1) |
| **OQ-B3** | Dissolved | No Mechanism Stakeholder; SH001/SG-01/SG-03 cover review (§1) |

### 12.2 Open questions for Replit Agent build

| **OQ** | **Question** | **Recommended default** |
| --- | --- | --- |
| **RA-1** | spaCy model size — `en_core_web_sm` vs `en_core_web_md` for subject/object extraction? Larger model = better extraction quality, higher memory. | Start with `en_core_web_sm`. If Stage 1 chunk assignment produces poor results in Step 7 verification, upgrade to `md`. |
| **RA-2** | Residual sub-batch size default — `ProjectProfile.residual_batch_size` default value? | 50 Sources per sub-batch. Adjust after Step 7 if context pressure observed. |
| **RA-3** | AI retry backoff parameters — 3 retries, 1s/2s/4s delays. Sufficient? | Yes for v1. Configurable via `ProjectProfile.ai_retry_config` if needed. |
| **RA-4** | Should the Stage 1 chunk_assignment audit be included in the AnalysisPass JSONB or stored separately? | Include in JSONB (`row_lens_data.chunk_assignment`) for v1. If it becomes too large (many Sources × many Domains), move to separate audit table in v1.x. |
| **RA-5** | How are Phase 10 re-run prior Signals/Concerns invalidated — deleted or soft-deleted (status flag)? | Per Row 4 Applied re-execution policy — check Applied §10 for the established pattern from Source Capture. Consistent approach required. |

### 12.3 Replit Agent task structure

The Replit Agent handoff should include:
- This Implementation Spec (primary input)
- Row 3 Mechanism Spec v0.3 (architectural reference)
- Row 4 Applied v0.2 (common foundations reference — technology stack, persistence, mode discipline decorator pattern)
- Canonical Ledger v2.12 (entity schemas)
- Existing Source Capture implementation as a reference for established patterns (transactional discipline, mode decorator, AnalysisPass population, identifier assignment)

The Agent should implement mechanisms/row_lens_source_reanalysis/ following the established pattern of mechanisms/source_capture/ and then implement the AI-specific additions (prompt templates, response schemas, three-step classification, Stage 1–4 orchestration).

---

## Document End

End of SysEngage Row 4 Mechanism: Row-Lens Source Re-Analysis v0.1.

Companion artefacts produced with this spec:
- SysEngage_Row_4_Understanding_v0_2.md — framework additions for AI-involving mechanisms
- SysEngage_Row_3_Mechanism_Row_Lens_Source_Reanalysis_v0_3.md — Row 3 architectural spec (complete)
- SysEngage_Issues_Tracker_v0_24.md — tracker current state
