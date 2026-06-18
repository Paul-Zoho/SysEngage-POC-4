# SysEngage Row 4 Mechanism: Requirement Derivation

**Implementation specification — physical / builder tier**

Filename: SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_30.md

Version: 0.30 (Supersedes v0.29 — SW-agent spec-review resolutions (six issues), no logic added beyond the corrections; realises Row 3 RD v0.19 / ledger v2.17 unchanged. **Issue 1 (§5.2):** `statement` is `Optional[str]=None` on all three proposal classes with a `@model_validator` requiring `class_model is not None OR statement.strip()` — the invariant is "a proposal carries a prose statement OR a `class_model` to project from" (`str(minLength=1)`+OPTIONAL was unimplementable). **Issue 2 (§5.2, CHK-3d-11, §4.4.3a):** `entity_ref` is allocated by the DD in Stage 4, so the AI-facing `ClassModel.entity_ref` is `Optional[str]=None` (the proposal form; the ledger committed form requires it) — the AI returns the entity **name**, never a `DD###` id (it never could on a FirstRun-empty DD, and authoring DD ids would break the names-only boundary). **CHK-3d-11 splits** into *structural* (Stage 3, against the proposal: enums, ≤1 PK, target *format*, domains, ≥1 attribute, `entity` present) and *referential* (Stage 4, after §4.4.3a sets `entity_ref` from the DD: `entity_ref` resolves, FK/relationship targets resolve). §4.4.3a gains the `entity_ref`-set step. **Issue 3 (§4.4.3a step 4):** `object_refs_resolver.py` is a thin RD-side orchestrator — it calls `dd_service.resolve_object_ref()` for the **name** half (DD resolves `<Entity>`→canonical and hands back the tail; the DD never touches `class_model`) and does the `.attr`/`.value` lookup itself against `class_model` (RD's table). **Issue 4 (§12.3):** the one-time migration for existing production data (no `class_model`s yet) simply **drops DD relationship entries + attributes/value-sets, leaving names + synonyms**; value-set→`class_model` promotion is deferred to the first v0.30 run that derives Structurals (the authoritative domain source is the Structural requirement content, not the DD shadow copies — ledger F107 note); a Non-Loss guard logs `orphan_value_set_on_migration` for any value-set not recoverable from a surviving requirement (the staging-table machinery is removed). **Issue 5 (CHK-3d-12, §9.7):** CHK-3d-12's parent-element set is **non-retired (surviving) parents only** (mirroring the CHK-3d-10 seed set) — a parent retired by a FullRerun of the row above is not a coverage obligation; Fixture 7 asserts it. **Issue 6 (CHK-3d-11, §5.4):** a zero-attribute `class_model` is **rejected** (HARD) — a name-only entity is a DD canonical, not a model; at Row 2, ≥1 attribute MUST carry a semantic type, closing the CHK-3d-12 bypass (zero-attr Row 2 → all Row 3 attributes `introduced` → coverage no-op). VER-3d-26 split (structural / referential); new `validation_failures` `detail`s + `orphan_value_set_on_migration` warning; §12.11 change detail. Version-stamp quadruple swept. No ledger or DD-spec change — DD v0.2/v0.3 already specify `resolve_object_ref` (name-only) and the dangling-`object_ref` Quality check.)

Version: 0.29 (Supersedes v0.28 — physical realisation of Row 3 Requirement Derivation v0.18: **F105 structured data-model representation** (the `class_model` payload on Structural requirements, the per-row population profile, transformation-aware refinement) **+ F107-T1(c,d) the materialised `object_refs` binding** and the DD reference-correction's behavioural arm. Realises ledger v2.17. **Schema (§5.1):** the `requirement` table gains two JSONB columns — `class_model` (NULL; CHECK present only when `requirement_type='Structural'`) and `object_refs` (NOT NULL DEFAULT `'[]'`; CHECK empty unless behavioural). **AI response schema (§5.2):** a `RequirementProposal` gains `class_model` (a new `ClassModel` Pydantic mirroring the ledger `$def`; Structural proposals only) and `object_refs` (candidate dotted paths the statement names; behavioural proposals only). **Stage 2 (IM):** a Structural proposal is formulated *as* a `class_model` at the row's population profile (R2 existence + semantic type → R3 + logical type + domain + business keys → R4 + physical type + null + PK/FK → R5 + precision + checks + storage), with `refinement_kind` ∈ {identity, decompose, realise_relationship, introduce, merge} and attribute `origin` ∈ {refines, realises, introduced} recorded **at derivation** (§5.4 shared block). **Stage 3 (DM):** **CHK-3d-11** — `class_model` structural validity (decidable, HARD: `entity_ref` resolves; `tier` matches `row_target`; ≤1 PK; FK/relationship targets resolve; domains well-formed; `core/class_model_validity.py`) — a valid `class_model`-bearing Structural **skips** the CHK-3d-09 prose-atomicity checks (the entity is the unit, D4); **CHK-3d-12** — `class_model` concept-coverage refinement (rows ≥ 3; every row n−1 model-element covered by ≥1 child under a recorded `refinement_kind`, **parent→child only**; `introduce`/`introduced` children legitimately parentless; an uncovered parent is model-element extinction → `model_coverage_gaps` hard, `core/class_model_coverage.py`), run **per adjacent parent→child row pair** as each child row completes (the CHK-3d-10 cadence — **chain-together** build order, Row 3 v0.18 D1). **Stage 4 (DM):** **§4.4.3c** commits the validated `class_model` and renders the prose `statement` projection (`core/class_model_projection.py`); **§4.4.3a** is rewritten — the DD service is **names-only** (post-F107): the relationship-record (DD §4.3) and value-record (DD §4.4) operations are **removed** (relationships → `class_model.relationships` committed in §4.4.3c; named values → `object_refs`), and a new **step 4 materialises `object_refs`** — each candidate dotted path is resolved leading-`<Entity>`-through-DD-canonical then `.attr`/`.value`-through the owning `class_model`; a fully-resolving path is committed to `requirement.object_refs`, an unresolvable value is recorded as a **dangling binding** (`object_refs_dangling`) for the Quality pass, NOT a derivation reject (the defining Structural may not yet be derived). **One-time migration** (`promote_dd_to_class_model`): promote legacy DD value-sets into `class_model` domains (de-duplicated against the authoritative Structural CHECK), delete the DD value-sets / relationship entries (the DD reverts to names + synonyms), establish `object_refs` for the first time. **Audit (§7):** `dd_binding` drops `relationships_recorded` / `values_recorded`; new `class_model_binding`, `object_refs_binding`, `model_coverage_gaps`. **VER-3d-26/27/28** (structural validity / concept-coverage / `object_refs` resolution); **PLB-3d-07**; **Fixtures 8/9** (PMT `Task` lineage R2→R5; `Task.status.available` + migration); new `execution_warnings`: `class_model_invalid`, `chk3d12_model_element_extinct`, `chk3d12_repair_performed`/`_failed`, `object_refs_dangling`. New §12.10 change detail; §12.3 migration steps. Version-stamp quadruple swept. Realises Row 3 RD v0.18. No change to Path R/N derivation, prose atomicity for behavioural/prose-Structural (CHK-3d-09), seed coverage (CHK-3d-10), the subject check, or the §5.4 row-guidance prose-statement blocks — F105 adds the structured Structural representation alongside them.)

Version: 0.28 (Supersedes v0.27 — physical realisation of Row 3 Requirement Derivation v0.17: **F106 decompose executor discipline** (split-don't-re-decide, children inherit `cci_refs`, no all-or-nothing parse drop). R4_Run10 (the v0.27 build) validated the F104 detector precision (Row-4 over-flags collapsed 13→3) but the 3 retained were trivially splittable ("the mobile application shall **retrieve and display** tasks with available status" → *retrieve tasks* + *display tasks with available status*); the decompose **mechanism** was failing, not hitting a capability limit. SW-agent traced two co-live causes (the R4_Run10 warnings carry no `detail` key → the IM call did not raise → the failure is at parse/schema). **Cause B — all-or-nothing parser (the live trigger), §4.3.** `_parse_repair_response` wrapped the whole child list in one `try/except → return None`: one malformed child silently discarded ALL children — the same swallow class as F100 (logging suppression) and F101 (truncation-to-all-empty). The child most likely malformed was the *retrieve* half, which the IM returned with empty `cci_refs`, tripping the repair schema's `cci_refs` `minItems=1` / `cci_refs_not_empty` validator — a constraint the spec never mandated (§4.3 already says children **inherit** the parent's `cci_refs`). Fixes: (1) `_parse_repair_response` is **item-level resilient** — validate each child independently, keep the valid ones, log+discard only the malformed one (`decompose_child_discarded`, loud), and NEVER return `None`/`[]` when ≥1 valid child exists; (2) **repair children inherit the parent compound's `cci_refs` by construction** — the repair-response schema (`requirement_repair_response_schema.py`) **drops the `cci_refs` `minItems=1` requirement** (children need not carry their own), and the executor assigns each child the parent's `cci_refs` after parse; a child is never rejected for empty `cci_refs`; (3) the secondary `confidence: float` non-Optional risk is removed — `confidence` is Optional/defaulted on repair children (a `null` no longer fails the whole parse). **Cause A — executor re-deciding the split (independent risk), §4.3 / decompose prompt.** The decompose prompt re-embedded the **derivation-time** two-step test ("is there a single unifying obligation? if yes, express it as one") via `_STATEMENT_FORMULATION_GUIDANCE` — but CHK-3d-09 has ALREADY ruled the statement a hard conjoined-predicate that MUST split, so the executor was re-litigating a settled decision and could collapse to one statement (or, under "don't reproduce the compound verbatim", to nothing). Fixes: the two-step subsume-or-split test is **removed from the decompose prompt** (it belongs in derivation, not repair — the repair splits, it does not re-decide); and a concrete **conjoined-predicate exemplar** is added ("retrieve **and** display tasks with available status" → "retrieve tasks" + "display tasks with available status", children inheriting the parent `cci_refs`). New verification **VER-3d-25**; new `execution_warnings`: `decompose_child_discarded`. Version-stamp quadruple swept. Realises Row 3 RD v0.17 §4.1.1(b). This reframes F104(a): the "retained" compounds were largely a decompose-mechanism failure, not inherent un-splittability — F102 retain-on-failure remains the net only for genuinely-hard residue.)

Version: 0.27 (Supersedes v0.26 — physical realisation of Row 3 Requirement Derivation v0.16: **F104(A) conjoined-predicate detector precision**. R5_Run13 (the v0.26 build) made decompose failures legible via the F100 `statement_preview` fix: of 15, only ~1–2 were genuine conjoined-predicates — the rest were behavioural over-flags (12 Functional + 3 Constraint; 0 Structural — the data-model representation is split to F105). The `core/slots.py` detector gains four refinements so it fires on genuine separable obligations only. **P1 — disjunction is a choice, not a split [latent correctness].** The conjoined-predicate and compound-object branches must test for **conjunction ("and") only**. A **disjunction ("or")** in the isolated predicate/object — "expose via a REST endpoint **or** equivalent", "execute a batch process **or** event-driven aggregation", "… **or** higher" — is ONE obligation (a choice/hedge); splitting "A or B" into "do A" + "do B" **inverts the meaning** (either → both), so the detector MUST NOT route predicate/object "or" to a hard branch. Slot-sensitive: an "or" in the **condition** slot stays a compound *condition* (meaning-preserving split) — unchanged. This was latent (the over-flagged ORs failed to decompose and retained as-is under F102), but an improved decompose prompt would have begun wrongly splitting them. **P2 — the conjunction must be in the MAIN predicate.** The verb-on-both-sides test must operate on the main predicate only; a conjunction inside a relative/subordinate clause (introduced by *that / which / who*) modifying a single object ("implement a service **that** evaluates X **and** transitions Y" → object = one service, main predicate single) does NOT flag — generalising the existing "…and which/that…" continuation carve-out to conjunctions *within* such a clause. Decidably: locate the relative-pronoun boundary; conjunctions to its right (inside the clause) are exempt from the main-predicate verb-on-both-sides test. **P3 — member lists extend to operation/privilege lists.** The F103 inseparable-member-list carve-out now also covers operation/privilege lists under one verb ("revoke UPDATE **and** DELETE" — a set of privileges, one obligation); the carve-out's bare-conjuncts-under-one-verb test already generalises, this makes operations/privileges explicit. **P4 — temporal/sequencing subordinators are not conjunctions.** "insert rows … **prior to** deleting" is one action with a temporal qualifier; *prior to / before / after / then* are sequencing subordinators, not "and", and must not be read as a compound trigger. **`statement_preview` sweep (F100 residual).** R5_Run13 still showed one `conjoined_predicate_decompose_failed` with empty `statement_preview` despite the v0.26 two-site fix — any remaining emission path (including non-`_run_conjoined_decompose` sites) must carry `proposal.statement[:80]`; the contract is "every emission, every path." **Residual (F104(a), deferred):** a genuinely conjoined-predicate the IM cannot cleanly split is RETAINED under F102 (present, logged); an enhanced decompose prompt for complex physical compound-verbs is a deferred quality item — not specced here. New verification: **VER-3d-24** (the four precision carve-outs do NOT hard-flag). Version-stamp quadruple swept. Realises Row 3 RD v0.16 §4.1.1(b). Physical-tier detector precision; no change to the F98 three-form rule, F102 retain-on-failure, or F103 — F104 bounds *when* the detector fires, the others govern *what happens* when it does.)

Version: 0.26 (Supersedes v0.25 — physical realisation of Row 3 Requirement Derivation v0.15: **F102 decompose-failure Non-Loss (retain-on-failure)** + **F103 inseparable enumeration/value-list carve-out**, both surfaced by the full v0.25-build re-run R5_Run12 once F100's logging made decompose failures visible. **F102 — retain-on-failure (§4.3).** R5_Run12 showed a high decompose-failure rate concentrated in the over-concentrated deployment domains D015/D016 (Row 4 5/6, Row 5 17/40 — OPEN-DOM-2). SW-agent confirmed the failure path: a hard-rejected compound that fails to decompose was **dropped** from `surviving_09` on the assumption it would fall to CHK-3d-05 orphan recovery — but `new_orphans_09 = eligible_ci − covered_after_09 − existing_orphans`, so when the dropped obligation's CCIs are **coincidentally covered by sibling proposals** (acute where CCIs are coarse — D015 had 3 CCIs across 9 proposals), `new_orphans_09` is empty, no repair fires, and the **obligation is silently lost** (17 drops at Row 5, 5 at Row 4). Fix: when `_run_conjoined_decompose` yields no atomic child, the original compound is **RETAINED in `surviving_09`**, tagged `chk3d09_decompose_failed_retained` (the `conjoined_predicate_decompose_failed` warning still recorded). A compound-but-present obligation beats an atomic-but-absent one; the residual non-atomicity is a logged quality exception, not a lost obligation. The prior v0.25 "CHK-3d-05 carries the recovery" claim is **withdrawn** — CCI coverage is not a sufficient Non-Loss test where CCIs are coarse; CHK-3d-05 remains the path only for genuinely **slotless** statements (no atomic obligation to retain). VER-3d-22 extended from outcome-traced to **obligation-present**: every hard-rejected compound's obligation must be demonstrably present — atomic children, retained compound, or recovered orphan — never absent. Also fixes the **F100 `statement_preview` residual**: both `conjoined_predicate_decompose_failed` emission sites (exception + empty-parse) omitted it in the v0.25 build; now carry `proposal.statement[:80]`. **F103 — inseparable member-list carve-out (§4.3, `core/slots.py`).** A subset of the R5_Run12 D016 failures — enumeration value lists ("shall accept only 'available', 'claimed', 'completed'") and column/attribute-definition lists ("shall define columns child_id, username, …") — are inseparable single concepts where the conjunction joins the members of ONE enumeration/definition, not separable obligations. The build had NO PLB-3d-01 carve-out (the inseparable-concept exemption was docstring-only since compound-object went hard in v0.24), so it hard-rejected these and they failed to decompose. The compound-object detector now carves out **member lists** (conjuncts are bare values / attribute names under a single enumeration-or-definition verb — accept / define / consist-of / contain — not finite action verbs): logged as the soft inseparable edge, not hard-rejected. New `execution_warnings`: `chk3d09_decompose_failed_retained`. Version-stamp quadruple swept. Realises Row 3 RD v0.15 §4.1.1(b). F98/F99/F101 validated at volume (R5_Run12); F102/F103 close on the post-build re-run confirming zero silent drops.)

Version: 0.25 (Supersedes v0.24 — two build bugs surfaced while validating F98/F99 on PMT rows 3 and 5 (R3_Run7/Run8, R5_Run11), both gaps in the v0.24 physical contract: **F100 — CHK-3d-09 decompose-failure logging (§4.3, `_run_conjoined_decompose`)** and **F101 — Stage 4 DD-extraction truncation + silent-swallow (§4.4.3a, `_extract_entity_terms_ai` / `_parse_extraction_response`)**. F98 itself validated cleanly (R3_Run8: 6 hard-rejects, 3 decomposes; R5_Run11: 36 hard-rejects, 30 decomposes, all atomic output well-formed) and F99's recording logic validated (zero clause-dumps under all conditions). **F100 — decompose-failure logging.** `_run_conjoined_decompose` has two failure paths (exception → `except` emits `conjoined_predicate_decompose_failed`; empty-parse → the `if not parsed_decompose:` block emits the same). A dedup guard scoped against the whole-pass `result.execution_warnings` suppressed every failure after the first *for a given `source_domain_id`* — so D017 in R5_Run11 logged 12 hard-rejects, 6 decomposes, 1 failure, leaving 5 rejected proposals with no trace as their CCIs fell to orphan detection. Fix: early `return []` in the `except` branch makes the two paths disjoint; each failed call emits exactly one warning. §4.3 now states the **failure-logging contract**: every decompose invocation that yields no atomic child records **one** `conjoined_predicate_decompose_failed` warning carrying `source_domain_id` + `statement_preview`, **per-invocation not per-domain**; the audit invariant `|conjoined_predicate_hard_reject| = |chk3d09_decompose_performed| + |conjoined_predicate_decompose_failed|` MUST hold within each domain's proposal set (VER-3d-22). **F101 — Stage 4 extraction truncation.** Root cause confirmed from the R5_Run11 fingerprint: `stage4_dd_entity_extraction` emitted `output_tokens: 2048` **exactly** — the `max_tokens` ceiling, hit precisely. Stage 4 issued **one unbatched extraction call for the whole row** (131 reqs, input 13,010 tokens); when decompose enlarged the row (N compounds → 2N+ atomic children), the output JSON overflowed 2048, `json.loads` threw on truncated text, and `_parse_extraction_response` **silently returned all-empty** (`by_idx.get(i, []) → []` for every index) — every requirement fell to `dd_zero_term` with a clean-looking `dd_entity_extraction_all_empty`. This wiped the entire row's DD on any decompose-firing run (R3_Run8, R5_Run11) while R3_Run7 (no decompose, row under-ceiling) extracted cleanly — the decompose↔extraction "interaction" was this latent scaling bug, not a structural fault. This is the **same truncation class v0.19 already fixed for Stage 2 Path-R** (token-ceiling batching); Stage 4 was the one IM call left unbatched. Fixes (§4.4.3a): (i) **extraction is now batched and ceiling-bounded** like Path-R — a batch's expected output must stay under the model `max_tokens`; `_extract_entity_terms_ai` runs in batches sized so total output cannot reach the ceiling, fingerprint stages `stage4_dd_entity_extraction_batch<N>`; (ii) **truncation is a loud hard failure, never silent** — a response detected as truncated (output at the ceiling / `json.loads` failure) records `dd_extraction_batch_truncated` and the batch is retried/re-split, NOT swallowed into all-empty; `_parse_extraction_response` may not return `[]` on a parse error without a warning; (iii) **slot-parse guard** — the `extract_slot_terms` / `_raw_slot_description` loop (currently outside the Stage 4 try/except) is guarded so a slot-parse exception on one proposal degrades that proposal to `dd_zero_term` (`slot_parse_failed`) rather than crashing the whole stage (the latent null-fingerprint cause). Completeness invariant (VER-3d-23, requirement-level): `|reqs contributing ≥1 presented term| + |dd_zero_term| == row requirement count`, with `terms_presented == resolved + |dd_unresolved|` and **no batch truncated**. New `execution_warnings`: `conjoined_predicate_decompose_failed` (now per-invocation), `dd_extraction_batch_truncated`, `slot_parse_failed`, `dd_entity_extraction_all_empty` (retained, but now only legitimate when a row genuinely yields no entity-grade terms — never as a truncation artifact). Version-stamp quadruple swept. F98 stands as resolved; F99 recording logic stands; F99 extraction-volume validation unblocks once F101 lands. Realises Row 3 RD v0.14 (no logical change — both fixes are physical-tier audit/scaling contracts). [Re-issued 15 Jun 2026 — VER-3d-23 corrected to the requirement-level partition; the v0.24-derived draft conflated a term count with the Requirement count (would false-fail a clean run, caught on R1_Run3). No behavioural/version change; the batching build is unaffected.])

Version: 0.24 (Supersedes v0.23 — physical realisation of Row 3 Requirement Derivation v0.14: **F98 conjoined-predicate atomicity** + **F99 Constraint entity extraction**, one shared root — the slot machinery (`core/slots.py` + `stage4_entity_production.py`) was Functional-Object-centric and never generalised to the Constraint-Rule slot or multi-predicate statements. Confirmed against the build by SW-agent review of R5_Run9. **F98 — CHK-3d-09 third compound form (§4.3, `core/slots.py`).** `_check_functional` / `_check_constraint` split on `shall`-count (≥2 → hard `multiple_obligations`), then route ANY `and/or` in the single-`shall` predicate to `compound_object_possible_exception` / `compound_constraint_rule_possible_exception`, both `is_hard=False` — so a conjoined predicate (`shall <verb X> and <verb Y>`: one `shall`, one `and`) was Practitioner-flagged, never rejected. This is why R013/R070/R075/R092/R148/R159/R172 survived Stage 3. §4.3 adds a **conjoined-predicate hard branch**: after the predicate is isolated, a verb-phrase test on both sides of the conjunction — if BOTH conjuncts carry a distinct finite action verb → `is_hard=True` (`conjoined_predicate`); a single verb with conjoined nouns is compound-object (now also hard, per Row 3 §4.1.1(b)); a relative-clause continuation ("…and which/that…", no second finite verb) does NOT flag. CHK-3d-09 **repair is automatic in-place decomposition**: the repair prompt re-expresses the flagged compound as N atomic statements (carrying any dependency as a Condition slot on the dependent half) from one flagged input — NOT the prior reject→orphan-pool→CHK-3d-05 re-derive path (which risked dropping a half). **F99 — §4.4.3a Constraint entity extraction + VER-3d-19 reject.** R5_Run9 registered 30 whole Constraint clauses as DD terms (all 30 malformed entries trace to Constraint-type requirements) via two build paths: `_extract_constraint_slots` returned only the Subject (pre-`shall`), so `_raw_slot_description` passed the Subject as `raw_slot` and the extraction prompt asked for the *subject entity* — yielding a thin subject ("system") or empty, at which point the `stmt[:60]` fallback in `_build_dd_ops_from_terms` fed a 60-char statement fragment to the DD as a canonical name (the DD service's "attribute record:" description is its own response to being handed a clause). Fixes: (1) `_extract_constraint_slots` also returns the **Constraint-Rule** (post-`shall` predicate); (2) `_raw_slot_description` passes the **rule** text as `raw_slot`; (3) the §5.4 / `build_dd_extraction_prompt` Constraint slot-guide redirects from "subject entity" to "**the named domain concept(s) the Constraint-Rule governs**", with rule-content examples; (4) the `stmt[:60]` fallback is **removed** — a Constraint with no extractable governed entity lands in `dd_zero_term`, never a fragment; (5) **VER-3d-19 promoted from warn to REJECT and relocated** from post-commit `__init__.py` into `_build_dd_ops_from_terms` where each term is appended as an op — a clause-grade term (finite verb phrase / sentence punctuation / > ~5 words) is skipped → `dd_zero_term`, not presented (the standalone `_check_ver19` is reused; routing change, not new logic). **Sequenced:** F98 decomposes the do-and-show compounds first, so F99's Constraint rule then handles only clean single-predicate Constraints. New `execution_warnings`: `conjoined_predicate_hard_reject`, `chk3d09_decompose_performed`, `ver_3d_19_term_rejected`. Version-stamp quadruple swept (line-5 filename, this Version line, §12.5 self-reference, doc-end stamp). Realises Row 3 RD v0.14 §4.1.1(b) / §5.5.)

Version: 0.12 (Supersedes v0.11 — concern-atomicity + non-redundancy authoring guidance. Realises Row 3 Requirement Derivation v0.9 §4.1.1. Adds a shared §5.4 cross-row block ("Concern-atomicity and non-redundancy") instructing the AI to (1) author one obligation per requirement at the CONCERN level — a requirement whose grouped CCIs span distinct concerns (different classification types across different Zachman columns) that it does not all voice must be split per obligation, so every concern is *voiced*, not merely referenced (the unvoiced-but-referenced concern is a silent Non-Loss failure and makes the requirement a downstream merge-magnet); and (2) not voice the same concern twice (no near-duplicate restatements, even from overlapping CCI sets — CHK-3d-07 collapses only exact duplicates). New soft diagnostic **ADVC-3d-03** records, decidably, requirements whose `cci_refs` span ≥2 classification types across ≥2 columns (`concern_atomicity_flags`) so over-bundling is measurable across runs. Motivated by PMT R2 Run11: a 4-concern requirement (R025: How/Process + How/Rule + What/Attribute + Why/Constraint) acted as a merge-magnet, and ~40% of a one-paragraph source's Row 2 requirements were near-duplicates — both upstream over-generation that inflate the downstream merge load. The complementary automatic Non-Loss guard on the merge itself is a Requirement Matching concern (deferred pending a re-run under this guidance). No hard reject added (concern-atomicity is an IM judgement, not decidable — guidance shapes generation, ADVC-3d-03 only instruments). CHK-3d-07/09, subject taxonomy, entity/state extraction, schema unchanged.)

Version: 0.11 (Supersedes v0.10 — entity-vs-state reduction. Realises Row 3 Requirement Derivation v0.8 §4.1.1(c). Confirmed against the PMT source, which uses one noun — "task" — in states ("available", "completed", "claimed"): §4.4.3a entity extraction now reduces a STATE/lifecycle-qualified phrase to the BARE entity + state as an attribute ("available tasks"/"completed tasks" → entity `task`, status available/completed), never a compound canonical; and §5.4 Row 1 entity-vocabulary gains the bare-noun clause (the entity is the bare source noun; states and roles are attributes, NOT separate entities — do not coin "task opportunity", "completed achievement", "economic activity", "household economy" for `task`). Fixes the Row 1 Run2 relapse where v0.10 stopped wholesale abstraction ("work unit") but the model coined state-qualified entities, fragmenting one `task` into separate canonicals and re-opening the cross-row resolution gap. Option A (entity flat; state is an attribute value, recorded via the existing DataDictionaryEntry.attributes) — no DD schema or matching change. Rows 2–6 §5.4 unchanged; §4.4.3a state-reduction applies to all rows.)

Version: 0.23 (Supersedes v0.22 — SC-6: `ai_model_fingerprints` placement corrected in the §7 example to match the implementation (align-to-implementation). The §7 JSON nested `ai_model_fingerprints` inside `mechanism_data`; the build emits it as a **top-level `outputs` key**, a sibling of `mechanism_data` / `execution_warnings` / `concern_entities` (`__init__.py`). The §7 prose already declares `execution_warnings` top-level but said nothing for `ai_model_fingerprints`; the example is corrected to place both at top level, and the line-809 callout now names `ai_model_fingerprints` alongside `execution_warnings`. Example-structure fix, no logic change. (VER-3d-08 validates mechanism_data completeness against §7, so the example must show the true nesting.))

Version: 0.22 (Supersedes v0.21 — single targeted §7 correction: the `dd_binding` field in the §7 mechanism_data example used wrong/short-form keys (`presented`/`resolved`/`flagged`) that I introduced in the v0.19 A2 edit, inconsistent with the authoritative §4.4.3b audit block and VER-3d-17 — both of which already use the correct keys (`terms_presented`/`resolved`/`new_canonical`/`synonyms_recorded`/`relationships_recorded`/`values_recorded`/`dd_zero_term`/`dd_unresolved`). The spec, VER-3d-17, and the implementation already agreed on the correct shape; only the §7 example line was wrong. Replaced it with the actual 8-key shape stage4 emits (matching §4.4.3b). No logic change — example-key correction only.)

Version: 0.21 (Supersedes v0.20 — five spec-silence points resolved to align with the validated implementation, per SW-agent review. No model change. **SC-1 (§4.2 IncrementalRerun fallback):** "persistent parse failure" = **ANY** Domain's parse failure (after its retry) during an IncrementalRerun → fall back to FullRerun for the whole row. This is any-domain, not all-domain — an IncrementalRerun is an optimisation; any failure abandons it for a clean full regeneration (consistent with the full-faithful-regeneration policy; the FullRerun loses nothing). Distinct from the FirstRun/FullRerun per-Domain path where a single-Domain failure skips that Domain (§10 edge case) — that path is not optimising and degrades gracefully; the incremental path restarts clean. **SC-2/SC-5 (§7 / §4.1 IdempotentRerun mechanism_data):** an IdempotentRerun writes the **full mechanism_data block** (not a minimal one); `requirements_produced` and `requirement_type_distribution` are sourced from the prior producing pass's `mechanism_data` (`prior_md.get(...)`, defaulting to `[]`/`{}` if absent). **SC-3 (§4.4.5 downstream_rerun_required):** `False` unconditionally on IdempotentRerun (no re-check) — an idempotent pass changed nothing, so it raises no downstream obligation; newly added/removed downstream passes are the orchestrator's concern, not this flag's. **SC-4 (§4.3 repair token budgets):** added an AI-call output-budget table covering all three repair/AI call sites (Path-R §4.2, CHK-3d-05, CHK-3d-09 — and the CHK-3d-10 Path-R repair) so a prompt change cannot silently truncate, the same failure class as the Path-R truncation (A1). Version-stamp quadruple swept.)

Version: 0.20 (Supersedes v0.19 — execution_status vocabulary standardised to the canonical ledger set per SW-agent investigation: `Completed`→`Success`, `CompletedWithWarnings`→`PartialSuccess`, and the IdempotentRerun status is `Success` with `idempotent=true`/`run_scenario="IdempotentRerun"` as the distinguisher (there is no `Skipped` status — the DB never wrote one; the spec word was retired). Background: the ledger always emitted the canonical set via a single export normalisation (`json_builder._map_execution_status`); the DB held a dual vocabulary (spec `Completed`/`CompletedWithWarnings` for SC/CCI/DD/RD, build `Success`/`PartialSuccess` for Matching). The build is being standardised to one vocabulary at source (`core/audit_trail.py`); this spec adopts the same so spec and ledger agree directly. `Failed` is unchanged (it was never transformed). Confirmed in the same investigation: the R5_Run2 Row 5 `Failed` was genuine CHK-3d-10 enforcement (token-overflow → parse failure → 0 Path-R proposals → 26 extinct seeds → extinction_failure branch), validating both the enforcement and the batching diagnosis. Version-stamp quadruple swept. No model/logic change — status-label rename only.)

Version: 0.19 (Supersedes v0.18 — spec reconciled to the batched Path-R implementation per SW-agent review of v0.18; no model change. **A1 (corrects SPEC-F):** §4.2 Path R is NOT one combined call — it runs in batches of ≤ `_PATH_R_BATCH_SIZE` (currently 15) seeds. SPEC-F's "one combined batch" was validated false against the build: ~60 seeds × ~300 output tokens ≈ 27k tokens exceeds the model's 8,192 max_tokens ceiling and truncates the JSON. The spec rule is the token-ceiling constraint (a Path-R call's expected output must stay under the model max_tokens); the batch size is a calibrated constant, not a magic number. Fingerprint stage naming `stage2_path_r_batch<N>`. **A2:** §7 mechanism_data example gains `path_r_count`, `seed_coverage`, `elaboration_gaps` (v0.13) and `dd_binding` (v0.7) — present in logic, absent from the audit example. **A3:** §7 execution_warnings list gains the 11 types the build emits (path_r_parse_failure, path_r_ai_error, path_r_invalid_refines_refs, empty_seed_set_upstream_gap, chk3d10_seed_extinct, chk3d10_repair_performed, chk3d10_repair_failed, atomicity_possible_exception, ver_3d_17_fail, ver_3d_18_fail, ver_3d_19_entity_grade_violations). **A4 + version-stamp sweep:** §12.5 self-reference, line-5 filename, Version line, and doc-end stamp all set to v0.19 (the stamp is a quadruple, not a triple — every occurrence of the version string swept this revision). **B:** §3.1 Stage 2 retry note corrected to per-batch; doc-end stamp carries the v0.18 connection-lifecycle line. Stale code docstrings (stage1 "two-part", stage2 "v0.13") remain flagged code-side. Open for separate investigation: execution_status "Success" vs "Completed" mapping (not specced here).)

Version: 0.18 (Supersedes v0.17 — Stage 4 now conforms to the new Common Implementation Reference §1 for connection/session lifecycle across the IM phase. Neon serverless endpoints auto-suspend (~5 min idle), so a connection held from Stage 1 through the Stage 2/3 IM (AI) phase is dead at the SSL level by Stage 4; `pool_pre_ping` cannot reliably catch this (OS-buffered SSL close_notify) and `session.close()` itself crashes (its ROLLBACK hits the dead connection). Stage 4 now applies the reference realisation — `session.invalidate()` → `engine.dispose()` + `_wait_for_db()` → fresh `get_session()` — by **citation**, not restatement; the dispatcher refreshes the pool between passes. Validated on PMT rows 1–5. This is the FIRST mechanism brought into conformance; Domain Derivation, CCI Construction, and Requirement Matching have the same IM exposure and are to be brought into conformance at their next revisions (Common Implementation Reference Conformance Register). Also: SPEC-17-A — line-5 filename header corrected to v0_18 (was v0_16; the version-stamp triple — Version line, line-5 filename, doc-end stamp — applied). No model/derivation-logic change.)

Version: 0.17 (Supersedes v0.16 — third reconciliation pass per SW-agent review; closes the SPEC-E residual and the §12.5 version stamp. No model change. **SPEC-16-A:** §4.4.2 implementation prose now carries the Path-R fallback carve-out (a reader following §4.4.2 step-by-step previously hit "guaranteed under MD-1" with no exception, though MD-2 §3.2 had it) — empty `domain_refs` from a pure-seed Path-R proposal with empty `cci_refs` falls back to `source_domain_id`, not fail-closed. **SPEC-16-B:** §12.5 primary-inputs line version-bumped v0.5 → v0.17. Two stale code docstrings remain (stage1_preflight.py L12 "two-part hash"; stage2_ai_derivation.py L4 "Spec v0.13") — code-side, flagged for the agent, not resolved in this spec. Implementation confirmed fully conformant to v0.16. No behaviour change.)

Version: 0.16 (Supersedes v0.15 — second reconciliation pass per SW-agent review; clears the MD-3 three-part-hash references and Path-R carry-overs that v0.15 missed, plus the filename. No model change. **SPEC-A:** §12.2 OQ-3d-01 resolution updated to the three-part hash (was "two-part"). **SPEC-B:** §12.5 deviation bullet updated to three-part. **SPEC-C:** §4.4.3 construction clause corrected — `refines_refs` is set at derivation for Path-R children (was the pre-v0.13 "`refines_refs=[]`, Matching-populated" carry-over, which contradicted §4.2); also fixed at the §12 framework bullet, VER-3d-16, and the v2.13→v2.16 normative-rules transcription (`cci_refs` non-empty → not-both-empty). **SPEC-E:** §4.4.2 MD-2 now documents the Path-R fallback — a pure-seed proposal with empty `cci_refs` yields an empty Domain intersection, so `domain_refs` falls back to the seed/source `source_domain_id` rather than failing the MD-2 assert. **SPEC-F:** §4.2 Path-R batching corrected to one combined batch (matches implementation), per-Domain batching noted as deferred. **Filename** line corrected to v0_16. Stale code docstrings (stage1/stage2 "two-part"/"v0.13") flagged for the agent — code change, not spec. No behaviour change.)

Version: 0.15 (Supersedes v0.14 — spec reconciled to the v0.14 implementation per the SW-agent status report; four doc corrections, no model change. **SPEC-1/MD-3:** the re-run input hash is **three-part for rows ≥ 2** — `CCI || DOM || SEEDS` (sorted surviving row n−1 requirement_ids) — because under refinement-driven derivation the row n−1 requirements are a primary derivation input, and an input outside the idempotency key causes a false IdempotentRerun (the BUG-3 cascade: an upstream fix lands, the downstream row's CCI+DOM hash is unchanged, stage 2 is skipped, Path R produces 0 one row lower). Row 1 hash stays two-part. **SPEC-2:** VER-3d-21 (seed-set size == surviving row n−1 count) added to the §8.1 decidable-criteria table with fixture mapping. **SPEC-3:** VER-3d-03 corrected to `≥1 cci_refs OR ≥1 refines_refs` (was `≥1 cci_refs`, which would falsely fail every Path-R requirement — it now matches CHK-3d-02 / migration 025 / ledger v2.16). **SPEC-4:** §3.1 module listing adds the two live Path-R files (`requirement_refinement_prompt.py`, `requirement_refinement_response_schema.py`). Implementation bugs BUG-1 (priority vocabulary High/Medium/Low), BUG-2 (migration 025 relaxes the cci_refs constraint to the not-both-empty OR — the v2.16 contract landing), BUG-3 (the ||SEEDS hash fix) are CLOSED in code; GAP-1/GAP-2 (VER-3d-21, empty_seed_set_upstream_gap) implemented. No model/behaviour change in this spec version.)

Version: 0.14 (Supersedes v0.13 — seed set is PROVENANCE-BLIND. PMT R4_Run4 showed Row 3 seeded from only the 24 Path-R-origin Row 2 requirements, excluding the 6 row-native Path-N ones (seed-coverage 24/27). Stage 1 seed-set assembly is corrected: the seed set = EVERY surviving (non-retired) row n−1 Requirement, irrespective of `cci_refs`/`refines_refs` status — a requirement's own provenance governs nothing about whether it seeds the row below (provenance-blind, as Matching D-rm-8). Only exclusion = retirement. New VER-3d-21: seed-set size == surviving row n−1 count. Also notes the open Row-4 Path-R wiring gap (R4_Run4: path_r=0 at Row 4, 30 elaboration_gaps correctly raised by CHK-3d-10) as an implementation item, not a spec change. No other change.)

Version: 0.13 (Supersedes v0.12 — PHYSICAL realisation of refinement-driven derivation. Realises Row 3 Requirement Derivation v0.12 (F87 corrected). Rows ≥ 2 now derive from TWO co-equal generative sources: **Path R** — interrogative elaboration of each row n−1 seed (F87 method: ask the row-n Zachman interrogatives the seed implies), producing row-n children with `refines_refs=[seed]` set AT DERIVATION; **Path N** — the existing per-Domain row-native CCI formulation, `cci_refs` set, `refines_refs` left for the Matching service to set (parent match) or to emit as an upward gap. Stage 1 assembles the row n−1 Requirement seed set as input (rows ≥ 2). New CHK-3d-10 = downward Non-Loss assertion: every seed must appear in some child's `refines_refs` (refined or linked) — an unrefined seed is extinct; re-prompt Path R, persistent failure = recorded hard failure (NO terminal exit). Path R may yield system OR process/organisational requirements (off-system seeds elaborate to a logical process, not "the system shall"). `cci_refs` relaxed to CONDITIONAL (CHECK: cci_refs OR refines_refs non-empty) — ledger-contract change. `refines_refs` schema note: set by Pass 3d for Path R, by Matching for Path N. §5.4 gains a Path-R interrogative-elaboration prompt block + the system-or-process subject note for Row 3+. mechanism_data gains `elaboration_gaps` and `seed_coverage`; VER-3d-20 (seed coverage). Two-dimensional Non-Loss: downward (seed coverage, CHK-3d-10) + row-native (CCI coverage, CHK-3d-05). Does NOT reopen F83 — Path R seeds enter at Pass 3d, not via Pass 3a signals; the v0.3 within-row realisation lost F87's cross-row half through conflation with F83, now restored. Concern-atomicity (v0.12), subject taxonomy, entity extraction, type/atomicity unchanged.)

Version: 0.10 (Supersedes v0.9 — Row 1 domain-entity vocabulary preservation. Realises Row 3 Requirement Derivation v0.7 §4.1.1(c). Adds a source-entity-preservation rule to §5.4 REQUIREMENT_ROW_GUIDANCE["1"]: abstraction at Row 1 lives in the subject and verb, NOT in renaming the domain entities — keep the Source's domain nouns ("task", "reward", "earnings"); do NOT coin abstract paraphrases ("work unit", "value-generating activity", "strategic value exchange mechanism"). Fixes the observed Row 1 failure where entity-paraphrase produced statements with no extractable entity (entity_extraction_empty → terms_presented=0 → empty Row 1 DD → zero cross-row candidates → zero refine links). The existing "do not reproduce verbatim" rule is reframed so "derive" means re-cast to normative form, NOT relabel entities. Worded as domain-entity preservation, not literal echoing (genuine implementation/UI nouns still neutralise to their domain entity). No change to subject/verb/type guidance, atomicity, or schema. Rows 2–6 unchanged.)

Version: 0.9 (Supersedes v0.8 — Row 2 subject taxonomy / boundary test. Realises Row 3 Requirement Derivation v0.6 §4.1.1(a) / Row 2 Understanding §2.3.3 (R2-AMEND-9, OD-R2-30). The §5.4 REQUIREMENT_ROW_GUIDANCE["2"] subject block is rewritten from "THE BUSINESS (or a named business role) only" to a FOUR-class taxonomy chosen by the BOUNDARY TEST: actor/stakeholder (crosses the boundary inward), system (the boundary affordance — WHAT the system provides, never HOW), business (off-boundary responsibility), named business role (off-boundary accountability). Vocabulary block made subject-class-aware; the no-realisation-vocabulary rule is repositioned as the WHAT/HOW guard that keeps a system-subject statement at Row 2. Atomicity block gains the over-generation brake (author the column-aspects the source expresses; actor-action and its system-affordance are a complementary pair, not independent duplicates). CHK-3d-08 Row 2 subject taxonomy widened accordingly (system-subject at Row 2 no longer a mismatch). Fixes the observed false-merge cascade (R023/R034-class) at its root: the subject slot now carries discriminating actor/system/business information instead of a constant "the business". No change to Stage 2/4 mechanics, DD binding (§4.4.3a), atomicity hard-reject (CHK-3d-09), or schema. Row 1 / Rows 3–6 subject guidance unchanged.)

Version: 0.8 (Supersedes v0.7 — DD term extraction corrected to entity reduction. Realises Row 3 Requirement Derivation v0.5 §5.5 / Data Dictionary v0.2 §3.1. The §4.4.3a term-extraction step is rewritten from a DM slot-reuse ("present the Object slot") to an IM entity reduction: identify the domain entity/entities the Object denotes and present those entity-grade noun phrases to the DD, never the verbatim Object-slot clause. Fixes the observed defect where clausal Objects were stored as DD canonical names (e.g. "a mechanism enabling household members to select and claim available work opportunities."), making every entry a unique one-off and defeating resolution. Extraction is now model-assisted and fingerprinted. New VER-3d-19 (entity-grade term guard). No change to Stage 2 derivation, atomicity, typing, domain_refs, or refines_refs.)

Version: 0.7 (Supersedes v0.6 — DD Object-slot binding activated; realises Row 3 Requirement Derivation v0.4 §5.5 / F90. New Stage 4 sub-step §4.4.3a presents each Functional Object slot / Structural entity / asserted relationship / named value to the Data Dictionary service's resolve-and-record (Row 4 Data Dictionary Service v0.1), which returns the canonical DataDictionaryEntry and records provenance back to the Requirement — this is the DD's incremental population path. The binding is a DM/service step; the derivation AI does not propose DD bindings (§4.2 contract extended). Stage 4 mechanism_data gains a dd_binding block; new VER-3d-17 (every Object/entity presented and resolved-or-flagged) and VER-3d-18 (DD non-empty after a producing run — the regression guard against the empty-DD defect). No change to Stage 2 derivation, atomicity (CHK-3d-09), typing, domain_refs (MD-2), or refines_refs (Matching-populated). Object-slot binding was declared-only through v0.6; v0.7 makes it operative.)

Version: 0.6 (Supersedes v0.5. Interrogative-elaboration increment, realising Row 3 Requirement Derivation v0.3 / findings F87/F88. Changes: (1) §5.4 — shared interrogative-completeness guidance added across all five row blocks: the AI formulates statements by filling the type-required slots (Functional When/Who/Action/Object; Constraint Rule/Subject/Condition/Criteria; Structural composition via Object-recursion), interrogating source content per slot, making the row's set generatively complete and surfacing Structural requirements — staying within the row (no cross-row parent invention). (2) New ADVC-3d-02 — interrogative slot-completeness advisory (soft; logs `interrogative_completeness_advisory` for PLB-3d-07): flags thin type-required slots / un-interrogated Objects, distinct from the HARD CHK-3d-09 atomicity reject. Soft because completeness is generative guidance, and an over-eager hard gate would reject legitimately-terminal requirements. See §12.9 for the v0.5→v0.6 change detail. This completes the F87/F88 guidance that v0.5 explicitly deferred.)

Date: 03 June 2026

**Abstraction level:** Row 4 — Builder / Physical. This spec is the implementable realisation of the mechanism. Every design decision traces to the Row 3 (logical) Requirement Derivation spec; where this spec makes a physical choice the Row 3 spec deferred (an OQ), that resolution is recorded in §12.2.

**Purpose.** Implementation specification for the Requirement Derivation mechanism (Pass 3d). Derives Requirement entities from the CCIs grouped by Pass 3c Domains, with full CCI traceability and deterministic Domain attribution. Architectural pattern is the four-stage IM-primary / DM-envelope pattern shared with Domain Derivation; the logical authority is the Row 3 Requirement Derivation spec. This spec records the physical realisation: module structure, DDL, response schemas, literal prompt guidance, audit structure, fixtures, and VER→pytest mapping.

**Status:** Rows 1–2 validated (Row 1: PMT Run 5 / NQPS Run 2; Row 2: PMT Row 2 Run 1 / NQPS Row 2 Run 1). Rows 3–5 authored, pending test (candidate guidance). §5.4 REQUIREMENT_ROW_GUIDANCE["1"]–["5"] are fully authored; Row 6 is a short-phrase stub. Supersedes v0.3; see §12.7 for the change detail.

---

## 1. Mechanism Identification

| Attribute | Value |
|---|---|
| **Mechanism name** | Requirement Derivation |
| **Mechanism ID** | MECH-3d |
| **Logical authority** | SysEngage_Row_3_Mechanism_Requirement_Derivation_v0.1.md — all sections. This physical spec realises that logical spec. Where silent on a shared pattern, the Row 4 Domain Derivation spec v0.24 governs as the structural sibling. |
| **Operational location** | Phase 3 Pass 3d. Executes after Pass 3c (Domain Derivation) completes for the row; before Phase 5 (Cell Quality) and Phase 6/8 (Coverage). Four stages: Stage 1 (pre-flight + CCI/Domain assembly + re-run detection, DM), Stage 2 (per-Domain AI derivation, IM), Stage 3 (structural validation + conditional repair, DM + IM conditional), Stage 4 (entity production + Domain-ref derivation + ledger commit, DM). |
| **Mechanism class** | AI-involving. IM-primary (Stage 2 per-Domain derivation; Stage 3 conditional Non-Loss repair). DM-envelope (Stage 1; Stage 3 structural checks; Stage 4 entity production, domain_refs derivation, ledger write). LPM throughout — CCI descriptions read as context, not rewritten verbatim into statements. |
| **Module location** | `mechanisms/requirement_derivation/`. See §3.1. |
| **Row applicability** | Row-sequential. Runs once per active row. Reads only the CCIs and Domains of the current row. The row's REQUIREMENT_ROW_GUIDANCE block (§5.4) governs statement subject and vocabulary. |
| **Mechanism Stakeholder** | None. SH001 covers structural review. SG-01 covers Practitioner quality review (§8.2). SG-03 carries execution attribution via AnalysisPass. |
| **Mode declaration** | Primary mode IM (Stage 2). DM sub-acts: pre-flight, structural validation, domain_refs derivation, entity production, RequirementRegister construction, AnalysisPass write. LPM throughout. |

---

## 2. Cross-References

| Source | Reference | What this provides |
|---|---|---|
| **Row 3 Requirement Derivation v0.18** | All sections | **Logical authority.** §4 stage logic, §4.1.1 REQUIREMENT_ROW_GUIDANCE incl. **§4.1.1(g) `class_model`** (logical), §5 schema, §5.5 DD name-registration + `object_refs`, §6 re-run, §8 VER/PLB, §12.4 decision trace. This spec realises each; section-level traces inline. |
| **Row 4 Domain Derivation v0.24** | All sections | **Structural sibling.** Shared four-stage pattern, mode-discipline decorator, `mechanism_data` audit convention, `execution_warnings` placement, fingerprint structure, fixture/AI-stub patterns, repair-prompt-as-IM-sub-act. This spec matches its conventions. |
| **Row 4 Applied v0.2** | All sections | Common architectural commitments: Python 3.12+, FastAPI, Neon PostgreSQL via SQLAlchemy + Alembic, Pydantic v2, Claude Sonnet via Anthropic API, pytest, transactional discipline, mode-discipline decorator. |
| **Canonical Ledger v2.17** | Requirement, RequirementRegister, AnalysisPass, `ClassModel` `$def`, DataDictionaryEntry | Authoritative schemas. Requirement carries `refines_refs`, the three-value `requirement_type`, and (v2.17) OPTIONAL `class_model` (Structural, F105) + `object_refs` (behavioural, F107). DataDictionaryEntry is reference-only (no `attributes`/value-sets, `relationship` `entry_kind` retired — Row 3 DD v0.3 / Row 4 DD v0.2). Normative rules transcribed in §5.1. |
| **Segmentation spec v9.2** | Statement formulation | Atomic, single-intent, normative, no inferred actors/behaviours. Realised in §5.4 guidance. |
| **sys_engage_specification_v2.md** | §Phase 3 Requirement Generation, §ADR | POC source for type-classification reasoning signals. Read as principle (D4), realised as §5.4 reasoning block — not a lookup table. |
| **Tracker v0.54** | F80, F81 | F80 (Open, derivation half closed): consume Domains by domain_id (§4.4.2). F81 (Open): Rows 1–2 validated; Rows 3–5 guidance authored here (§5.4), candidate/pending test; Row 6 stub. |

---

## 3. Architectural Approach

### 3.1 Module structure

```
mechanisms/requirement_derivation/
  __init__.py                                  # Orchestration — Stages 1–4 in sequence
  stage1_preflight.py                          # DM: Pass 3c prerequisite; eligible CCI + active Domain
                                               #     assembly; input hash (three-part for rows ≥ 2: CCI|DOM|SEEDS); scenario detection; idempotent exit
  prompts/requirement_refinement_prompt.py     # Path R: seed interrogative-elaboration prompt (stage2 + CHK-3d-10 repair)
  schemas/requirement_refinement_response_schema.py  # Pydantic: Path R refinement response
  stage2_ai_derivation.py                      # IM: per-Domain derivation loop; schema validation at boundary;
                                               #     per-batch retry on parse failure (Path R batched ≤15, §4.2); IncrementalRerun branch
  stage3_structural_validation.py              # DM: CHK-3d-01..08; ADVC-3d-01; Non-Loss repair dispatch (IM conditional)
  stage4_entity_production.py                  # DM: requirement_id allocation; domain_refs DM-derivation;
                                               #     Requirement construction; §4.4.3a DD name-registration (names only, post-F107)
                                               #     + object_refs materialisation (F107); §4.4.3c class_model commit + prose projection (F105);
                                               #     (_extract_constraint_slots/_raw_slot_description/_build_dd_ops_from_terms; VER-3d-19 reject, F99);
                                               #     FullRerun retirement; ledger
                                               #     transaction; RequirementRegister replace; AnalysisPass write
  prompts/
    requirement_derivation_prompt.py           # FirstRun / FullRerun per-Domain template; injects ROW_GUIDANCE[row]
    requirement_incremental_prompt.py          # IncrementalRerun template
    requirement_repair_prompt.py               # CHK-3d-05 Non-Loss repair template
    requirement_row_guidance.py                # REQUIREMENT_ROW_GUIDANCE dict (§5.4) — DISTINCT from domain ROW_GUIDANCE
  schemas/
    requirement_derivation_response_schema.py  # Pydantic: primary derivation response
    requirement_incremental_response_schema.py # Pydantic: IncrementalRerun response — DISTINCT class (§5.2)
    requirement_repair_response_schema.py      # Pydantic: repair response — DISTINCT class (§5.2)
    class_model_schema.py                      # Pydantic: ClassModel ($def mirror, F105) — Structural proposal payload (§5.2)
  core/
    slots.py                                   # CHK-3d-09 conjoined/compound detector (F98/F102/F103/F104/F106)
    class_model_validity.py                    # CHK-3d-11: class_model structural validity (F105, §4.3)
    class_model_coverage.py                    # CHK-3d-12: cross-row concept-coverage refinement (F105/OQ-105-01, §4.3)
    class_model_projection.py                  # DM: render the prose `statement` projection from a class_model (§4.4.3c)
    object_refs_resolver.py                    # DM: materialise object_refs (name→DD canonical→class_model value), §4.4.3a step 4 (F107)
  migrations/
    add_class_model_object_refs_columns.py     # Alembic: requirement.class_model (JSONB NULL) + object_refs (JSONB NOT NULL '[]'), §5.1
    promote_dd_to_class_model.py               # one-time data migration: DD value-sets → class_model domains; delete DD value-sets/relationships; establish object_refs (F107-T1(d), §12.3)
```

### 3.2 Major design decisions

These realise the Row 3 logical decisions (Row 3 §12.4). Rationale is in the Row 3 spec; this section records only the physical realisation.

**MD-1 — Per-Domain Stage 2 (realises Row 3 §4 Stage 2 / D1a).** One AI call per active Domain; the Domain's `cell_content_item_refs` is the derivation scope. A Requirement references CCIs from exactly one Domain. Forward-compatible with whole-row (D1b): the Stage 4 `domain_refs` intersection (MD-2) is general, so a later switch changes only the Stage 2 loop boundary.

**MD-2 — `domain_refs` DM-derived (realises Row 3 §4 Stage 4 / D2).** The AI never proposes `domain_refs`. Stage 4 computes, per Requirement, the set of active Domains whose membership intersects the Requirement's `cci_refs`. Guarantees the ledger's resolution and row-consistency rules by construction. Under MD-1 the intersection yields one Domain; written generally regardless. **Path-R fallback:** a pure-seed-elaboration proposal may carry empty `cci_refs` (it traces to its seed, not a row-n CCI), so the CCI-intersection yields an empty Domain set — in that case `domain_refs` is taken from the proposal's `source_domain_id` (the seed's Domain lineage, tagged in §4.2), NOT failed. Empty result with empty `cci_refs` → fall back to `source_domain_id`; empty result with non-empty `cci_refs` → fail closed (a genuine defect, §4.4.2).

**MD-3 — Input hash; three-part for rows ≥ 2, two-part for Row 1 (realises Row 3 §6 / D3, resolves OQ-3d-01).** `requirement_input_hash = SHA-256("CCI:" + "|".join(sorted(ci_ids)) + "||DOM:" + "|".join(sorted(active_domain_ids)) [ + "||SEEDS:" + "|".join(sorted(surviving_row_(n-1)_requirement_ids)) ])`. The `||SEEDS:` segment is included **for rows ≥ 2 only** (Row 1 has no row above; its hash stays two-part). The seed segment is REQUIRED at rows ≥ 2 because the row n−1 requirement set is a primary derivation input under refinement-driven derivation: omitting it lets a change in the row above go undetected, producing a false `IdempotentRerun` that skips Stage 2 and yields `path_r=0` one row down (the BUG-3 cascade — each upstream constraint fix would otherwise silently reproduce the wiring-gap symptom at the next row). The sorted active Domain-id list is also stored separately in `mechanism_data.domain_id_set` for the Domain-set-change comparison. A Pass 3c FullRerun changes the DOM portion; a change in any surviving row n−1 requirement_id changes the SEEDS portion; either forces FullRerun (§4.1).

**MD-4 — Four re-run scenarios (realises Row 3 §6).** FirstRun / IdempotentRerun / IncrementalRerun / FullRerun, selected by hash comparison refined by the Domain-set rule. Same detection skeleton as the sibling §4.1.

**MD-5 — Type classification principle-based (realises Row 3 §4.1.1(d) / D4).** Enum enforced at the Pydantic parse boundary; value choice is IM, informed by the §5.4 reasoning block. No lookup table.

**MD-6 — Global `R###` allocation (realises Row 3 §5.4).** Single per-project sequence, never row-scoped, never reused (includes retired). See §5.3.

**MD-7 — `class_model` is IM-proposed, DM-validated, per-row profile (realises Row 3 §4.1.1(g) / §5.5 / D1, D4–D6, OQ-105-01; F105).** A Structural proposal carries a `class_model` (the structured What/Data model of one entity at this row) as an IM output of Stage 2 — populated to the row's profile per the §5.4 shared block (R2 existence+semantic-type → R3 +logical-type+domain+business-keys → R4 +physical-type+null+PK/FK → R5 +precision+checks+storage), with `refinement_kind` and attribute `origin` recorded **at derivation** (the IM that splits an entity records which transformation it did — never inferred downstream). It is validated by **CHK-3d-11** (DM, decidable structural validity — the entity is the unit of atomicity, D4, so a valid `class_model`-bearing Structural skips the CHK-3d-09 prose checks) and **CHK-3d-12** (DM, cross-row concept-coverage), and committed in **§4.4.3c**, where a deterministic projector renders the prose `statement`. **Build order — chain-together:** the chain is derived top-down R2→R5 and CHK-3d-12 runs per adjacent parent→child row pair as each child row completes (the CHK-3d-10 cadence), so coverage validates incrementally; this is the Row 3 v0.18 D1 sequencing, NOT a physical-first backfill.

**MD-8 — `object_refs` is DM-materialised at Stage 4; the DD is names-only (realises Row 3 §5.5; F107).** A behavioural proposal carries candidate `object_refs` (the dotted paths the statement names — `<Entity>` / `<Entity>.<attr>` / `<Entity>.<attr>.<value>`) as an IM output; Stage 4 §4.4.3a **materialises** each by resolving the leading `<Entity>` through the DD canonical name and the trailing `.attr`/`.value` through the owning `class_model`, committing the resolved path to `requirement.object_refs` and recording an unresolvable value as a **dangling binding** for the Quality pass (NOT a derivation reject). Post-F107 the DD is a pure naming / synonym index: the §4.4.3a relationship-record (DD §4.3) and value-record (DD §4.4) operations are **removed** — relationships live in `class_model.relationships`, named values in `object_refs`. The DD service answers "what is this called and what does the name resolve to"; `class_model` answers "what is the thing."

### 3.3 Large CCI set advisory threshold

Per-Domain derivation keeps per-call CCI counts small, so the sibling's whole-row large-set risk is largely mitigated. A `large_cci_set_advisory` fires if the **row's** total `cci_count_input > requirement_large_cci_set_advisory_threshold` (default 80) — a Practitioner density signal, not a chunking trigger (no chunking at v0.1). Per-Domain processing proceeds regardless.

---

## 4. Stage-by-Stage Implementation

### 4.1 Stage 1 — Pre-flight, CCI/Domain Assembly, Re-run Detection (DM)

Realises Row 3 §4 Stage 1 and §6.

**Precondition (hard stop):** Query AnalysisPass for `mechanism="DomainDerivation"`, `row_ref=current_row`, `project_id`. If absent or `execution_status="Failed"`: Pass 3d `execution_status="Failed"`, `failure_reason="Pass 3c prerequisite not met"`. An IdempotentRerun Pass 3c satisfies the gate if a prior Success Pass 3c exists.

**CCI assembly:** `cell_content_item JOIN zachman_cell WHERE zachman_cell.row_target = str(current_row) AND project_id = :pid`. Record `cci_count_input`.

**Domain assembly:** `SELECT domain_id, name, description, cell_content_item_refs FROM domain WHERE project_id=:pid AND row_target=str(current_row) AND retired_at IS NULL`. Record `domain_count_input`.

**Zero-CCI early exit (realises Row 3 §3.1):** if `cci_count_input==0`: AnalysisPass `execution_status="PartialSuccess"`, `execution_warnings += no_cci_input`. RequirementRegister `member_ids = query_all_active_requirement_ids(project_id)` — project-wide, all rows, `retired_at IS NULL`. **Do NOT empty the register.** Exit. (NQPS Row 4.)

**Pass 3c invariant guard (realises Row 3 §3.1):** if `cci_count_input>0 AND domain_count_input==0`: `execution_status="Failed"`, `failure_reason="Pass 3c invariant violated — CCIs exist but no active Domains cover them"`. Unreachable given VER-3c-05; asserted not silently patched.

**Large-set advisory:** if `cci_count_input > threshold`: `mechanism_data.large_cci_set_advisory=true`.

**Re-run detection (MD-3):** compute `current_hash`. Query most recent non-Failed Pass 3d AnalysisPass for this row/project.
- None → `FirstRun`.
- `current_hash == prior.mechanism_data.requirement_input_hash` → `IdempotentRerun`.
- Else:
  - If `sorted(active_domain_ids) != prior.mechanism_data.domain_id_set` → **`FullRerun`** (Domain-set change; per-Domain scoping invalidated).
  - Else (Domain set unchanged, CCI delta only):
    - `prior_cci_count = prior.mechanism_data.cci_count_input`. If `prior_cci_count==0` → treat as `FirstRun`.
    - `covered = query_covered_cci_ids_for_row(row, project_id)` — live query: `SELECT DISTINCT jsonb_array_elements_text(cci_refs) FROM requirement WHERE project_id=:pid AND row_target=:row AND retired_at IS NULL`.
    - `new_cci_count = len(eligible_ci_ids - covered)`.
    - If `new_cci_count / prior_cci_count >= requirement_rerun_threshold` → `FullRerun`; else `IncrementalRerun`.

**IdempotentRerun exit:** AnalysisPass `execution_status="Success"`, `mechanism_data.run_scenario="IdempotentRerun"`, `idempotent=true`, `requirement_input_hash=current_hash`, `ai_model_fingerprints=[]`. Existing Requirements and register unchanged. **mechanism_data is the FULL block (SC-2), not a minimal one** — `requirement_count_produced=0` (this run produced nothing), and `requirements_produced` / `requirement_type_distribution` are **sourced from the prior producing pass's `mechanism_data`** (`prior_md.get(...)`; default `[]` / `{}` if no prior pass exists, SC-5). `downstream_rerun_required=false` (SC-3, §4.4.5). Exit.

**Error cases:** DB failure during assembly → `Failed`. CCI referencing a non-existent ZachmanCell → `execution_warnings += cci_referential_integrity_violation`; exclude; continue.

### 4.2 Stage 2 — Derivation Act (IM): Path R (refinement) + Path N (row-native)

Realises Row 3 §4 Stage 2 (v0.12). **At rows ≥ 2 both paths run; at Row 1, only Path N.** Stage 1 additionally assembles the **seed set** = the surviving (non-retired) row n−1 Requirements `[{requirement_id, statement, requirement_type, domain_refs}]` (runtime query of the RequirementRegister; rows ≥ 2 only). **The seed set is provenance-blind: it includes EVERY surviving row n−1 Requirement irrespective of `cci_refs`/`refines_refs` status — Path-R-origin, row-native Path-N (empty `refines_refs`), and policy-source (empty `cci_refs`) requirements are all seeds. A requirement's own provenance does NOT filter it from seeding the row below; the only exclusion is retirement.** Decidable check (VER-3d-21): `len(seed_set) == count(surviving row n−1 Requirements)` — a smaller seed set means a provenance filter has wrongly crept in (the R4_Run4 defect: 24 instead of 27). Empty seed set at row ≥ 2 → `execution_warnings += empty_seed_set_upstream_gap`.

**Path R — interrogative elaboration of seeds (rows ≥ 2; F87).** Invoke over the seed set **in batches of ≤ `_PATH_R_BATCH_SIZE` seeds** (currently 15; constant in `stage2_ai_derivation.py`). Batching is REQUIRED, not optional: a single call over a large seed set (~60 seeds × ~300 output tokens ≈ 27k) exceeds the model's `max_tokens` ceiling (8,192) and truncates the response JSON. The governing spec rule is the **token-ceiling constraint** — each Path-R call's expected output must stay under the model `max_tokens`; the batch size is a calibrated constant satisfying it for the current model/seed profile, not a fixed magic number (recalibrate if the model ceiling or per-seed output size changes). Each batch invokes `requirement_refinement_prompt.py` with `row_ref`, `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]`, the seed list, and the Path-R interrogative block (§5.4). For each seed the AI returns either (i) one or more row-n child statements realising it — each tagged `refines_refs=[seed_id]` (set AT DERIVATION, by construction); or (ii) a link to an already-produced row-n requirement (seed_id appended to that requirement's `refines_refs`). **No terminal option.** Children may be system OR process/organisational (§5.4). Parse against `requirement_refinement_response_schema.py`; **one retry per batch** on parse failure; persistent per-seed failure feeds CHK-3d-10. Fingerprints record each batch as `stage2_path_r_batch<N>`. (Per-Domain batching of seeds remains deferred — the size-based batching here is orthogonal and driven by the token ceiling, not by Domain boundaries.)

**Path N — per-Domain row-native derivation (all rows):**

**FirstRun / FullRerun (per-Domain loop — MD-1):** for each active Domain `d`:
- Expand `d.cell_content_item_refs`; assemble `domain_cci_set` = `[{ci_id, column, classification_type, description}]` joined from eligible CCIs.
- Invoke `requirement_derivation_prompt.py` with `row_ref`, `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` (§5.4), `domain={domain_id,name,description}`, `domain_cci_set`.
- Claude Sonnet (model per Row 4 Applied §4.5). Parse against `requirement_derivation_response_schema.py`. Parse failure → one retry, identical prompt. Second failure → log `domain_derivation_parse_failure` in `validation_failures`; skip Domain (its CCIs become orphans for CHK-3d-05). **All** Domains fail → `execution_status="Failed"`, `failure_reason="AI derivation parse failure for all Domains after retry"`.
- Tag each proposal with in-memory `source_domain_id` (not a Requirement attribute).

**IncrementalRerun:** reachable only when Domain set unchanged. For each Domain owning ≥1 new CCI: assemble existing Requirement summaries `{requirement_id, statement, requirement_type}` for that Domain and `new_domain_ccis` (the Domain's not-yet-covered CCIs). Invoke `requirement_incremental_prompt.py`. Parse against the incremental schema. One retry. **Persistent failure on ANY Domain (SC-1)** — not only all Domains — → `execution_warnings += incremental_fallback_to_fullrerun`; re-invoke Stage 2 FullRerun path for the whole row. Rationale: IncrementalRerun is an optimisation; any per-Domain failure abandons it for a clean full regeneration (full-faithful-regeneration policy — the FullRerun discards and regenerates the whole row, losing nothing). This is deliberately distinct from the FirstRun/FullRerun per-Domain path (§10), where a single-Domain parse failure skips that Domain (its CCIs → CHK-3d-05) and the run continues — that path is not optimising and degrades gracefully in place.

**Fingerprinting:** one `ai_model_fingerprints` entry per call: `{stage:"stage2_domain_<domain_id>", model, input_tokens, output_tokens}`. Repair fingerprinted separately (`stage3_repair`).

**LPM:** prompt instructs the AI not to copy CCI description text verbatim into the statement. Automated verbatim detection not implemented at v0.1 (PLB-3d-04).

### 4.3 Stage 3 — Structural Validation (DM, with conditional IM repair)

Realises Row 3 §4 Stage 3. All in-memory except the repair prompt.

**CHK-3d-01 — No empty statement.** Empty/whitespace → reject; log in `validation_failures`.

**CHK-3d-02 — Reference present (conditional).** A proposal with BOTH `len(cci_refs)==0` AND `len(refines_refs)==0` → reject; log. A Path-R refinement child may have empty `cci_refs` if it carries `refines_refs` (it realises a seed, not a row-n CCI); a Path-N requirement must carry `cci_refs`. Invariant: `cci_refs` OR `refines_refs` non-empty.

**CHK-3d-03 — cci_refs ⊆ source Domain membership.** Strip refs not in the source Domain's membership; log stripped. If emptied → reject (as CHK-3d-02). Enforces MD-1.

**CHK-3d-04 — fit_criteria integrity.** Present-but-empty → strip, log `fit_criteria_empty_stripped`. `verification_method=="Measurement"` and fit_criteria absent → log `measurement_missing_fit_criteria` (informational; PLB-3d-05).

**CHK-3d-05 — Non-Loss.** `orphaned = eligible_ci_ids - {ref for p in proposals for ref in p.cci_refs}`. If non-empty: invoke repair (IM sub-act). For each orphan resolve owning Domain(s) (non-empty by Pass 3c Non-Loss). Assemble `requirement_repair_prompt.py` with `orphaned_ccis=[{ci_id,column,classification_type,description,owning_domain_id,owning_domain_name}]` + REQUIREMENT_ROW_GUIDANCE. Parse against repair schema; one attempt (no retry). Tag repair proposals `source_domain_id=owning_domain_id`. Merge; recompute `orphaned`. Persistent orphan → record in `mechanism_data.orphaned_ccis`; `execution_status="PartialSuccess"`; raise Concern (CN-NNN). `execution_warnings += chk3d05_repair_performed` / `chk3d05_repair_failed` as applicable.

**AI-call output budgets (SC-4).** Every IM call site must keep expected output under the model `max_tokens` ceiling, or risk truncated JSON (the Path-R truncation class, A1/§4.2). Budgets for all repair/derivation IM calls:

| Call site | Prompt | Output-size control |
|---|---|---|
| Stage 2 per-Domain derivation | `requirement_derivation_prompt.py` | One Domain's CCIs per call — bounded by Domain CCI count |
| Stage 2 Path-R elaboration (§4.2) | `requirement_refinement_prompt.py` | **Batched ≤ `_PATH_R_BATCH_SIZE` (15) seeds** — keeps output < `max_tokens` (8,192) |
| Stage 3 CHK-3d-05 Non-Loss repair | `requirement_repair_prompt.py` | Scoped to the orphaned CCI set (typically small); if the orphan set could exceed the ceiling, batch as Path-R does |
| Stage 3 CHK-3d-10 Path-R repair | `requirement_refinement_prompt.py` (scoped to unrefined seeds) | Inherits the §4.2 ≤15-seed batching |
| Stage 3 CHK-3d-09 atomicity (re-formulation, where applicable) | repair path | Scoped to the flagged statement(s); per-statement, inherently small |

The governing rule is the token-ceiling constraint (§4.2); batch sizes are calibrated constants in `stage2_ai_derivation.py` / repair modules, recalibrated if the model ceiling or per-item output size changes. A new or widened repair prompt MUST re-check its budget against this table.

**CHK-3d-10 — Downward Non-Loss (rows ≥ 2; the seed-coverage assertion, realises Row 3 §CHK-3d-10).** `unrefined = {seed_id for seed in seed_set} - {p for child in proposals for p in child.refines_refs}`. If non-empty: invoke Path-R repair (IM sub-act) — re-prompt elaboration of each unrefined seed (`requirement_refinement_prompt.py` scoped to the unrefined seeds); one attempt. Recompute `unrefined`. Persistent unrefined seed → record in `mechanism_data.elaboration_gaps`; `execution_status` escalates and a **hard failure is recorded** for Practitioner attention (`execution_warnings += chk3d10_seed_extinct`) — an unrefined seed is dropped from the design (extinction), the downward analogue of CHK-3d-05. Record `mechanism_data.seed_coverage = {seeds, covered, ratio}`. (Non-Loss is two-dimensional: CHK-3d-05 = row-native CCI coverage; CHK-3d-10 = downward seed coverage.)

**CHK-3d-06 — Failure path.** Proposal set empty after CHK-3d-01..03 **and** repair produced nothing → `execution_status="Failed"`, `failure_reason="No valid Requirement proposals survived validation"`.

**CHK-3d-07 — Exact-duplicate collapse.** Two proposals with identical `statement` (case-insensitive) **and** identical `cci_refs` set → collapse to first; log `duplicate_requirement_collapsed`. (No name-uniqueness analogue — Requirements have no unique name. Near-duplicates → PLB-3d-01.)

**CHK-3d-08 — Row-appropriate statement subject (decidable; realises Row 3 §4 Stage 3 / closes F81 detection).** For each surviving Requirement, test the statement's grammatical subject against the row's permitted subject set (§5.4(a)). At Row 1 the subject must be the enterprise; a statement opening "The system shall…" (or otherwise system/component-subjected) at Row 1 is a mismatch. **At Row 2 the permitted set is {the business, a named business role, an actor/stakeholder, the system} (the four-class taxonomy, R2-AMEND-9 / OD-R2-30): an actor-subject ("a child can claim…") and a system-subject ("the system shall make … claimable") are NOT mismatches at Row 2; only an out-of-set subject (e.g. "the enterprise shall…" at Row 2) is.** The WHAT-vs-HOW discrimination for a system-subject statement (does it name realisation — Row 3 — rather than the provided capability?) is a *vocabulary* concern enforced by §5.4's no-realisation-vocabulary guidance, NOT by this subject check; CHK-3d-08 tests the subject only. **Severity (resolves Row 3 OQ-3d-03): soft** — a mismatch logs `subject_vocabulary_mismatch` in `mechanism_data.subject_vocabulary_flags` (`[{requirement_id_placeholder, row, detected_subject}]`) and surfaces via PLB-3d-02; it does NOT reject the Requirement or block production. Rationale: validated across Rows 1–3, 5 production runs (Tracker F81) — the §5.4 guidance held subject discipline at 100%, so the check has been a clean backstop rather than a frequent rejecter; soft severity is retained. The check is a decidable detector (subject extraction is a closed test), consistent with classifying it CHK not PLB.

**CHK-3d-09 — Typed-slot atomicity (decidable, HARD; realises Row 3 §4.1.1(b) / F88).** For each surviving Requirement, validate the statement against the slot pattern its `requirement_type` selects (F88):
- *Functional* → `[Condition,] Subject shall Action Object`. Required slots present: Subject, Action, Object.
- *Constraint* → `Subject shall comply-with Constraint-Rule [under Condition] [to Criteria]`. Required: Subject, Constraint Rule.
- *Structural* → `Entity comprises/has/relates-to Structural-element`. Required: Entity, structural assertion.

Reject (log `atomicity_violation {requirement_id_placeholder, violation}` in `validation_failures`) when any of: **compound condition** (two+ conditions joined by and/or); **compound object** (two+ independent objects joined by conjunction under a *single* predicate verb, unless an inseparable single concept — PLB-3d-01); ***conjoined predicate*** (two+ obligations joined by a conjunction, each conjunct carrying its **own finite action verb** — `Subject shall <verb X> and <verb Y>`, the "do-and-show" form — F98); **multiple constraint rules / criteria** in one statement; **missing required slot** for the type.

**Detector (`core/slots.py`, F98).** `_check_functional` / `_check_constraint` first split on `shall`-count: ≥2 `shall` → hard `multiple_obligations` (unchanged). For the single-`shall` case they isolate the predicate (text after `shall`) and scan for `and/or`. The v0.23 build routed ANY predicate conjunction to a soft `compound_object_possible_exception` / `compound_constraint_rule_possible_exception` (`is_hard=False`) — the gap that passed the seven R5_Run9 compounds. v0.24 adds a **verb-phrase test on the two conjuncts**: if BOTH sides of the conjunction carry a distinct finite action verb → **conjoined predicate**, `is_hard=True` (`conjoined_predicate`); if a single verb governs two conjoined noun phrases → **compound object**, `is_hard=True` (`compound_object` — promoted from the soft exception to honour Row 3 §4.1.1(b)); a conjunction introducing a **relative / subordinate clause** with no second finite verb ("…and which is retained…", "…and that the parent approves") is NOT a compound and does not flag. The inseparable-single-concept case (one genuine concept lexicalised with "and", e.g. a "name and address" record) remains the single soft edge (PLB-3d-01, logged not auto-rejected) — and it **explicitly includes member lists (F103, extended F104 P3)**: an **enumeration value list** ("shall accept only 'available', 'claimed', 'completed'"), a **column / attribute-definition list** ("shall define columns child_id, username, …"), an **operation / privilege list** ("shall revoke UPDATE **and** DELETE" — a set of privileges under one verb), and any other list whose conjunction joins the **members of ONE enumeration/definition**, not separable obligations. The carve-out is decidable: the conjuncts are **bare values or attribute names governed by a single enumeration-or-definition verb** (accept / define / consist-of / contain / comprise), NOT distinct finite action verbs — `core/slots.py` must apply this member-list test **before** the compound-object hard branch fires. The v0.24/v0.25 build had no such carve-out (the inseparable-concept exemption was docstring-only once compound-object went hard), so it hard-rejected these lists, which then could not decompose (R5_Run12 D016). **Detector precision (F104) — three further bounds so the hard branches fire on genuine separable obligations only (R5_Run13: the bulk of decompose "failures" were behavioural over-flags):** **(P1) conjunction only, never disjunction.** Both hard branches (conjoined-predicate and compound-object) test for **"and"**; a predicate/object **"or"** — "via a REST endpoint **or** equivalent", "a batch process **or** event-driven aggregation", "… **or** higher" — is a single-obligation choice/hedge and MUST NOT route to a hard branch (splitting "A or B" into two conjuncts inverts either→both). The split on `and/or` that fed the hard branches is narrowed to `and`. Slot-sensitive: an `or` joining two **conditions** (the pre-predicate condition slot) remains a compound *condition* (its split is meaning-preserving) — unchanged. **(P2) main-predicate scope.** The verb-on-both-sides test runs on the **main predicate only**. After isolating the predicate, if a relative/subordinate clause is present (a *that / which / who* boundary), conjunctions **to the right of that boundary** (inside the clause, modifying a single object) are exempt — "implement a service **that** evaluates X **and** transitions Y" has main predicate "implement a service" (single). This generalises the existing trailing-"…and which/that…" carve-out to any conjunction *within* the relative clause. **(P4) temporal/sequencing subordinators are not "and".** *prior to / before / after / then* joining two clauses ("insert rows … **prior to** deleting …") express one action with a temporal qualifier, not a conjoined obligation, and do not trigger the hard branch. After P1–P4, a residual genuinely-conjoined predicate the IM cannot split is RETAINED under F102 (below); the decompose-prompt enhancement for such physical compound-verbs is deferred (F104(a)). The same verb-on-both-sides test applies in `_check_constraint` against the Constraint-Rule predicate.

**Severity: HARD. Repair: automatic in-place decomposition (F98).** A compound or slotless statement is a structural defect — it explodes the verification test space and cannot be elaborated downward (the recursive object-interrogation needs a single object). For a **compound** violation (conjoined-predicate / compound-object / compound-condition) the repair is **automatic in-place decomposition**, NOT reject-and-re-derive: the CHK-3d-09 repair prompt is handed the single flagged statement and instructed to re-express it as N atomic single-obligation statements, **preserving any dependency the conjunction carried** — as its own requirement, or, where one half is conditioned on the other, as a **Condition slot on the dependent half** (Row 3 §4.1.1(b) splitting note; e.g. "validate X **and** reject on failure" → "shall validate X" + "when validation fails, shall reject X"). The repair emits ≥2 statements from one input (the repair response schema admits a statement list, not a single statement); each re-enters validation; `chk3d09_decompose_performed` is logged and the produced atomics **inherit the original compound's `cci_refs` by construction** (assigned by the executor after parse — a child does NOT carry, and is NEVER required to carry, its own `cci_refs`; the visibility/access half frequently dedupes at Matching). The repair executor splits — it does **not** re-decide the split, and a partial/malformed response never collapses the whole repair (F106, below). A genuinely **slotless** statement (missing required slot, no decomposition possible — and thus no atomic obligation to retain) still falls to the CHK-3d-05 repair path — its CCIs return to the orphan pool and are re-covered with the atomic-single-obligation instruction. This is distinct from a **compound that fails to decompose**, which is RETAINED rather than dropped (retain-on-failure, F102, below) — a compound carries a real obligation, so it must survive even un-split. The decidable detector is the conjunction + verb-phrase / slot-presence analysis above; the inseparable-single-concept judgement is the one soft edge (logged, not auto-rejected). This is the physical realisation of the F88/F98 hard-atomicity constraint with automate-everything repair (v0.4 carried only the soft "and"-test in guidance; v0.23 left the predicate conjunction soft).

**Decompose-failure logging contract (F100).** `_run_conjoined_decompose` can fail two ways — the IM call raises (exception path) or it returns no parseable child proposals (empty-parse path). **Each decompose invocation that yields no atomic child MUST record exactly one `conjoined_predicate_decompose_failed` warning**, carrying the rejected proposal's `source_domain_id` and `statement_preview`. This is **per-invocation, not per-domain**: N failed decompose calls for one domain produce N distinct warnings — each failed call is a distinct rejected proposal whose CCIs are entering orphan detection, so there is no legitimate deduplication across calls (the v0.24 build scoped its anti-double-emit guard against the whole-pass warning list, silently suppressing every failure after the first per `source_domain_id`; the fix makes the exception and empty-parse paths disjoint via an early return). The two failure paths must be mutually exclusive (one warning per call, never two). **Audit invariant (VER-3d-22):** within each domain's proposal set, `|conjoined_predicate_hard_reject| = |chk3d09_decompose_performed| + |conjoined_predicate_decompose_failed|`. A non-zero residual means a rejected proposal took the decompose path and left no trace — its CCIs entered the orphan pool unexplained, making the pass un-auditable. **Retain-on-failure — Non-Loss takes precedence over atomicity (F102).** The v0.24/v0.25 build **dropped** a `conjoined_predicate_decompose_failed` proposal from `surviving_09`, assuming it would fall to CHK-3d-05 orphan recovery. It does NOT: `new_orphans_09 = eligible_ci − covered_after_09 − existing_orphans`, so when the dropped obligation's CCIs are **coincidentally covered by sibling proposals** (acute in the over-concentrated physical domains — OPEN-DOM-2, where many obligations share few coarse CCIs; D015 had 3 CCIs across 9 proposals), `new_orphans_09` is empty, no repair fires, and the **obligation is silently lost** (R5_Run12: 17 drops at Row 5, 5 at Row 4). Fix: when `_run_conjoined_decompose` yields no atomic child, the original compound is **RETAINED in `surviving_09`**, tagged `chk3d09_decompose_failed_retained`; the `conjoined_predicate_decompose_failed` warning is still recorded (audit), and the compound re-enters validation as a logged atomicity exception. A compound-but-present obligation is strictly preferable to an atomic-but-absent one; the residual non-atomicity is a quality exception, not a lost obligation. **The prior 'CHK-3d-05 carries the recovery' line is withdrawn** — CCI coverage is NOT a sufficient Non-Loss test where CCIs are coarse (the obligation itself must be present, which retain-on-failure guarantees by construction). **`statement_preview` (F100 residual):** both emission sites of `conjoined_predicate_decompose_failed` (the exception path and the empty-parse path) omitted `statement_preview` in the v0.25 build — recoverable only from the paired `conjoined_predicate_hard_reject`; both now carry `proposal.statement[:80]` directly, per the F100 contract. **Every-path sweep (F104):** R5_Run13 still showed one `conjoined_predicate_decompose_failed` with empty `statement_preview` despite the two-site v0.26 fix — the contract is **every emission on every path** carries `statement_preview`; any remaining emission site (including paths outside `_run_conjoined_decompose`) must be swept to comply.

**Decompose executor robustness — split, don't re-decide; inherit; no all-or-nothing (F106).** R4_Run10 retained three trivially-splittable compounds ("retrieve **and** display tasks…") because the decompose mechanism failed, not because the statements were un-splittable. The R4_Run10 `conjoined_predicate_decompose_failed` warnings carried **no `detail` key** → the IM call did not raise → the failure was at parse/schema. Three physical fixes: **(1) Item-level resilient parse.** `_parse_repair_response` must NOT wrap the whole child list in a single `try/except → return None` (one malformed child silently discarding ALL children — the F100/F101 swallow class). Each child is validated **independently**: valid children are kept; a malformed child is logged (`decompose_child_discarded`, carrying the child index and the validation error) and discarded **individually**; the function returns `None`/`[]` **only** when zero valid children remain. A repair yielding ≥1 valid child always returns those children. **(2) Children inherit `cci_refs`; the schema must not require them.** The IM returned the *retrieve* half with empty `cci_refs`, which tripped the repair schema's `cci_refs` `minItems=1` (`cci_refs_not_empty`) and — via the all-or-nothing parse — discarded every child. The repair-response schema (`requirement_repair_response_schema.py`) **drops the `cci_refs` `minItems=1` constraint**; the executor assigns each child the **parent compound's `cci_refs`** after parse (the §4.3 inheritance rule, now enforced in code, not requested from the IM). The secondary `confidence: float` non-Optional risk is likewise removed — `confidence` is Optional/defaulted so a `null` cannot fail the parse. **(3) The executor does not re-decide the split.** The decompose prompt must NOT embed the derivation-time two-step "single unifying obligation?" subsume-or-split test (it is shipped via `_STATEMENT_FORMULATION_GUIDANCE` from the derivation prompt) — by the time the executor runs, CHK-3d-09 has already ruled the statement a hard conjoined-predicate that MUST split, so re-applying the should-I-split test lets the executor collapse the compound back to one statement, or to none. The two-step test is **removed from the decompose prompt**, and a concrete **conjoined-predicate exemplar** is added showing the expected split ("The mobile application shall **retrieve and display** tasks with available status" → "The mobile application shall retrieve tasks" + "The mobile application shall display tasks with available status", both inheriting the parent `cci_refs`). Together (1)+(2) close the live trigger and (3) the independent risk; F102 retain-on-failure remains the net for genuinely-hard residue, which should now be rare.

**CHK-3d-11 — `class_model` structural validity (decidable, HARD; split structural / referential — F105 / Issue 2).** Realises Row 3 §4.1.1(g) / CHK-3d-11. **Structural clauses run in Stage 3 against the AI proposal alone** (`core/class_model_validity.py`); **referential clauses are deferred to Stage 4** (§4.4.3a), because the proposal carries the entity *name* but not its `DD###` `entity_ref` — that id is allocated by the DD service in Stage 4 (on a FirstRun the DD is empty, so no `entity_ref` could exist at proposal time, Issue 2).

*Stage 3 — structural (against the proposal):*
- `entity` (the canonical name) present and non-empty; `tier` matches `row_target` (2→`conceptual`, 3→`logical`, 4→`physical`, 5→`detailed`);
- **≥1 attribute** — a zero-attribute `class_model` is not a model but a bare name (a name belongs in the DD as a `canonical`, not here): **reject** (Issue 6, `detail: no_attributes`). At **Row 2** (`conceptual`) ≥1 attribute MUST carry a **semantic type** (the conceptual profile, §5.4; `detail: row2_no_semantic_type`) — this stops a zero-/typeless-attribute Row 2 model from trivially satisfying CHK-3d-12 and forcing every Row 3 child attribute to `origin=introduced`;
- **at most one** attribute has `key == "PK"` (`detail: multiple_pk`); every `key == "FK"` carries a `target_ref` and every `relationships[].target` is a **well-formed** entity-name reference (non-empty; *format*, not resolution — `detail: malformed_target`);
- attribute `domain`s are well-formed (a parseable enumeration / range / type expression, non-empty where present — `detail: bad_domain`);
- `tier` / `refinement_kind` ∈ {`identity`,`decompose`,`realise_relationship`,`introduce`,`merge`} / attribute `key` ∈ {PK,FK} / `origin` ∈ {`refines`,`realises`,`introduced`} enums valid (`detail: bad_enum`).

*Stage 4 — referential (after §4.4.3a sets `entity_ref` from the resolved DD canonical):* `entity_ref` resolves to a `canonical` `DataDictionaryEntry` (`detail: entity_ref_unresolved` — trivially satisfied since §4.4.3a sets it from the DD); every FK `target_ref` and every `relationships[].target` **resolves** to a known entity, i.e. a canonical with a defining `class_model` (`detail: target_unresolved`).

A `class_model` failing a structural clause is **rejected in Stage 3** (log `{check_id:"CHK-3d-11", requirement_id_placeholder, detail}` in `validation_failures`, `execution_warnings += class_model_invalid`); a referential failure is rejected at §4.4.3a. A rejected Structural's obligation is re-covered via the orphan (CHK-3d-05) / seed (CHK-3d-10) paths. **A valid `class_model`-bearing Structural SKIPS the CHK-3d-09 prose-atomicity checks** — the entity is the unit of atomicity (D4). (A prose-only Structural with no `class_model` — migration residue — still runs CHK-3d-09.) Decidable; no IM.

**CHK-3d-12 — `class_model` concept-coverage refinement (decidable, downward Non-Loss over the model; rows ≥ 3; realises Row 3 §4.1.1(g) / CHK-3d-12 / OQ-105-01; F105).** The model-level analogue of CHK-3d-10 (`core/class_model_coverage.py`), run **per adjacent parent→child row pair** as each child row completes (chain-together, MD-7). For each row-n `class_model` and its `refines_refs` parent row n−1 `class_model`(s) — **drawn from non-retired (surviving) Structural Requirements only**, mirroring the CHK-3d-10 surviving seed set; a parent retired by a FullRerun of the row above is not a coverage obligation (Issue 5):
- assemble `parent_elements` = the parent's model-elements (the entity itself, each attribute, each relationship);
- assemble `child_elements` across all children refining that parent;
- assert every `parent_element` is **covered** by ≥1 `child_element` under a recorded transformation: the parent entity by a child entity whose `refinement_kind` ∈ {`identity`,`decompose`,`merge`} traces to it; a parent attribute by a child attribute with `origin ∈ {refines, realises}` (or by an FK / relationship realising it); a parent relationship by a child `realise_relationship` FK or a carried `relationships[]` entry.

**Parent→child only.** A child element with `refinement_kind == "introduce"` (a new entity with no conceptual ancestor — a junction) or attribute `origin == "introduced"` (a surrogate key, an FK column) is **exempt from requiring a parent** — the `class_model` analogue of a Path-N row-native Requirement with empty `refines_refs` (F86). The check never runs child→parent. A `parent_element` covered by no child is **model-element extinction** — the structural analogue of CHK-3d-10 seed extinction: re-prompt the row's Structural derivation to cover the uncovered element (conditional IM repair via the Path-N/derivation prompt scoped to that entity; `chk3d12_repair_performed`); recompute. Persistent → record `mechanism_data.model_coverage_gaps = [{parent_ref, element, kind, reason}]`; `execution_status` escalates; `execution_warnings += chk3d12_model_element_extinct` (HARD, Practitioner attention) / `chk3d12_repair_failed`. Never a silent drop. Record `mechanism_data.model_coverage = {parent_elements, covered, ratio}`.

**ADVC-3d-01 — Requirement-per-Domain soft bounds.** Per source Domain, count surviving Requirements; `m = len(domain.cell_content_item_refs)`. Zero Requirements → manifests as orphans (CHK-3d-05). `> m` Requirements → log `requirement_count_advisory {domain_id, requirement_count, cci_count}` (PLB-3d-06). Informational; production proceeds.

**ADVC-3d-03 — Concern-atomicity advisory (soft diagnostic; realises Row 3 §4.1.1 concern-atomicity).** For each surviving Requirement, compute the spread of its `cci_refs` over CCI classification types and Zachman columns. A Requirement whose `cci_refs` span **≥2 distinct classification types across ≥2 distinct columns** is flagged `concern_atomicity_advisory {requirement_id_placeholder, cci_refs, classification_types, columns}` in `mechanism_data.concern_atomicity_flags`. This is a **decidable diagnostic** (classification_type and column are CCI fields), not an IM act. **Severity: soft** — informational; production proceeds; it does NOT reject or auto-split. Rationale for soft (not hard): a multi-column / multi-type CCI span is a reliable *signal* of possible concern over-bundling (the R025 case — How/Process + How/Rule + What/Attribute + Why/Constraint in one statement) but not proof, since a legitimately-single obligation can draw on facets from two columns; whether to split is the IM judgement made at authoring under the §5.4 concern-atomicity guidance. The flag instruments the requirement set so over-bundling is measurable across runs — the data source for judging whether the §5.4 guidance is holding — exactly as `subject_vocabulary_flags` (CHK-3d-08) instruments subject discipline. A persistently high `concern_atomicity_flags` count after the guidance lands is the evidence that would justify promoting concern-atomicity from guidance to a harder mechanism.

**ADVC-3d-02 — Interrogative slot completeness (advisory; realises Row 3 §4.1.1(f) / F87/F88).** For each surviving Requirement, check whether the slots its `requirement_type` requires are *filled* (Functional: Subject/Action/Object present, Condition where the source implies a trigger; Constraint: Subject/Constraint-Rule, Criteria where Measurement-verified; Structural: entity + composition/attribute/relationship assertion). This is distinct from CHK-3d-09 (which HARD-rejects compound/missing-required-slot *atomicity* violations): ADVC-3d-02 is a **soft generative-completeness advisory** — it flags a requirement whose type-required slots are thin or whose Object was not interrogated to structure where the source implied it, logging `interrogative_completeness_advisory {requirement_id_placeholder, type, thin_slots}` for Practitioner review (PLB-3d-07). Rationale for soft (not hard): interrogative completeness is a *generative guidance* property (it makes the AI surface more, validated in the F87 sandbox) — its absence is an under-elaboration to review, not a structural defect to reject. A missing *required* slot is already hard-caught by CHK-3d-09; ADVC-3d-02 catches the softer "could have been interrogated further" case. Informational; production proceeds. (Why advisory and not hard: an over-eager hard completeness gate would reject legitimately-terminal requirements — a Row 1 enterprise constraint need not decompose to an Object the way a Functional behaviour does. The row-and-type-awareness is in the guidance, §5.4; the check only flags thinness for review.)

### 4.4 Stage 4 — Entity Production and Ledger Commit (DM)

Realises Row 3 §4 Stage 4.

**Connection lifecycle (conformance — Common Implementation Reference §1).** The Stage 2/3 IM phase routinely exceeds the Neon serverless idle threshold, so the connection held before it is dead by Stage 4. Before Stage 4 acquires its write connection, the mechanism applies the reference realisation: `session.invalidate()` (release the dead connection WITHOUT the ROLLBACK that `session.close()` would crash on), then `refresh_engine_pool()` (= `engine.dispose()` + `_wait_for_db()`, purging the pool and verifying the endpoint is awake), then a fresh `get_session()`. Stage 1 reads into memory and releases its connection rather than holding it across the IM phase. The realisation is governed by Common Implementation Reference §1 and is NOT restated here; this spec conforms by citation. (Validated PMT rows 1–5.)

**4.4.1 requirement_id allocation.** `query_max_requirement_id(project_id)` including retired rows. Allocate forward from next `R###`. §5.3.

**4.4.2 domain_refs DM-derivation (MD-2).** Per surviving proposal: `domain_refs = sorted({d.domain_id for d in active_domains if set(proposal.cci_refs) & set(d.cell_content_item_refs)})`. Assert `len(domain_refs) >= 1` (guaranteed under MD-1 post-CHK-3d-03 for a CCI-bearing proposal) and every referenced Domain `row_target == str(current_row)`. **Path-R fallback (MD-2 §3.2):** a pure-seed-elaboration proposal may carry empty `cci_refs`, so the intersection is empty — in that case `domain_refs` is taken from the proposal's `source_domain_id` (the seed's Domain lineage, §4.2), NOT failed. Empty result therefore branches: empty `cci_refs` → set `domain_refs = [source_domain_id]`; non-empty `cci_refs` with empty intersection → fail closed: reject proposal, log `{check_id:"MD-2", detail:"domain_refs derivation empty"}` in `validation_failures`; re-run CHK-3d-05 on the reduced set.

**4.4.3 Requirement construction.** Build each Requirement: allocated `requirement_id`; `statement`; `requirement_type`; `row_target=str(current_row)`; `confidence`; `cci_refs`; derived `domain_refs`; `refines_refs` (F82 — set **at derivation** for a Path-R child to the seed(s) it was elaborated from, per §4.2; **empty** for a Path-N row-native proposal, to be populated later by the Requirement Matching service or left as an upward gap, §5.5 / F93); optional `rationale`/`fit_criteria`/`verification_method`/`priority` where present; `answer_refs=[]`. A **Structural** Requirement additionally carries its IM-proposed **`class_model`**, validated (CHK-3d-11) and committed in §4.4.3c with its prose `statement` rendered as a projection (F105). A **behavioural** Requirement's name terms are registered with the Data Dictionary and its candidate `object_refs` materialised in §4.4.3a (ledger v2.17: `class_model` and `object_refs` are now fields on the Requirement; relationships and value-sets are no longer DD content, F107).

**4.4.3a DD name-registration + `object_refs` materialisation (realises Row 3 v0.18 §5.5; F90 / F107).** For each surviving Requirement, extract its controlled-vocabulary **names** and present them to the Data Dictionary service (Row 4 Data Dictionary Service v0.2) for **name** resolution only; then (behavioural Requirements) materialise its `object_refs`. Post-F107 the DD is a naming / synonym index — it holds no model content, so only names are presented; relationships are `class_model.relationships` (§4.4.3c) and named values are `object_refs` (step 4):

1. **Entity extraction from the Object (IM).** Identify the **domain entity/entities the Object denotes** — the controlled-vocabulary noun(s) the obligation concerns — and present *those*, not the verbatim Object slot. At lower rows the Object is often already entity-grade ("task", "child earnings") and reduction is near-identity; at Row 1 the Object is typically clausal ("a mechanism enabling household members to select and claim available work opportunities") and MUST be reduced to its entity head(s) (here: `work opportunity`, `household member`). A statement may yield zero, one, or several entity terms. This is an **interpretive act** (which noun is the domain entity vs an incidental modifier / verb nominalisation like "a mechanism enabling…"), so it is **model-assisted, not a verbatim slot copy**: the CHK-3d-09 slot parse bounds *where* to look (the Object slot), but reducing that slot to its entity head(s) is IM. The presented term MUST be an entity-grade noun phrase; presenting the Object clause or the full statement is prohibited (it defeats the DD — each clause is unique, resolves to nothing shared, and yields one canonical entry per statement). Structural → the **entity** asserted, plus any **relationship** `(entity_a, relation, entity_b)` the statement asserts. **Constraint → the domain entit(ies) the Constraint-Rule governs** (F99 — see the Constraint sub-step below), NOT the Subject. Any **value referenced by name** in any type (e.g. `Task.status.available`) → the attribute value.

   **Reduce STATE / lifecycle qualifiers to the bare entity (do NOT coin a qualified entity).** A phrase naming the entity *in a state* — "available tasks", "completed tasks", "claimed task" — reduces to the **bare entity** (`task`) with the state carried as an **attribute** (status = available / completed / claimed), recorded on the entry's `attributes` (DD §4.4 value-record), NOT minted as a separate canonical ("task opportunity", "completed achievement"). Likewise do not substitute a near-synonym or role/abstraction-qualified coinage for a source entity ("economic activity", "work unit", "household economy" for `task`/`child`). The rule: the presented term is the **bare source noun**; lifecycle states and role qualifiers are attributes *of* that entity, never new entities. This is what makes the available / completed / claimed states of one entity resolve to ONE canonical rather than three — and what keeps Row 1 and Row 2 sharing the same `task` canonical for cross-row matching.

   **Constraint entity extraction — from the Constraint-Rule, not the Subject (F99).** A Constraint has **no Object slot** (`Subject shall comply-with Constraint-Rule [under Condition] [to Criteria]`), so there is no Object to reduce; extracting the Subject (the v0.23 behaviour) yields a thin generic noun ("system", "enterprise") or nothing. The entity term(s) are the **domain concept(s) the Constraint-Rule governs** — the noun(s) the rule bounds — taken from the **rule predicate** (post-`shall`), NOT the Subject. Three aligned build changes (SW-agent-confirmed against R5_Run9): (i) `_extract_constraint_slots` returns the **Constraint-Rule** (predicate after `shall`) in addition to the Subject; (ii) `_raw_slot_description` passes the **rule** text — not the Subject — as the `raw_slot` hint for the Constraint case; (iii) the Constraint slot-guide in `build_dd_extraction_prompt` is redirected from "return the subject entity" to "**return the named domain concept(s) the Constraint-Rule governs**", with rule-content examples ("The system shall enforce retention of task-completion records" → `task completion record`; "shall comply with ISO-27001" → `ISO-27001`). The rule's threshold / bound / value is recorded as an **attribute/value on the governed entity** (DD §4.4 value-record), never as a clause-named canonical. **No `stmt[:60]` fallback (F99):** the v0.23 `_build_dd_ops_from_terms` line that fed `stmt[:60]` (a 60-character statement fragment) to the DD as `canonical_term` when extraction returned empty is **removed**; a Constraint that governs no extractable domain entity contributes **no DD term** — it is recorded in `dd_binding.dd_zero_term`, never a fragment (Non-Loss is preserved by the produced Requirement; the DD simply gains no entry). This is the source path for all 30 malformed R5_Run9 Constraint entries — a thin/empty subject extraction, then the `stmt[:60]` fragment presented to the DD service, which stored it as a canonical with the "attribute record:" description.
   **Batched, ceiling-bounded extraction with loud truncation (F101).** The entity-extraction IM call (`_extract_entity_terms_ai`) processes the whole row's surviving proposals. It MUST be **batched and output-ceiling-bounded**, exactly as Stage 2 Path-R was made in v0.19: a batch is sized so its *expected output* (≈ proposals × per-proposal term JSON) cannot reach the model `max_tokens`, fingerprint stages `stage4_dd_entity_extraction_batch<N>`. A single unbatched call does **not** scale — when CHK-3d-09 decomposition enlarges the row (N compounds → 2N+ atomic children) the output JSON overflows the ceiling, the response is truncated mid-serialisation, and the parse fails. **Truncation MUST be a loud hard failure, never a silent all-empty (F101).** `_parse_extraction_response` may **not** return `[]` on a `json.loads` failure or a short/index-mismatched array without recording `dd_extraction_batch_truncated`; a batch detected as truncated (output at the ceiling, or unparseable, or returning fewer indices than proposals sent) is **re-split and retried**, not swallowed. The v0.24 build hit this: one whole-row call returned `output_tokens` exactly at the 2048 ceiling, `json.loads` threw, and the silent `by_idx.get(i, []) → []` fallback wiped the entire row's DD to `dd_zero_term` while emitting only a benign-looking `dd_entity_extraction_all_empty` — so `dd_entity_extraction_all_empty` is legitimate ONLY when a row genuinely yields no entity-grade terms, never as a truncation artifact (the two are now distinguishable: truncation raises `dd_extraction_batch_truncated`). **Slot-parse guard (F101).** The `extract_slot_terms` / `_raw_slot_description` loop that builds the batch payload runs **outside** the Stage 4 try/except in the v0.24 build; a slot-parse exception on any one proposal therefore propagates uncaught and crashes the whole stage (the null-fingerprint failure mode). The loop MUST be guarded so a slot-parse failure on one proposal degrades **that proposal** to `dd_zero_term` (`slot_parse_failed`) and the stage continues. **Completeness invariant (VER-3d-23), requirement-level:** every surviving Requirement is in exactly one bucket — it contributes ≥1 presented term, or it is recorded in `dd_zero_term`: `|reqs contributing ≥1 presented term| + |dd_zero_term| == row requirement count`. Separately, presented terms partition: `terms_presented == resolved + |dd_unresolved|` (`dd_unresolved` is a sub-state of "contributed a term", not a third bucket; and `terms_presented` is a term count — one Requirement may present several — never equated to the Requirement count). AND no batch recorded `dd_extraction_batch_truncated` — every surviving Requirement is accounted for, and the account is not the product of a swallowed truncation.

2. **Resolve-and-record (service call).** **Entity-grade gate first (VER-3d-19, REJECT — F99):** at the point each term is appended as an op (`_build_dd_ops_from_terms`), a clause-grade candidate — one that contains a finite verb phrase, ends with sentence punctuation, or exceeds the entity-grade length bound (heuristically > ~5 words) — is **skipped** and recorded in `dd_binding.dd_zero_term` (warning `ver_3d_19_term_rejected`), NOT presented to the service. This relocates VER-3d-19 from its v0.23 post-commit warn-only position in `__init__.py` (where it logged `ver_3d_19_entity_grade_violations` *after* the bad entry was already committed) to an enforcing **pre-presentation reject**; the standalone `_check_ver19` predicate is reused unchanged (routing change, not new logic). For each term that passes the gate, call the DD service `resolve_and_record(term, context=statement, provenance_ref=requirement_id)` (DD spec §4.1–§4.4). The service performs its own three-way judgement (canonical-match → synonym; no-match → new canonical entry; ambiguous → flagged) and returns the canonical `DataDictionaryEntry`. **The relationship-record (DD §4.3) and value-record (DD §4.4) operations are REMOVED (F107):** a relationship between two entities is a `class_model.relationships` entry on the asserting Structural Requirement (committed in §4.4.3c), and a named value is an `object_refs` entry (materialised in step 4) — neither is presented to the DD, which holds only names + synonyms. **The name-resolution calls are what populate the DD** — Pass 3d is the DD's primary caller and the DD accretes names incrementally across the run and across rows.
3. **Bind / flag (names).** Resolved → the Requirement's entity name is bound (the binding lives in the DD via the entry's `provenance_ref` and synonym register; the *name* binding is not written onto the Requirement element). **Unresolved / flagged** → record `dd_unresolved {requirement_id, term, reason}` in `mechanism_data.dd_binding` (§4.4.3b). The Requirement is still produced (Non-Loss); the unresolved name is the signal that the Matching service must treat this Requirement as not-yet-matchable (Matching §4.1 / VER-rm-07).
   **(Structural — set `entity_ref`, Issue 2.)** When the entity name of a Structural Requirement resolves (step 2), write the resolved canonical's `dd_id` to its `class_model.entity_ref`. The **Stage-4 referential half of CHK-3d-11** then runs: `entity_ref` resolves (trivially — just set from the DD), and every FK `target_ref` / `relationships[].target` (entity-name references) resolves to a canonical with a defining `class_model`; an unresolved target → reject (`{check_id:"CHK-3d-11", detail:"target_unresolved"}`), obligation re-covered via orphan/seed. `entity_ref` is set here, before the §4.4.3c commit, so the committed `class_model` satisfies the ledger's `required` `entity_ref`.
4. **`object_refs` materialisation — behavioural Requirements only (DM; F107).** `object_refs_resolver.py` is a **thin RD-side orchestrator** (Issue 3): it does NOT re-implement DD lookup. For each candidate path it (i) calls **`dd_service.resolve_object_ref(path)`** — the DD resolves the leading `<Entity>` segment to a `canonical` (directly or via a `synonym`'s `resolves_to`) and **hands back the canonical + the unresolved `.attr`/`.value` tail; the DD never touches `class_model`** (it holds no model content) — then (ii) resolves the returned tail itself against the `class_model`(s) whose `entity_ref` is that canonical, querying the Structural Requirements (RD's own table) that define the entity (typically this row and the rows above). The name half is the DD's job; the `class_model` value half is RD's — matching the existing "RD names, DD resolves the name" boundary. A **fully-resolving** path is committed to `requirement.object_refs`. A path whose leading entity does not resolve, or whose `.<value>` is absent from every defining `class_model` domain, is a **dangling binding** — recorded in `object_refs_binding.dangling [{requirement_id, ref, reason}]` (`execution_warnings += object_refs_dangling`) for the Quality pass (F107-T1), and **NOT** a derivation-time reject: the defining Structural may be derived later (the value resolves when its row completes), so a reject here would false-fail a legitimate forward reference. `object_refs` is materialised AFTER §4.4.3c so the row's `class_model`s exist to resolve against.
5. **Idempotency.** Re-presenting the same name resolves against existing entries and does not duplicate them (DD §6). On IdempotentRerun of Pass 3d, no DD calls are made and `object_refs` is unchanged (no new requirements).

**Mode.** The entity extraction (step 1) is an **IM act** — a model-assisted reduction of the Object to its domain entity/entities — and its fingerprint IS recorded in the Pass 3d AnalysisPass `ai_model_fingerprints` (stage label `stage4_dd_entity_extraction`), alongside the Stage 2 derivation fingerprints. The DD service's own resolution judgement (same/new/ambiguous) is a separate IM act, fingerprinted within the DD service, not here. The derivation AI does not author DD entries — it presents candidate entity terms; the DD service decides resolution. (This corrects the v0.7 framing of extraction as a cheap DM slot-reuse, which produced verbatim clausal terms.)

**Ordering.** §4.4.3a runs inside Stage 4, after §4.4.3 construction and before the §4.4.6 transaction commit, so the DD is populated within Pass 3d. The Requirement Matching service (Phase 3e) subsequently reads the populated DD. Runner-level: Matching MUST NOT run for a row before that row's Pass 3d (with §4.4.3a) has committed; a Matching invocation finding an empty DD is a precondition failure (defer/halt), not a free-text fallback.

**4.4.3b dd_binding / class_model / object_refs audit.** Stage 4 records three blocks in `mechanism_data` (siblings of `subject_vocabulary_flags`, `validation_failures`). **Post-F107 `dd_binding` drops `relationships_recorded` and `values_recorded`** (relationships → `class_model`; values → `object_refs`):

```jsonc
"dd_binding": {
  "terms_presented": 18, "resolved": 16, "new_canonical": 7,
  "synonyms_recorded": 9,
  "dd_zero_term": [],
  "dd_unresolved": [ { "requirement_id": "R019", "term": "pocket money allocation", "reason": "flagged_ambiguous" } ]
},
"class_model_binding": {                                  // F105 — §4.4.3c
  "structural_count": 6, "with_class_model": 6,           // Structural reqs and how many carry a class_model
  "by_tier": { "conceptual": 0, "logical": 4, "physical": 2, "detailed": 0 },
  "by_refinement_kind": { "identity": 1, "decompose": 1, "realise_relationship": 2, "introduce": 2, "merge": 0 },
  "invalid": []                                           // [{requirement_id, detail}] — CHK-3d-11 rejects
},
"object_refs_binding": {                                  // F107 — §4.4.3a step 4
  "formed": 11,                                           // behavioural Requirements with ≥1 resolved object_ref
  "dangling": [ { "requirement_id": "R040", "ref": "Task.status.archived", "reason": "value_absent_from_class_model_domain" } ]
}
```

**4.4.3c `class_model` population and prose projection (DM; realises Row 3 §4.1.1(g) / §5.5; F105).** For each surviving **Structural** Requirement carrying an IM-proposed `class_model` (Stage 2 output, §5.4 shared block):

1. **Validate (CHK-3d-11).** Structural validity is checked in Stage 3; a `class_model` that failed has already removed its Requirement from the surviving set. (Belt-and-braces: a survivor with a malformed `class_model` reaching Stage 4 is a defect → reject, `class_model_invalid`.)
2. **Profile conformance.** Spot-check that the populated fields match the row's profile (`requirement_row_guidance` enforces this at IM time; this is a decidable backstop): a Row-2/3 `class_model` MUST NOT carry physical types / `null` / PK-FK / storage (those are R4–R5); a Row-4 `class_model` MAY. A profile violation is logged (`class_model_profile_advisory`, soft — the model is still committed; the row guidance is the corrective lever, not a reject) so over/under-population is measurable across runs.
3. **Commit.** Write the `class_model` JSONB onto the Requirement (§5.1). `entity_ref` was set in §4.4.3a (the resolved DD canonical id — Issue 2; the committed form now satisfies the ledger `required` `entity_ref`); `refinement_kind` and attribute `origin` are persisted as the IM recorded them; FK `target_ref`/`relationships[].target` names were resolved by the §4.4.3a Stage-4 referential check.
4. **Prose projection.** If the proposal did not supply a `statement`, `class_model_projection.py` renders a deterministic one from the payload — e.g. `"<Entity> comprises <attr1> (<type/domain>), <attr2> (<type/domain>), … ; keys: <PK> ; relationships: <rel> <target> (<cardinality>)"` — so the prose `statement` is a faithful projection and existing `statement` consumers (CHK-3d-08 subject check, VER-3d-03, search/display) keep working and cannot drift from the model. A supplied `statement` is checked against the projection for gross divergence (`class_model_statement_divergence`, soft).

Concept-coverage (CHK-3d-12) has already run in Stage 3 against this row's committed parents. The `class_model_binding` audit (§4.4.3b) records the produced models by tier and `refinement_kind`.

**4.4.4 FullRerun retirement (resolves Row 3 OQ-3d-04).** On FullRerun: set `retired_at=now()` on all active Requirements for the row before inserting the new set (soft-retire, not delete — preserves referential integrity for any downstream refs, consistent with the sibling OQ-3c-03 soft-delete). `query_max_requirement_id` includes retired; new ids continue forward. Build `retirement_mapping` (one per retired Requirement; `inferred_successor_requirement_id` populated if statement similarity ≥ 0.50 against a new Requirement).

**4.4.5 downstream_rerun_required.** If Phase 5/6/8 AnalysisPasses exist for this row and this run committed a non-trivial change (FullRerun, or Incremental that added/retired): `mechanism_data.downstream_rerun_required=true`. Orchestrator surfaces advisory; downstream NOT auto-triggered. **On IdempotentRerun: `false` unconditionally (SC-3)** — no re-check; an idempotent pass changed nothing, so it raises no downstream obligation. (A downstream pass added or removed since the prior producing run is the orchestrator's concern — it runs because it has not yet run, not because Pass 3d flags it — so a stale `false` here is correct by design, not an omission.)

**4.4.6 Transaction.** Single transaction: insert (and on FullRerun retire) Requirements; replace `RequirementRegister.member_ids` with `query_all_active_requirement_ids(project_id)` (project-wide, all rows, active); write the AnalysisPass. On rollback: `execution_status="Failed"`; pre-run state preserved.

**4.4.7 execution_status.** `Success` unless: persistent orphan (CHK-3d-05) → `PartialSuccess`; `incremental_fallback_to_fullrerun` logged → `PartialSuccess`; an earlier Failed condition fired → `Failed`; IdempotentRerun → `Success` (distinguished by `run_scenario="IdempotentRerun"`, `idempotent=true` — there is no separate `Skipped` status). Informational advisories alone (including `subject_vocabulary_mismatch`) do not change status.

---

## 5. Schema and Validation

### 5.1 SQLAlchemy / Pydantic models and Database DDL

**`requirement` table:**

| Column | Type | Constraint |
|---|---|---|
| `requirement_id` | VARCHAR(8) | PK component; `^R\d{3}$` |
| `project_id` | VARCHAR/UUID | FK → project; PK component |
| `statement` | TEXT | NOT NULL; CHECK length > 0 |
| `requirement_type` | VARCHAR(16) | NOT NULL; CHECK IN ('Functional','Constraint','Structural') |
| `row_target` | VARCHAR(1) | NOT NULL; CHECK IN ('1','2','3','4','5','6') |
| `rationale` | TEXT | NULL |
| `cci_refs` | JSONB | NOT NULL DEFAULT '[]'; CONDITIONAL — see table CHECK below. Non-empty for Path-N and all Row 1 Requirements; MAY be empty for a Path-R refinement child carrying `refines_refs` |
| `domain_refs` | JSONB | NOT NULL; CHECK jsonb_array_length >= 1 |
| `refines_refs` | JSONB | NOT NULL DEFAULT '[]'; «refine» links to row n-1 Requirements (F82). **Path R:** populated by Pass 3d AT DERIVATION (the seed the child was elaborated from). **Path N:** populated by the Matching service (parent match) or left empty → upward gap (F86). Empty at Row 1. Table CHECK: `jsonb_array_length(cci_refs) >= 1 OR jsonb_array_length(refines_refs) >= 1`  **Cardinality:** «refine» is many-to-many, lower-bounded at the parent (every row n−1 seed ≥ 1 child — CHK-3d-10, no extinction) and unbounded at the child (0..* parents: 0 = upward gap/F86, 1 = simple refinement, many = convergence); not 1→1, not a tree. |
| `fit_criteria` | TEXT | NULL; CHECK (fit_criteria IS NULL OR length(fit_criteria) > 0) |
| `verification_method` | VARCHAR(16) | NULL; CHECK IN ('Test','Analysis','Inspection','Demonstration','Measurement') |
| `priority` | VARCHAR(8) | NULL; CHECK IN ('High','Medium','Low') |
| `answer_refs` | JSONB | NOT NULL DEFAULT '[]' |
| `class_model` | JSONB | NULL; the structured What/Data model of one entity (ledger v2.17 `ClassModel`, F105). **CHECK (`class_model` IS NULL OR `requirement_type`='Structural')** — present only on Structural. Shape per §5.2 `ClassModel`. Validated by CHK-3d-11 |
| `object_refs` | JSONB | NOT NULL DEFAULT '[]'; dotted-path strings binding a behavioural Requirement to `class_model` value(s) (F107). **CHECK (`requirement_type`<>'Structural' OR jsonb_array_length(`object_refs`)=0)** — empty on Structural (a Structural *is* the model). Materialised in §4.4.3a step 4 |
| `confidence` | DOUBLE PRECISION | NOT NULL; CHECK 0.0 <= confidence <= 1.0 |
| `retired_at` | TIMESTAMPTZ | NULL (soft-delete for FullRerun) |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() |

`cci_refs`/`domain_refs`/`answer_refs` are JSONB arrays on the row (same JSONB-array-on-row convention as the sibling `cell_content_item_refs`; no join table). `retired_at` mirrors the `domain` table.

**`requirement_register`:** one seeded row per project (migration seeds it): `register_id` PK, `project_id`, `register_type='Requirement'`, `member_ids` JSONB, `completeness_rule` TEXT, `confidence` DOUBLE PRECISION.

**Ledger normative rules (transcribed v2.17, all enforced):** `requirement_id` unique and `^R\d{3}$`; `statement` non-empty; **at least one of `cci_refs` / `refines_refs` non-empty (not-both-empty; `cci_refs` may be empty for a Path-R child)**; `domain_refs` ≥1 referencing existing Domain; if `fit_criteria` present, non-empty; if `refines_refs` present, each entry references an existing Requirement at row_target−1 (MAY be empty at any row, F82/F86); `requirement_type` in {Functional, Constraint, Structural}; a Measurement-verified Constraint SHOULD carry `fit_criteria`; `row_target` in "1".."6"; `row_target` equals row of every referenced CCI and Domain; `confidence` 0.0..1.0. Exactly one RequirementRegister; `member_ids` contains all `requirement_id`. **`class_model` (v2.17, F105):** present ONLY when `requirement_type='Structural'`; when present, `entity` / `entity_ref` / `tier` present, `entity_ref` resolves to a `canonical` `DataDictionaryEntry`, `tier` matches `row_target` (2–5), ≤1 attribute `key='PK'`, every FK `target_ref` and `relationships[].target` resolves (CHK-3d-11). **`object_refs` (v2.17, F107):** present ONLY on behavioural Requirements; each entry's leading `<Entity>` resolves to a `canonical` DataDictionaryEntry (directly or via synonym); trailing `.attr`/`.value` resolution into a `class_model` domain is a Quality-pass obligation (a dangling value is a finding, not a schema error).

### 5.2 AI response schemas (Pydantic)

**`requirement_derivation_response_schema.py` — primary (FirstRun / FullRerun):**

```
Response root: List[RequirementProposal]
RequirementProposal:
  statement:            Optional[str]       = None                # Issue 1: present UNLESS a class_model is (then projected, §4.4.3c)
  requirement_type:     Literal["Functional","Constraint","Structural"]
  cci_refs:             List[str]           (minItems=1)
  rationale:            Optional[str]
  fit_criteria:         Optional[str]
  verification_method:  Optional[Literal["Test","Analysis","Inspection","Demonstration","Measurement"]]
  priority:             Optional[Literal["High","Medium","Low"]]
  confidence:           float               (0.0..1.0)
  class_model:          Optional[ClassModel]                     # F105 — Structural proposals ONLY
  object_refs:          Optional[List[str]]                      # F107 — behavioural proposals ONLY (candidate dotted paths)

ClassModel:             # AI-facing PROPOSAL form (schemas/class_model_schema.py); the ledger v2.17 committed form requires entity_ref
  entity_ref:           Optional[str]       = None                # Issue 2: NOT proposed by the AI; §4.4.3a sets it from the resolved DD canonical (^DD\d{3}$) before §4.4.3c commit
  entity:               str                 (minLength=1)         # the canonical NAME — what the AI authors; the DD resolves name→entity_ref
  tier:                 Literal["conceptual","logical","physical","detailed"]
  refinement_kind:      Optional[Literal["identity","decompose","realise_relationship","introduce","merge"]]
  attributes:           List[Attribute]     # each: attr_name(req), attr_ref?, type?, domain?, key?∈{PK,FK},
                                            #       null?, unique?, default?, aggregatable?, derived?, composite?,
                                            #       origin?∈{refines,realises,introduced}
  keys:                 List[dict]          # {kind, attrs, target_ref}
  relationships:        List[dict]          # {rel_ref, kind, target, via, cardinality}
```
**Cross-field rules (Pydantic validators, all three proposal classes):** **(Issue 1)** `@model_validator(mode='after')` raises unless `class_model is not None or (statement and statement.strip())` — a proposal MUST carry a prose `statement` OR a `class_model` to project from (decompose/orphan-repair children always carry a `statement`, so the repair class is unaffected in practice). `class_model` present ⟺ `requirement_type=="Structural"`; `object_refs` present ⟹ `requirement_type` ∈ {Functional, Constraint}; a Structural proposal SHOULD carry a `class_model` at rows 2–5 (prose-only Structural logged un-promoted, not rejected — migration residue). **(Issue 2)** the AI-facing `ClassModel` does NOT require `entity_ref` — the AI authors the entity **name** (`entity`); §4.4.3a resolves the name to a DD canonical and sets `entity_ref` before the §4.4.3c commit (the ledger committed form then has it). The AI is **not** given the DD's name→id map and never proposes a `DD###` id — consistent with not proposing `domain_refs`/`refines_refs`, and necessary because a FirstRun DD is empty. `keys[].target_ref` / `relationships[].target` are likewise entity **names** at proposal time (format-checked Stage 3, resolved Stage 4). The candidate `object_refs` the AI returns are **resolved and materialised** in §4.4.3a step 4.
The AI does NOT return `requirement_id`, `row_target`, `domain_refs`, `refines_refs`, or `answer_refs` (Stage 4 / deferred / service-populated). `refines_refs` in particular is established by the separate Requirement Matching service (F85/F93), never proposed by the derivation AI. The AI likewise does **not** propose Data Dictionary bindings: Object-slot/entity/value resolution is the §4.4.3a service call, not an AI output (the AI formulates the statement; the DD service resolves its terms). Enum enforced at parse (MD-5).

**`requirement_incremental_response_schema.py` — IncrementalRerun:** **IMPORTANT — DISTINCT CLASS** `IncrementalRequirementProposal`. Same field shape; do NOT alias the primary class. Covers only `new_domain_ccis`; refs outside the new-CCI set logged `incremental_ref_outside_new_set`.

**`requirement_repair_response_schema.py` — repair:** **IMPORTANT — DISTINCT CLASS** `RepairRequirementProposal`. Same field shape, with two F106 relaxations: **`cci_refs` drops `minItems=1`** (a CHK-3d-09 decompose child inherits the parent compound's `cci_refs` and need not carry its own — see §4.3 F106; an empty value must not fail the parse), and **`confidence` is Optional/defaulted** (a `null` must not fail the parse). The `cci_refs` coverage the CHK-3d-05 **orphan-repair** path needs is enforced by that path's **post-merge orphan re-check** (a repair proposal that covers no orphan simply leaves the orphan persistent — recorded), NOT by a schema `minItems`. Every orphan-repair proposal still covers ≥1 orphaned ci_id by construction of its prompt; decompose children are assigned the parent's `cci_refs` by the executor. The three classes handle different operations and MUST be separate (same discipline as the sibling §5.2 distinct-schema warning).

### 5.3 Identifier conventions

- Requirement `R###` — global per-project sequence, zero-padded 3 digits, allocated Stage 4.4.1, never reused (includes retired). **Scale ceiling (resolves Row 3 OQ-3d-05):** 999 ids per project including retired. If a project exceeds 800 allocated ids, raise a tracker finding for a 4-digit format (R####). Same caveat as `domain_id`.
- RequirementRegister: one per project; `register_id` seeded by migration.
- AnalysisPass: `P###` via the common writer utility.

### 5.4 REQUIREMENT_ROW_GUIDANCE — prompt constants

Realises Row 3 §4.1.1. **DISTINCT from the domain ROW_GUIDANCE** (decision B): that governs domain naming/grouping; this governs requirement-statement formulation. Held in `prompts/requirement_row_guidance.py`, injected by `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` into the derivation, incremental, and repair prompts. Principle-based, not pattern-based.

**Rows 1–5 are fully authored. Rows 1 and 2 are validated (Row 1: PMT/NQPS Run; Row 2: PMT/NQPS Row 2 Run 1). Rows 3–5 are CANDIDATE guidance, authored ahead of test (NOT yet validated) — they must be confirmed by run evidence before being treated as closed. Row 6 is a short-phrase stub.** Rows 1–2 followed the validate-then-author cadence (the same staged approach as the domain ROW_GUIDANCE); Rows 3–5 were authored together to accelerate the remaining rows on the proven pattern.

**Interrogative completeness — shared across all rows (§4.1.1(f), F87/F88).** Every per-row block instructs the AI to formulate statements by **filling the slots the requirement's type requires**, interrogating the source content for each — not by paraphrasing CCIs. The slot questions, per type (the row block supplies the row-appropriate vocabulary for each):
- **Functional** — *When?* (Condition, if the source implies a trigger) · *Who/what acts?* (Subject, row-appropriate) · *Does what?* (Action) · *To what?* (Object).
- **Constraint** — *What bound?* (Constraint Rule) · *On whom/what?* (Subject) · *When applies?* (Condition?) · *Measured how?* (Criteria — required if Measurement-verified).
- **Structural** — *What is the entity made of?* (composition / attributes / relationships). Reached by interrogating a behavioural Object until the answer is structure rather than further behaviour (the Object-recursion), which surfaces Structural requirements the source only implied.
This makes the row's requirement set generatively complete against its inputs. A statement whose type-required slots are thin is flagged by ADVC-3d-02 (advisory); a *missing required* slot is hard-caught by CHK-3d-09.

**Path-R interrogative elaboration of seeds — rows ≥ 2 (F87; the corrected cross-row half).** When elaborating a row n−1 seed (Path R), apply the SAME slot interrogatives, but to the **seed obligation** rather than to a row-n CCI: ask, of the seed, the row-n interrogatives its intent implies — *What does realising this require at this row? Who acts / who receives? How is it provided? When / Where / Why?* — and emit the row-n children those answers produce, each `refines_refs=[seed]`. This is F87's downward elaboration (the R004 method: interrogating "provide visibility into inventory" yields inventory-holder, item-source, presenter, scope as distinct children that decomposition misses). It runs at Pass 3d on the seed directly (NOT via Pass 3a signals — so F83 is not reopened). **A seed child may be a system requirement OR a process/organisational requirement:** some obligations are realised outside the system boundary (a Row 2 "the business pays out earned money" elaborates to a Row 3 logical disbursement *process*, not "the system shall") — do NOT force a system subject, or off-system seeds are falsely extinguished. Every seed MUST yield a child or a link (CHK-3d-10); there is no terminal exit.

**Concern-atomicity and non-redundancy — shared across all rows (Non-Loss; over-merge prevention).** Two authoring failure modes inflate the requirement set and corrupt downstream matching; both are prevented at generation, not patched later:

1. **Concern-atomicity — one obligation per requirement at the CONCERN level, not only the sentence level.** CHK-3d-09 enforces *sentence*-level atomicity (no compound condition/object). This is the deeper rule. The CCIs you group into a single Requirement should correspond to **one obligation**. When the CCIs you would group span **distinct concerns** — different classification types (Process / Rule / Attribute / Constraint / Relationship / Event / Cycle / …) across different Zachman columns (How / What / Why / When / …) — ask whether they are genuinely one obligation. Usually they are not: a *retention rule* (How/Rule), an *accessibility constraint* (Why/Constraint), and a *status attribute* (What/Attribute) are three obligations even though all concern "task-completion records". **Split per distinct obligation, so every concern is VOICED by a requirement — not merely referenced by one.** A Requirement that lists a CCI in its `cci_refs` but does not *state* that CCI's concern leaves the concern silently uncovered (a Non-Loss failure: coverage on paper, no obligation in fact) and makes the Requirement a merge-magnet downstream (narrower, correctly-atomic siblings get judged duplicates of it and retired, dropping their concerns). This is a judgement, NOT "one Requirement per CCI": a legitimately-single obligation may draw on several CCIs (e.g. one relationship asserted by two signals) — the test is *one obligation, all of whose CCIs are facets the single statement actually expresses*.

2. **Non-redundancy — do not voice the same concern twice.** Within the Requirements you produce for a Domain, do not emit two statements asserting the same obligation, even reworded ("scope task visibility to the current week" / "limit task visibility to the current week scope") and even from overlapping CCI sets. Each concern is stated once; if two candidate statements would voice the same CCI's content, produce the single best statement. CHK-3d-07 collapses only *exact* statement+ref duplicates — near-duplicates are yours to not generate, and they are the principal driver of spurious downstream duplicate-merges (each near-duplicate pair becomes a merge the Matching service must resolve, risking retirement of a distinct obligation).

Both rules serve Non-Loss and matching quality directly: a concern-atomic, non-redundant set gives the Matching service almost nothing to merge, so the merge step cannot accidentally retire a distinct obligation. (Instrumentation: ADVC-3d-03 records, decidably, any Requirement whose `cci_refs` span ≥2 classification types across ≥2 columns — a soft over-bundling signal, not a reject.)

**`class_model` population — Structural requirements, all rows (§4.1.1(g), F105).** When the Object-recursion bottoms out in structure (a Structural requirement), do NOT serialise the entity into prose ("shall define columns A, B, and C" — that manufactures a false compound). Return a **`class_model`**: one entity, with its attributes, keys, and relationships, populated to THIS row's profile:
- **Row 2 (conceptual):** attribute *existence* + *semantic type* ("money", "date", "identifier"); relationships as plain associations. NO physical types, keys, or domains. **At least one semantic-typed attribute is REQUIRED** (Issue 6 / CHK-3d-11): an entity you can give no attribute is a name, not a model — return it as a DD entity name with NO `class_model`, not a degenerate empty model.
- **Row 3 (logical):** + logical type + attribute *domain*; logical-identity (business) keys. Technology-agnostic — no DB types, surrogate keys, or FK columns.
- **Row 4 (physical):** + physical type + nullability + PK/FK; relationships as FK columns. Surrogate keys appear here.
- **Row 5 (detailed):** + precision + check constraints + storage / index / default.

Record, **at the moment you form the model**, how this entity relates to its parent (the row-above `class_model` it refines): `refinement_kind` — `identity` (same entity refined), `decompose` (one parent entity becomes several here — e.g. a Task with a completion event becomes Task + TaskCompletion), `realise_relationship` (a parent association becomes an FK/junction), `introduce` (a child with no conceptual parent — a surrogate key or junction), or `merge` (several parents fold into one). Each attribute carries an `origin` — `refines` (a parent attribute), `realises` (an FK materialising a parent relationship), or `introduced` (a physical artefact with no parent). You know which transformation you performed; record it — it is never inferred later. Preserve the source's entity name (§domain-entity vocabulary); states and roles are attributes, not new entities.

**`object_refs` identification — behavioural requirements, all rows (§5.5, F107).** When a Functional / Constraint statement references a data-model element **by name** — an entity, an attribute, or a named value ("a task with status *available*", "the *weekly earnings* total") — return the dotted path(s) it names in `object_refs`: `<Entity>` / `<Entity>.<attr>` / `<Entity>.<attr>.<value>` (e.g. `Task.status.available`). Use the entity's canonical name and the attribute/value as the model defines them. Do NOT invent values or attributes not present in the data model; the resolver (§4.4.3a) binds each path to the owning `class_model`, and an unresolvable value is flagged for review, not silently accepted. A behavioural statement that references no data-model element by name returns an empty `object_refs`.

```
REQUIREMENT_ROW_GUIDANCE = {
    "1": """
## Row 1 — Planner / Scope Layer — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the enterprise scope level — the view of
a senior executive or board member. Each requirement expresses something the enterprise
commits to, is accountable for, or is constrained by — without reference to how any
system works.

### Statement subject (REQUIRED)
Every Row 1 requirement statement takes THE ENTERPRISE as its subject:
  "The enterprise shall ..."
Do NOT write "The system shall ..." at Row 1 — that is Row 2+ vocabulary and describes
a system, not an enterprise commitment.

This holds for COMPLIANCE, LEGISLATIVE, and REGULATORY obligations, which otherwise tend
to attract conventional system-requirements phrasing. Write:
  "The enterprise shall comply with applicable legislative obligations."
NEVER:
  "The system shall comply with applicable legislative obligations."
If the source content is a regulatory or compliance constraint, the enterprise is still
the accountable subject — not a system.

### Normative form and atomicity
- Use the normative "shall". One obligation per statement.
- If a statement would join two distinct obligations with "and" / "," apply the two-step
  test: (1) is there a single obligation that subsumes both? Use it. (2) If not, split
  into two requirements. (Requirement-level analogue of the domain "and" test.)
  Example: "shall determine and present aggregate earnings" is two acts (determine;
  present) — prefer one obligation, or split.

### Statement vocabulary
Row 1 statements use enterprise-commitment verbs:
  Appropriate: recognise, establish, maintain, provide, govern, ensure, comply, commit,
               be accountable for, be entitled to, enable (at enterprise scope)
  Avoid: calculate, display, track, store, retrieve, retain, generate, manage, process
         (these describe system functions — they belong at Row 2 or below). "retain" in
         particular is storage vocabulary — say "maintain records" / "be accountable for"
         at Row 1.

### Domain entity vocabulary (REQUIRED — preserve the source's nouns)
Abstraction at Row 1 lives in the SUBJECT and the VERB (the enterprise commits to / is
accountable for / establishes) — NOT in renaming the things the enterprise commits to.
KEEP the domain-entity nouns the source uses. If the source says "task", write "task" —
NOT "work unit", "value-generating activity", or "strategic instrument". If the source
says "reward" / "pocket money", write that — NOT "monetary reward as a strategic value
exchange mechanism". Do NOT coin abstract paraphrases (instrument, mechanism, metric,
exchange) for concrete source entities.
  Right:  "The enterprise shall enable children to claim and complete tasks."
  Wrong:  "The enterprise shall establish work units as strategic instruments for value
           creation."
This is a DOMAIN-ENTITY rule, not literal echoing: still neutralise genuinely system- or
UI-level source nouns to their domain entity (source "claim button" / "screen" → the
domain entity "claim" / "task", not "button"). Preserve the DOMAIN nouns (task, reward,
child, earnings); drop only implementation/UI nouns.

The entity is the BARE source noun — not a qualified, compounded, or abstracted form. The
source names ONE entity ("task") and describes it in STATES ("available", "completed",
"claimed"); the entity is `task` and the states are ATTRIBUTES, not separate entities. Do
NOT coin "task opportunity", "completed achievement", "economic activity", or "household
economy" — those are the bare entity (`task`, `child`) dressed in a state or an
abstraction. One entity, one bare name; states and roles are attributes of it.
  Right:  "...children to claim available tasks ... and view completed tasks."   (entity: task)
  Wrong:  "...identify available task opportunities ... view completed achievements." (two coined entities)
Why this matters: a single entity must carry ONE name from enterprise scope down to
realisation. That consistent thread is what the Data Dictionary resolves and what
cross-row refinement matches on; a Row-1-only synonym ("work unit" for "task") OR a
state-qualified coinage ("task opportunity"/"completed achievement" for "task") breaks the
thread (Non-Loss failure) and fragments one entity into several Data Dictionary canonicals.

### requirement_type reasoning (principle-based — choose, do not pattern-match)
Weigh the source CCIs' Zachman columns and content against the row's abstraction level:
- Why-column / motivation / rule / policy / commitment content → lean Constraint.
- How / What / When / capability / function content → lean Functional.
- Content expressing a measurable threshold, rate, latency, or capacity → Constraint,
  verified by Measurement (the statement SHOULD carry fit_criteria — the threshold).
- Content expressing a quality attribute (usability, maintainability, portability) →
  Constraint (a bound on a quality dimension), verified by Inspection or Measurement.
- Content asserting what an entity is — its composition, attributes, or relationships →
  Structural.
These are reasoning signals, not a lookup table. A genuinely ambiguous obligation may
read as either Constraint or Functional — choose the dominant force; do not force a
distribution.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include only when the content gives a measurable acceptance basis.
- verification_method (Test/Analysis/Inspection/Demonstration): include only when a
  natural method exists. An abstract enterprise constraint (e.g. "support charitable
  responsibility obligations") may have NO natural verification method at Row 1 — OMIT
  the field rather than guessing. Omission is correct, not a defect.
- priority (High/Medium/Low): include only when the source content supports a relative
  priority judgement. Do NOT default every requirement to High. If the content gives no
  basis, omit.

### What NOT to do
- Do NOT introduce actors, behaviours, or constraints not present in the source CCIs.
- Do NOT reproduce CCI description text verbatim as the statement — derive a normative
  statement from it. "Derive" means re-cast the sentence into normative enterprise-
  commitment form; it does NOT mean renaming the domain entities — keep the source's
  domain nouns (see Domain entity vocabulary).
- Do NOT produce one thin requirement per CCI mechanically; consolidate where CCIs
  express one obligation, split where one CCI carries two.
""",

    "2": """
## Row 2 — Owner / Business Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the business-owner level — the view of
someone who understands what the enterprise is responsible for delivering and how it
must behave, but who is NOT concerned with how that responsibility is technically
realised. Each requirement expresses a business capability, obligation, or rule the
business must satisfy — stated as a persistent business responsibility, not a workflow
step and not a system function.

### Statement subject (REQUIRED)
Row 2 has FOUR legitimate statement subjects. Choose by the BOUNDARY TEST — do NOT
default to the business. The boundary test: does the party or function this CCI
describes cross the system boundary?

(a) ACTOR / STAKEHOLDER subject — an external party interacting WITH the system
    (reaching in to do something). Subject = the actor; verb = their real action:
      "A child can claim a completed task."
      "A parent can view their child's earnings."
    These are Who-column, boundary-crossing statements. They NAME the system boundary
    and are first-class. Do NOT re-express them as "the business shall enable the child
    to ..." — that buries the actor in the object and loses the boundary. Required
    wherever a CCI describes an actor interacting with the system (the Who column must
    be occupied — Cell Occupancy).

(b) SYSTEM subject — the capability the system PROVIDES at the boundary (the affordance
    meeting the actor), stated as WHAT the system provides, NOT how:
      "The system shall make completed tasks claimable by entitled children."
      "The system shall make a child's earnings visible to the parent."
    Legitimate at Row 2 as a BLACK-BOX affordance. Name the provided capability and NO
    realisation (no API/schema/database/service/endpoint/algorithm/validation rule —
    that is Row 3 HOW). "The system enables claimable tasks" = Row 2 (names the
    mechanism the system provides); "the system exposes a claim operation validating
    entitlement against the ledger" = Row 3 (names the realisation).

(c) BUSINESS subject — what the business does BEHIND the boundary: a responsibility,
    rule, or artefact it maintains:
      "The business shall maintain a record of each task claim."
      "The business shall enforce the weekly reset cycle."

(d) NAMED BUSINESS ROLE — a WHO-column CCI naming an accountable internal role that
    does NOT act through the system (off-boundary accountability):
      "The account holder shall approve ..."

The boundary test, applied:
  - Party acts THROUGH the system (reaches in)        → ACTOR subject (a)
  - System OFFERS the capability to that actor         → SYSTEM subject (b)
  - Function happens BEHIND the boundary (responsibility/rule/record)
                                                        → BUSINESS subject (c)
  - Accountable internal party, off-system             → NAMED BUSINESS ROLE (d)

Subject by Zachman column (illustration — the boundary test decides; this orients):
  Who (external party interacting)     → ACTOR         "a child can claim a task"
  Who (internal accountable party)     → BUSINESS ROLE "the account holder approves"
  How (capability offered to an actor) → SYSTEM        "the system makes tasks claimable"
  How (internal business process)      → BUSINESS      "the business settles compensation"
  What (artefact the business keeps)   → BUSINESS      "maintain a record of each claim"
  When (cycle / trigger)               → BUSINESS (or Condition slot) "enforce weekly reset"
  Why (rule / goal / constraint)       → BUSINESS (Constraint) "enforce approval threshold"

Do NOT use "The enterprise shall ..." — that is Row 1 (Planner) scope vocabulary.
The distinction from Row 1: Row 1 says what the enterprise commits to at scope level
("The enterprise shall recognise child users as participants"); Row 2 says who does
what at the business boundary and what the business is responsible for behind it
("A child can claim a completed task"; "The system shall make tasks claimable"; "The
business shall maintain a record of each claim").

### Normative form and atomicity
- Use the normative "shall" (or "can"/"may" for an ACTOR capability — "a child can claim…"). One obligation per statement.
- Apply the two-step "and" test: (1) is there a single obligation that subsumes both clauses? Use it. (2) If not, split into two requirements.
- OVER-GENERATION BRAKE: a single source concept can span columns (an actor-action, the system-affordance that enables it, and a business record). Author ONLY the column-aspects the source actually expresses — do NOT mechanically manufacture an actor + system + business statement for every concept. Where both an actor-action and its system-affordance ARE expressed, author both but treat them as a COMPLEMENTARY PAIR (the affordance enables the action — related, not two independent obligations, and NOT duplicates of each other). Never state one obligation twice under two different subjects.
- Row 2 statements are STATELESS obligations — a capability/responsibility, NOT a step-by-step sequence ("first X, then Y"). A statement describing an ordered workflow has dropped to Row 3+ and must be re-stated.

### Statement vocabulary
Vocabulary depends on the SUBJECT CLASS:
  ACTOR subject — the actor's real action verb: claim, approve, view, define, submit,
    request. Do NOT wrap it as "be enabled to" / "be able to be given" — name the action.
  SYSTEM subject — the provided capability (WHAT, never HOW): make available, make
    visible, make claimable, present, provide, enable (a capability).
  BUSINESS subject / role — business-responsibility vocabulary: maintain, record,
    govern, settle, approve, authorise, account for, be responsible / accountable for,
    steward, enforce (a business rule), recognise (a business role).
  Avoid at Row 2 (ALL subjects): calculate, process, store, retrieve, aggregate,
    compute, manage, track, retain / retention, generate, display — system-function /
    technical-storage vocabulary belonging to Row 3+ ("retain"/"retention" → "maintain
    a record").
  Avoid (ALL subjects) — the WHAT/HOW guard: any word implying a technical REALISATION
    mechanism — API, schema, database, service, endpoint, algorithm, validation rule.
    This is what keeps a SYSTEM-subject statement a Row 2 black-box affordance (WHAT the
    system provides) rather than a Row 3 design (HOW it provides it).

### requirement_type reasoning (principle-based — choose, do not pattern-match)
Weigh the source CCIs' Zachman columns and content against the business-owner level:
- WHY-column business governance rules / motivation / constraints on business behaviour
  → lean Constraint ("The business shall enforce the approval threshold ...").
- HOW-column business capability declarations / WHAT-column business artefacts the
  business must maintain / WHEN-column business triggers → lean Functional ("The
  business shall maintain a record of ...").
- Content expressing a measurable business threshold, rate, or service level →
  Constraint, verified by Measurement (the statement SHOULD carry fit_criteria).
- Content expressing a business quality attribute → Constraint (quality bound).
- Content asserting what a business entity is (composition/attributes/relationships) → Structural.
Reasoning signals, not a lookup table. Note: at Row 2 the Functional/Constraint balance
is typically more even than at Row 1 — business capability declarations (HOW-column) are
genuinely Functional, while business rules (WHY-column) are genuinely Constraint. Do not
carry a Row-1 lean into Row 2; judge each statement on its source columns.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include only when the content gives a measurable acceptance basis (more
  common at Row 2 than Row 1 — business service levels and thresholds appear here).
- verification_method (Test/Analysis/Inspection/Demonstration): include when a natural
  method exists for the business responsibility; omit when the content gives no basis.
- priority (High/Medium/Low): include only when the source supports a relative judgement.
  Do NOT default every requirement to High; omit if there is no basis.

### What NOT to do
- Do NOT bury an interacting actor inside an object ("the business shall enable the child to claim …") — author the actor as subject (a). Burying it loses the boundary.
- Do NOT introduce actors, roles, capabilities, or rules not present in the source CCIs.
- Do NOT reproduce CCI description text verbatim — derive a normative statement.
- Do NOT state a workflow sequence; state a stateless capability / responsibility.
- Do NOT frame at enterprise/scope level (Row 1).
- Do NOT describe HOW the system realises a capability (Row 3 — operations, validation, structure); for a system subject, name only WHAT it provides at the boundary.
""",

    # Rows 3–5: AUTHORED AHEAD OF TEST (Mechanism Spec v0.4). Candidate guidance — NOT yet validated
    # against run evidence (Rows 1–2 were validate-then-author; Rows 3–5 authored together to accelerate
    # the remaining rows on the proven pattern). Treat as pending test until run evidence confirms each.
    # Row 6 remains a short-phrase stub. The prompt template handles full blocks and short phrases alike.
    "3": """
## Row 3 — Designer / Logical Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the logical design level — the view of a
system designer translating business obligations into logical structures, behaviours,
and rules, WITHOUT committing to any specific technology or implementation. Each
requirement expresses a logical system capability or a logical integrity constraint —
technology-agnostic, but more concrete than a business responsibility.

### Statement subject (REQUIRED)
Row 3 requirement statements take THE SYSTEM as subject, expressed LOGICALLY:
  "The system shall ..."
This is the row where "The system shall …" becomes correct (it is wrong at Rows 1–2).
But the system is described LOGICALLY — what it must do or enforce as a logical design,
NOT how it is built. Do NOT name technologies, platforms, or code constructs (that is
Row 4+). Do NOT frame as a business responsibility ("The business shall…" is Row 2).
The distinction from Row 2: Row 2 says what the business must be able to do ("The
business shall maintain a record of completed tasks"); Row 3 says how the system
logically realises that ("The system shall maintain a logical association between each
task instance and its completion state").

### Normative form and atomicity
- Use the normative "shall". One logical capability or constraint per statement.
- Apply the two-step "and" test; split genuine compound obligations.
- A Row 3 statement may describe a logical state transition or rule, but NOT a
  step-by-step algorithm (that is Row 5). "The system shall transition a task to
  Claimed state when a child claims it" is logical; "the system shall iterate the task
  list and set status=1" is algorithmic (Row 5) and out of level.

### Statement vocabulary
Row 3 statements use logical-design vocabulary:
  Appropriate: logical structure, logical association, state, state transition,
               validate, enforce (an invariant), derive, logical constraint, access
               boundary, visibility, lifecycle, logical model, decision logic
  Avoid: physical technology names (PostgreSQL, React, Redis, AWS, iOS), code constructs
         (class, function, module, endpoint, table, schema), business-obligation language
         (Row 2: stewardship, entitlement, accountability), and algorithmic/output detail
         (Row 5: calculate, compute, format, report — prefer "derive" / "decision logic"
         / "visibility model").

### requirement_type reasoning (principle-based — choose, do not pattern-match)
- WHY-column logical integrity rules / design-level invariants → lean Constraint ("The
  system shall enforce that …").
- HOW-column logical processes / WHAT-column logical structures / WHEN-column logical
  state triggers → lean Functional ("The system shall maintain / validate / derive …").
- Logical performance characteristics (a logical throughput or latency invariant) →
  Constraint, verified by Measurement (with fit_criteria).
- Logical quality attributes → Constraint (quality bound).
- Logical composition/attribute/relationship assertions → Structural.
Reasoning signals, not a lookup. Judge each statement on its source columns; do not
carry a lean from another row.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: include when a logical acceptance basis exists (a state invariant can
  often be expressed as a checkable condition).
- verification_method: Analysis or Inspection are common at Row 3 (logical assessment);
  include when a natural method exists, omit otherwise.
- priority: include only when the source supports a relative judgement; do not default
  to High.

### What NOT to do
- Do NOT name technologies, platforms, or code constructs (Row 4+).
- Do NOT frame as a business responsibility (Row 2) or describe a step-by-step algorithm (Row 5).
- Do NOT reproduce CCI description text verbatim — derive a normative statement.
""",

    "4": """
## Row 4 — Builder / Physical Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the physical builder level — the view of a
builder making concrete technology choices and specifying physical components, without
yet writing code or configuring runtime detail. Each requirement expresses a physical
construction obligation — a concrete technology, component, or platform decision.

### Statement subject (REQUIRED)
Row 4 statements take THE SYSTEM or a NAMED PHYSICAL COMPONENT as subject:
  "The system shall ..."           (default)
  "<Named component> shall ..."    (when a CCI identifies a specific physical component,
                                   e.g. "The mobile application shall ...")
Technology and platform names are APPROPRIATE here (unlike Row 3). The distinction from
Row 3: Row 3 says what the system must do logically; Row 4 says how it is physically
realised ("The system shall persist task records in a relational store", "The mobile
application shall run on iOS and Android").

### Normative form and atomicity
- Normative "shall"; one physical construction obligation per statement; apply the "and" test.
- Physical does not mean code-level — a Row 4 statement specifies the technology/component
  choice, not the algorithm or configuration value (those are Row 5).

### Statement vocabulary
Row 4 statements use physical-construction vocabulary:
  Appropriate: platform, component, infrastructure, deployment, interface, integration,
               physical schema, service, API, persist, host, named technologies (iOS,
               Android, relational store, REST, etc.)
  Avoid: business-level language (Row 2), purely logical abstractions with no physical
         specifics (Row 3), and code-level/configuration detail (Row 5: exact field
         types, timeout values, algorithm steps).

### requirement_type reasoning (principle-based)
- WHY-column physical constraints (platform version requirements, hardware limits,
  build-level compliance mandates) → lean Constraint.
- HOW/WHAT/WHERE/WHO physical construction obligations (components, schemas, deployment
  targets, interfaces) → lean Functional.
- Physical performance requirements (concrete throughput, latency, capacity) →
  Constraint, verified by Measurement (with fit_criteria — common and expected at Row 4).
- Physical quality attributes → Constraint (quality bound).
- Physical composition/attribute/relationship assertions (schemas, component structure) → Structural.
Judge each statement on its source columns.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: more frequently warranted at Row 4 (physical performance/capacity has
  measurable acceptance bases).
- verification_method: Test and Demonstration become common at Row 4 (physical artefacts
  are testable); include when a natural method exists.
- priority: include when the source supports it; do not default to High.

### What NOT to do
- Do NOT frame as business (Row 2) or purely logical (Row 3) — name the physical realisation.
- Do NOT drop to code-level/configuration detail (Row 5).
- Do NOT reproduce CCI description text verbatim.

### Sparse rows
Row 4 is often sparse for conceptually-framed source material. If the row has zero CCIs
the mechanism takes the no_cci_input path (e.g. NQPS Row 4) — this guidance is not invoked.
A single physical constraint legitimately yields a single requirement.
""",

    "5": """
## Row 5 — Implementer / Detailed Design Level — Requirement Statement Formulation

You are formulating REQUIREMENT STATEMENTS at the detailed design level — the view of an
implementer specifying the precise detail needed before a developer writes code:
algorithms, data formats, platform-specific configuration, interface contracts, detailed
runtime behaviours. Each requirement expresses a detailed specification obligation.

### Statement subject (REQUIRED)
Row 5 statements take THE SYSTEM or a NAMED COMPONENT/INTERFACE as subject:
  "The system shall ..."
  "<Named component/interface> shall ..."
The distinction from Row 4: Row 4 chooses the technology ("persist in a relational
store"); Row 5 specifies the detail ("store the reward value as a decimal(10,2) field
with a non-negative constraint"). Row 5 is where exact formats, algorithms, and
configuration values are correct.

### Normative form and atomicity
- Normative "shall"; one detailed specification per statement; apply the "and" test.
- Row 5 statements may specify precise algorithmic steps, exact field definitions,
  exact timing values — the detail a developer needs without making further design
  decisions.

### Statement vocabulary
Row 5 statements use detailed-implementation vocabulary:
  Appropriate: exact field definitions, data types, format constraints, validation
               rules, enumeration values, algorithm steps, timeout values, cycle
               durations, interface contracts, configuration parameters, calculate,
               compute, format (these algorithmic/output verbs are CORRECT at Row 5)
  Avoid: business-level (Row 2) and high-level logical/physical framing without the
         precise detail (Rows 3–4). At Row 5 the detail is the point — a vague
         statement is out of level downward.

### requirement_type reasoning (principle-based)
- WHY-column detailed constraints (precise validation rules, exact platform version
  requirements expressed as implementable constraints) → lean Constraint.
- HOW-column detailed algorithms / WHAT-column detailed data specifications / WHEN-column
  detailed timing → lean Functional.
- Detailed performance specifications (exact latency/throughput targets with values) →
  Constraint, verified by Measurement (the fit_criteria IS the numeric target).
- Detailed quality specifications → Constraint (quality bound).
- Detailed data-structure / format / field composition assertions → Structural.

### Optional fields — populate when warranted, omit otherwise
- fit_criteria: frequently warranted at Row 5 and often IS the specification (exact
  values, formats, thresholds).
- verification_method: Test is common at Row 5 (detailed specs are directly testable).
- priority: include when the source supports it; do not default to High.

### What NOT to do
- Do NOT frame at business/logical/physical-choice level without the implementable detail.
- Do NOT reproduce CCI description text verbatim — derive a normative specification.

### Column-sparse rows
Row 5 CCIs often cluster by column (deployment nodes, UI actors, timing cycles). Derive
requirements grouped by their natural implementation boundary; a sparse single-column
row legitimately yields few requirements.
""",

    "6": "Operational level — statements covering runtime procedures and user/operator interactions; "
         "subject is the system or the operator as the operational content dictates. "
         "[Short phrase — operational content is rare in the reference source documents; full block "
         "pending Row 6 requirement-derivation validation if/when operational CCIs appear.]",
}
```

The prompt template accesses `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` and injects the full block (Row 1) or short phrase (Rows 2–6) as a prompt section, exactly as the domain ROW_GUIDANCE template does.

---

## 6. Mode Discipline Realisation

Mode-discipline decorator pattern (Row 4 Applied §4.7), identical structure to the sibling §6.

| Stage / Sub-act | Declared mode | Constraint | AnalysisPass record |
|---|---|---|---|
| Stage 1 — Pre-flight | DM | No AI calls | `mode_active:["DM"]` |
| Stage 2 — Per-Domain derivation | IM | AI call per Domain; LPM on CCI text | `mode_active:["IM"]`; one fingerprint per Domain |
| Stage 2 — Retry | IM | Second AI call; same constraint | Retry fingerprint appended |
| Stage 3 — Structural checks (CHK-3d-01..04,06,07,08; ADVC-3d-01) | DM | No AI calls (except repair) | `mode_active:["DM"]` |
| Stage 3 — Non-Loss repair (conditional) | IM | AI call; `repair_prompt_issued=true` | `stage3_repair` fingerprint |
| Stage 4 — Entity production | DM | No AI calls; domain_refs derivation + ledger write | `mode_active:["DM"]` |
| Stage 4 — `class_model` commit + prose projection (§4.4.3c) | DM | No AI calls; the `class_model` was the Stage 2 IM proposal — Stage 4 validates (CHK-3d-11) and commits | `mode_active:["DM"]` |
| Stage 4 — `object_refs` materialisation (§4.4.3a step 4) | DM | No AI calls; resolves IM-named candidate paths through DD→`class_model` | `mode_active:["DM"]` |
| Stage 3 — CHK-3d-12 model-coverage repair (conditional) | IM | AI call; re-derive the uncovered entity | `chk3d12_repair` fingerprint |

`declared_transformation_modes=["IM","DM"]`; primary `mode_active="IM"`. **Do NOT record `mode_active:"LPM"`** — LPM is a preservation constraint, not a transformation mode (carry forward the sibling's PMT build correction). Mode violations → `mechanism_data.mode_violations`; `execution_status="PartialSuccess"`.

---

## 7. Audit Trail Population

AnalysisPass `outputs` for `mechanism="RequirementDerivation"`. All fields required; zero-value arrays `[]`. **`mechanism_data` naming (resolves Row 3 OQ-3d-02): this spec adopts the sibling's `mechanism_data` convention** — not `requirement_data` — for consistency with the Domain Derivation spec and with the existing production run files, which already emit `mechanism_data`. `execution_warnings`, `ai_model_fingerprints`, and `concern_entities` are **standard top-level `outputs` fields**, siblings of `mechanism_data`, NOT nested inside it (same as the sibling §7; matches `__init__.py`).

`execution_warnings` types: `no_cci_input` (§4.1 → PartialSuccess); `cci_referential_integrity_violation` (info); `incremental_fallback_to_fullrerun` (→ PartialSuccess); `fit_criteria_empty_stripped`, `performance_missing_fit_criteria`, `duplicate_requirement_collapsed`, `requirement_count_advisory`, `incremental_ref_outside_new_set`, `chk3d05_repair_performed`, `chk3d05_repair_failed`, `subject_vocabulary_mismatch` (info); `path_r_parse_failure`, `path_r_ai_error`, `path_r_invalid_refines_refs` (Path-R batch failures, §4.2); `empty_seed_set_upstream_gap` (GAP-2, rows ≥ 2 with no surviving parent); `chk3d10_seed_extinct` (hard — persistent unrefined seed, §CHK-3d-10), `chk3d10_repair_performed`, `chk3d10_repair_failed`; `atomicity_possible_exception` (CHK-3d-09 edge); `conjoined_predicate_hard_reject`, `chk3d09_decompose_performed` (CHK-3d-09 conjoined-predicate hard reject + automatic in-place decomposition, F98); `conjoined_predicate_decompose_failed` (per-invocation decompose-failure trace, F100 — one per failed decompose call, never deduped per domain, carrying `statement_preview`); `chk3d09_decompose_failed_retained` (F102 — a compound that could not be decomposed is RETAINED in the surviving set, not dropped; pairs 1:1 with a `conjoined_predicate_decompose_failed`); `decompose_child_discarded` (F106 — one malformed child in a repair response is logged with its index + validation error and discarded individually; the valid children are kept, never an all-or-nothing collapse); `ver_3d_17_fail`, `ver_3d_18_fail`; `ver_3d_19_term_rejected` (VER-3d-19 presentation-time entity-grade reject → `dd_zero_term`, F99 — supersedes the v0.23 post-commit `ver_3d_19_entity_grade_violations` warn); `dd_extraction_batch_truncated` (Stage 4 extraction batch hit the output ceiling / unparseable / index-short — re-split and retried, NEVER swallowed to all-empty, F101), `slot_parse_failed` (per-proposal slot-parse guard → that proposal to `dd_zero_term`, F101), `dd_entity_extraction_all_empty` (legitimate only when a row genuinely yields no entity-grade terms; a truncation must raise `dd_extraction_batch_truncated` instead, F101); `class_model_invalid` (CHK-3d-11 reject — a Structural `class_model` failing structural validity, F105), `class_model_profile_advisory` / `class_model_statement_divergence` (soft, §4.4.3c), `chk3d12_model_element_extinct` (hard — a row n−1 model-element covered by no child, F105/CHK-3d-12), `chk3d12_repair_performed` / `chk3d12_repair_failed` (model-coverage repair, CHK-3d-12), `object_refs_dangling` (a behavioural `object_refs` value absent from every defining `class_model` domain — a Quality-pass finding, NOT a reject, F107); `orphan_value_set_on_migration` (a legacy DD value-set with no backing surviving requirement, logged loud at the one-time migration rather than silently dropped — §12.3, Issue 4).

```jsonc
{
  "mechanism_data": {
    // --- Stage 1 ---
    "run_scenario":              "FirstRun",        // one of four scenario names
    "requirement_input_hash":    "<sha256-hex>",    // MD-3: CCI-ids + active Domain-ids (+ SEEDS: surviving row n−1 req-ids, rows ≥ 2)
    "domain_id_set":             ["D001","D002"],   // sorted active Domain-ids at run time (Domain-set comparison)
    "cci_count_input":           7,                 // 0 on zero-CCI exit
    "domain_count_input":        3,
    "large_cci_set_advisory":    false,
    "idempotent":                false,             // true on IdempotentRerun only
    "path_r_count":              13,                // v0.13: # Path-R refinement children produced (rows ≥ 2; 0 at Row 1)
    "seed_coverage":             { "total_seeds": 11, "refined_count": 11, "unrefined_count": 0, "unrefined_seed_ids": [] }, // v0.13; CHK-3d-10 metric (rows ≥ 2)
    "elaboration_gaps":          [],                // v0.13: [{seed_id, reason}] — persistent unrefined seeds after Path-R repair (CHK-3d-10)

    // --- Stage 3 ---
    "repair_prompt_issued":      false,
    "orphaned_ccis":             [],                // persistent orphans after repair
    "validation_failures":       [],                // [{check_id, source_domain_id, detail}]
    "duplicate_requirements_collapsed": [],         // [{kept_statement, collapsed_count}]
    "subject_vocabulary_flags":  [],                // [{requirement_id, row, detected_subject}] — CHK-3d-08
    "concern_atomicity_flags":   [],                // [{requirement_id, cci_refs, classification_types, columns}] — ADVC-3d-03
    "dd_binding":                { "terms_presented": 18, "resolved": 16, "new_canonical": 7, "synonyms_recorded": 9, "dd_zero_term": [], "dd_unresolved": [] }, // §4.4.3b DD name-registration audit (post-F107: no relationships_recorded/values_recorded)
    "class_model_binding":       { "structural_count": 6, "with_class_model": 6, "by_tier": {}, "by_refinement_kind": {}, "invalid": [] }, // F105 — §4.4.3c
    "object_refs_binding":       { "formed": 11, "dangling": [] },   // F107 — §4.4.3a step 4
    "model_coverage":            { "parent_elements": 14, "covered": 14, "ratio": 1.0 }, // F105/CHK-3d-12 (rows ≥ 3)
    "model_coverage_gaps":       [],                                 // [{parent_ref, element, kind, reason}] — persistent uncovered parent elements (CHK-3d-12)

    // --- Stage 4 ---
    "requirement_count_produced": 5,
    "requirement_count_retired":  0,                // non-zero on FullRerun only
    "requirement_type_distribution": {
      "Functional": 3, "Constraint": 2, "Structural": 0
    },
    "requirements_produced": [
      { "requirement_id": "R001", "requirement_type": "Functional",
        "cci_ref_count": 2, "domain_refs": ["D001"] }
    ],
    "downstream_rerun_required": false,
    "retirement_mapping":        [],                // [{old_requirement_id, inferred_successor_requirement_id}]

    // --- Mode discipline ---
    "mode_violations":           []
  },

  // --- top-level outputs siblings of mechanism_data (NOT nested; per §7 prose / __init__.py) ---
  "execution_warnings":  [],
  "ai_model_fingerprints": [                          // all IM calls this run
    { "stage": "stage2_domain_D001", "model": "claude-sonnet-4-20250514",
      "input_tokens": 0, "output_tokens": 0 }
  ],
  "concern_entities":    []
}
```

`ai_model_fingerprints` accumulates every IM call: each Stage 2 per-Domain call, any retry, the Stage 3 repair. On IdempotentRerun: `[]` and `idempotent=true`. `row_ref` is set both top-level on the AnalysisPass and inside `mechanism_data` (sibling convention). VER-3d-08 checks `mechanism_data` completeness; `execution_warnings` is verified by the common AnalysisPass schema validator.

---

## 8. Verification Criteria

### 8.1 Decidable criteria (automated — pytest)

In `tests/test_requirement_derivation.py`, Neon test DB with transaction-rollback isolation (same pattern as `tests/test_domain_derivation.py`). Realises Row 3 §8.1.

| ID | Criterion | pytest assertion |
|---|---|---|
| **VER-3d-01** | All `requirement_id` match `^R\d{3}$` | `re.fullmatch` all in project |
| **VER-3d-02** | All `requirement_id` unique (active + retired) | `len(set(ids))==len(ids)` |
| **VER-3d-03** | Non-empty `statement`; ≥1 `cci_refs` OR ≥1 `refines_refs` (not-both-empty; matches CHK-3d-02 / migration 025 / ledger v2.16 — a Path-R requirement has empty `cci_refs` by design) | `len(statement)>0` and `(jsonb_array_length(cci_refs)>=1 OR jsonb_array_length(refines_refs)>=1)` |
| **VER-3d-21** | Seed-set size equals surviving row n−1 count (provenance-blind guard) | `len(seed_set) == count(retired_at IS NULL AND row_target=str(row−1))`; assert `ver3d21_seed_set_size_mismatch` absent in producing runs; negative fixture seeds Stage 2 with a filtered list and asserts the mismatch warning fires |
| **VER-3d-04** | `cci_refs` resolve to CCIs with matching `row_target` | expand; JOIN `cell_content_item → zachman_cell`; assert row match |
| **VER-3d-05** | Non-Loss: every eligible CCI in ≥1 Requirement | union of `cci_refs` ⊇ eligible set for the row |
| **VER-3d-06** | RequirementRegister `member_ids` == active set (all rows) | set equality, `retired_at IS NULL`, no row filter; ≥2 rows in integration test |
| **VER-3d-07** | AnalysisPass `mechanism="RequirementDerivation"`, `row_ref` exists | presence query |
| **VER-3d-08** | `mechanism_data` present; required fields non-null | schema validation against §7 |
| **VER-3d-09** | All `requirement_type` in {Functional, Constraint, Structural} | membership check |
| **VER-3d-10** | `domain_refs` ≥1; resolve to existing Domains with matching `row_target` | expand; JOIN `domain`; assert exists + row match |
| **VER-3d-11** | IdempotentRerun: set unchanged; `idempotent==true`; status=Success; idempotent==true | before/after + flag |
| **VER-3d-12** | FullRerun: `requirement_count_retired` == prior active count | query prior; assert equality |
| **VER-3d-13** | `requirement_count_produced >= 1` when `cci_count_input > 0` | conditional |
| **VER-3d-14** | No `fit_criteria` present-but-empty | `fit_criteria IS NULL OR length>0` |
| **VER-3d-15** | No surviving Requirement violates typed-slot atomicity (CHK-3d-09 hard) | assert `validation_failures` carries no surviving `atomicity_violation`; spot-check survivors parse to required slots for their type |
| **VER-3d-16** | `refines_refs` valid: a Path-R child carries its seed(s) as produced by Pass 3d; a Path-N proposal is empty until Matching; every present entry references an existing Requirement at `row_target − 1` | Pass 3d output: assert Path-R children non-empty and Path-N empty; for every entry JOIN `requirement` and assert parent row = child row − 1 |
| **VER-3d-17** | Every Functional Object slot and every Structural entity in the produced set was presented to the DD service and is either resolved to a `DataDictionaryEntry` or recorded in `mechanism_data.dd_binding.dd_unresolved` (none silently absent) | `test_dd_binding_complete` — for each survivor, assert its Object/entity term appears once in `dd_binding` as resolved or `dd_unresolved` |
| **VER-3d-18** | Regression guard: after a Pass 3d run that produced ≥1 Requirement, the project Data Dictionary is non-empty (≥1 `DataDictionaryEntry`) | `test_dd_populated_after_derivation` — `requirement_count_produced >= 1 ⇒ count(DataDictionaryEntry) >= 1` |
| **VER-3d-19** | Entity-grade term guard (**REJECT at presentation time, F99** — relocated from post-commit warn): a clause-grade candidate (contains a finite verb phrase, ends with sentence punctuation, or exceeds the entity-grade bound — heuristically > ~5 words) is refused presentation to the DD and recorded in `dd_binding.dd_zero_term` (`ver_3d_19_term_rejected`); no presented term equals the verbatim slot or the full statement, and DD `canonical.name` values produced by this run are entity-grade noun phrases | `test_dd_terms_entity_grade` — assert no presented `dd_binding` term contains a finite verb phrase / trailing period; assert clause-grade candidates are routed to `dd_zero_term`, not committed as canonicals; spot-check produced canonical names against the bound |
| **VER-3d-22** | CHK-3d-09 decompose **obligation-present** invariant (F100 + F102): (a) outcome-traced — within each `source_domain_id`'s proposal set, `|conjoined_predicate_hard_reject| == |chk3d09_decompose_performed| + |conjoined_predicate_decompose_failed|` (no untraced residual); (b) obligation-present — **every** hard-rejected compound's obligation is demonstrably present in the output: as atomic children (`chk3d09_decompose_performed`), OR a **retained compound** (`chk3d09_decompose_failed_retained`, F102), OR a genuinely recovered orphan — NEVER absent. A `conjoined_predicate_decompose_failed` with no matching `chk3d09_decompose_failed_retained` and no orphan recovery is a Non-Loss breach (the v0.25 silent-drop) | `test_decompose_obligation_present` — group by `source_domain_id`, assert (a) the count identity; assert (b) every `conjoined_predicate_decompose_failed` proposal is present in `surviving_09` tagged `chk3d09_decompose_failed_retained` (NOT absent); negative fixture forces a decompose failure whose CCIs are covered by a sibling and asserts the compound is RETAINED (not dropped); plus the F100 sub-asserts — ≥2 failures in one domain yield 2 distinct warnings (not deduped), each carrying `statement_preview` |
| **VER-3d-24** | CHK-3d-09 detector precision (F104) — the four non-separable forms do NOT hard-flag: (P1) a predicate/object disjunction ("expose via REST **or** equivalent") is not rejected and is not split; (P2) a conjunction inside a relative/subordinate clause modifying one object ("implement a service **that** evaluates X **and** transitions Y") is not flagged; (P3) an operation/privilege list under one verb ("revoke UPDATE **and** DELETE") is not flagged; (P4) a temporal subordinator ("insert … **prior to** deleting") is not flagged. Conversely, a genuine conjoined predicate ("enforce checks **and** delete records") still hard-flags | `test_detector_precision` — positive fixtures for each of P1–P4 assert no `conjoined_predicate_hard_reject` / no compound-object hard; a control genuine-conjoined-predicate fixture asserts the hard reject still fires; a P1 fixture additionally asserts no conjunct-split occurs (the OR is preserved whole); assert the condition-slot "or" still flags as compound condition (P1 slot-sensitivity) |
| **VER-3d-25** | CHK-3d-09 decompose executor robustness (F106): (a) **no all-or-nothing** — a repair response with ≥1 valid child returns those children; a malformed sibling is discarded individually (`decompose_child_discarded`), never collapsing the result to empty; (b) **cci_refs inheritance** — every decompose child carries the parent compound's `cci_refs` and is never rejected for empty `cci_refs`; (c) **split, don't re-decide** — a known-splittable conjoined predicate ("retrieve **and** display tasks") produces ≥2 children, not 0 or 1 | `test_decompose_executor_robust` — (a) fixture: a 3-child repair response with one child carrying a schema violation → assert 2 valid children returned (not None) + one `decompose_child_discarded`; (b) fixture: a child with empty `cci_refs` → assert it is kept and assigned the parent's `cci_refs`; (c) fixture: "retrieve and display tasks with available status" → assert ≥2 children whose statements are single-verb (regression guard that the prompt no longer re-decides / collapses) |
| **VER-3d-23** | Stage 4 extraction completeness + no swallowed truncation (F101), three clauses: **(a) requirement-level completeness** — every surviving Requirement is in exactly one bucket, either contributing ≥1 presented term or recorded in `dd_zero_term`: `|reqs contributing ≥1 presented term| + |dd_zero_term| == row requirement count` (`dd_unresolved` is a sub-state of "contributed a term", NOT a separate bucket — do not add it here); **(b) term-level consistency** — `terms_presented == resolved + |dd_unresolved|` (presented terms partition into resolved and flagged); **(c) no swallowed truncation** — no batch recorded `dd_extraction_batch_truncated`, and a row-wide `dd_zero_term == row requirement count` is permitted ONLY when no batch truncated (otherwise it is a masked truncation). NB: `terms_presented` is a TERM count (one Requirement may present several entity terms); it is never equated to the Requirement count | `test_extraction_complete_and_untruncated` — assert (a) the requirement-level identity (count distinct requirements presenting ≥1 term, add `|dd_zero_term|`, equals row req count); assert (b) `terms_presented == resolved + |dd_unresolved|`; assert (c) no `dd_extraction_batch_truncated` in a clean producing run; negative fixture forces an over-ceiling batch and asserts `dd_extraction_batch_truncated` fires and the batch is re-split (NOT all-empty); assert extraction runs in `stage4_dd_entity_extraction_batch<N>` stages, never one unbatched call |

| **VER-3d-26** | `class_model` validity (F105, CHK-3d-11), **two phases** (Issue 2/6): **(a) structural (Stage 3, against the proposal)** — `entity` present, `tier`==row, **≥1 attribute** (≥1 *semantic-typed* at Row 2), ≤1 `key=="PK"`, FK/relationship target *format* well-formed, domains well-formed, enum-valid `tier`/`refinement_kind`/`key`/`origin`; `entity_ref` is NOT required of the proposal; **(b) referential (Stage 4, after §4.4.3a sets `entity_ref`)** — `entity_ref` resolves to a canonical DataDictionaryEntry and every FK `target_ref`/`relationships[].target` resolves to a known entity. Behavioural Requirements carry no `class_model`; Structural at rows 2–5 SHOULD carry one | `test_class_model_validity` — (a) structural clauses on each Structural survivor; negative fixtures: zero attributes → `no_attributes`, Row-2 typeless attribute → `row2_no_semantic_type`, two PKs → `multiple_pk`; assert the AI proposal parses WITHOUT `entity_ref`; (b) post-§4.4.3a assert `entity_ref` is `^DD\d{3}$` resolving to a canonical, a dangling FK target → `target_unresolved`; assert DB CHECK rejects `class_model` on Functional / `object_refs` on Structural |
| **VER-3d-27** | `class_model` concept-coverage (F105/CHK-3d-12, rows ≥ 3): every row n−1 `class_model` model-element is covered by ≥1 child element under a recorded `refinement_kind`; `introduce` children / `introduced` attributes are exempt from requiring a parent; an uncovered parent element after repair is recorded in `model_coverage_gaps` and raises `chk3d12_model_element_extinct` (never silently dropped) | `test_class_model_coverage` — PMT Task lineage fixture (R2 Task → R3 Task+TaskCompletion → R4 +completion_id/FKs): assert every parent element covered, `model_coverage.ratio==1.0`, the surrogate `completion_id` exempt (parentless `introduce`); negative fixture drops a conceptual attribute from the child and asserts `chk3d12_model_element_extinct` + a `model_coverage_gaps` entry |
| **VER-3d-28** | `object_refs` materialisation (F107): every committed `object_refs` entry's leading `<Entity>` resolves to a canonical DataDictionaryEntry (directly or via synonym) and its trailing `.attr`/`.value` resolves to a `class_model` `attr_name`/domain value; an unresolvable value is recorded in `object_refs_binding.dangling` (NOT a derivation reject); no `object_refs` on a Structural Requirement | `test_object_refs_resolution` — `Task.status.available` fixture: assert it is committed and resolves end-to-end; `Task.status.archived` fixture (value absent): assert it is recorded dangling + `object_refs_dangling`, the Requirement still produced; assert migration promotes the DD `lifecycle_state` value-set into the `Task.status` `class_model` domain and removes the DD value-set |

(CHK-3d-08 subject mismatch is recorded in `subject_vocabulary_flags` and reviewed via PLB-3d-02; it is soft severity and not a VER gate. CHK-3d-09 atomicity is HARD — VER-3d-15 gates it. ADVC-3d-02 interrogative-completeness is a soft advisory — it logs `interrogative_completeness_advisory` for PLB-3d-07 review and is not a VER gate, consistent with its generative-guidance nature.)

### 8.2 Plausibility checklist for Practitioner review

Realises Row 3 §8.2.

1. **PLB-3d-01 — Statement atomicity and non-redundancy.** One obligation per statement (sentence-level, CHK-3d-09) AND per concern (§5.4 concern-atomicity guidance; ADVC-3d-03 flags multi-concern spans). Near-duplicates are now prevented at authoring (§5.4 non-redundancy guidance); any not so prevented and not collapsed by CHK-3d-07 are flagged here. Review `concern_atomicity_flags` (ADVC-3d-03) — a requirement bundling distinct cross-column concerns it does not all voice should have been split.
2. **PLB-3d-02 — Row-appropriate abstraction.** Subject and vocabulary match the row. Review `subject_vocabulary_flags` (CHK-3d-08) — any Row 1 statement subjected to "the system" is an abstraction failure to correct. Implementation verbs (calculate, store, retain) at Row 1/2 are PLB failures.
3. **PLB-3d-03 — requirement_type plausibility.** Type matches source CCI columns. Review `requirement_type_distribution` for anomalies. Boundary-case type variance across runs is accepted (Tracker F81 related item).
4. **PLB-3d-04 — No inferred content (LPM).** No actor/behaviour/constraint absent from source CCIs; no verbatim CCI text.
5. **PLB-3d-05 — Measurement fit_criteria.** Every Measurement-verified Constraint carries meaningful `fit_criteria`; complete where `measurement_missing_fit_criteria` fired.
6. **PLB-3d-06 — Requirement-per-Domain balance.** Where `requirement_count_advisory` fired, review for over-decomposition (thin near-passthrough requirements) or genuine fan-out.
7. **PLB-3d-07 — `class_model` fidelity and `refinement_kind` soundness (F105).** Review `class_model_binding` — the structured model captures the entity the source intends (no coined/fragmented entities; key attributes present); the recorded `refinement_kind` matches the transformation actually performed (especially `decompose` — Task → Task + TaskCompletion — and `introduce` for parentless surrogates). Where `class_model_profile_advisory` or `class_model_statement_divergence` fired, confirm the row-profile fit and the prose projection. Structural validity is decidable (CHK-3d-11); this is the modelling judgement.

---

## 9. Test Fixtures

Seven fixtures in `tests/test_requirement_derivation.py`; AI stubs via monkeypatch (sibling §9 pattern). Realises Row 3 §9. Worked examples use the rows with production evidence (**PMT Row 1, NQPS Row 1**).

### 9.1 Fixture 1 — PMT Row 1: FirstRun happy path
**Test:** `test_pmt_row1_firstrun`. Setup: PMT Row 1 with Pass 3c Domains D001–D004 and their CCIs (18 CCIs). AI stub returns RequirementProposals per Domain.
**Assertions:** VER-3d-05 (all 18 CCIs covered); VER-3d-09; VER-3d-10 (each Requirement's `domain_refs` == source Domain); RequirementRegister populated.

### 9.2 Fixture 2 — NQPS Row 1: FirstRun constraint-heavy (and zero-CCI companion)
**Test:** `test_nqps_row1_firstrun`. Setup: NQPS Row 1 Domains D001–D006 + CCIs (34 CCIs, constraint-heavy).
**Assertions:** VER-3d-05; VER-3d-09 with Constraint present where warranted (type distribution not forced all-Functional); CHK-3d-08 clean (no "the system shall" at Row 1, including on the compliance Domain — the D005 case); optional fields omitted where content gives no natural value without that being a failure (the D005 verification_method/priority case). **Companion** (`test_nqps_row4_zero_cci`): NQPS Row 4 (zero CCIs) → `no_cci_input`, `PartialSuccess`, RequirementRegister preserves other-row members, Stage 2 not invoked.

### 9.3 Fixture 3 — PMT Row 1: IdempotentRerun
**Test:** `test_pmt_row1_idempotent_rerun`. Re-invoke Fixture 1 with identical CCI and Domain sets.
**Assertions:** VER-3d-11; `run_scenario=="IdempotentRerun"`; Stage 2 stub `assert_not_called()`; `requirement_input_hash` matches prior.

### 9.4 Fixture 4 — PMT Row 1: IncrementalRerun (one new CCI)
**Test:** `test_pmt_row1_incremental_rerun`. Run Fixture 1; add one CCI to an existing Domain (Domain set unchanged → Incremental reachable). Incremental stub returns one proposal.
**Assertions:** `run_scenario=="IncrementalRerun"`; VER-3d-05 after delta; existing `requirement_id`s preserved; prior AnalysisPass unchanged.

### 9.5 Fixture 5 — Non-Loss repair: orphaned CCI recovered
**Test:** `test_noloss_repair_prompt_recovery`. PMT Row 1 FirstRun; primary stub omits one CCI. CHK-3d-05 detects 1 orphan; repair stub covers it.
**Assertions:** `repair_prompt_issued==true`; `orphaned_ccis==[]`; VER-3d-05 passes; `execution_status=="Success"`; fingerprints include per-Domain entries plus `stage3_repair`.

### 9.6 Fixture 6 — Persistent orphan after repair failure
**Test:** `test_noloss_repair_persistent_orphan`. Primary stub omits one CCI; repair stub returns `[]`.
**Assertions:** `repair_prompt_issued==true`; `orphaned_ccis==[<ci_id>]`; `execution_status=="PartialSuccess"`; VER-3d-05 asserted to FAIL here (the orphan is recorded); Concern CN-NNN exists.

### 9.7 Fixture 7 — FullRerun forced by Domain-set change
**Test:** `test_pmt_row1_fullrerun`. Run Fixture 1; simulate a Pass 3c FullRerun retiring D001–D004 and committing D005–D008 over the same CCIs (Domain-id set changed → MD-3 forces FullRerun). Invoke Pass 3d.
**Assertions:** `run_scenario=="FullRerun"`; prior Requirements `retired_at IS NOT NULL`; new ids from next `R###` (no reuse); VER-3d-12; VER-3d-05 on new set; `domain_refs` reference new Domain-ids; `downstream_rerun_required` reflects Phase 5/6 presence. **(Issue 5)** a Structural variant: after a FullRerun of a parent row retires its Structural `class_model`s, assert the **next** row's CHK-3d-12 parent-element set **excludes** the retired parents' `class_model`s (only non-retired parents are coverage obligations) — `model_coverage` is computed against surviving parents only, and a retired parent's dropped element does NOT raise `chk3d12_model_element_extinct`.


### 9.8 Fixture 8 — PMT class_model chain + concept-coverage (R2→R5, Task lineage)
**Test:** `test_pmt_class_model_chain`. Setup: PMT Structural requirements over the `Task` lineage across rows 2–5; AI stubs return `RequirementProposal`s carrying `class_model`s (R2 `Task` existence+semantic-type → R3 `Task` + `TaskCompletion` (`refinement_kind=decompose`, logical types, business keys) → R4 +`completion_id` (`origin=introduced`, parentless), FK columns (`realise_relationship`), `monetary_value` snapshot → R5 precision/checks).
**Assertions:** VER-3d-26 (each `class_model` structurally valid; `class_model_binding.by_refinement_kind` populated); VER-3d-27 (`model_coverage.ratio==1.0`; the surrogate key exempt); the prose `statement` of each Structural is a faithful projection (§4.4.3c); a negative variant drops a conceptual attribute from the child → `chk3d12_model_element_extinct` + `model_coverage_gaps` entry.

### 9.9 Fixture 9 — object_refs materialisation + migration (Task.status.available)
**Test:** `test_object_refs_and_migration`. Setup: a behavioural (Functional) Requirement whose statement references status "available", and a committed `Task` `class_model` with `status` domain ⊇ {available}.
**Assertions:** the Requirement's `object_refs == ["Task.status.available"]` and resolves end-to-end (VER-3d-28); a companion Requirement referencing `Task.status.archived` (absent value) is recorded in `object_refs_binding.dangling` with `object_refs_dangling`, NOT rejected; `promote_dd_to_class_model` promotes the legacy DD `lifecycle_state` value-set into the `class_model` domain (de-duplicated against the Structural CHECK) and removes the DD value-set + relationship entries (DD retains name + synonyms only).

---

## 10. Edge Cases

Physical handling; logical disposition in Row 3 §10.

| Edge case | Handling |
|---|---|
| **Zero CCIs for the row** | Stage 1 early exit: `PartialSuccess`, `no_cci_input`; RequirementRegister = project-wide active set (not emptied). Stage 2 not invoked. (NQPS Row 4.) |
| **CCIs exist but zero active Domains** | §4.1 invariant guard → `Failed`. Unreachable given VER-3c-05; asserted. |
| **Single CCI in a Domain** | One-CCI Domain → AI returns ≥1 Requirement covering it. |
| **Domain yields zero Requirements** | CCIs become orphans → CHK-3d-05 repair. Repair fails → persistent orphan, Concern raised. |
| **cci_refs outside source Domain** | Stripped by CHK-3d-03; emptied proposal rejected; orphans → CHK-3d-05. |
| **Row 1 statement subjected to "the system"** | CHK-3d-08 logs `subject_vocabulary_mismatch` (soft); PLB-3d-02 review. Prevention is §5.4 Row 1 subject discipline. |
| **Measurement-verified Constraint without fit_criteria** | `measurement_missing_fit_criteria` (info); PLB-3d-05. |
| **fit_criteria present but empty** | Stripped (CHK-3d-04); `fit_criteria_empty_stripped`. |
| **Optional verification_method/priority omitted for abstract constraints** | Correct per §5.4(optional-field policy); not a failure. (NQPS D005.) |
| **Parse failure one Domain (others ok)** | Domain skipped; logged; its CCIs → CHK-3d-05. |
| **Parse failure all Domains after retry** | `Failed`. |
| **IncrementalRerun parse failure** | `incremental_fallback_to_fullrerun`; FullRerun path. If that also fails → `Failed`. |
| **Domain-id set changed since prior run** | FullRerun forced (MD-3) even if CCI set unchanged. |
| **FullRerun with Phase 5/6/8 complete** | `downstream_rerun_required=true`; not auto-triggered. |
| **Repair empty list** | Persistent orphan; `PartialSuccess`; Concern; surviving Requirements committed. |
| **FullRerun retirement rollback** | Single transaction → no partial retirement; pre-run state; `Failed`. |
| **RequirementRegister seed missing** | `Failed`, `failure_reason="RequirementRegister not found — migration may not have run"`. |
| **Large CCI set (>80 for row)** | `large_cci_set_advisory`; per-Domain processing proceeds; no chunking at v0.1. |
| **Structural proposal with no `class_model`** | Valid but un-promoted (migration residue) — runs the CHK-3d-09 prose-atomicity path; logged for review, not rejected. SHOULD carry one at rows 2–5 (VER-3d-26 `SHOULD`). |
| **`class_model` fails CHK-3d-11** (two PKs / dangling FK target / tier≠row) | Reject the Requirement (`class_model_invalid`); obligation re-covered via orphan/seed paths. |
| **Parentless physical introduction** (surrogate key, FK column, junction) | `refinement_kind=introduce` / attribute `origin=introduced` — exempt from CHK-3d-12 parent-coverage; NOT extinction. |
| **One conceptual entity → several physical** (Task → Task + TaskCompletion) | Expected; `refinement_kind=decompose`; coverage runs parent→child, not 1:1. |
| **Conceptual/logical parent element covered by no child** | CHK-3d-12 repair; persistent → `model_coverage_gaps` + `chk3d12_model_element_extinct` (hard). Never silently dropped. |
| **`object_refs` value absent from every defining `class_model` domain** | `object_refs_binding.dangling` + `object_refs_dangling` (Quality-pass finding); NOT a derivation reject (the defining Structural may be derived later). |
| **`class_model` on a behavioural Requirement / `object_refs` on a Structural** | DB CHECK + Pydantic validator reject; logged. |
| **DB lacks the `class_model`/`object_refs` columns** | `Failed`, `failure_reason="add_class_model_object_refs_columns migration not run"`. |

---

## 11. Cross-Mechanism Interactions

### 11.1 Upstream

| Mechanism | What this mechanism receives | Dependency type |
|---|---|---|
| **Pass 3c — Domain Derivation** | Domain entities (with `cell_content_item_refs`) — per-Domain derivation scope and basis for DM-derived `domain_refs`. | Hard — orchestrator checks Pass 3c `execution_status ∈ {Success, PartialSuccess}` (an IdempotentRerun satisfies if a prior Success exists). |
| **Pass 3b — CCI Construction** | CellContentItem rows — source content. | Transitive via Pass 3c; CCIs read directly for descriptions. |
| **Phase 2 — Mechanism Activation** | ProjectProfile — the two Pass 3d parameters. | Soft. |

### 11.2 Downstream

| Mechanism | What this mechanism produces | Dependency type |
|---|---|---|
| **Phase 5 — Cell Quality** | Requirement rows for quality assessment. | Analytical. |
| **Phase 6 / Phase 8 — Coverage** | Requirement rows (with `cci_refs`, `domain_refs`) as coverage inventory. | Analytical. |
| **Phase 10 — Gap/Question/Answer** | Populates `answer_refs`; may create Requirements via Answer resolution. | Writes `answer_refs`; not a Pass 3d concern at v0.1. |

### 11.3 Ledger coordination

Mechanisms coordinate via ledger reads, not direct calls (Row 4 Applied §4.11). Pass 3d reads CCIs and Domains; writes Requirements, RequirementRegister, AnalysisPass in one transaction. The orchestrator enforces sequencing by querying AnalysisPass records before invoking each mechanism. No mechanism imports another.

---

## 12. Build Notes

### 12.1 Tracker findings relevant to this build

| Finding | Status | Relevance |
|---|---|---|
| **F80** | Open | Consume Domains by `domain_id`, not name (MD-2). Derivation unaffected by cross-row name duplication. Presentation concern remains for review tooling. Stays Open. |
| **F81** | Open → Rows 1–2 validated, Rows 3–5 authored | REQUIREMENT_ROW_GUIDANCE["1"] and ["2"] validated; ["3"]–["5"] candidate, pending test; Row 6 stub. |
| **F105** | Realised (pending test) | `class_model` payload on Structural requirements: DDL column (§5.1), `ClassModel` Pydantic + proposal field (§5.2), §5.4 population-profile guidance, CHK-3d-11 structural validity + CHK-3d-12 concept-coverage (§4.3), §4.4.3c commit + projection, VER-3d-26/27, Fixture 8. Build order chain-together (MD-7). Validation: Pass 3d runs over the PMT Task lineage R2→R5. |
| **F107 / F107-T1(c,d)** | Realised (pending test) | §4.4.3a rewritten to names-only DD (relationship/value-record ops removed) + `object_refs` materialisation (step 4); `object_refs` DDL column; candidate `object_refs` proposal field; VER-3d-28; Fixture 9. The DD-mechanism half landed at Row 4 DD v0.2. (d) one-time `promote_dd_to_class_model` migration (§12.3). |

### 12.2 OQ resolutions committed at this spec

Resolving the open questions deferred by the Row 3 logical spec (Row 3 §12.2):

| OQ | Resolution |
|---|---|
| **OQ-3d-01** (re-run mechanics) | SHA-256 input hash: two-part at Row 1 (CCI-ids + active Domain-ids), **three-part at rows ≥ 2** (+ `||SEEDS:` sorted surviving row n−1 requirement-ids); `domain_id_set` stored separately for Domain-set comparison; a Domain-set change or any change in the row n−1 requirement set forces FullRerun (§4.1, MD-3). |
| **OQ-3d-02** (audit naming) | Adopt the sibling's `mechanism_data` convention (not `requirement_data`), matching Domain Derivation and the existing production run files (§7). |
| **OQ-3d-03** (CHK-3d-08 severity) | Soft at v0.1: log `subject_vocabulary_mismatch`, surface via PLB-3d-02, do not reject (§4.3 CHK-3d-08). Revisit when Row 1 production data accrues. |
| **OQ-3d-04** (retirement persistence) | Soft-retire via `retired_at` timestamp (not delete), consistent with sibling OQ-3c-03 (§4.4.4). |
| **OQ-3d-05** (id scale ceiling) | 999 ids per project incl. retired; raise a tracker finding for `R####` if a project exceeds 800 allocated (§5.3). |

### 12.3 One-time DD→`class_model` migration (F107-T1(d))

`promote_dd_to_class_model.py` runs once, after `add_class_model_object_refs_columns` and after the DD v0.2 schema migration (which drops the DD model columns), and before the first F105/F107 Pass 3d run. **For all current production data NO Structural Requirement has a `class_model` yet** (Issue 4), so there is nothing to promote *into* — the common case is therefore a clean strip, with the authoritative value domains preserved where they already live (the Structural requirement content, NOT the DD shadow copies — ledger F107 confirms the DD `lifecycle_state` set was an unreferenced, inconsistent shadow of the Structural CHECK). The steps:

1. **Non-Loss guard (loud, before deletion).** For each legacy DD value-set, assert its values are recoverable from a surviving requirement (the Structural CHECK domain / Constraint content that asserts them). Any value-set with **no** backing requirement is logged `orphan_value_set_on_migration {dd_id, attr, values}` for Practitioner review — recorded, never silently dropped (expected zero; the guard makes a real loss visible).
2. **Strip the DD.** Delete the `canonical` `attributes` arrays / value-sets and all `relationship` entries; the DD retains `name`, `description`, `provenance_ref`, `confidence`, and `synonym` entries only (ledger v2.17 / Row 4 DD v0.2). (The DD v0.2 schema migration drops the columns; this data migration clears the rows' model content first / asserts it empty.)
3. **Defer promotion to the first run.** The value-set→`class_model` `domain` promotion happens at the **first v0.30 Pass 3d run that derives the entity's Structural** — that run builds the `class_model` `domain` from the authoritative Structural requirement content (the prose value-list it asserts), de-duplicated against the Structural CHECK. No staging table is needed (the source is the Structural requirement, which survives the strip); the v0.29 staging machinery is **removed**.
4. **`object_refs` follow from derivation.** Behavioural `object_refs` are formed by §4.4.3a step 4 once the relevant `class_model`s exist; the migration establishes none directly (there is no `class_model` to resolve against yet). A reference whose value is not yet defined resolves later or is flagged dangling — never back-filled.

**Migration ordering (cross-spec).** The DD v0.2 schema migration drops the DD's `attributes`/value-set/relationship columns; this strip must run **before or together with** that drop. If the DD columns are already dropped when this runs, the DD model content is already gone — acceptable, since it was non-authoritative (the Structural content is the source); the guard in step 1 then operates on whatever DD content remains (possibly none). Idempotent and re-runnable. Pre-v2.17 residual DD model content reaching a post-migration run is treated as un-migrated, not authoritative.

### 12.4 v0.1 → v0.2 change detail

v0.1 was implemented and is the version behind the PMT Row 1 and NQPS Row 1 production runs reviewed during this design cycle. v0.2 does not change the implemented mechanism's runtime behaviour for the cases v0.1 already handled correctly; it re-frames the specification and adds the requirement-statement guidance and subject check that v0.1 lacked. Changes:

- **Re-framing (no behavioural change):** v0.1 was a standalone, row-agnostic physical spec naming the Pass 3c Domain Derivation spec as its authority. v0.2 establishes the Row 3 (logical) Requirement Derivation spec as the logical authority and the Row 4 Domain Derivation spec as the structural sibling, with section-level traces throughout. The four-stage flow, DDL, response schemas, and re-run mechanics are unchanged.
- **§5.4 REQUIREMENT_ROW_GUIDANCE (new):** v0.1 had a thin sketch of statement/type guidance. v0.2 introduces the full per-row guidance dict, distinct from the domain ROW_GUIDANCE (decision B), with Row 1 fully authored — carrying the statement-subject discipline ("The enterprise shall…", robust to compliance phrasing) that addresses the observed Row 1 subject leak (Tracker F81; NQPS Row 1 D005). This is the substantive behavioural addition: prompts built from v0.2 §5.4 will anchor the Row 1 subject where v0.1 did not.
- **CHK-3d-08 (new):** decidable row-subject check added to Stage 3, soft severity (records `subject_vocabulary_mismatch`, does not reject). No analogue in v0.1.
- **Optional-field policy (clarified):** §5.4 now states explicitly that `verification_method` and `priority` are populated when warranted and omitted otherwise — making the v0.1-observed ragged emission (NQPS D005) principled rather than accidental.
- **OQ resolutions (new):** §12.2 resolves OQ-3d-01..05 raised by the Row 3 logical spec — including adopting the `mechanism_data` audit naming (§7) that v0.1's implementation already emitted, now formally reconciled against the sibling convention.
- **Fixtures:** worked examples moved from PMT Row 2 / NQPS Row 3 (v0.1, illustrative) to PMT Row 1 / NQPS Row 1 (v0.2, the rows with production evidence), with Fixture 2 now explicitly exercising the D005 cases.

**Re-implementation impact:** the Row 1 statement-guidance and CHK-3d-08 are the parts requiring a code change from the v0.1 implementation. The rest is documentation re-framing. Re-running PMT Row 1 / NQPS Row 1 under v0.2 guidance is the validation step for the F81 Row 1 closure.

### 12.5 Replit Agent task structure

**Primary inputs:**
- This spec (Row 4 Requirement Derivation v0.30) — implementation authority (DDL §5.1, schemas §5.2, guidance §5.4)
- Row 3 Requirement Derivation v0.18 — logical authority (stage logic incl. §4.1.1(g) `class_model`, §5.5 `object_refs`, VER/PLB intent)
- Row 4 Domain Derivation v0.24 — structural sibling (four-stage pattern, audit/fingerprint conventions)
- Row 4 Understanding §14 — framework (module structure, ProjectProfile params, VER→pytest, fixtures)

**Reference:** Row 4 Applied v0.2; Canonical Ledger v2.13; Segmentation spec v9.2.

**Build sequence:**
1. Alembic migration `add_requirement_tables` — `requirement` table + RequirementRegister seed (DDL §5.1).
2. Alembic migration `add_requirement_profile_params` — two ProjectProfile columns (Understanding §14.2).
3. `prompts/requirement_row_guidance.py` — REQUIREMENT_ROW_GUIDANCE (§5.4): Row 1 full, Rows 2–6 stubs.
4. `schemas/` — three DISTINCT response schemas (§5.2).
5. `prompts/` — three prompt templates injecting `REQUIREMENT_ROW_GUIDANCE[row]`.
6. `stage1_preflight.py` → `stage4_entity_production.py` and `__init__.py`.
7. `tests/test_requirement_derivation.py` — Fixtures 1–7 (§9); AI stubs via monkeypatch.
8. Alembic migration `add_class_model_object_refs_columns` — `requirement.class_model` (JSONB NULL) + `object_refs` (JSONB NOT NULL '[]') with the two CHECK constraints (§5.1); `schemas/class_model_schema.py`; `core/class_model_validity.py` (CHK-3d-11), `core/class_model_coverage.py` (CHK-3d-12), `core/class_model_projection.py`, `core/object_refs_resolver.py`; §5.4 shared `class_model`/`object_refs` guidance; one-time `promote_dd_to_class_model` migration (§12.3).
9. Migrations; pytest; verify VER-3d-01..14 on Fixtures 1, 2, 3, 4, 7; Fixtures 5/6 against their specific assertions; **VER-3d-26/27/28 on Fixtures 8/9** (PMT Task lineage R2→R5 + object_refs/migration).

**Deviations from the Domain Derivation sibling to watch:**
- Stage 2 is a **per-Domain loop**, not a single whole-row call.
- `domain_refs` is **DM-derived in Stage 4**, never AI-proposed — response schema omits it.
- Re-run hash is **two-part at Row 1, three-part at rows ≥ 2** (adds `||SEEDS:` over the surviving row n−1 requirement-ids); a Domain-set change OR a change in the row n−1 requirement set forces FullRerun (MD-3).
- **CHK-3d-08** (subject vocabulary) has no sibling analogue — soft severity at v0.1.
- **REQUIREMENT_ROW_GUIDANCE** is a separate dict from the domain ROW_GUIDANCE (decision B) — do not merge them.
- No name-uniqueness merge (no CHK-3c-03 analogue); CHK-3d-07 collapses only exact statement+cci_refs duplicates.
- Non-Loss repair derives a **covering Requirement** (not a Domain), scoped to the orphan's owning Domain.

---

### 12.6 v0.2 → v0.3 change detail

v0.3 is a guidance-content addition only — no change to stages, schemas, DDL, audit structure, or re-run mechanics.

- **§5.4 REQUIREMENT_ROW_GUIDANCE["2"] (new):** the Row 2 stub is replaced with a full block, authored at business-owner abstraction with the same anatomy as Row 1 (statement subject / atomicity / vocabulary / type-reasoning / optional-field policy). Key Row 2 distinctions from Row 1: subject is "The business shall…" (or a named business role), not "The enterprise shall…"; statements are stateless business-capability obligations, not scope-level commitments and not workflows; the Functional/Constraint balance is expected to be more even than Row 1 (business capability declarations are genuinely Functional, business rules genuinely Constraint), with an explicit instruction not to carry the Row 1 Constraint lean into Row 2.
- **Row 1 guidance unchanged** and now carries its validation record (PMT Run 5 / NQPS Run 2).
- **Rows 3–6** remain short-phrase stubs.
- **No code-path change** beyond loading the expanded `REQUIREMENT_ROW_GUIDANCE["2"]` block — the prompt template already injects `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` for any row. Row 2 testing requires no mechanism change, only the guidance content added here plus Pass 3c Row 2 Domains in the ledger.

**Re-implementation impact:** update `prompts/requirement_row_guidance.py` with the Row 2 block; no other code change. The Row 2 validation step is a Pass 3d run against PMT Row 2 and NQPS Row 2 (both have Row 2 CCIs and Domains).

### 12.7 v0.3 → v0.4 change detail

v0.4 is a guidance-content addition only — no change to stages, schemas, DDL, audit structure, or re-run mechanics.

- **§5.4 REQUIREMENT_ROW_GUIDANCE["3"], ["4"], ["5"] (new):** the three stubs are replaced with full blocks, authored at logical-design (Row 3), physical-builder (Row 4), and detailed-implementation (Row 5) abstraction, each the requirement-statement analogue of the corresponding sibling domain ROW_GUIDANCE block. Key per-row distinctions: Row 3 is where "The system shall…" becomes correct but expressed *logically* (no technology names, no algorithms); Row 4 introduces named technologies/components and physical realisation; Row 5 introduces exact detail (formats, algorithms, values) and is where algorithmic/output verbs like "calculate"/"compute"/"format" become correct. Each block carries the standard anatomy (subject / atomicity / vocabulary / type-reasoning / optional-field policy) and explicit "what NOT to do" boundaries against the adjacent rows.
- **IMPORTANT — Rows 3–5 are candidate, not validated.** Rows 1–2 were validated before the next row was authored. Rows 3–5 were authored together, ahead of run evidence, to accelerate the remaining rows on the proven pattern. They MUST be confirmed by run evidence (per-row test against PMT and NQPS) before being treated as closed. This is a deliberate, recorded departure from the validate-then-author cadence.
- **Rows 1–2 unchanged**; Row 6 remains a short-phrase stub.
- **No code-path change** beyond loading the expanded `REQUIREMENT_ROW_GUIDANCE["3"]`–`["5"]` blocks — the prompt template already injects `REQUIREMENT_ROW_GUIDANCE[str(row_ref)]` for any row.

**Re-implementation impact:** update `prompts/requirement_row_guidance.py` with the three blocks; no other code change. Validation steps: Pass 3d runs against PMT Rows 3/4/5 and NQPS Rows 3/5 (NQPS Row 4 has zero CCIs → no_cci_input path, guidance not invoked).

### 12.8 v0.4 → v0.5 change detail

v0.5 is the Tier 2 reconciliation to the closed cross-row/structural design (findings F82–F93). It realises Row 3 Requirement Derivation v0.2 and ledger v2.13. Unlike v0.2–v0.4 (guidance-content additions), v0.5 changes **schema and validation**:

- **Ledger v2.13 schema reconciliation:** DDL `requirement_type` CHECK and Pydantic `Literal` collapsed to `Functional|Constraint|Structural` (F89); `verification_method` CHECK/Literal gains `Measurement`; new `refines_refs` JSONB column (F82), `NOT NULL DEFAULT '[]'`. Transcribed normative rules updated to v2.13 (refines_refs rule; Measurement-fit-criteria rule replacing the Performance one).
- **New hard check CHK-3d-09 (F88):** typed-slot atomicity, decidable, HARD-rejecting. Compound condition/object, multiple constraint rules, or a missing required slot for the type → reject; CCIs return to the orphan pool for CHK-3d-05 repair. Gated by VER-3d-15. This is the physical enforcement of the F88 hard-atomicity constraint that v0.4 carried only as soft guidance.
- **CHK-3d-08 severity unchanged (soft) but re-justified:** now soft because validated across Rows 1–3/5 (the §5.4 guidance holds subject discipline), not because evidence is pending.
- **§5.4 guidance type-vocabulary reconciled** in all five blocks: former Performance/Suitability/quality-attribute → Constraint (Measurement/Inspection-verified); composition/attribute/relationship → Structural.
- **§4.4.3 / response schema:** `refines_refs` is set at derivation for Path-R children (the seed); empty for Path-N row-native proposals (Matching-populated or upward gap, F85/F93).
- **VER-3d-15, VER-3d-16 added** (atomicity gate; refines_refs validity).

**Explicitly NOT in v0.5 (deferred to later authoring steps, per F93 sequence):**
- The full **F87/F88 interrogative-elaboration guidance** — CSPO slot-elicitation prompts and per-requirement interrogative completeness questions that expand §5.4. v0.5 reconciles the *type vocabulary* of the guidance blocks and adds the *atomicity check*, but does not yet rewrite the prompts to elicit slot-structured CSPO statements or to run the interrogative completeness sweep. That is the next guidance-authoring increment.
- The **Requirement Matching service** and **Data Dictionary service** internals (F85/F90) — declared as interfaces (refines_refs population, Object-slot binding) per Row 3 v0.2 §5.5; specified in their own service specs.

**Re-implementation impact:** Alembic migration to alter `requirement_type` CHECK, add `Measurement` to `verification_method` CHECK, add `refines_refs` JSONB column (existing rows default `[]`); implement CHK-3d-09 in `stage3_structural_validation.py`; update the three response schemas' type Literal; update `requirement_row_guidance.py` type-reasoning lines. Existing PMT/NQPS data migrates per ledger v2.13 Appendix D (Performance/Suitability→Constraint, Non-Functional→Structural).

### 12.9 v0.5 → v0.6 change detail

v0.6 adds the interrogative-elaboration guidance that v0.5 explicitly deferred (the §12.8 "Explicitly NOT in v0.5" item). It is **guidance + advisory only** — no schema, DDL, or hard-check change.

- **§5.4 shared interrogative-completeness guidance:** a preamble across all five row blocks instructing slot-filling-by-interrogation (type-required slots, with the Object-recursion that surfaces Structural requirements), making the row's set generatively complete and explicitly staying within the row (no cross-row parent invention — that is Matching/GQA).
- **ADVC-3d-02 (new, soft advisory):** flags thin type-required slots / un-interrogated Objects (`interrogative_completeness_advisory`, PLB-3d-07). Distinct from the HARD CHK-3d-09 atomicity reject. Soft because interrogative completeness is generative guidance; a hard completeness gate would wrongly reject legitimately-terminal requirements (e.g. an abstract Row 1 constraint).

**Re-implementation impact:** update `prompts/requirement_row_guidance.py` with the shared interrogative preamble (and per-row slot vocabulary); implement ADVC-3d-02 as a soft advisory in `stage3_structural_validation.py` (logging only, no reject). No migration, no schema change.

**Still NOT in v0.7 (deferred):** the Requirement Matching service internals remain its own spec (Row 3/4 Requirement Matching v0.2). **The Data Dictionary Object-slot binding is now active (§4.4.3a) — Pass 3d populates the DD; the DD service's internal resolution mechanics remain in the DD spec (Row 3/4 Data Dictionary v0.1).** The state-completeness capability (F91) remains deferred.

### 12.10 v0.28 → v0.29 change detail

v0.29 is the physical realisation of Row 3 Requirement Derivation **v0.18** (F105 + F107-T1(c,d)), against ledger v2.17. It changes **schema, validation, and Stage 4** — the largest increment since v0.5.

- **DDL (§5.1):** `requirement` gains `class_model` (JSONB NULL; CHECK Structural-only) and `object_refs` (JSONB NOT NULL `'[]'`; CHECK empty-unless-behavioural). Alembic `add_class_model_object_refs_columns`.
- **Response schema (§5.2):** `RequirementProposal` gains `class_model` (new `ClassModel` Pydantic mirroring the ledger `$def`; Structural only) and candidate `object_refs` (behavioural only); cross-field validators bind each to its `requirement_type`; `statement` becomes optional when a `class_model` is supplied (projected).
- **Stage 2 (§5.4):** a shared block instructs the IM to formulate a Structural *as* a `class_model` at the row's population profile and to record `refinement_kind`/attribute-`origin` at derivation, and to identify behavioural `object_refs` by name.
- **Stage 3 (§4.3):** **CHK-3d-11** (`class_model` structural validity, HARD, `core/class_model_validity.py` — a valid `class_model`-bearing Structural skips CHK-3d-09) and **CHK-3d-12** (concept-coverage refinement, `core/class_model_coverage.py`, run per adjacent parent→child row pair — chain-together).
- **Stage 4:** **§4.4.3c** commits the `class_model` and renders the prose projection (`core/class_model_projection.py`); **§4.4.3a** rewritten — the DD is names-only (relationship-record/value-record ops removed), and a new **step 4** materialises `object_refs` (`core/object_refs_resolver.py`), recording danglers for the Quality pass. **§4.4.3b** audit gains `class_model_binding` / `object_refs_binding` / `model_coverage[_gaps]` and `dd_binding` drops `relationships_recorded`/`values_recorded`.
- **One-time migration (§12.3):** `promote_dd_to_class_model` — DD value-sets → `class_model` domains (de-duplicated against the Structural CHECK), DD value-sets/relationships deleted, `object_refs` established.
- **VER-3d-26/27/28; PLB-3d-07; Fixtures 8/9;** new `execution_warnings` (`class_model_invalid`, `chk3d12_model_element_extinct`, `chk3d12_repair_*`, `object_refs_dangling`, soft `class_model_profile_advisory`/`class_model_statement_divergence`).

**Re-implementation impact:** the migration + two columns; the `ClassModel` schema and proposal fields; CHK-3d-11/12 in `stage3_structural_validation.py`; §4.4.3a step 4 + §4.4.3c in `stage4_entity_production.py`; the §5.4 shared block. **Status:** authored, pending test — validated against the PMT `Task` lineage (R2→R5) and the `Task.status.available` binding; chain-together build order (MD-7). No change to Path R/N derivation, the behavioural prose-atomicity machinery, seed coverage, or the subject check.

### 12.11 v0.29 → v0.30 change detail

v0.30 carries the six SW-agent spec-review resolutions; it adds no new mechanism beyond the corrections, and **touches no other spec** — ledger v2.17 and DD v0.2/v0.3 are unchanged (verified: the ledger `ClassModel` `$def` requires `entity_ref` only in the *committed* form, and `attributes` carries no `minItems`, so the ≥1-attribute floor is correctly a mechanism rule; DD v0.2/v0.3 already specify `resolve_object_ref` name-only and the dangling-`object_ref` Quality check). Realises Row 3 RD **v0.19** (the logical shadows of Issues 2/5/6 cascade there).

- **Issue 1 — `statement` type (§5.2).** `Optional[str]=None` on all three proposal classes + a `@model_validator` requiring `class_model is not None or statement.strip()`. The `str(minLength=1)`-plus-OPTIONAL form was unimplementable.
- **Issue 2 — `entity_ref` timing (§5.2, CHK-3d-11, §4.4.3a/c).** AI-facing `ClassModel.entity_ref` → `Optional`; the AI authors the entity **name**, §4.4.3a sets `entity_ref` from the resolved DD canonical (no DD-state prompt injection; a FirstRun DD is empty). **CHK-3d-11 split** structural (Stage 3) / referential (Stage 4).
- **Issue 3 — resolver ownership (§4.4.3a step 4).** `object_refs_resolver.py` calls `dd_service.resolve_object_ref()` for the name half (DD never touches `class_model`) and does the `.attr`/`.value` `class_model` query itself.
- **Issue 4 — migration scope (§12.3).** Common case is a clean strip (DD relationships + value-sets) leaving names + synonyms; promotion deferred to the first v0.30 run (authoritative source = Structural requirement content); staging removed; `orphan_value_set_on_migration` Non-Loss guard; cross-spec ordering note (strip before/with the DD column-drop).
- **Issue 5 — retired parents (CHK-3d-12, §9.7).** Parent-element set restricted to non-retired (surviving) parents; Fixture 7 asserts it.
- **Issue 6 — zero-attribute Row 2 (CHK-3d-11, §5.4).** Hard reject of a zero-attribute `class_model` (a name-only entity is a DD canonical, not a model); Row 2 requires ≥1 semantic-typed attribute, closing the CHK-3d-12 bypass.

**Re-implementation impact:** schema-level (`statement`/`entity_ref` Optional + validators), the CHK-3d-11 structural/referential split in `core/class_model_validity.py` + `stage4`, the `entity_ref`-set + `resolve_object_ref` call in §4.4.3a, the simplified `promote_dd_to_class_model`, the ≥1-attribute floor. No DDL change beyond v0.29; no ledger/DD change.

## Document End

End of SysEngage Row 4 Mechanism: Requirement Derivation v0.30. (v0.30: SW-agent spec-review resolutions (six issues) — Issue 1 `statement` Optional+validator (all three proposal classes); Issue 2 AI-facing `ClassModel.entity_ref` Optional + CHK-3d-11 split structural(Stage 3)/referential(Stage 4), `entity_ref` set from the DD in §4.4.3a (the AI authors the entity name, never a DD id); Issue 3 `object_refs_resolver` calls `dd_service.resolve_object_ref()` for the name half and queries `class_model` itself; Issue 4 migration simplified to a clean strip with deferred promotion + `orphan_value_set_on_migration` guard (staging removed); Issue 5 CHK-3d-12 parent set = non-retired parents (+Fixture 7 assertion); Issue 6 zero-attribute `class_model` hard-rejected, Row 2 needs ≥1 semantic-typed attribute. VER-3d-26 split; §12.11. Version-stamp quadruple swept. No ledger/DD-spec change. Realises Row 3 RD v0.19.) (v0.29: **F105** — structured data-model representation: the `requirement` table gains `class_model` (JSONB NULL, Structural) and `object_refs` (JSONB, behavioural) columns; `RequirementProposal` gains a `ClassModel` payload (Structural) and candidate `object_refs` (behavioural); Stage 2 formulates a Structural *as* a `class_model` at the row's population profile with `refinement_kind`/attribute-`origin` recorded at derivation; **CHK-3d-11** (structural validity, `core/class_model_validity.py` — a valid `class_model`-bearing Structural skips the CHK-3d-09 prose checks, the entity being the unit, D4) and **CHK-3d-12** (concept-coverage refinement, `core/class_model_coverage.py`, run per adjacent row pair — chain-together) added to Stage 3; §4.4.3c commits the `class_model` and renders the prose projection; **F107** — §4.4.3a rewritten to the names-only DD (relationship-record/value-record ops removed) plus a new step 4 materialising `object_refs` (name→DD canonical→`class_model` value, danglers recorded for the Quality pass); the one-time `promote_dd_to_class_model` migration. VER-3d-26/27/28; PLB-3d-07; Fixtures 8/9; `class_model_invalid`/`chk3d12_model_element_extinct`/`chk3d12_repair_performed`/`chk3d12_repair_failed`/`object_refs_dangling`. Version-stamp quadruple swept. Realises Row 3 RD v0.18 / ledger v2.17.) (v0.28: F106 — decompose executor discipline: `_parse_repair_response` made item-level resilient (a malformed child is logged `decompose_child_discarded` and discarded individually, never an all-or-nothing collapse — the F100/F101 swallow class again); decompose children inherit the parent's `cci_refs` by construction (repair schema drops `cci_refs` `minItems=1`, `confidence` Optional); the derivation-time two-step subsume-or-split test removed from the decompose prompt + a conjoined-predicate exemplar added, so the executor splits without re-deciding. VER-3d-25; `decompose_child_discarded`. Reframes F104(a) — R4_Run10's "retained" compounds ("retrieve and display tasks") were a decompose-mechanism failure, not un-splittability. Realises Row 3 RD v0.17.) (v0.27: F104(A) — `core/slots.py` detector precision: the hard branches split on "and" only, never disjunction ("or" in the predicate/object is a single-obligation choice — splitting inverts either→both, P1); the verb-on-both-sides test is scoped to the main predicate, exempting conjunctions inside a relative/subordinate clause (P2); the member-list carve-out covers operation/privilege lists (P3); temporal subordinators (prior to/before/after/then) are not conjunctions (P4); plus a `statement_preview` every-path sweep (F100 residual). VER-3d-24 asserts the four carve-outs do not hard-flag while a genuine conjoined predicate still does. Realises Row 3 RD v0.16; bounds *when* CHK-3d-09 fires — F98/F102/F103 unchanged. The structured data-model representation B item is split to F105.) (v0.26: F102 — retain-on-failure: a hard-rejected compound that cannot be decomposed is RETAINED in `surviving_09` (`chk3d09_decompose_failed_retained`), never dropped — the v0.25 build silently dropped it because orphan recovery doesn't fire when coarse CCIs are coincidentally covered (R5_Run12: 17+5 drops); VER-3d-22 extended from outcome-traced to obligation-present; the F100 `statement_preview` residual fixed on both emission sites; the "CHK-3d-05 carries the recovery" claim withdrawn. F103 — `core/slots.py` carves out inseparable member lists (enumeration value lists, column/attribute-definition lists — conjuncts are bare values/attribute-names under one enumeration/definition verb) before the compound-object hard branch, so they are logged-soft not hard-rejected. Realises Row 3 RD v0.15. Surfaced by R5_Run12 once F100 logging made decompose failures visible; F98/F99/F101 already validated at volume there.) (v0.25: F100 — CHK-3d-09 decompose-failure logging made per-invocation (not per-domain), audit invariant `|hard_reject| = |decompose_performed| + |decompose_failed|` per domain (VER-3d-22); F101 — Stage 4 DD-extraction batched and output-ceiling-bounded like Stage 2 Path-R (v0.19), truncation is a loud `dd_extraction_batch_truncated` hard failure with re-split (never a silent all-empty), `_parse_extraction_response` may not swallow a parse error, and the `extract_slot_terms` loop is guarded (`slot_parse_failed`); completeness invariant (requirement-level) `|reqs with ≥1 presented term| + |dd_zero_term| == row count` with `terms_presented == resolved + |dd_unresolved|` and no truncation (VER-3d-23, corrected on re-issue). Both surfaced validating F98/F99 on R3_Run7/Run8 + R5_Run11 — F98 validated (R5_Run11: 36 rejects / 30 decomposes), the DD-wipe was a 2048-ceiling truncation exposed by decompose enlarging the row, not a structural interaction. Physical-tier only; no Row 3 logical change.) (v0.24: F98 — CHK-3d-09 gains a conjoined-predicate hard branch in `core/slots.py` (verb on both sides of the conjunction), compound-object promoted from soft to hard, repair changed to automatic in-place decomposition with dependency carried as a Condition slot; F99 — §4.4.3a Constraint entity extraction from the Constraint-Rule not the Subject (`_extract_constraint_slots` + `_raw_slot_description` + `build_dd_extraction_prompt` redirect), `stmt[:60]` fallback removed → `dd_zero_term`, VER-3d-19 promoted from post-commit warn to pre-presentation reject; shared root — the slot machinery was Functional-Object-centric. Realises Row 3 RD v0.14. SW-agent-confirmed against R5_Run9.) (v0.23: SC-6 — §7 example places ai_model_fingerprints (and execution_warnings, concern_entities) at top-level outputs, siblings of mechanism_data, matching the implementation; example-structure fix.) (v0.22: §7 dd_binding example keys corrected to the canonical §4.4.3b / VER-3d-17 shape; example-key fix, no logic change.) (v0.21: five spec-silence points aligned to implementation — SC-1 any-domain IncrementalRerun fallback; SC-2/5 full IdempotentRerun mechanism_data sourced from prior pass; SC-3 downstream_rerun_required=false on IdempotentRerun; SC-4 repair AI-call output-budget table §4.3.) (v0.20: execution_status vocabulary standardised — Completed→Success, CompletedWithWarnings→PartialSuccess, Skipped retired (IdempotentRerun = Success + idempotent flag); Failed unchanged. Label rename, no logic change.) (v0.19: Path-R batching reconciled — token-ceiling-driven ≤15-seed batches, not one call; §7 audit example + warning types completed; version stamps swept. v0.18: Stage 4 connection-lifecycle conformance to Common Implementation Reference §1 — invalidate → refresh_engine_pool → fresh session across the IM boundary, validated PMT rows 1–5.)

Physical realisation of the Row 3 (logical) Requirement Derivation spec v0.7, against ledger v2.15. Reconciled type/atomicity/schema (v0.5) + interrogative elaboration (v0.6) + DD Object-slot binding (v0.7) + DD entity-reduction extraction (v0.8) + Row 2 subject taxonomy / boundary test (v0.9) + **Row 1 domain-entity vocabulary preservation (v0.10)**: §5.4 REQUIREMENT_ROW_GUIDANCE["1"] gains a source-entity-preservation rule — Row 1 abstraction lives in subject and verb, not in renaming domain entities; keep the source's domain nouns (task, reward, earnings), do not coin abstract paraphrases. Fixes the empty-Row-1-DD / zero-cross-row-recall failure at its root (entity-paraphrase left no entity to extract). The fix also removes the need for cross-abstraction DD synonymy: one entity, one name, all rows. §5.4 four-class Row 2 subjects; CHK-3d-08 widened taxonomy; CHK-3d-09 hard atomicity; ADVC-3d-02 advisory; DD binding §4.4.3a (entity reduction); VER-3d-17/18/19. `refines_refs` populated by Requirement Matching (Row 3/4 v0.3). F80 Open; F81 Open; F82/F87/F88/F89/F90 derivation portions realised here; Row 2 subject taxonomy realises R2-AMEND-9 / OD-R2-30.

Companion artefacts:
- SysEngage_Row_3_Mechanism_Requirement_Derivation_v0_7.md — logical authority (§4.1.1(c) domain-entity preservation; §4.1.1(a) subject taxonomy)
- SysEngage_Row_2_Understanding_v1_5.md §2.3.3 — subject taxonomy & boundary semantics
- SysEngage_Row_3_Mechanism_Data_Dictionary_v0_2.md / Row_4 v0.1 — the service §4.4.3a calls
- SysEngage_Row_3_Mechanism_Requirement_Matching_v0_3.md / Row_4 v0.3 — populates `refines_refs`; subject-class distinctness + empty-candidate-set corrections are the remaining Matching cascade items
- SysEngage_Row_4_Domain_Derivation_v0_24.md — structural sibling
- SysEngage_Issues_Tracker_v0_65.md — F80–F93 disposition
- sysengage_minimal_ledger_spec_v2_15.md — canonical schema authority
