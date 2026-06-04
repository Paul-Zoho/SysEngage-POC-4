# SysEngage Issues Tracker

**Version:** 0.65
**Date:** 03 June 2026
**Status:** Active

**Changes from v0.64 (bookkeeping — no new findings; Tier 4 dual-stream revert COMPLETE):** The dual-stream Pass-3a model is removed across the affected artefacts per finding F83 (and the F93 sequencing/scope ruling). Reverted to single-stream: **Row 3 Row-Lens Source Re-Analysis v0.3 → v0.4** (four-stage Domain-chunked dual-stream pass → two-stage single-stream: Source classification + contradiction sweep; ledger v2.12 → v2.13) and **Row 4 Row-Lens Source Re-Analysis v0.1 → v0.2** (physical: chunk-assembly/dedup/sweep modules, spaCy dependency, stream-2 fields, and the Row N-1 Phase 3d hard prerequisite all removed; two-stage realisation). Understandings (TARGETED revert — load-bearing dual-stream definitions corrected, RSSF-retirement annotations left intact as still-accurate): **Row 3 Understanding v1.1 → v1.2** (§3.9.3, §7.10, §8.5, §8.17 operationalisation, entity descriptions); **Row 1 Understanding v1.2 → v1.3** (§8.5 — the "upper-row signal feed" cross-row mechanism reversed, the other two mechanisms retained); **Row 2 Understanding v1.1 → v1.2** (two signal-feed references in §3.8/§3.9.3 corrected; §8.17/RSSF/ADR-GOV-012 content left as-is — separate RSSF lineage, outside F83 scope). F83 annotated below with realisation status. F35's dual-stream portion is now reversed in the artefacts (not just the tracker). F80–F93 substance unchanged.

**Changes from v0.63 (bookkeeping — no new findings; the requirements build is now spec-complete):** Tier 3 continued and the requirements-build mechanism set is complete. Authored this cycle: **Requirement Matching service** Row 3 logical v0.1 + Row 4 physical v0.1 (populates `refines_refs`; three-way refine-link/no-match/duplicate-merge; DD-anchored candidate pre-filter; bidirectional upward/downward gaps; F85/F82/F86/F84); the **interrogative-elaboration increment** into Requirement Derivation (Row 3 v0.2→**v0.3**, Row 4 v0.5→**v0.6**: §4.1.1(f)/§5.4 type-and-row-aware slot elicitation, ADVC-3d-02 soft completeness advisory; F87/F88 — completing the guidance v0.5 deferred); and **Phase 4 Requirement Quality Analysis** Row 3 logical v0.1 + Row 4 physical v0.1 (the INCOSE/ISO-29148 framework from `requirements_document_v6.docx`, reconciled to the F89 triad — Functional rules carried, Design-Constraint/Environmental/Performance-Suitability merged into Constraint with verification_method selecting which rules bite, Structural rules newly authored candidate; F88/F89/F90). **A filename-convention correction was applied:** the DD and Matching service specs were renamed to the standard `SysEngage_Row_<n>_Mechanism_<Name>` form (they had been authored with a non-conforming `SysEngage_Mechanism_..._Row<n>_<Tier>` name). F82/F87/F88/F89/F90 annotated with realisation status below; all stay Open until a production run exercises the built mechanisms. F80–F93 substance unchanged.

**Changes from v0.62 (bookkeeping — no new findings):** Tier 3 begun (Data Dictionary). The F90/F85 **representation open items are now closed by design decision** (recorded in the F90 annotation below): aliases stored ONLY as synonym entries (single source of truth, found by query); value-sets a field on the attribute with named-addressable values (not separate elements; state-model deferred F91); relationships as directed entries (from→to + cardinality); provenance a single `provenance_ref` pointer into existing traceability; alias-resolution gating = auto-resolve-with-register-review, confidence-banded, threshold a **fixed mechanism constant** (provisional, promotable to ProjectProfile when data exists); DD is a **standalone cross-row service** populated incrementally, not a numbered pass. Two artefacts authored: **ledger v2.13 → v2.14** (`DataDictionaryEntry` + `DataDictionaryRegister` element types, DD### prefix, no-row-context, JSON schema with entry_kind discriminator, migration notes) and the **Data Dictionary Service Row 3 logical mechanism spec v0.1** (resolve-and-record operations, the three-way resolution judgement, gating, inclusion rule, read operations). F90 annotated with realisation status (representation realised in v2.14; mechanism logical-specced; stays Open until the Row 4 physical spec is built and the service runs). F82/F88/F89 realisation annotations carried from v0.62. F80–F93 substance unchanged.

**Changes from v0.61 (carried, v0.62 — bookkeeping):** Tier 1 (ledger v2.13) and Tier 2 (Row 3 Requirement Derivation v0.2, Row 4 v0.5, Row 4 Understanding v0.27) complete; F82/F88/F89 annotated with ledger+schema realisation.

---

## Status Summary

| Status | Count | Finding IDs |
|---|---|---|
| Open | 35 | F1, F2, F4, F5, F6, F8, F9, F12, F13, F14, F15, F16, F17, F19, F20, F21, F22, F33, F34, F40, F41, F42, F80, F81, F82, F83, F84, F85, F87, F88, F89, F90, F91, F92, F93 |
| Action-Required | 4 | F43, F53, F66, F86 |
| Conditionally Resolved | 1 | F35 |
| Resolved | 45 | F3, F7, F10, F11, F18, F23–F32, F37, F44, F45–F79 |
| Noted | 1 | F74 |
| Deferred | 9 | F33, F34, F36, F38, F39, F62, F63, F64, F68 |
| Wont-Fix | 0 | — |

**Total findings:** 93 (F1–F93)

---

## Active Findings — New in v0.51

### F78 — Nuanced "and"/"&" Test Replaces Blunt Prohibition → Mechanism Spec v0.24

**Status:** Resolved (26 May 2026, v0.50 cycle)
**Surfaced by:** NQPS Run 4 D005 "Regulatory and Social Responsibility" — correct grouping, blunt prohibition would have forced an incorrect split
**Category:** Prompt Quality / Spec Design

**Description:** The blunt prohibition ("if you need 'and', create two domains") was challenged by NQPS R4 D005. The six underlying CCIs (regulatory compliance management, commitment to regulatory compliance, social responsibility, environmental responsibility, charitable responsibility, legislative compliance) represent a single enterprise concern — the enterprise's accountability to the external world. A better name is "Corporate Responsibility Governance": one concept, no "and". The blunt prohibition would have forced a split into two thin domains where one rich domain is analytically correct.

The distinction is between two failure modes:
- **Case A — Grouping failure:** "Task Entitlement and Accountability" — two distinct concerns (specification vs. completion) that fail differently. Correct response: split.
- **Case B — Naming precision failure:** "Regulatory and Social Responsibility" — one enterprise concern named via its two sub-themes. Correct response: find the single-concept name.

**Resolution:** Blunt prohibition replaced with a two-step "and" test in all row guidance blocks (Rows 1–5):
1. Is there a single concept that encompasses both sub-themes without 'and'? If yes, use it.
2. If no single concept exists, the domain has two distinct concerns — create two domains.

Row 1 previously had no "and" guidance at all. Added "and" test block to Row 1 prohibition rules. Evidence: PMT R11 D003 "Earnings Transparency and Stewardship"; NQPS R4 D005 "Regulatory and Social Responsibility".

---

### F79 — Repair Prompt Naming Prohibition + Row 2 "Retention" Vocabulary → Mechanism Spec v0.24

**Status:** Resolved (26 May 2026, v0.50 cycle)
**Surfaced by:** PMT Run 11 Row 3: D011 "Earnings Derivation and Aggregation Logic" and D013 "Task Availability and Persistence Model" — "and" names produced by CHK-3c-08 split repair; PMT Run 11 D009 "Historical Record Retention" — "retention" vocabulary at Row 2
**Category:** Spec Gap / Prompt Quality

**Finding 1 — Repair prompt naming gap:** CHK-3c-08 split and CHK-3c-07 absorption repair prompts received ROW_GUIDANCE as context but did not have the "and" test explicitly stated as a naming requirement for their outputs. The primary grouping prompt correctly applied the prohibition (Row 2 and Row 3 primary outputs had no "and" names). The repair prompts produced "and" names because their task framing (absorb / split CCIs) did not include an explicit naming constraint. ROW_GUIDANCE injection alone is insufficient when the repair task framing can override it.

**Resolution:** §4.3 CHK-3c-07 and CHK-3c-08 now specify that their respective repair prompt templates MUST include an explicit naming prohibition statement. For CHK-3c-07: "Any new domain names must not use 'and'/'&' without first confirming no single concept covers both sub-themes." For CHK-3c-08: "Each split domain name must not be compound — find the single concept that unifies the sub-theme's CCIs."

**Finding 2 — Row 2 "retention" vocabulary:** PMT R11 D009 "Historical Record Retention" — "retention" is data storage vocabulary (Row 3/4 level). At Row 2 the business concern is stewardship of historical records, not technical retention. "Retention" added to the Row 2 vocabulary avoid list alongside "retrieve", "store", etc. Recommended alternatives: "stewardship", "record", "accountability".

---


---

## Active Findings — New in v0.51

### F80 — Cross-Row Domain Name Duplication — Pending Decision

**Status:** Open
**Surfaced by:** NQPS Run 6 — D001 "Quality Governance" (Row 1, 7 refs) and D007 "Quality Governance" (Row 2, 11 refs) — identical names at different rows within the same project
**Category:** Analytical Quality / Pending Design Decision

**Description:** Pass 3c Row 1 and Row 2 both produced a domain named "Quality Governance" for the NQPS project. The two domains are distinct ledger entities — different `domain_id` values (D001 vs D007), different `row_target` values (1 vs 2), different `cell_content_item_refs` arrays. They are not shared or linked. CHK-3c-03 (duplicate domain name merge) only operates within a single row's proposal set — it does not check across rows.

**Why this may not be an issue:** Domains are row-scoped entities. The name "Quality Governance" at Row 1 (Planner/Contextual) and at Row 2 (Owner/Business) describes two different levels of the same architectural concern — much like two streets in different cities sharing a name. The `domain_id` is the authoritative unique identifier; name is a human-readable label. If downstream phases (Phase 3d Requirement Derivation, Phase 6/8 Coverage Analysis) consume domains by `domain_id` rather than by `name`, the duplication is harmless.

**Why this may be an issue:** If Phase 3d allocates requirements to domains and presents them by name, two "Quality Governance" entries in the same project ledger will create practitioner confusion at review time. If Phase 6/8 aggregates or reports by domain name, the two entries may be collapsed or mis-attributed. The practitioner experience of reading a ledger with duplicate domain names across rows is ambiguous.

**Pending decision:** Resolution depends on how Phase 3d and Phase 6/8 consume domain entities. Specifically:
- Does Phase 3d require domain names to be unique within a project (across all rows), or is `domain_id` the key?
- Does Phase 6/8 reporting group or filter by domain name?

**If the decision is "names must be unique across rows":** PLB-3c-01 should be extended to flag cross-row name duplication, and the ROW_GUIDANCE blocks should advise the AI to include a row-level qualifier when the name would otherwise be shared (e.g. "Enterprise Quality Governance" at Row 1, "Business Quality Governance" at Row 2). No automated check is needed — this is a Practitioner review concern.

**If the decision is "names need not be unique across rows":** No action needed. F80 closed as Wont-Fix.

**Cross-references:** PMT Run 12 / NQPS Run 6 production review; PLB-3c-01 (domain name quality)

**v0.53 update (Pass 3d disposition):** The Pass 3d mechanism (Row 3 Requirement Derivation v0.1 / Row 4 v0.2) consumes Domains by `domain_id`, never by `name` (Row 4 §4.4.2, MD-2). Cross-row Domain name duplication is therefore confirmed harmless to requirement derivation — validated in production: NQPS Run 2 derived requirements against D001 "Quality Governance" with no name-based ambiguity. The derivation half of F80 is closed. The residual presentation/reporting half — whether Phase 6/8 reporting or Practitioner review tooling requires cross-row name uniqueness — is untouched by Pass 3d and remains the open question. F80 stays **Open**, scoped now to the downstream presentation concern only.

### F81 — Requirement-Statement Guidance Does Not Yet Exist (REQUIREMENT_ROW_GUIDANCE) — Pending Mechanism Creation

**Status:** Open
**Surfaced by:** Phase 3d design review. PMT Row 1 Run 1 (NQPS Row 1 Run 1, D005 "Regulatory Obligation"): five of six Row 1 domains produced requirement statements correctly subjected to "The enterprise shall…"; D005 alone slipped to "The system shall comply…" — Row 2+ subject vocabulary at Row 1. The same call also omitted `verification_method` and `priority`. D005's CCI membership is the most abstract/constraint-heavy in the project (five Why-column Constraint CCIs), which appears to have pulled the statement into conventional system-requirements boilerplate.
**Category:** Analytical Quality / Prompt Specification Gap

**Description:** Requirement Derivation currently has no dedicated requirement-statement guidance. The Pass 3c `ROW_GUIDANCE` blocks were authored for **domain naming and grouping** — every instruction in them is framed around what a domain *represents* and how it should be *named* (e.g. "A Row 1 domain SHOULD be nameable to a non-technical executive"; "Row 1 domain names use nouns of enterprise concern"). None of it specifies the surface form a requirement *statement* must take: its subject ("The enterprise shall…" at Row 1), its normative verb discipline, atomicity, or the row-appropriate vocabulary re-expressed for statements rather than names. When the Phase 3d derivation prompt inherits a domain-naming block to produce requirements, the abstraction *concept* transfers but the statement *form* is unspecified — so where a strong competing lexical prior exists (compliance/legislative phrasing → "the system shall comply"), the statement drifts because there is no explicit anchor to hold it.

**Why this may not require separate action:** The forthcoming Row 3 (logical) and Row 4 (physical) Requirement Derivation mechanisms will, by design (decision B), carry a dedicated `REQUIREMENT_ROW_GUIDANCE` distinct from the domain `ROW_GUIDANCE`. If that guidance is authored correctly — explicit requirement-subject form per row, normative verb discipline, statement-level vocabulary, robust to compliance/constraint phrasing — the gap closes as a natural part of writing those mechanisms, and no separate remediation is needed. This finding exists to ensure that requirement is not lost between the logical and physical specs.

**What the guidance must contain (when written):**
- Per-row requirement-statement **subject** (Row 1: "The enterprise shall…"; explicitly NOT "The system shall…", and explicitly robust to compliance/legislative content — "The enterprise shall comply…", never "The system shall comply…"). Lower rows take their row-appropriate subject.
- Normative verb discipline and **atomicity** (one obligation per statement; compound "and"/"," obligations split — the requirement-level analogue of the F78 domain-naming "and" test).
- Statement-level vocabulary avoid-list re-expressed for statements (the domain-naming avoid-list — calculate, display, track, store, retrieve, retain — applies to statement verbs too at the higher rows).
- **Optional-field emission policy** — `verification_method` and `priority` populated when the content warrants and omitted otherwise (the "populate-when-warranted" discipline `fit_criteria` already follows correctly), rather than left as silent discretionary optionals. NQPS D005 omitting both fields where four Why-column constraints gave no natural verification method is *content-rational omission*; the policy should make that behaviour explicit rather than producing ragged output by accident. (Note: `priority` was uniformly "High" across all populated PMT/NQPS Row 1 requirements — its value as a discriminating signal is itself questionable; whether to elicit it deliberately or leave it for Practitioner assignment is an open sub-question for the guidance author.)

**Deterministic backstop (optional, for the physical/Row 4 spec):** A row-subject-vocabulary check (e.g. flag any Row 1 statement whose subject is not the enterprise) is fully decidable and would catch a drift like D005 before it reaches downstream, regardless of whether the prompt holds. This is a genuine CHK (decidable), not a PLB — recommend considering it when the Row 4 physical spec is written. The prompt fix is primary; the check is the safety net.

**Related (logged separately in spirit, not yet a numbered finding):** `requirement_type` classification variance across identical-input PMT Row 1 runs (4 Constraint then all-Functional). NQPS Row 1 classified Constraint readily (16/26) where the source warranted it, indicating no systemic suppression — the variance is concentrated on genuinely ambiguous boundary obligations. Parked for review once more projects have run through the system; not actioned now.

**Cross-references:** PMT Ph03 3d Requirement Derivation Row 1 Runs 1–4; NQPS Ph03 3d Requirement Derivation Row 1 Run 1; decision B (separate `REQUIREMENT_ROW_GUIDANCE`); F78 (domain-naming "and" test — statement-level analogue); Pass 3c `ROW_GUIDANCE` §5.4 (the domain-naming blocks this finding distinguishes requirement guidance from)

**v0.53 update — Row 1 portion VALIDATED.** The guidance was authored (Row 3 Requirement Derivation v0.1 §4.1.1 logical; Row 4 v0.2 §5.4 REQUIREMENT_ROW_GUIDANCE["1"] physical, full block) and the decidable backstop implemented (Row 4 §4.3 CHK-3d-08, soft severity). Re-implemented and re-run: **PMT Row 1 Run 5, NQPS Row 1 Run 2.** Evidence:
- **Subject discipline holds 100%** — 33/33 statements subjected to "the enterprise" across both runs. The exact v0.1 failure case is fixed: NQPS D005 now reads "The enterprise shall comply with applicable legislative obligations" (R016) where v0.1 produced "The system shall comply…". `subject_vocabulary_flags` empty in both runs (CHK-3d-08 fired, found nothing — prompt held, backstop not needed).
- **Optional-field policy now principled** — D005 (the v0.1 ragged case) shows verification_method/priority populated on the four verifiable obligations (R016–R019, Inspection/High-Medium) and correctly omitted on the one abstract obligation (R020, charitable responsibility). The "populate-when-warranted, omit otherwise" §5.4(e) policy operates as designed; no longer ragged-by-accident.
- **Entity completeness, Non-Loss, mechanism_data naming** all confirmed (18/18 and 34/34 CCIs covered, zero orphans; `mechanism_data` audit key per OQ-3d-02).

**Disposition:** F81 **Row 1 portion is validated and closed**. F81 remains **Open** overall, scoped now to Rows 2–6 — whose REQUIREMENT_ROW_GUIDANCE blocks are short-phrase stubs pending their own validation cycles (Row 2 authored in Mechanism Spec v0.3; Rows 3–6 pending). F81 closes fully when all rows in scope are authored and validated.

**New observation (type-distribution swing under v0.2) — added to the parked type-variance item.** Under v0.2 guidance, requirement_type swung markedly toward Constraint on both projects: PMT Row 1 8 Constraint + 2 Functional (was mostly/all Functional under v0.1); NQPS Row 1 20 Constraint + 3 Functional (was 16C+10F). Likely the §5.4(d) "Why/commitment → lean Constraint" cue interacting with Row 1's enterprise-commitment framing. Cannot determine from two runs whether this is more-correct (Row 1 obligations *are* largely constraints) or over-correction (capability statements mis-typed Constraint). Consistent with the accepted-non-determinism stance: parked for review with more project evidence, alongside the original v0.1 variance observation. Not actioned.

**v0.54 update — Row 2 portion VALIDATED; Rows 3–5 authored ahead of test.** Row 2 guidance (Mechanism Spec v0.3 §5.4 REQUIREMENT_ROW_GUIDANCE["2"]) re-run: **PMT Row 2 Run 1, NQPS Row 2 Run 1.** Evidence:
- **Subject discipline 100%** — 40/40 statements subjected to "the business" (36) or a named business role (4: "The Parent user…", "The child user…", "The parent user…", "Leadership shall…"). The named-role allowance (§5.4(a) Row 2) was used correctly and sparingly — WHO-column accountable actors framed with business-responsibility verbs. Zero "the enterprise" (Row 1) and zero "the system" (Row 3+) leaks. `subject_vocabulary_flags` empty.
- **Type balance Functional-dominant** (PMT 9F+3C, NQPS 20F+8C) — the explicit §5.4(d) Row 2 instruction "do not carry the Row 1 Constraint lean into Row 2; business capability declarations are genuinely Functional" held. The split is defensible on inspection ("maintain a record" / "account for" → Functional; "enforce that…" → Constraint).
- **Vocabulary clean** — zero implementation-verb leaks (calculate/store/retrieve/track/retain/compute/aggregate/display/generate) in either run.
- **Non-Loss, row_target, entity completeness** all confirmed (22/22 and 35/35 CCIs covered, zero orphans; all entities row_target="2"; required attrs complete; `mechanism_data` audit key).

**Type-variance evidence (added to the parked item).** The Row 2 Functional-dominant result is the *inverse* of the Row 1 Constraint swing, and it followed a deliberate guidance instruction. This is positive evidence that requirement_type classification **responds to row-level guidance** rather than being globally biased or random — which makes the parked type-variance question more tractable when revisited across more projects. Still parked; not actioned.

**Rows 3–5 authored ahead of test (Mechanism Spec v0.4).** REQUIREMENT_ROW_GUIDANCE["3"], ["4"], ["5"] authored at logical-design, physical-builder, and detailed-implementation abstraction respectively, each as the requirement-statement analogue of the corresponding sibling domain ROW_GUIDANCE block. **These are candidate guidance, NOT validated** — authored ahead of run evidence to enable Rows 3–5 testing, a deliberate (and noted) departure from the validate-then-author cadence used for Rows 1–2. They must be treated as pending test, not closed.

**Disposition:** F81 **Row 1 and Row 2 portions validated and closed.** F81 remains **Open**, scoped now to: **Rows 3–5** (authored in v0.4, pending test) and **Row 6** (short-phrase stub, pending authoring). F81 closes fully when Rows 3–5 are validated and Row 6 is dispositioned.

**v0.55 update — Rows 3 and 5 VALIDATED; Row 4 lightly exercised; F81 held Open pending more evidence.** Full Rows 1–5 runs (PMT AllRows Run 1: 41 requirements R001–R041 across Rows 1–5; NQPS AllRows Run 1: 53 requirements R001–R053 across Rows 1, 2, 3, 5 — Row 4 zero CCIs). Evidence:
- **Row 3 — validated.** All statements subjected to "The system", expressed *logically*: zero technology/code/algorithm vocabulary leaks (scan for postgres/react/aws/ios/android/api/endpoint/schema/table/class/function/module/calculate/compute/format returned nothing). The §5.4 Row 3 boundary ("system expressed logically, no tech names, no algorithms") held. Type balance mixed and sensible (PMT 4F+2C, NQPS 2F+2C).
- **Row 5 — validated.** Subject discipline holds, including the named-component/interface allowance: "The child user interface shall provide UI components…" is a correct Row 5 *named-interface* subject, correctly distinct from the Row 2 "the child user shall…" *business-actor* subject. The §5.4 Row 5 distinction between interface-as-component (Row 5) and actor (Row 2) is observed. Row 5 detail-level verbs and field enumerations appear (appropriate at this row). Type Functional-dominant (PMT 12F; NQPS 2F+1C) — defensible, as PMT Row 5 content is capability/UI-heavy.
- **Row 4 — validated only on the cases present, NOT richly exercised.** PMT Row 4 = a single CCI → single Constraint requirement ("The system shall…"), the sparse-row case the guidance anticipates. NQPS Row 4 = zero CCIs → `no_cci_input` path (guidance not invoked). Neither reference project has a multi-CCI physical Row 4, so the Row 4 block is confirmed for the single-CCI and zero-CCI cases but not stress-tested against rich physical content. **This is the specific gap keeping the Rows 3–5 validation incomplete.**
- **Integrity flawless across all nine row-instances, both projects:** Non-Loss 100% every row (PMT 18/18, 22/22, 6/6, 1/1, 9/9; NQPS 34/34, 35/35, 3/3, 3/3 — zero orphans); zero incomplete entities; zero domain_ref row-mismatches; all requirement_ids valid R### and globally sequential (R001–R041, R001–R053); no regression on the validated Rows 1–2.

**Disposition (per decision — F81 held Open pending more evidence):** Rows 1, 2, 3, 5 are validated. Row 4 is validated only on single-CCI/zero-CCI cases and needs a **physical-content-rich project** to be considered fully validated. Row 6 has **no operational CCIs in either reference project** and remains entirely unexercised (its v0.4 short-phrase stub has never been invoked). F81 is **NOT closed** — it is held Open until: (a) a project with rich Row 4 physical content confirms the Row 4 guidance, and (b) a project with Row 6 operational content allows the Row 6 block to be authored and validated (or a documented decision is taken that no such content will arise). Closing F81 now would close on absence of evidence rather than evidence.

**Type-variance evidence (added to the parked item).** Across the full Rows 1–5 sweep, the type distribution tracks row guidance consistently: Row 1 Constraint-leaning (PMT 6C+4F, NQPS 17C+4F+1P), Row 2 Functional-leaning (PMT 8F+4C, NQPS 14F+10C), Rows 3–5 mixed-to-Functional. The pattern continues to support the reading that classification responds to per-row guidance rather than being globally biased. Still parked; not actioned.

**Checker note (no action):** an automated subject-vocabulary scan during this review produced false positives at Row 2 (R019 "The parent shall…", a valid named-business-role subject) and Row 5 (named-interface subjects). These were artifacts of a crude opener-pattern check, not defects in the output; the mechanism's own CHK-3d-08 `subject_vocabulary_flags` were empty. Recorded so the false positives are not mistaken for findings.

## Active Findings — New in v0.56

### F82 — Cross-Row Requirement «refine» Relationship Missing from Ledger Requirement Payload

**Status:** Open — **ledger portion REALISED in v2.13** (`refines_refs` optional array on Requirement, many-to-many, empty-permitted, parent at row n−1; prose + normative rule + JSON schema). Schema also realised in Row 4 Requirement Derivation v0.5 (JSONB column, set empty at construction). Stays Open: the field is *populated* by the Requirement Matching service (F85/F93), which is not yet built — `refines_refs` is empty as produced by Pass 3d until Matching runs.
**Surfaced by:** Phase 3d → later-phase design discussion. Phase 4 (Requirement Quality Analysis) scores "where higher-level requirements are demonstrably satisfied by linked lower-level requirements" — i.e. it depends on a persisted Req(n-1)↔Req(n) relationship. The ledger v2.12 Requirement payload carries `cci_refs` and `domain_refs` but **no requirement-to-requirement reference**.
**Category:** Ledger Schema / Architecture

**Description.** A row n requirement that is a more-detailed expression of a row n-1 requirement stands in a UML «refine» relationship to it (client = the more-refined R(n), supplier = the more-abstract R(n-1); the dependency points from child up to parent). This relationship is the substrate Phase 4 quality scoring consumes and the spine of top-down traceability across the Zachman rows. The ledger has no field for it. The absence is the schema fingerprint of the original **req → source → cci → req** plan (F83): under that plan cross-row influence travelled through the shared source/cci provenance, so a direct requirement-to-requirement edge was never needed.

**Decision.** Add a `refines_refs` array to the Requirement payload, carried on the **child** R(n), pointing up to the R(n-1) it refines. Semantics: UML «refine» (change of abstraction level — same intent, more detail), NOT «satisfy» (which is design-element-to-requirement and the wrong stereotype here). Cardinality **many-to-many**, expected in both directions (one parent → many children on decomposition; many parents → one child for cross-cutting requirements). **Empty is permitted at every row** (see F84). Requires canonical ledger spec **v2.12 → v2.13**. Human-supplied vs system-generated provenance of the link is already answerable from existing ledger element-relationship traceability — no extra provenance field needed.

**Cross-references:** F83, F84, F85, F86; Phase 4 (Requirement Quality Analysis, main process flow §Phase 4); Row 3 Understanding §1.3 ("Row 3 Requirements are refinements of Row 2 Requirements"), §8.5.

### F83 — Dual-Stream / Pass-3a Requirement Injection Model Rejected — Separate Matching Pass Adopted

**Status:** Open — **REALISED in the artefacts (Tier 4 revert complete).** The dual-stream model is removed: Row 3 Reanalysis v0.4 + Row 4 Reanalysis v0.2 are single-stream; Row 3 Understanding v1.2, Row 1 Understanding v1.3, Row 2 Understanding v1.2 have their load-bearing dual-stream definitions corrected. The replacement mechanism (separate Matching pass establishing `refines_refs`) is specced (Requirement Matching service Row 3/4 v0.1, F85) and the schema landed (refines_refs, ledger v2.13, F82). Stays Open until a production run exercises the single-stream Reanalysis + Matching end-to-end (specced, not yet run).
**Surfaced by:** Design challenge to the inherited POC architecture.
**Category:** Architecture / Methodology (reverses a prior Practitioner-locked decision)

**Description.** The inherited design (dual-stream model, F35 resolution, Practitioner-locked) injected Req(n-1) as a second input stream into **Pass 3a (Row Lens Source Reanalysis)** of row n. Tracing a requirement through the pass chain (3a reanalysis → Signals → 3b CCIs → 3c Domains → 3d Requirements) shows the requirement is **atomised** — fragmented into signals, redistributed across cells and domains, and fused with source-derived content — so that **no requirement-level thread survives** to form the Req(n-1)↔Req(n) link. 3a injection therefore destroys the very relationship Phase 4 needs. Further: per Practitioner, **Pass 3a's role is to faithfully capture that row's sources** — not to enrich or gap-fill against upper-row intent — so injecting non-source material into 3a would contaminate a faithful source capture. Gap-finding against the dataset is owned by robustness analysis, not 3a.

**Decision.**
1. **Pass 3a stays single-stream** (faithful source capture). The dual-stream model as a *Pass 3a mechanism* is **rejected** — this reverses the F35 dual-stream decision (Practitioner-locked); the reversal is deliberate and recorded here. The Row 1/2/3 Understanding documents describing dual-stream at Pass 3a will need amendment notes.
2. **The single-stream-first build order was correct and deliberate** — Req(n-1) could not be injected/matched until Pass 3d existed to *produce* requirements. Reaching validated Pass 3d across Rows 1–3, 5 is precisely the precondition that unblocks cross-row matching. No divergence from plan; the planned next step is now reachable.
3. The Req(n-1)↔Req(n) relationship is established by a **separate matching pass** (F85), not by injection into the downward pipeline.

**Cross-references:** F35 (dual-stream resolution — reversed by this finding); F82, F84, F85; Row 3 Understanding §8.5 (dual-stream / RowLensSourceReanalysis), §3.8.2.

### F84 — Unparented Row n Requirements Are Expected; Gap Closure via Existing Gap→Question→Answer Mechanism

**Status:** Open
**Surfaced by:** Design discussion on novel requirements and abstraction-level gaps.
**Category:** Architecture / Methodology

**Description.** Human input arrives at inconsistent abstraction levels — rich detail where the author knows/cares, vague high-level statements (or silence) elsewhere. Consequently a row n requirement legitimately **appears with no row n-1 parent** (`refines_refs` empty) — the author supplied detail without the higher-level framing. This is **expected, initially.** A novel R(n) implies a **missing R(n-1)**; that missing parent is a gap to be closed, and once closed and transformed back down it surfaces **further** gaps (e.g. an author specifies "Turn On" in detail; the reverse-derived parent "power-state control", transformed back down, demands "Turn Off" — a sibling gap invisible at row n until the parent existed). The system's purpose is to converge ragged multi-level input toward consistent abstraction coverage at every level.

**Decision.** Gap closure is **NOT a new mechanism.** It is performed by the **existing gap → question → answer (robustness analysis / iteration cycle) mechanism**: an unparented requirement is a gap; the GQA flow can answer "yes, a higher-level requirement should exist here", **generate the R(n-1)**, and **drive it back down through the normal pipeline**. The re-descent reconnects parent to child (via the matching pass, F85), making the parent "real" for the child and populating `refines_refs`. Termination, convergence, propose-vs-auto-create, and Practitioner gating are all governed by the **existing** GQA / Phase 10 iteration-cycle machinery — no new convergence engine is designed. The "only initially" matters: at first ingest there are many unparented requirements and abstraction gaps; the lift-and-re-descend cycle drives the count toward zero.

**Cross-references:** F82, F85, F86; gap → question → answer mechanism; Phase 9 Gap Analysis; Phase 10 Iteration Cycle.

### F85 — Requirement Matching Mechanism (separate pass, IM) — establishes «refine» links

**Status:** Open — **mechanism SPECCED:** Requirement Matching service Row 3 logical v0.1 + Row 4 physical v0.1 (standalone cross-row service; three-way refine-link/no-match/duplicate-merge; DD-anchored candidate pre-filter; bidirectional upward child-orphan + downward parent-orphan gaps; confidence-banded auto-link/merge-with-review, fixed constant; populates `refines_refs`). Stays Open until a production run exercises it (the dictionary and requirement set must be populated; no run yet).
**Surfaced by:** Design discussion — the matching operation is needed regardless of how a parent comes to exist.
**Category:** New Mechanism (design)

**Description.** Establishing a Req(n-1)↔Req(n) «refine» link requires matching a requirement against the requirements at the adjacent abstraction level — a **semantic abstraction-level judgement**, not a structural/string match (the whole point is that levels are expressed differently). The same matching operation is needed in all provenance cases: parent and child both human-supplied; both derived in the same multi-row run; or parent generated later by GQA and driven down (F84). The row-2 worked example: a requirement derived from a source CCI at row 2, then — on reading the available requirements — found to have a matching row 1 parent; the match must be made.

**Decision.**
1. Matching is a **separate matching pass over the assembled requirement set** (initial choice), NOT an integral step inside Pass 3d. Rationale: ragged multi-level input means the parent may not exist when the child is derived; a separate pass decouples matching from derivation order and handles the "parent appears later" case (including GQA-generated parents) uniformly.
2. Matching is an **IM act** (Claude call) with its own response schema and confidence — abstraction-level relatedness cannot be determined structurally.
3. The matching act is **symmetric/bidirectional**: given a requirement and the adjacent-row requirement set, it runs child-looks-up (normal derivation) and parent-looks-down (GQA re-descent).
4. The match outcome is **three-way**: `no-match` | `refine-link` (relate as parent/child; populate `refines_refs`) | `duplicate-merge` (the re-descent produced a requirement that *is* an existing orphan — collapse rather than duplicate). The duplicate-merge outcome is what prevents GQA re-descent from creating a near-duplicate child alongside the existing orphan.
5. Candidate search space is bounded — a requirement only refines **one level up**, so candidates are the adjacent-row requirement set already in the ledger.

**OPEN sub-questions (for the matching-mechanism spec):** confidence threshold for auto-linking vs Practitioner review; how `duplicate-merge` reconciles differing fields between the merged pair; whether matching runs once after full multi-row derivation or is re-invokable incrementally by GQA (likely both).

**Cross-references:** F82 (the link it populates), F83 (replaces injection), F84 (GQA re-invokes it), F86.

### F86 — Empty `refines_refs` Is the Gap Trigger (no Concern artefact)

**Status:** Action-Required (ledger field + gap-check wiring)
**Surfaced by:** Design discussion on how unparented requirements are surfaced.
**Category:** Mechanism / Decision

**Description.** An unparented requirement must be detectable as a gap. Two options considered: (a) Pass 3d raises an explicit Concern (CN-NNN) when it cannot parent a requirement; (b) the **empty `refines_refs` field is itself the gap signal**, with no additional artefact.

**Decision.** Option (b). The gap-detection mechanism is the **same check** (scan for empty `refines_refs`) regardless of whether it runs at Pass 3d or in robustness analysis — wrapping it in a Concern adds an artefact without adding information, since the emptiness already encodes the gap. No CN-NNN is raised for an unparented requirement. The only axis on which "check at 3d" vs "check at robustness" differs is **performance** (when/how often the scan runs), not correctness — that placement is an implementation choice, not an architectural one. Action-Required: the `refines_refs` field (F82, ledger v2.13) and the empty-field gap check must be implemented for this to operate.

**Cross-references:** F82 (the field), F84 (what consumes the gap), F85 (what populates the field).

## Active Findings — New in v0.57

### F87 — FOUNDATIONAL: "Is Elaboration Gap Analysis?" — Downward Elaboration is Gap-Prevention, Not Gap Analysis

**Status:** Open (foundational framing — governs interpretation of F82–F86; expected to be referenced in many future conversations) — **guidance REALISED:** the interrogative-elaboration increment is authored into Requirement Derivation Row 3 v0.3 §4.1.1(f) (type-and-row-aware slot elicitation; Object-recursion to structure; within-row, no cross-row parent invention; the gap-prevention-not-gap-analysis boundary) and Row 4 v0.6 §5.4 (shared slot-question preamble) + ADVC-3d-02 (soft completeness advisory). Stays Open until a production run validates that guided interrogation is generatively complete on built output (it was validated in sandbox on R004; the built mechanism is not yet run).
**Surfaced by:** Isolated sandbox test of the cross-row approach on real PMT Row 1↔Row 2 requirements (Test 1 matching; Test 2 R004 completeness re-descent). The test surfaced the conceptual distinction; the analysis below is the decision.
**Category:** Architecture / Methodology — foundational concept

**The question.** When a row n requirement turns out to need more detail than is present (e.g. PMT R004 "provide visibility into the inventory and status of work opportunities" had only a *constraint* child R016 limiting visibility, but no child *providing* the visibility, no child holding the *inventory*, and no child identifying the *who* that sources the inventory items) — is finding that shortfall a **gap-analysis** activity, or is it **correct elaboration behaviour** that should simply happen during derivation? And do we need GQA (gap→question→answer) for it, or only for traceability of the AI's reasoning?

**The blurred distinction that had to be separated.** Two activities were sliding together in discussion:
1. **Downward elaboration** — taking R(n-1) and deriving the R(n) children that realise it. Generative, top-down, primary derivation. Pass 3d's job, with R(n-1) as an additional input.
2. **Completeness checking** — asking whether a requirement has been *fully* elaborated.

**The decision.** *Good downward elaboration IS the completeness mechanism — there is no separate elaboration-gap-analysis activity.* If Pass 3d elaboration is **guided to be thorough**, the children that would otherwise be "gaps" are generated *in the act of derivation* and the gap never forms. Therefore:

- **Elaboration completeness is achieved by derivation GUIDANCE, not by a post-hoc gap-analysis pass.** This is why embedding gap analysis in Pass 3d was correctly rejected (twice, by Practitioner) — yet the completeness *guidance* legitimately belongs in Pass 3d. The distinction: guidance makes elaboration *not leave* gaps (gap-prevention); a gap-analysis pass *detects* gaps after the fact. The former is derivation; the latter is the thing that does not belong in 3d.
- **The guidance mechanism is a row-aware Zachman-interrogative check (candidate — to be validated).** Humans leave gaps because, when specifying a requirement, they answer the one or two interrogatives they are thinking about and silently skip the rest. The Zachman Framework columns ARE the six interrogatives (What/How/Where/Who/When/Why). So elaboration completeness = "for this requirement, have the row-appropriate interrogatives its intent implies been answered?" Asked **per requirement** (NOT per cell — cross-cutting domains span cells, so cell-level completeness is the wrong unit; the requirement is the unit regardless of how many domains/cells it cross-cuts). Each interrogative must be asked in its **row-specific form** (Who at Row 1 = enterprise role; at Row 2 = business actor; at Row 3 = logical role; etc.) — this rides on the existing REQUIREMENT_ROW_GUIDANCE per-row blocks. Advantages over open-ended decomposition: terminates by construction (fixed question set, no unbounded recursion), auditable (you can see *which* interrogative was unanswered), more stable than generative re-derivation. Open risk: not every interrogative is load-bearing for every requirement (R004 implies What/Who/How strongly, Where barely) — the guidance must convey *which* interrogatives a requirement of a given kind should answer, or it over-generates false gaps.

**Does GQA apply to elaboration? NO — GQA is reserved for the irreducible UPWARD residue.** Even with perfect downward elaboration, two residues survive that elaboration cannot prevent:
- **Genuinely novel R(n)** — content appearing at row n from row n's *own sources*, with no row n-1 origin (the human supplied detail at row n they never framed above). Downward elaboration cannot prevent this orphan because it did not come from above — it came "from the side" (the sources). This is the empty-`refines_refs` case (F86), and it is **real and irreducible.**
- That novel orphan **implies a missing R(n-1)** — and reverse-derivation of that missing parent is the *only* genuine gap-closure, runs **upward**, and is where GQA earns its place (F84). GQA generates a requirement that did not exist and gates it past a Practitioner — real work, not mere traceability.

**Clean architectural cleavage (the lasting result):**

| Direction | Activity | Mechanism | Is it gap analysis? | GQA? |
|---|---|---|---|---|
| **Downward** | Elaborate R(n-1) → R(n) thoroughly | Pass 3d + row-aware interrogative guidance | **No — gap-prevention** | No |
| **Upward** | Novel orphan R(n) → missing R(n-1) | Reverse-derivation via existing GQA | Yes — the only true gap closure | Yes |

**On the `rationale` attribute.** The AI's interrogative reasoning for *why* a new R(n) child exists can be recorded in the Requirement `rationale` attribute for traceability — cheap, no process burden. This is optional auditability, NOT a load-bearing mechanism; the child's `refines_refs` link plus the parent's intent already explain the child's existence. (This is the lightweight "record why we have new R(n) requirements" route, refined: prefer thorough guided elaboration over post-hoc justification, with rationale as the optional trace.)

**Why this is recorded as foundational.** It resolves a recurring confusion (gap analysis vs elaboration) that will arise every time the downward/upward flows are discussed. The governing principles to carry forward: (1) **good elaboration is gap-prevention, not gap analysis**; (2) **completeness guidance belongs in derivation; gap-analysis passes do not belong in 3d**; (3) **GQA is for the upward novel-orphan residue only**; (4) **the requirement, not the cell, is the unit of completeness** (cross-cutting domains make cell-level the wrong unit).

**OPEN — the decisive test still to run.** Whether downward elaboration can actually be *made* thorough by interrogative guidance, or whether it still leaves downward holes needing post-hoc detection. The Test-2 R004 hand-trace MISSED the inventory (and its who-source) when using *decomposition*; the question is whether *with* explicit row-2 interrogative guidance ("elaborate R004 — row-2 What? Who-source? Who-recipient? How-present? When? Where?") the full child-set (inventory-holder, item-source, presenter, scope) falls out *generatively*. If yes, downward gaps genuinely do not form and the cleavage above holds as-is. If no, downward completeness *does* need a check and more machinery is required. **This test gates whether F87's "elaboration = gap-prevention" claim is operationally true or only conceptually attractive.**

**Cross-references:** F82 (`refines_refs` — the link guided elaboration populates), F83 (separate matching pass — establishes links for content that does arrive), F84 (GQA — the upward residue this finding scopes GQA to), F85 (matching mechanism), F86 (empty-`refines_refs` = novel orphan = the upward trigger); Zachman Framework six interrogatives = matrix columns; REQUIREMENT_ROW_GUIDANCE (Mechanism Spec v0.4 §5.4 — where row-aware interrogative guidance would live).

## Active Findings — New in v0.58

### F88 — FOUNDATIONAL: Requirement Structural Canon — Typed Condition-Subject-Predicate-Object Patterns; Slot-Based Atomicity as Hard Constraint

**Status:** Open (foundational — defines the concrete form a requirement statement must take; governs derivation, atomicity enforcement, and Phase 4) — **derivation portion REALISED:** Row 3 Requirement Derivation v0.2 §4.1.1(b) (hard slot-based atomicity, typed CSPO patterns, type-selects-pattern) and Row 4 v0.5 CHK-3d-09 (decidable HARD typed-slot atomicity check, gated by VER-3d-15). Stays Open: the interrogative-elaboration guidance (Row 3 v0.3 §4.1.1(f), Row 4 v0.6 §5.4 + ADVC-3d-02) and Phase 4 (Row 3/4 Requirement Quality Analysis v0.1 — the slot canon as graded scoring) are now AUTHORED; the finding stays Open until a production run exercises the built derivation + Phase 4 (the slot canon is realised in specs but not yet run end-to-end).
**Surfaced by:** Discussion of allowed concrete requirement structure, grounded in `requirements_document_v6.docx` (prior INCOSE / ISO-29148-grounded requirement-authoring work — confirmed readable this session; earlier sessions had a corrupt copy). This document turns out to be, in effect, the Phase 4 Requirement Quality Analysis framework.
**Category:** Architecture / Methodology — foundational concept

**The canon.** A requirement is not free prose. It takes a **typed pattern** with defined slots; the requirement's *type selects the pattern*. The canonical leading form is **Condition-Subject-Predicate-Object** ("If this happens, the system shall do this to that object"), with Condition optional. Per type (pre-collapse — see F89 for the collapse):

| Type | Pattern | Slots |
|---|---|---|
| Functional | `[Condition,] <Subject> shall <action> <object> [with <performance>]` | Condition?, Subject, Action, Object, Performance? |
| Design Constraint | `<Subject> shall comply with <Constraint Rule> [under <Condition>] [with <performance>]` | Subject, Constraint Rule, Condition?, Performance? |
| Environmental | `<Subject> shall operate/store/transport under <Env Condition> [with <criteria>]` | Subject, Env Condition, Criteria?, Lifecycle Phase |
| Performance/Suitability | `<Subject> shall achieve <Attribute> [under <condition>] [with <criteria>]` | Subject, Attribute, Criteria, Condition? |

**Atomicity is a HARD constraint, defined precisely by the slot rules (not a vague "one thing per requirement").** The atomicity violations are decidable, per-type checks against the slots:
- Compound condition (High) — multiple logical conditions joined by and/or, or nested conditional logic.
- Compound object / multiple objects (Medium) — multiple independent objects joined by conjunction unless an inseparable single concept.
- Multiple constraints / environmental factors / performance attributes in one requirement (High/Medium per type).
- Missing required slot (Subject / Action / Object / Constraint Rule / Performance Criteria) — High — destroys verifiability.
- Ambiguous verb ("handle", "manage", "support", "process"), subjective terms ("robust", "easy") — Medium.
- Implied design in a functional requirement — Medium.
This is the real specification of the atomicity discipline that CHK-3d-07 and the REQUIREMENT_ROW_GUIDANCE "and"-test approximate crudely. **A compound requirement is not merely poor quality — it breaks the elaboration mechanism** (the recursive object-interrogation, F87, has no single object to descend into) and explodes the verification test space (the requirements-engineering rationale: atomic requirements map to bounded, enumerable test cases; compound requirements hide cross-condition cases that get silently missed and conceal inter-obligation coupling).

**Three unifications established:**
1. **Type selects structure.** The `requirement_type` is not just a classification label — it selects the slot template the statement must conform to. This coupling is currently absent from the mechanism specs and must be added.
2. **F87 interrogative completeness = slot completeness, parameterised by type × row.** "Have the load-bearing interrogatives been answered?" becomes "are the required slots for this requirement's type filled?" (Functional → Subject/Action/Object/Condition?/Performance?; Performance → Attribute/Criteria/Condition?). A Functional requirement missing its Object is simultaneously an F87 completeness gap and an F88 −30 quality violation. The interrogatives are disciplined by the type pattern, not six free-floating Zachman columns — refines F87 from "row-aware" to "type-and-row-aware slot checks."
3. **`requirements_document_v6.docx` IS the Phase 4 Requirement Quality Analysis framework** — severity levels (High −30 / Medium −15 / Low −5), per-type scoring rules, worked examples. Phase 4 had no spec; this document supplies it. Promote from "POC material to challenge" to canonical input.

**Condition slot interaction with the elaboration recursion (open).** The recursion (F87) interrogates the Object → structure. A Condition slot is a state/event; the document notes compound conditions "should be handled through scenarios or state models." So the recursion likely has two descent paths — Object → structure, Condition → state/behaviour model — both BSBA territory. To be tested.

**Cross-references:** F87 (interrogative completeness — now slot-based), F89 (type collapse — changes which patterns survive), F82 (`refines_refs`), Phase 4 Requirement Quality Analysis (= this document); `requirements_document_v6.docx`; ISO/IEC/IEEE 29148:2018; INCOSE (Harwell et al. 1993).

### F89 — Requirement Type Taxonomy Collapsed to Functional / Constraint / Structural

**Status:** Open (resolves long-running requirement-type debate; gates a ledger v2.13 enum change) — **REALISED:** enum collapsed to Functional/Constraint/Structural in ledger v2.13, Row 3 Requirement Derivation v0.2 (§4.1.1(d), §5.1, §5.3), and Row 4 v0.5 (DDL CHECK, Pydantic Literal, all five §5.4 guidance blocks); `verification_method` gained Measurement to carry the measured-vs-inspected distinction. Stays Open until existing PMT/NQPS data is migrated per ledger v2.13 Appendix D (Performance/Suitability→Constraint, Non-Functional→Structural) and a derivation run confirms the triad in production.
**Surfaced by:** Discussion challenging the requirement-type set ("isn't performance just a constraint on the design?").
**Category:** Ledger Schema / Methodology

**The collapse.** The four authoring types in `requirements_document_v6.docx` (Functional / Design Constraint / Environmental / Performance-Suitability) and the current ledger enum (Functional / Constraint / Performance / Suitability / Non-Functional) collapse to **three fundamental kinds**:

| Kind | What it expresses | Verified by | Absorbs |
|---|---|---|---|
| **Functional** | behaviour — what the system *does* (Subject shall Action Object) | Test / Demonstration | — |
| **Constraint** | a bound on behaviour / solution / quality dimension / operating context | Inspection (conformance) OR Measurement (threshold) | Design Constraint, Performance, Suitability, Environmental, quality-attributes |
| **Structural** | composition / attribute / relationship — what the system *is made of* | Schema / composition conformance | (renamed from "Non-Functional") |

**Rationale.**
- **Performance, Environmental, and quality-attribute requirements are all species of Constraint** — none describes behaviour; each *bounds* something (a quality dimension, an operating envelope, a solution choice). "Shall achieve 500 tps" = "throughput shall not be less than 500" = a measured constraint.
- **The measured-vs-inspected distinction that justified separate types is carried by `verification_method`, not by the type.** This is *why* `verification_method` exists: a design constraint verifies by Inspection (uses USB-C? yes/no); a performance constraint verifies by Measurement (measure tps vs 500). Collapsing the types preserves the distinction in the field that was always going to carry it. **Guardrail:** the "measurable Performance Criteria mandatory" rule must survive the collapse as a Constraint obligation — collapse the type, keep the criteria discipline, or verifiability is lost.
- **"Non-Functional" is renamed "Structural"** to de-overload the term. The genuinely-new kind is the *structural-composition* form (a work-opportunity *has* {title, value, status, assignee}) — the **S in BSBA** — which the recursive interrogation (F87) produces and which none of the behavioural/constraint patterns can hold. Quality-attribute "non-functionals" fold into Constraint (above); the structural form is what "Structural" names.

**Ledger change (rides v2.13).** `requirement_type` enum `Functional | Constraint | Performance | Suitability | Non-Functional` → `Functional | Constraint | Structural`. This rides the v2.13 update already queued for `refines_refs` (F82) — not a new schema disruption. Migration of existing data: Performance/Suitability-typed requirements in PMT/NQPS re-type to Constraint with `verification_method = Measurement`; any Non-Functional re-types to Structural or Constraint per its content. Small, mechanical.

**Methodological guardrail (recorded by Practitioner direction).** Requirement-type taxonomy attracts endless debate that does not help anyone write a good requirement. The governing rule: a type exists only to do real work — here, **(1) select the structural pattern (F88), (2) route the verification method.** Collapse types aggressively; push distinctions that matter into fields that are doing real work (`verification_method`, the slot structure). Stop the taxonomy discussion once the set is *sufficient to write good requirements against* — which the triad is. Do not re-open type names without a work-driving reason.

**Cross-references:** F88 (type selects pattern — the patterns the triad maps to), F82 (ledger v2.13 — this enum change rides it), F87 (Structural type holds the S-in-BSBA output of the interrogation), `verification_method` field (carries the collapsed distinction).

## Active Findings — New in v0.59

### F90 — FOUNDATIONAL: Project Data Dictionary — Single Cross-Row Controlled Vocabulary; the Substrate for Structural Matching and Behaviour Binding

**Status:** Open (foundational — the artefact that makes the structural half of F85/F88/F89 operable) — **representation open items CLOSED by design decision; representation REALISED in ledger v2.14; mechanism LOGICAL-specced.** Closed items: aliases = synonym entries only (single source of truth, query-found); value-sets = attribute field with named-addressable values (not separate elements; state-model deferred F91); relationships = directed entries (from→to + cardinality); provenance = single `provenance_ref` pointer; alias-resolution gating = auto-resolve-with-register-review, confidence-banded, fixed-constant threshold (provisional, promotable); DD = standalone cross-row service, incrementally populated. Realised: ledger v2.14 `DataDictionaryEntry`/`DataDictionaryRegister`; Data Dictionary Service Row 3 logical spec v0.1. **Stays Open** until the Row 4 physical DD spec is authored and the service runs (the dictionary is not yet populated by any production run; the Object-slot binding in Requirement Derivation §5.5 is still a declared interface, not yet wired to a running service).
**Surfaced by:** Stress-testing the structural-matching risk flagged by the F87 decisive test. The risk turned out to be fundamentally a **language-inconsistency problem**, not a confidence-threshold problem. Validated by deriving the canonical structural model from real PMT requirements.
**Category:** Architecture / Ledger Schema — foundational artefact

**Root cause it resolves.** The structural-matching risk (last load-bearing worry from the F87 test) is that the same concept wears different names across rows and authors, and different concepts wear similar names. Real PMT evidence: **Task** appeared as "task / work opportunity / compensated work opportunity / pocket money task / chore" (5 surface terms, one entity, across Rows 1/2/5); **Inventory** as "inventory / work opportunity inventory / work inventory / task availability list" (4 terms, one collection). No confidence threshold fixes this — the strings *should* match conceptually while differing lexically. The resolution is a canonical entity with recorded aliases: matching changes from "do these two strings mean the same thing?" (hard, noisy judgement) to "does this term resolve to a known entity?" (a lookup against the alias set — stable). The matching "unreliability" is actually a **signal** — the system correctly detecting inconsistent authored language, which is a core defect SysEngage exists to find.

**The decision — one project-wide Data Dictionary, available to all rows.** Entity identity is row-independent even though its detail is row-dependent: a Task *is the same Task* whether the Planner calls it a "compensated work opportunity" or the implementer calls it a "chore." Resolved once, when first encountered; every later surface term across any row resolves against the existing DD. Rejected alternative: per-row structural models that themselves refine (would treat "work opportunity" and "task" as two entities in a refine relationship — a category error; would double the matching burden).

**Inclusion rule — "the DD holds whatever behaviour BINDS TO."** This is the crisp line (sharper than "existence vs detail" or "abstraction level"):
- **IN the DD:** entity identity + aliases; attribute *existence*; attribute *value-sets/enumerations where behaviour binds to the values*; relationships (cardinality). Abstraction-stable; implementation-free.
- **NOT in the DD:** representation, bounds, types, storage, keys (PK), encodings — anything no behaviour references. These are **row requirements** that *elaborate* a DD attribute.
- **The test:** "can a behavioural requirement, at any row, reference this by name?" Yes → DD. No → row requirement.

Worked examples (the rule's calibration):
- `Task.name` *exists* → DD (behaviour: "specify task name"). Its char-limit (3–40) → NOT DD (no behaviour binds to "40") — it is a Row 3 requirement elaborating `Task.name`. Its db field type → NOT DD — Row 4 requirement.
- `Task.monetary_value` exists → DD. Its DECIMAL(10,2) → NOT DD (Row 5).
- `Task.status` exists → DD. Its enumeration {available, claimed, completed} → **IN the DD** — because Row 2 behaviour binds to the named states (R013 "claim", R016 "limited to available and completed"). The enumeration is shared vocabulary, not attribute detail. *(This case set the rule: a value-set is DD content when behaviour references the values, distinguishing it from a representation like the char-limit which nothing binds to.)*

**Per-row attribute detail lives in requirements, not the DD.** The same attribute is legitimately re-described down the rows — `Task.name` (Row 2, exists) → "string, 3–40 chars" (Row 3 requirement) → "db field of chosen type" (Row 4 requirement). These are NOT three DD entries; they are one DD attribute with three requirements *referencing* it. The PK/storage question answers itself: a Row 4 requirement elaborating how `Task` is realised, linked to the `Task` DD entry — present in the ledger, absent from the DD. The DD is the still point; requirements at all rows point at it and progressively detail it. This keeps Zachman row-stratification entirely in the requirement layer; the DD sits orthogonal to the rows as shared vocabulary.

**Two registers (the synonym register is author-facing and load-bearing):**
1. **Canonical entries:** e.g. `Task | an atomic item of work within the inventory; has name, monetary value, status {available, claimed, completed} | Inventory 1:* Task`.
2. **Synonym / cross-reference register:** e.g. `Work opportunity | See Task | NA`, `Chore | See Task`, `Pocket money task | See Task`. PRESERVED PERMANENTLY (not throwaway matching metadata). Two jobs: (a) **author-facing** — an author who wrote "work opportunity" can find their concept and confirm it was captured, not silently dropped (this is **Non-Loss applied to vocabulary** — authored terminology is content and must not vanish through canonicalisation); (b) **audit surface** — every "See Task" entry exposes a canonicalisation decision for Practitioner review, making a wrong merge *visible and correctable* (a false merge without the register is invisible and unrecoverable). The synonym register is therefore *how* the alias-resolution-gating question is reviewed. Refinement: a cross-reference should carry **provenance** (which author/source/row first used the term), resolvable through existing ledger element-relationship traceability, so a wrong merge is not just visible but attributable to the input that caused it.

**Emergent state model (BSBA made concrete).** Once `Task.status` carries its enumeration AND behaviour references transitions between those states ("claim" moves available→claimed; "complete" moves claimed→completed), the DD's status entry plus the transitioning behavioural requirements *constitute* a state machine for Task. The state model is not a separate artefact to build — it is what you *have* once the DD holds the states and behaviour binds to them. This is the Behaviour-Structure binding the POCs were reaching for: behaviour (transitions) bound to structure (the state-set in the DD).

**Derived entities.** The DD must represent derived structure (e.g. `EarningsRecord.amount = sum of monetary_value of completed Tasks`). This explained a session-long puzzle: earnings kept appearing as both "maintain a record of earnings total" (data) and "derive a weekly earned amount" (computation) — a derived entity legitimately appears as both, which only the structural view exposes. Not an inconsistency to fix; a derived-vs-primitive property to represent.

**Adjustments to existing findings:**
- **F85 (matching):** splits cleanly into *behavioural* matching (refine links between requirements — still IM judgement) and *structural/term* matching (resolve a term against the DD — a lookup against aliases, much more reliable). The DD removes most of the structural-matching risk. BUT the merge judgement is not eliminated — it is **relocated to entity-resolution time** (resolve-once, when a term is first encountered) instead of resolve-repeatedly. The same three-way no-match / link / merge risk applies to DD entities (false merge = data loss; false split = the inconsistency the DD was meant to cure).
- **F88 (Object slot):** a behavioural requirement's Object (and the values it references) must resolve to a DD entity/attribute/value. This is the vocabulary-consistency enforcement mechanism — Object must name a DD entry or alias.
- **F89 (Structural type):** a Structural requirement is "a projection of the project Data Dictionary" — it declares or refines a DD entry, not free-standing assertions.

**OPEN sub-question (partly answered).** Alias/entity resolution gating — auto (IM judgement, with duplication/false-merge risk) vs Practitioner-gated. Partly answered by this finding: the synonym register is the surface on which a Practitioner *reviews* resolutions, so resolution can be auto-with-review rather than auto-blind or fully-manual. The gating threshold and the false-merge reconciliation procedure remain to be specified (shared with the F85 matching threshold question).

**Cross-references:** F85 (matching — DD is its substrate; merge judgement relocated to resolution time), F88 (Object binds to DD), F89 (Structural type projects the DD), F87 (the structural recursion populates the DD), F82 (DD needs ledger representation — likely rides v2.13), Non-Loss principle (vocabulary Non-Loss = the synonym register); `requirements_document_v6.docx` (the Object slot definition: "Must be concrete and unambiguous" = must resolve to a DD entry).

## Active Findings — New in v0.60

### F91 — Back-Refinement Validated (closes the cross-row/structural design phase); State-Model Transition-Completeness Noted as a Future Capability

**Status:** Open (design decision recorded; closes the F82–F91 design phase)
**Surfaced by:** The pre-committed decisive test — re-express the real PMT R004 cluster (R004 + Row 2 children R011/R012/R013/R014/R016) against the DD-canonical vocabulary, judged on three pass/fail criteria, with a stopping rule: pass → close design and go to build; do NOT chase a further finding.
**Category:** Architecture / Methodology — validation milestone

**Result — all three criteria PASS:**
1. **Object-binding resolves cleanly (PASS).** Every behavioural object resolved to a DD entity/attribute/value (R011 "tasks"→`Task`, "monetary values"→`Task.monetary_value`; R016 "available and completed tasks"→`Task` filtered by `status∈{available,completed}`; etc.). The binding also *did work*: disambiguated R011 (task-with-value = one object, atomic), distinguished R016's status-filter from a compound object, and separated R014's structural assertion ("Task has status" — now DD) from its behaviour.
2. **DD structure FORCES atomicity (PASS — stronger than hoped).** R004's "visibility into the **inventory and status**" could not be re-expressed as one requirement, because `Inventory` (a collection) and `Task.status` (an item attribute) are separate DD elements — there is no single DD element "inventory-and-status." The compound became *structurally un-expressible* and split into R004a (visibility into `Inventory`) and R004b (visibility into each `Task.status`). Atomicity is therefore a *consequence* of DD-binding, not a rule layered on top.
3. **No semantic drift (PASS — over-delivered).** Re-expression introduced no drift AND exposed two pre-existing defects invisible in the prose: R012 "govern task availability" was vaguer than its DD-bound meaning (`set Task.status=available weekly` — flagged for Practitioner confirmation, legitimate sharpening not drift); and R013 "claim **completed** tasks" was **incoherent against the state model** — see F92.

**Conclusion:** the structural half of the architecture (F82 refine-link, F85 matching, F87 interrogative elaboration, F88 typed CSPO atomicity, F89 type triad, F90 data dictionary) is validated and internally coherent. **The cross-row/structural design phase is complete.** Per the stopping rule, the next action is the build at ledger v2.13 — NOT further sandbox design.

**NOTED capability — deliberately NOT designed now (stopping-rule discipline).** Criterion 3 demonstrated that **binding behaviour to the DD state model detects missing states and missing transitions, which are missing behavioural requirements.** Inspecting the state model for any transition that no behavioural requirement enacts is a *near-decidable* gap detector (a transition either has an enacting requirement or it does not) — potentially a fourth gap-detection path alongside forward interrogative elaboration (F87), the empty-`refines_refs` upward trigger (F86), and matching (F85). This is recorded as a **validated capability of back-refinement, to be formalised in a future cycle.** It is explicitly NOT being designed now — chasing it would breach the stopping rule and reopen a closed design phase. The build should know back-refinement carries this consistency-check payload; the mechanism for it is future work.

**Cross-references:** F88 (atomicity — now shown to be DD-enforced, not just rule-checked), F90 (the DD that behaviour binds to; the state model whose transition-completeness is the noted capability), F92 (the concrete defect criterion 3 found), F85/F86/F87 (the other gap-detection paths the noted capability would join).

### F92 — PMT Dataset Defect: Missing Parent-Approval State and Behaviour (regression check for the built pipeline)

**Status:** Open (validation-dataset finding — not an architecture finding)
**Surfaced by:** F91 back-refinement criterion 3 — R013 binding incoherence against the Task state model, corroborated independently by R038.
**Category:** Validation Dataset (PMT) / Regression Check

**The defect (in the PMT requirement set, not the architecture).** The derived Task lifecycle `available → claimed → completed` is **incomplete**: it conflates "child asserts done" with "parent approved." The real lifecycle requires a parent-approval step:
`available → claimed (child) → done/asserted (child) → approved (parent) → earns`.
Evidence converging from two independent directions:
- **R013** "the child user shall claim **completed** tasks" is incoherent against `available→claimed→completed` (you claim available tasks, not completed ones) — it was gesturing at the missing child-assert / parent-approve gap.
- **R038** (Row 5) lists Task "**approval requirements**" as a configuration attribute — the implementation-row shadow of an approval state never modelled upstream.

**Consequences in the PMT spec:**
- A **missing behavioural requirement**: "The parent shall approve a child's claimed/done task before earnings accrue" (the `done → approved` transition has no enacting requirement at any row).
- A **missing DD state**: `Task.status` should include `approved` (or distinguish `done` from `approved`), not collapse to `completed`.
- A **mis-bound derived value**: `EarningsRecord.amount` derives from *completed* Tasks (R027) but should derive from *approved* Tasks — a child should not earn on unapproved self-assertion. This is a **material, financial** defect, plausible enough to pass linear human review.

**Why recorded:** this is a defect in the PMT *validation dataset*, surfaced by hand during back-refinement. It becomes a **regression check for the built pipeline**: when PMT is re-run through the eventual implemented cross-row/structural mechanisms (back-refinement + state-model transition-completeness, F91), the pipeline *should* independently surface the missing approval state, the missing approval behaviour, and the EarningsRecord mis-binding. If it does, the architecture is confirmed to catch what was caught by hand here. Until then, no fix is applied to the PMT data — it is preserved as the test case.

**Cross-references:** F91 (the test that surfaced it; the noted state-completeness capability that should re-detect it), F90 (the DD state model — `Task.status` enum and `EarningsRecord` derivation are the affected entries).

## Active Findings — New in v0.61

### F93 — Spec-Architecture Ruling: Cross-Row Mechanisms Are Standalone Services (standard two-level treatment); F83 Dual-Stream Debt Corrected to Substantial Revision

**Status:** Open (architecture/process ruling — governs how F82–F92 specs are authored)
**Surfaced by:** Planning the structured spec updates for F82–F92 — needing to decide where the new cross-row mechanisms (Data Dictionary, Requirement Matching) sit in a spec corpus that has been purely row-stratified, and a grep check of the Pass-3a/3b/3c mechanism specs for dual-stream references.
**Category:** Architecture / Methodology / Spec corpus structure

**Ruling 1 — the logical/physical split is abstraction-of-the-mechanism, not row-data scope.** Row 3 logical = what the mechanism *does* (Designer abstraction); Row 4 physical = how it is *built* (Builder abstraction). This is independent of whether the mechanism runs per-row or cross-row. Therefore every mechanism — including cross-row ones — gets a Row 3 logical spec and a Row 4 physical spec. **No new spec tier is introduced.**

**Ruling 2 — cross-row mechanisms are standalone services.** The Data Dictionary and Requirement Matching mechanisms are row-independent and are modelled as **standalone services used by the requirement mechanisms at each row** — not steps inside Pass 3d. Each gets the standard two-level treatment with operational scope declared "cross-row" in §1 (vs "row-sequential"). This is the structural expression of F85's "separate matching pass, not integral to 3d": a service specified once and *referenced* by each caller, not re-specified per caller.

**Service/caller dependency map:**
```
SERVICES (cross-row; Row3 logical + Row4 physical each):
  - Data Dictionary service       persistent state; written by structural derivation,
                                   read by Matching, bound to by Object slots (F88), read by Phase 4
  - Requirement Matching service  stateless act; called by Requirement Derivation, GQA re-descent (F84),
                                   back-refinement (F91); three-way outcome (F85)
ROW-SEQUENTIAL MECHANISMS (call the services):
  - Requirement Derivation (3d)   calls Matching; reads/writes DD; binds Objects to DD
  - GQA re-descent (F84)          calls Matching
PHASE MECHANISM:
  - Phase 4 Requirement Quality   reads DD; scores against the F88 structural canon (= requirements_document_v6.docx)
```

**Ruling 3 — services are interface dependencies of their callers.** A caller spec cannot be *completed* before the service it calls is specified; it can be *partially reconciled* with the service points declared as interfaces ("calls Matching service; binds Object to DD service — see service spec"). This sharpens the authoring sequence.

**Authoring sequence (refined):**
1. **Ledger v2.13** — `refines_refs` (F82) + `requirement_type` enum collapse (F89) + Data Dictionary representation (F90). Foundation; do first.
2. **Reconcile in-flight Requirement Derivation specs** (Row 3 v0.1 → v0.2, Row 4 v0.4 → v0.5) for the service-independent parts: type triad (F89), CSPO canon + slot-based hard atomicity (F88), enum in §5.1/§5.2. Declare DD-binding and Matching-call as interface points.
3. **Author the service specs** when build-imminent: DD service (Row3→Row4), Matching service (Row3→Row4) — cross-row scope in §1.
4. **Complete** the derivation specs' service-dependent parts; GQA interface (F84); Phase 4 (= `requirements_document_v6.docx`); then the dual-stream debt cleanup (below).
5. Later: formalise the noted state-completeness capability (F91); verify PMT regression (F92).

**Correction to the F83 dual-stream debt (material).** A grep of the Pass-3a/3b/3c mechanism specs found the dual-stream model is **NOT a stub — it is fully specified and built-out**:
- `SysEngage_Row_3_Mechanism_Row_Lens_Source_Reanalysis_v0_3` is named and architected as "Dual-Stream Row-Lens Classification": stream 2 (Row N-1 Domains + Requirements) is a precondition input (§3.2), with a Row N-1 readiness gate, a hard prerequisite that Row N-1 Phase 3d be complete (§10.1, §11), `stream2_requirement_count`/`stream2_domain_count` AnalysisPass fields, and "evidence of dual-stream engagement" as a postcondition. Cites Tracker v0.22 F35 as the resolution that established it.
- `SysEngage_Row_4_Mechanism_Row_Lens_Source_Reanalysis_v0_1` fully implements it (Stage 1 stream-2 Domain processing, `requirement_id` in Signal `source_refs`, stream-2 fixtures and edge cases).
- The Row 1/2/3 Understandings carry the framing (§8.5 Row-to-Row Signal Feed, §3.9.3, §8.17, §8.5 Derivation Lineage).

**F83 re-examined and CONFIRMED (not reversed).** The discovery that stream 2 preserves `requirement_id` in Signal `source_refs` was tested against F83's atomisation argument: this signal-level provenance is **exactly the atomisation F83 described**, not a usable requirement-level link. One R(n-1) requirement_id scattered across many Signals across many CCIs across many Domains records *diffuse influence*, not *which R(n) refines which R(n-1)*. It cannot reconstitute the «refine» link. F83 holds; the sunk specification ("already built dual-stream") is not a reason to reverse a decision reasoned on its merits — it is the reason the *other specs* must be revised.

**Consequent debt re-scoped (annotation → substantial revision) and sequenced.** The two Reanalysis specs and the three Understandings must be **reverted to single-stream Pass 3a** — not merely annotated. Knock-on: Domain Derivation MD-6 withdrew `upstream_domain_ref` *because* cross-row tracing was navigable via stream-2 signal provenance (`CCI → signal_refs → Requirement(n-1) → domain_refs`); removing stream 2 deletes that trace path, so **the cross-row requirement trace relocates to F82 `refines_refs`** (explicit link on the requirement, cleaner than diffuse signal provenance). **Sequencing constraint:** ledger v2.13 (`refines_refs`) MUST land before the Reanalysis specs are reverted, or the traceability the dual-stream provided is lost in the gap. F35's reversal (by F83) touches every spec citing F35's dual-stream resolution — both Reanalysis specs and the Row 1/2/3 Understandings.

**Cross-references:** F82 (`refines_refs` — receives the relocated MD-6 trace; gates the dual-stream revert), F83 (dual-stream rejection — confirmed; debt re-scoped here), F35 (established dual-stream — reversed by F83; citations to be cleared), F84/F85/F90/F91 (the services and callers in the dependency map), F88 (Phase 4 = the structural canon Phase 4 scores against), Domain Derivation v0.24 MD-6 (the traceability rationale that relocates to `refines_refs`).

## v0.52 Cycle Summary

**Phase 3d (Requirement Derivation) status:** Design begun. Established that the mechanism must be specified at two abstraction levels, consistent with how Domain Derivation is specified — a Row 3 (logical/Designer) mechanism answering the Row 3 Understanding, and a Row 4 (physical/Builder) mechanism answering the Row 4 Understanding. SysEngage is being used to design SysEngage; the rows are SysEngage's own design rows, not project content rows. The Row 3 (logical) Requirement Derivation mechanism is to be written first, then the Row 4 (physical) mechanism traced to it.

**Confirmed Phase 3d design decisions (to be expressed at the correct abstraction level in each spec):**
- D1a — per-Domain derivation scope (logical); start here, switch to whole-row later if required
- D2 — `domain_refs` deterministically derived from `cci_refs` ∩ Domain membership; never AI-proposed (logical decision; physical encoding at Row 4)
- D3 — re-run detection keys on BOTH the eligible CCI set and the active Domain set; a Domain-set change forces full re-derivation (logical decision; SHA-256 / stored-hash encoding is physical)
- D4 — `requirement_type` classification is principle-based, not pattern-based
- D5 — F80 consumed by `domain_id` not name; F80 remains Open

**Findings added:** F81 (Open) — requirement-statement guidance gap; to be closed by correct authoring of `REQUIREMENT_ROW_GUIDANCE` in the Row 3/Row 4 mechanisms.

**Total findings after v0.52:** 81 (F1–F81)

**Next:** Write Row 3 (logical) Requirement Derivation mechanism, using Row 3 Domain Derivation v0.1 as the template and abstraction benchmark. Then Row 4 (physical) Requirement Derivation mechanism traced to it. Ensure F81's requirement-statement guidance is authored into both at the correct abstraction level. Continue F80 monitoring.

## v0.53 Cycle Summary

**Phase 3d artefacts now in place:**

| File | Role |
|---|---|
| `SysEngage_Row_3_Mechanism_Requirement_Derivation_v0_1.md` | Logical authority (Designer) |
| `SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_3.md` | Physical implementation spec (Builder) — Row 1 validated, Row 2 authored |
| `SysEngage_Row_4_Understanding_v0_26.md` | §14 structural framework (indexes the physical spec) |
| `SysEngage_Issues_Tracker_v0_53.md` | Finding disposition |

(Mechanism Spec history: v0.1 row-agnostic, implemented; v0.2 re-framed + Row 1 guidance + CHK-3d-08; v0.3 adds Row 2 REQUIREMENT_ROW_GUIDANCE for Row 2 testing. Understanding history: v0.25 published to build agent for the v0.1 prototype; v0.26 re-pointed to the v0.2/v0.3 physical spec.)

**Validation status by row (Pass 3d Requirement Derivation):**
- **Row 1 — validated** (PMT Run 5, NQPS Run 2). Subject discipline, optional-field policy, Non-Loss, entity completeness all confirmed under v0.2 guidance.
- **Row 2 — guidance authored (Mechanism Spec v0.3 §5.4 REQUIREMENT_ROW_GUIDANCE["2"]), pending test.** Next validation target.
- **Rows 3–6 — short-phrase stubs**, pending their own validation cycles.

**Findings:**
- F81 — Row 1 portion validated and closed; remains Open scoped to Rows 2–6. Type-distribution swing under v0.2 logged as a parked observation.
- F80 — derivation half closed (domain_id consumption confirmed in production); remains Open scoped to the downstream presentation/reporting concern.

**Total findings after v0.53:** 81 (F1–F81); no new findings; F80 and F81 annotated, both remain Open with narrowed scope.

**Next:** Test Row 2 requirement derivation (PMT Row 2, NQPS Row 2) under Mechanism Spec v0.3 §5.4 Row 2 guidance. Validate the Row 2 portion of F81. Watch the type-distribution behaviour at Row 2 for further evidence on the parked type-variance question.

---

## Document End

End of SysEngage Issues Tracker v0.53. Eighty-one findings; no new findings this cycle. F81 Row 1 portion validated (PMT Run 5 / NQPS Run 2) — statement subject discipline and optional-field policy confirmed under Mechanism Spec v0.2; F81 remains Open scoped to Rows 2–6 (Row 2 guidance authored in v0.3, pending test). F80 derivation half closed via domain_id consumption; remains Open scoped to the downstream presentation concern. requirement_type distribution swing under v0.2 logged as a parked observation under the type-variance item.

---

## v0.54 Cycle Summary

**Validation status by row (Pass 3d Requirement Derivation):**
- **Row 1 — validated** (PMT Run 5, NQPS Run 2). Subject discipline, optional-field policy, Non-Loss, completeness.
- **Row 2 — validated** (PMT Row 2 Run 1, NQPS Row 2 Run 1). Subject discipline incl. named-role allowance, Functional-dominant type balance (deliberate), vocabulary clean, Non-Loss.
- **Rows 3–5 — guidance authored (Mechanism Spec v0.4 §5.4), NOT yet validated.** Candidate guidance authored ahead of test. Next validation targets.
- **Row 6 — short-phrase stub**, pending authoring.

**Artefact versions current:**

| File | Role |
|---|---|
| `SysEngage_Row_3_Mechanism_Requirement_Derivation_v0_1.md` | Logical authority |
| `SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_4.md` | Physical spec — Rows 1–2 validated, Rows 3–5 authored pending test |
| `SysEngage_Row_4_Understanding_v0_26.md` | §14 structural framework |
| `SysEngage_Issues_Tracker_v0_54.md` | Finding disposition |

**Findings:**
- F81 — Rows 1 and 2 validated and closed; Open scoped to Rows 3–5 (authored, pending test) and Row 6 (stub). Type-distribution behaviour tracked as a parked observation, now with positive evidence (Row 2) that classification responds to row guidance.
- F80 — derivation half closed; Open scoped to downstream presentation/reporting concern.

**Methodology note:** Rows 1–2 followed the validate-then-author cadence (author one row, test, then author the next). Rows 3–5 were authored together ahead of testing to accelerate the remaining rows, on the strength of the now-proven guidance pattern. This is a deliberate, recorded departure — Rows 3–5 guidance is candidate, not validated, until run evidence confirms each.

**Total findings after v0.54:** 81 (F1–F81); no new findings; F80 and F81 annotated.

**Next:** Test Rows 3–5 requirement derivation against PMT and NQPS (note: NQPS Row 4 has zero CCIs — expect the `no_cci_input` path). Validate the Rows 3–5 portions of F81. Disposition Row 6 (likely a short stub given operational content is rare in the reference projects). Continue tracking the type-variance question with the accumulating per-row evidence.

---

## Document End

End of SysEngage Issues Tracker v0.54. Eighty-one findings; no new findings this cycle. F81 Rows 1 and 2 validated (PMT/NQPS Row 1 and Row 2 runs); Rows 3–5 guidance authored ahead of test in Mechanism Spec v0.4 (candidate, pending validation); F81 remains Open scoped to Rows 3–5 (pending test) and Row 6 (stub). F80 derivation half closed; remains Open scoped to the downstream presentation concern. Type-variance question parked, now with positive Row 2 evidence that classification responds to row guidance.

---

## v0.55 Cycle Summary

**Validation status by row (Pass 3d Requirement Derivation):**
- **Row 1 — validated** (PMT/NQPS Run; PMT AllRows Run 1 confirms no regression).
- **Row 2 — validated** (PMT/NQPS Row 2 Run 1; AllRows Run 1 confirms no regression).
- **Row 3 — validated** (PMT/NQPS AllRows Run 1). Logical subject discipline, zero tech/code/algorithm leaks.
- **Row 4 — validated on single-CCI and zero-CCI cases only**; not stress-tested against rich physical content. Needs a physical-content-rich project.
- **Row 5 — validated** (PMT/NQPS AllRows Run 1). Named-component/interface subject allowance used correctly.
- **Row 6 — unexercised** (no operational CCIs in either reference project); v0.4 short-phrase stub never invoked.

**Artefact versions current:**

| File | Role |
|---|---|
| `SysEngage_Row_3_Mechanism_Requirement_Derivation_v0_1.md` | Logical authority |
| `SysEngage_Row_4_Mechanism_Requirement_Derivation_v0_4.md` | Physical spec — Rows 1–3, 5 validated; Row 4 lightly exercised; Rows 1–5 authored |
| `SysEngage_Row_4_Understanding_v0_26.md` | §14 structural framework |
| `SysEngage_Issues_Tracker_v0_55.md` | Finding disposition |

**Findings:**
- F81 — Rows 1, 2, 3, 5 validated; Row 4 validated on sparse/zero cases only; Row 6 unexercised. **Held Open pending more evidence** (rich Row 4 physical content; Row 6 operational content) per decision. Not closed on absence of evidence.
- F80 — derivation half closed; Open scoped to downstream presentation/reporting concern.

**Total findings after v0.55:** 81 (F1–F81); no new findings; F80 and F81 annotated.

**Next:** Await a project with (a) rich multi-CCI Row 4 physical content and (b) Row 6 operational content, to complete F81 validation. In the interim, Pass 3d Requirement Derivation is production-usable for Rows 1–3 and 5 (and the Row 4 sparse case) across the reference projects. Continue tracking the type-variance question with accumulating per-row evidence. Optional: settle the Row 4 Understanding version-pinning convention (de-version inline mechanism references; pin only in the handoff table) to stop per-increment churn.

---

## Document End

End of SysEngage Issues Tracker v0.55. Eighty-one findings; no new findings this cycle. F81 Rows 1, 2, 3, 5 validated (PMT/NQPS AllRows Run 1 and prior dedicated runs); Row 4 validated only on single-CCI/zero-CCI cases; Row 6 unexercised. F81 **held Open pending more evidence** (rich Row 4 physical content and Row 6 operational content) — not closed on absence of evidence. F80 derivation half closed; remains Open scoped to the downstream presentation concern. Type-variance question parked, with accumulating evidence that classification responds to per-row guidance. Integrity (Non-Loss, completeness, ID allocation, row consistency) flawless across all 94 requirements in the AllRows runs.

---

## v0.56 Cycle Summary

**Cross-row requirement architecture decided (design discussion, no code/runs this cycle).** Five findings (F82–F86) capture a coherent architecture for the Req(n-1)↔Req(n) relationship and the gap-closure flow:

- **F82** — add `refines_refs` (UML «refine», child-carried, many-to-many, empty permitted) to the Requirement payload. Ledger **v2.12 → v2.13**.
- **F83** — reject dual-stream / Pass-3a injection (it atomises the requirement, destroying the link; 3a must stay faithful source capture). Reverses Practitioner-locked F35. Single-stream-first build order confirmed correct.
- **F84** — unparented requirements are expected initially; gap closure uses the **existing** gap→question→answer mechanism (generate parent, drive it down, link forms on re-descent). No new gap-closure engine.
- **F85** — a **separate requirement-matching pass** (IM, bidirectional, three-way outcome no-match/refine-link/duplicate-merge) establishes the links; needed regardless of parent provenance.
- **F86** — empty `refines_refs` is itself the gap trigger; no Concern artefact; 3d-vs-robustness placement is a performance choice only.

**Dependency ordering implied by these decisions:**
1. **Ledger v2.13** — add `refines_refs` (F82). Foundation; everything else depends on the field existing.
2. **Requirement Matching mechanism** (F85) — logical (Row 3) then physical (Row 4) spec, following the Pass 3d two-abstraction-level pattern. Populates `refines_refs`.
3. **Empty-field gap check** (F86) wiring — placement (3d vs robustness) decided on performance.
4. **GQA / iteration-cycle interface** (F84) — confirm the existing mechanism can generate a higher-level requirement and re-invoke the matching pass on re-descent. Likely small, but needs verification against the existing GQA spec.

**Documentation debt created:** Row 1/2/3 Understanding documents describe the now-rejected dual-stream-at-3a model (F83) and need amendment notes; F35's reversal must be reflected wherever F35 is referenced.

**Total findings after v0.56:** 86 (F1–F86). Five added (F82–F86); F80, F81 unchanged.

**Next:** discussion of next steps (sequencing of ledger v2.13, the matching mechanism spec, and the GQA interface verification) — see live discussion. No implementation started this cycle; these are design decisions captured ahead of build.

---

## Document End

End of SysEngage Issues Tracker v0.56. Eighty-six findings; five added this cycle (F82–F86) capturing the cross-row requirement «refine» architecture: ledger `refines_refs` field (v2.13), rejection of dual-stream/Pass-3a injection (reversing F35), gap closure via the existing gap→question→answer mechanism, a separate requirement-matching pass, and empty-`refines_refs`-as-gap-trigger. No code or runs this cycle — design decisions captured ahead of build. F80 and F81 unchanged. Ledger v2.13 (F82) is the gating dependency for the matching mechanism (F85) and the gap check (F86).

---

## v0.57 Cycle Summary

**Foundational concept recorded (F87), reached via isolated sandbox testing — no spec/code/ledger changes.** Per Practitioner discipline (validate before committing to the upheaval of understanding-spec/ledger/process changes), the cross-row approach was tested in isolation on real PMT Row 1↔Row 2 requirement data:

- **Test 1 (matching):** every Row 2 requirement found a plausible Row 1 parent through abstraction-level reasoning. Many-to-many is real (5/12 children refine multiple parents) — validates the `refines_refs` array design. Three-way outcome (no-match/refine-link/duplicate-merge) sufficient; no fourth category needed. Caveat: ~5/12 matches "medium" confidence — the F85 threshold question is real.
- **Test 2 (completeness re-descent, R004):** surfaced a genuine specification gap invisible to every cheaper check — R004 "provide visibility into inventory and status" had only a *constraint* child (R016) limiting visibility, but no child *providing* it, no child holding the *inventory*, and no *who* sourcing the inventory items. Confirmed against R004's source CCIs (the "view" obligation is in the Goal CCI and was dropped at Row 2). Demonstrated that completeness-via-re-descent does work no other mechanism can.
- **Test 2 correction (Practitioner):** the initial re-descent under-derived because it *decomposed* the parent rather than tracing *presuppositions* ("where does the inventory come from? who sources it?"). This led to the F87 insight: completeness is better framed as a **row-aware Zachman-interrogative check** (What/Why/Where/When/Who/How, per-requirement, row-specific) than as open-ended decomposition.

**F87 is the governing framing:** downward elaboration made thorough by interrogative guidance is **gap-prevention, not gap analysis**; GQA is reserved for the **irreducible upward residue** (novel orphans implying missing parents); the **requirement, not the cell, is the unit of completeness** (cross-cutting domains rule out cell-level). F87 governs how F82–F86 are interpreted.

**Methodology note (positive):** the isolated-sandbox approach worked exactly as intended — it validated the architecture's core value (finding a real gap a linear human read would miss) AND surfaced a refinement (interrogatives over decomposition) AND localised the remaining risk (re-derivation noise / interrogative load-bearing judgement) — all WITHOUT touching a single spec, schema, or line of pipeline code. Validation before commitment, as planned.

**The decisive open test (gates F87):** whether downward elaboration can be *made* thorough by row-aware interrogative guidance (so downward gaps never form), or whether it still leaves holes needing post-hoc detection. Re-run R004's elaboration *using the six row-2 interrogatives as explicit derivation guidance* and check whether the full child-set falls out generatively. This is the next sandbox test.

**Total findings after v0.57:** 87 (F1–F87). One added (F87); F80–F86 unchanged.

**Next:** run the decisive interrogative-elaboration test on R004 (sandbox, no commitment). If it confirms F87, proceed to sequence the build (ledger v2.13 → matching mechanism → interrogative guidance into REQUIREMENT_ROW_GUIDANCE → GQA upward-residue interface). If it does not, revisit whether downward completeness needs its own check.

---

## Document End

End of SysEngage Issues Tracker v0.57. Eighty-seven findings; one added this cycle (F87) — the foundational "Is elaboration gap analysis?" framing, reached through isolated sandbox testing of the cross-row approach on real PMT data with no spec/code/ledger changes. Governing principles: good downward elaboration is gap-prevention (not gap analysis); completeness guidance belongs in derivation while gap-analysis passes do not belong in 3d; GQA is for the upward novel-orphan residue only; the requirement (not the cell) is the unit of completeness. The decisive test — whether row-aware interrogative guidance makes downward elaboration generatively thorough — remains open and gates F87. F80–F86 unchanged.

---

## v0.58 Cycle Summary

**Requirement structure and type taxonomy resolved (design discussion + reading of `requirements_document_v6.docx`; no code/runs/spec edits this cycle).**

- **F88 — requirement structural canon.** Requirements take typed Condition-Subject-Predicate-Object patterns; the type selects the slot template. Atomicity is a hard constraint defined precisely by per-type slot rules (compound condition/object/constraint → reject; missing required slot → reject). Three unifications: type-selects-structure; F87 interrogative completeness = type-and-row-aware slot completeness; `requirements_document_v6.docx` IS the Phase 4 quality-scoring framework.
- **F89 — type collapse to Functional / Constraint / Structural.** Performance, Environmental, and quality-attributes are all Constraints; the measured-vs-inspected distinction is carried by `verification_method`, not by extra types. "Non-Functional" renamed "Structural" (the S in BSBA — the composition form the recursive interrogation produces). Ledger enum change rides v2.13 alongside `refines_refs`.

**Methodological guardrail (Practitioner direction):** stop debating requirement types once the set is sufficient to write good requirements. A type earns its place only by doing real work (pattern selection + verification routing). Collapse aggressively; push distinctions into working fields. The triad is sufficient — do not re-open.

**The arc of this design session (F82–F89), for future reference.** Starting from "where do we inject Req(n-1)?", reasoning + isolated sandbox testing on real PMT/NQPS data produced a coherent architecture: reject Pass-3a injection (F83); add `refines_refs` «refine» link (F82); unparented children are expected and gap-closure is the existing GQA upward (F84, F86); a separate IM matching pass establishes links (F85); downward elaboration made thorough by interrogatives is gap-prevention, not gap analysis (F87); requirements take typed CSPO slot patterns with hard atomicity (F88); types collapse to Functional/Constraint/Structural with verification_method carrying the distinction (F89). The recursive object-interrogation that elaborates behaviour bottoms out in structure — deriving BSBA rather than positing it. **No specs, schemas, or pipeline code were changed this session — all decisions captured ahead of build, validated in sandbox.**

**Total findings after v0.58:** 89 (F1–F89). Two added (F88, F89); F80–F87 unchanged.

**Pending build sequence (when design phase closes):** ledger v2.13 (`refines_refs` + `requirement_type` enum collapse to triad) → requirement structural canon into REQUIREMENT_ROW_GUIDANCE / derivation (typed CSPO patterns, slot-based hard atomicity, type-selects-pattern) → requirement-matching pass (F85) → row-aware interrogative elaboration guidance (F87/F88) → GQA upward-residue interface (F84) → Phase 4 quality analysis (= `requirements_document_v6.docx`). Documentation debt: dual-stream amendment notes in Row 1/2/3 Understanding (F83); F35 reversal back-reference.

**Next:** at Practitioner discretion — either continue sandbox validation (the open F87 decisive test: does interrogative guidance make R004's elaboration generatively complete, including the object-recursion to structure), or begin the build sequence starting with ledger v2.13.

---

## Document End

End of SysEngage Issues Tracker v0.58. Eighty-nine findings; two added this cycle (F88 requirement structural canon — typed CSPO patterns, slot-based hard atomicity, type-selects-pattern, Phase 4 framework identified; F89 type collapse to Functional/Constraint/Structural with verification_method carrying the measured/inspected distinction). Both foundational. `requirements_document_v6.docx` confirmed readable and promoted to canonical input (it is the Phase 4 quality framework). Methodological guardrail recorded: stop taxonomy debate once sufficient to write good requirements. No specs/schemas/code changed this session — F82–F89 are captured design decisions, sandbox-validated, ahead of build. Ledger v2.13 (F82 `refines_refs` + F89 enum collapse) is the gating build dependency. F80–F87 unchanged.

---

## v0.59 Cycle Summary

**Project Data Dictionary defined (F90), resolving the structural-matching risk left open by the F87 decisive test.**

The F87 test (this session) confirmed guided interrogative elaboration is generatively complete — R004's full child-set, including the inventory and the structural backbone, fell out of the type-and-row-aware slot interrogation without hand-spotting, and the object-recursion bottomed out in structure (BSBA emergent, as predicted). The test relocated the risk to **structural matching**, which F90 then diagnosed as fundamentally a **language-inconsistency problem** and resolved:

- **One project-wide Data Dictionary**, available to all rows; entity identity row-independent, detail row-dependent.
- **Inclusion rule:** the DD holds whatever behaviour binds to (identity + aliases, attribute existence, value-sets where behaviour references the values, relationships) — never representation/bounds/types/storage (those are row requirements). Test: "can a behavioural requirement reference this by name?"
- **Two registers:** canonical entries + a permanent synonym cross-reference register ("Work opportunity → See Task") that preserves authored terminology (vocabulary Non-Loss) and doubles as the audit surface for alias-resolution decisions.
- **Emergent state model:** DD value-sets + transition behaviour = a state machine (the BSBA binding made concrete).
- Adjusts F85 (DD is the matching substrate; merge judgement relocated to resolve-once entity-resolution time), F88 (Object binds to a DD entry), F89 (Structural type projects the DD).

**Method note:** F90, like F87–F89, was reached and validated entirely in sandbox on real PMT data — the canonical structural model was *derived* (Task + 5 aliases, Inventory as collection, EarningsRecord as derived) to prove the dictionary resolves the matching risk. No specs/schemas/code changed.

**The structural half of the architecture is now coherent.** F82 (refines link) + F85 (matching) + F87 (interrogative elaboration) + F88 (typed CSPO atomicity) + F89 (type triad) + F90 (data dictionary) form a complete account: behaviour is elaborated thoroughly by interrogatives, bottoms out in structure, structure is captured in a controlled-vocabulary DD, behaviour binds to the DD, and the DD doubles as the matching substrate and the state-model source.

**Total findings after v0.59:** 90 (F1–F90). One added (F90); F80–F89 unchanged.

**Pending build sequence (unchanged in order; DD inserted):** ledger v2.13 (`refines_refs` + `requirement_type` enum collapse + **Data Dictionary representation**) → DD + requirement structural canon into derivation (typed CSPO, slot-based atomicity, Object-binds-to-DD) → requirement-matching pass resolving terms against the DD (F85) → row-aware interrogative elaboration guidance (F87/F88) → GQA upward-residue interface (F84) → Phase 4 quality analysis (= `requirements_document_v6.docx`). Documentation debt: dual-stream amendment notes in Row 1/2/3 Understanding (F83); F35 reversal back-reference.

**Next:** at Practitioner discretion — the design phase for the cross-row/structural architecture (F82–F90) is now substantially complete and internally coherent. Natural next step is to begin the build at **ledger v2.13** (the gating dependency: `refines_refs`, the type-enum collapse, and the Data Dictionary representation), or to run one more sandbox validation on the DD alias-resolution gating before committing schema.

---

## Document End

End of SysEngage Issues Tracker v0.59. Ninety findings; one added this cycle (F90 — the project Data Dictionary: single cross-row controlled vocabulary; "behaviour binds to it" inclusion rule; canonical + synonym registers; emergent state model; the substrate for structural matching and Object-slot binding). Foundational. Resolves the structural-matching risk (a language-inconsistency problem) left open by the F87 decisive test, which itself confirmed interrogative elaboration is generatively complete and BSBA emerges from the object-recursion. The structural half of the architecture (F82, F85, F87–F90) is now coherent. No specs/schemas/code changed — all sandbox-validated design decisions ahead of build. Ledger v2.13 (now: `refines_refs` + type-enum collapse + Data Dictionary representation) is the gating build dependency. F80–F89 unchanged.

---

## v0.60 Cycle Summary — CROSS-ROW/STRUCTURAL DESIGN PHASE COMPLETE

**The back-refinement decisive test passed all three pre-committed criteria (F91), closing the design phase.** Re-expressing the real R004 cluster against the DD-canonical vocabulary: Object-binding resolved cleanly; DD structure *forced* atomicity (the "inventory and status" compound became un-expressible and split); no semantic drift — and criterion 3 over-delivered by exposing a material defect (F92: missing parent-approval state, mis-bound EarningsRecord).

**The complete architecture (F82–F91), for reference.** From "where do we inject Req(n-1)?", reasoning + isolated sandbox testing on real PMT/NQPS data produced a coherent cross-row/structural design:
- **F82** `refines_refs` «refine» link (child→parent, many-to-many, empty permitted); ledger v2.13.
- **F83** reject Pass-3a dual-stream injection (atomises the requirement); single-stream-first build order confirmed correct; reverses F35.
- **F84** unparented children expected; gap closure via existing GQA, upward only.
- **F85** separate IM matching pass (no-match/refine-link/duplicate-merge), DD-substrated.
- **F86** empty `refines_refs` = the novel-orphan gap trigger.
- **F87** downward elaboration made thorough by row-aware interrogatives = gap-prevention, not gap analysis; GQA for the upward residue only; requirement (not cell) is the unit. *Validated this phase: interrogative elaboration is generatively complete; BSBA emerges from object-recursion.*
- **F88** typed Condition-Subject-Predicate-Object patterns; slot-based hard atomicity; type-selects-pattern; `requirements_document_v6.docx` IS the Phase 4 quality framework.
- **F89** type triad Functional/Constraint/Structural; `verification_method` carries the measured/inspected distinction.
- **F90** project Data Dictionary: single cross-row controlled vocabulary; "behaviour binds to it" inclusion rule; synonym register (author Non-Loss + audit surface); emergent state model.
- **F91** back-refinement validated; atomicity shown to be DD-enforced; state-model transition-completeness noted as a future gap-detection capability.

**Noted-not-designed (stopping-rule discipline):** state-model transition-completeness as a fourth gap-detection path (F91) — captured, deliberately not designed now, to avoid reopening the closed phase.

**Method (the whole arc):** every decision F82–F92 was reached and validated in isolated sandbox on real data — NO specs, schemas, or pipeline code changed across the entire design phase. Validation before commitment, throughout. The sandbox repeatedly caught things before they were committed (the inventory gap, the language-inconsistency problem, the parent-approval gap), which is the justification for the approach.

**Total findings after v0.60:** 92 (F1–F92). Two added (F91, F92); F80–F90 unchanged.

**NEXT ACTION — begin the build at ledger v2.13.** The gating dependency carries three changes: (1) `refines_refs` array on Requirement (F82); (2) `requirement_type` enum collapse to Functional/Constraint/Structural (F89); (3) Data Dictionary representation (F90 — canonical entries + synonym register). Then, in order: DD + requirement structural canon into derivation (typed CSPO, slot-based atomicity, Object-binds-to-DD) → matching pass resolving terms against the DD (F85) → row-aware interrogative elaboration guidance (F87/F88) → GQA upward-residue interface (F84) → Phase 4 quality analysis (= `requirements_document_v6.docx`). Then formalise the noted state-completeness capability (F91) and verify the PMT regression check (F92).

**Documentation debt (carried):** dual-stream amendment notes in Row 1/2/3 Understanding (F83); F35 reversal back-reference; Row 4 Understanding inline mechanism-version de-version-and-pin (from earlier cycle).

---

## Document End

End of SysEngage Issues Tracker v0.60. Ninety-two findings; two added this cycle (F91 back-refinement validated — all three criteria passed, atomicity shown to be DD-enforced, state-model transition-completeness noted as future capability; F92 the PMT parent-approval dataset defect as a pipeline regression check). **The cross-row/structural design phase (F82–F91) is complete and internally coherent — reached entirely through isolated sandbox testing on real data with no specs/schemas/code changed.** Next action is the build at ledger v2.13 (`refines_refs` + type-enum collapse + Data Dictionary representation). F80–F90 unchanged.

---

## v0.61 Cycle Summary — SPEC-UPDATE PLANNING

**Transitioning from design to structured spec updates.** This cycle scoped the spec-update work for F82–F92 and made the structural ruling that governs it (F93).

**Impact map (verified, not inferred):**
- **Tier 1 — foundation, do first:** `sysengage_minimal_ledger_spec_v2_12.md` → **v2.13** (`refines_refs` F82 + type-enum collapse F89 + Data Dictionary representation F90).
- **Tier 2 — in-flight specs to reconcile:** Row 3 Requirement Derivation v0.1 → v0.2; Row 4 Requirement Derivation v0.4 → v0.5 (type triad, CSPO canon, slot-based atomicity, DD-binding/Matching as declared interfaces); Row 4 Understanding v0.26 → v0.27 (§14 reindex + the de-version-and-pin cleanup).
- **Tier 3 — new specs, authored build-imminent, as standalone services (F93):** Data Dictionary service (Row3+Row4), Requirement Matching service (Row3+Row4), Phase 4 Requirement Quality (= `requirements_document_v6.docx`), interrogative elaboration guidance (into Requirement Derivation §5.4).
- **Tier 4 — dual-stream debt, re-scoped to SUBSTANTIAL REVISION (F93):** Row 3 Reanalysis v0.3 + Row 4 Reanalysis v0.1 reverted to single-stream; Row 1/2/3 Understandings de-dual-streamed; F35 citations cleared; MD-6 traceability relocates to `refines_refs`. **Sequenced after ledger v2.13.**
- **Tier 5 — REMOVED:** `sys_engage_main_process_flow_v9`, `sys_engage_specification_v2`, `Implementation-Plan-Updated_v2`, `SysEngage_Main_Process` are POC source material (information-only), not live specs. The authoritative Phase 4 artefact will be the new mechanism spec, not the process-flow doc.

**F93 rulings:** logical/physical = abstraction-of-the-mechanism (cross-row mechanisms still get Row3/Row4 specs, scope flagged in §1); cross-row mechanisms are standalone services called by the row mechanisms; services are interface dependencies of their callers (sharpens authoring order). Plus the F83 dual-stream debt correction: fully-built-out not stubbed; F83 re-confirmed against the discovery; debt re-scoped annotation → substantial revision, sequenced after v2.13.

**Total findings after v0.61:** 93 (F1–F93). One added (F93); F80–F92 unchanged.

**NEXT ACTION — begin Tier 1: ledger v2.13.** Three changes: `refines_refs` array on Requirement; `requirement_type` enum → Functional/Constraint/Structural; Data Dictionary representation (canonical entries + synonym register). This is the gating dependency for Tier 2 reconciliation, Tier 3 services, and the Tier 4 dual-stream revert.

**Documentation debt (carried):** Tier 4 dual-stream revert (now F93-scoped, post-v2.13); F35 reversal back-reference; Row 4 Understanding de-version-and-pin.

---

## Document End

End of SysEngage Issues Tracker v0.61. Ninety-three findings; one added this cycle (F93 — spec-architecture ruling: cross-row mechanisms are standalone services with the standard Row 3 logical / Row 4 physical two-level treatment; services are interface dependencies of their callers; the F83 dual-stream debt corrected to substantial revision, F83 re-confirmed, MD-6 traceability relocating to `refines_refs`, sequenced after ledger v2.13). The spec-update impact map is verified (Tier 5 removed as POC reference). Next action is Tier 1 — ledger v2.13. F80–F92 unchanged.

---

## v0.62 Cycle Summary — BUILD PROGRESS (Tier 1 + Tier 2 complete; bookkeeping, no new findings)

The structured spec updates began. No findings added or closed; F82/F88/F89 annotated with realisation status (they stay Open until consuming mechanisms run).

**Tier 1 — COMPLETE.** `sysengage_minimal_ledger_spec_v2_13.md` authored from v2.12. `refines_refs` optional array (F82); `requirement_type` enum collapsed to Functional/Constraint/Structural (F89); `verification_method` gains Measurement; Performance-fit-criteria rule → Measurement-fit-criteria rule; Appendix D v2.12→v2.13 migration notes. Data Dictionary deliberately NOT added (Path A / F90 open items). Validated: RequirementPayload parses, three-value enum, refines_refs optional, no stray retired values.

**Tier 2 — COMPLETE.** Reconciled to the closed design, authority-first:
- Row 3 Requirement Derivation **v0.2** (logical authority): §4.1.1(b) hard slot-based atomicity + typed CSPO patterns (F88); §4.1.1(d)/§5.3 type triad + type-selects-pattern (F89); §5.1 schema to v2.13; new §5.5 declared service interfaces (F93).
- Row 4 Requirement Derivation **v0.5** (physical): DDL/Pydantic/normative rules to v2.13; new HARD CHK-3d-09 typed-slot atomicity (F88) gated by VER-3d-15; VER-3d-16 for refines_refs; all five §5.4 guidance blocks reconciled to the triad; refines_refs=[] at construction.
- Row 4 Understanding **v0.27**: §14 reindex to v0.2/v0.5/ledger-v2.13; de-version-and-pin convention adopted (inline refs version-less; exact version only in §14.5 handoff) to stop per-increment churn.

**Realised vs designed-only (the honest line):**
- *Realised in specs:* the `refines_refs` schema, the type triad, the hard atomicity check, the verification_method distinction.
- *Designed-only, not yet specced/built:* Requirement Matching service (F85 — populates refines_refs), Data Dictionary service (F90 — Object-slot binding), the F87/F88 interrogative-elaboration guidance increment (CSPO slot prompts + completeness sweep), Phase 4 Quality spec (= requirements_document_v6.docx).
- *Not yet run:* no derivation run has yet exercised v2.13/v0.5; existing PMT/NQPS data not yet migrated to the triad.

**Total findings after v0.62:** 93 (F1–F93). None added; F82/F88/F89 annotated. 

**NEXT ACTION — Tier 3 (build-imminent authoring) or Tier 4 (dual-stream revert, now unblocked).** Tier 3: author the Data Dictionary service spec (Row3+Row4) — requires closing F90/F85 open items first (alias storage, value-set representation, relationship representation, provenance, alias-resolution gating); author the Requirement Matching service spec (Row3+Row4); author the interrogative-elaboration guidance increment (expands §5.4); author Phase 4 Quality (= requirements_document_v6.docx). Tier 4: revert both Row-Lens Source Re-Analysis specs to single-stream, de-dual-stream Row 1/2/3 Understandings, clear F35 citations, relocate MD-6 traceability rationale to refines_refs — now safe because ledger v2.13 (`refines_refs`) has landed.

**Documentation debt (carried):** Tier 4 dual-stream revert (F93-scoped); F35 reversal back-reference; PMT approval-gap regression check (F92) to run once the pipeline is built.

---

## Document End

End of SysEngage Issues Tracker v0.62. Ninety-three findings (F1–F93); none added this cycle — bookkeeping only. Records Tier 1 (ledger v2.13) and Tier 2 (Row 3 Requirement Derivation v0.2, Row 4 v0.5, Row 4 Understanding v0.27) complete. F82/F88/F89 annotated: ledger+schema portions REALISED, findings stay Open until the consuming mechanisms (Requirement Matching service, interrogative-elaboration guidance, Phase 4) are built and run. Next: Tier 3 service-spec authoring (DD/Matching, gated on F90/F85 open items) or Tier 4 dual-stream revert (now unblocked by v2.13). F80–F93 substance unchanged.

---

## v0.63 Cycle Summary — TIER 3 BEGUN (Data Dictionary; bookkeeping, no new findings)

The Data Dictionary design open items (F90/F85) were closed and the first two DD artefacts authored.

**F90/F85 representation items CLOSED by design decision (reached this session, grounded in the real PMT model):**
- Aliases = `synonym` entries only (single source of truth; a canonical entry has no alias array; aliases found by query). *(Practitioner: "ok with the query being the mechanism for finding synonyms".)*
- Value-sets = a field on the attribute, named-addressable (`Task.status.available` as a dotted path); NOT separate elements; transition/state-model behaviour deferred (F91).
- Relationships = directed `relationship` entries (`from_ref` → `to_ref` + cardinality).
- Provenance = single `provenance_ref` pointer into existing ledger traceability (makes the synonym register auditable at a glance; not a duplicate trace).
- Alias-resolution gating = auto-resolve-with-register-review, confidence-banded; high-confidence auto-records (reviewable/reversible via the register), low-confidence/multi-candidate blocks-and-flags. Threshold a **fixed mechanism constant** — provisional, promotable to ProjectProfile when resolution-confidence data exists (tuning now would be false precision). *(Practitioner: "auto resolve option … fixed constant for now. Difficult to say what real effect tuning the value would have … without data to test it.")*
- DD = **standalone cross-row service** (F93) populated incrementally as rows produce requirements — not a numbered pass. *(Practitioner: "standalone service".)*

**Artefacts authored:**
- **Ledger v2.13 → v2.14:** `DataDictionaryEntry` (DD###, entry_kind ∈ canonical/synonym/relationship) + `DataDictionaryRegister`; no-row-context; JSON schema with entry_kind conditional requireds; migration notes. Requirement element unchanged (Object-binding is mechanism-level). Validated: both payload defs parse; conditional requireds correct; register references GenericRegisterPayload.
- **Data Dictionary Service — Row 3 logical mechanism spec v0.1:** cross-row standalone service; `resolve_term` three-way act (canonical/synonym/flagged); confidence-banded gating; `record_relationship` / `record_value` / read operations; the F90 inclusion rule as a decidable test; per-term idempotency; false-merge rejection propagation flagged as a Row 4 requirement.

**Realised vs designed-only (updated line):**
- *Realised in specs:* DD element types (v2.14); DD service logical contract (Row 3 v0.1).
- *Designed-only, not yet specced/built:* DD service **Row 4 physical** (the resolution-judgement implementation, the literal confidence constant, rejection-propagation, audit carrier); Requirement Matching service (Row3+4); interrogative-elaboration guidance; Phase 4 Quality.
- *Not yet run:* the dictionary is unpopulated; no production run has exercised the DD service; Object-slot binding (Requirement Derivation §5.5) is still a declared interface.

**Total findings after v0.63:** 93 (F1–F93). None added; F90 annotated (representation closed/realised, mechanism logical-specced, stays Open until Row 4 + run).

**NEXT ACTION — Data Dictionary Service Row 4 physical spec** (completes the DD pair): DDL realising v2.14; the resolution-judgement implementation (the §4.1 IM act made concrete — lexical/semantic/model-judged comparison is the main Row 4 decision); the fixed confidence-band constant's literal value; false-merge rejection propagation to dependent Object bindings; the audit-trail carrier. Then: Requirement Matching service (Row3+4); interrogative-elaboration guidance increment (expands Requirement Derivation §5.4); Phase 4 Quality (= requirements_document_v6.docx). Tier 4 dual-stream revert remains unblocked and outstanding.

**Documentation debt (carried):** Tier 4 dual-stream revert (F93-scoped, post-v2.13 — now also post-v2.14); F35 reversal back-reference; PMT approval-gap regression check (F92).

---

## Document End

End of SysEngage Issues Tracker v0.63. Ninety-three findings (F1–F93); none added — bookkeeping. Records Tier 3 begun: F90/F85 representation items closed by design decision; ledger v2.14 (DataDictionaryEntry/DataDictionaryRegister) and the Data Dictionary Service Row 3 logical spec v0.1 authored. F90 annotated (representation realised, mechanism logical-specced, stays Open until Row 4 physical + run). Next: DD Service Row 4 physical spec to complete the pair. F80–F93 substance unchanged.

---

## v0.64 Cycle Summary — REQUIREMENTS BUILD SPEC-COMPLETE (bookkeeping, no new findings)

The requirements-build mechanism set is now fully specified. Authored across this session (Tier 1 → Tier 3):

**The complete requirements artefact set:**
- **Ledger v2.13** — `refines_refs` (F82), type triad (F89), verification_method Measurement.
- **Ledger v2.14** — `DataDictionaryEntry` / `DataDictionaryRegister` (F90).
- **Requirement Derivation** — Row 3 **v0.3** (logical: hard slot atomicity F88, type triad F89, §5.5 service interfaces F93, §4.1.1(f) interrogative completeness F87), Row 4 **v0.6** (physical: DDL/Pydantic to v2.13, CHK-3d-09 hard atomicity, §5.4 interrogative slot guidance, ADVC-3d-02 advisory), Understanding **v0.27** (§14 reindex + de-version-and-pin).
- **Data Dictionary service** — Row 3 **v0.1** + Row 4 **v0.1** (cross-row standalone service F93; three-way term resolution; synonym-as-single-source; named-addressable value-sets; directed relationships; provenance_ref; auto-resolve-with-register-review, fixed-constant band; F90/F85).
- **Requirement Matching service** — Row 3 **v0.1** + Row 4 **v0.1** (cross-row standalone service; populates `refines_refs`; three-way refine-link/no-match/duplicate-merge; DD-anchored pre-filter; bidirectional gaps; F85/F82/F86/F84).
- **Requirement Quality Analysis (Phase 4)** — Row 3 **v0.1** + Row 4 **v0.1** (INCOSE/ISO-29148 framework from `requirements_document_v6.docx`, reconciled to the F89 triad; Functional rules carried, DC/Env/Perf merged into Constraint with verification_method selecting which bite, Structural rules new candidate; read-and-score; iteration gate; F88/F89/F90).

**How the pieces fit (the requirements pipeline, end to end):** Derivation (3d) produces typed, atomic, slot-complete requirements (interrogative elaboration makes the row's set generatively complete) with `refines_refs` empty and Object slots to be DD-bound → the Data Dictionary service resolves Object/entity terms to the controlled vocabulary (the language-consistency authority) → the Requirement Matching service establishes the cross-row «refine» links (`refines_refs`) and surfaces upward/downward gaps for GQA → Phase 4 scores each requirement's quality against the type rules and drives the iteration loop. The DD is the shared vocabulary that makes matching tractable; the slot canon (F88) is shared by derivation's hard atomicity check and Phase 4's scoring (one slot-detector implementation, D-q-2).

**Realisation status (all stay Open until a production run):** F82 (refines_refs schema realised; populated by Matching, specced not run), F85 (Matching specced not run), F87 (interrogative guidance authored; sandbox-validated, built-mechanism not run), F88 (slot canon realised in derivation + Phase 4; not run end-to-end), F89 (triad realised; data not migrated, not run), F90 (DD realised in v2.14 + service specced; dictionary unpopulated, not run). **Nothing is yet exercised by a production run** — the build is spec-complete, not run-validated.

**Filename-convention correction:** the DD and Matching specs were renamed to the standard `SysEngage_Row_<n>_Mechanism_<Name>` form (Practitioner caught a non-conforming name).

**Total findings after v0.64:** 93 (F1–F93). None added; F82/F85/F87/F88/F89/F90 annotated.

**NEXT ACTION — the requirements build is spec-complete; remaining work is (a) RUN it and (b) Tier 4 cleanup.** (a) Exercise the built pipeline on PMT/NQPS — this is the validation that turns the "stays Open" annotations into closures, and the F92 PMT approval-gap regression check (does the pipeline re-find the missing parent-approval state?). (b) Tier 4 dual-stream revert (F93-scoped, unblocked by v2.13/v2.14): revert both Row-Lens Source Re-Analysis specs to single-stream; de-dual-stream Row 1/2/3 Understandings; clear F35 citations; relocate MD-6 traceability to `refines_refs`. Also outstanding: formalise the deferred state-completeness capability (F91); migrate existing PMT/NQPS requirement data to the triad (ledger v2.13/v2.14 Appendix D).

---

## Document End

End of SysEngage Issues Tracker v0.64. Ninety-three findings (F1–F93); none added — bookkeeping. **The requirements build is spec-complete:** ledger v2.13 + v2.14; Requirement Derivation Row 3 v0.3 / Row 4 v0.6 / Understanding v0.27; Data Dictionary service Row 3+4 v0.1; Requirement Matching service Row 3+4 v0.1; Requirement Quality Analysis (Phase 4) Row 3+4 v0.1. F82/F85/F87/F88/F89/F90 annotated — all realised in specs, all stay Open until a production run exercises the built mechanisms. Next: run the pipeline (turns annotations into closures; F92 regression check); Tier 4 dual-stream revert. F80–F93 substance unchanged.

---

## v0.65 Cycle Summary — TIER 4 DUAL-STREAM REVERT COMPLETE (bookkeeping, no new findings)

The dual-stream Pass-3a model is removed across all affected artefacts per finding F83 (with the F93 sequencing/scope ruling). Sequencing was satisfied — ledger v2.13 (`refines_refs`) landed before the revert, so the cross-row traceability the dual-stream provided had its new home (the Requirement Matching service writing `refines_refs`) before the dual-stream was removed.

**Key insight (recorded for future reference):** the single-stream behaviour already existed in the dual-stream specs as the "Row 1 / residual" path — reverting made it universal. The four-stage structure (Domain-chunk assembly / per-chunk classification / chunk dedup / cross-chunk sweep) existed ONLY to serve dual-stream Domain-chunking; with no stream 2 there are no chunks, so it collapses to two stages (Source classification + contradiction sweep). The valuable principle that SURVIVES F83 is *independent source re-analysis per row* (each row re-engages the Sources through its own lens — Strand A v2.6 evidence that row-specific content is missed otherwise); F83 removes only the *second stream* (re-analysing the row-above's Requirements). Cross-row requirement traceability relocates to `refines_refs`.

**Artefacts reverted:**
- **Row 3 Row-Lens Source Re-Analysis v0.3 → v0.4** (logical): clean single-stream; four stages → two; §1–§12 reverted; ledger v2.12 → v2.13; OQ-B1/OQ-B4 (chunking) moot.
- **Row 4 Row-Lens Source Re-Analysis v0.1 → v0.2** (physical): chunk-assembly/dedup/sweep modules removed; spaCy dependency removed; stream-2 Pydantic/DDL fields removed; the Row N-1 Phase 3d hard prerequisite removed (the real dual-stream coupling); two-stage realisation; ledger v2.12 → v2.13.
- **Row 3 Understanding v1.1 → v1.2** (targeted): §3.9.3, §7.10 ("why source re-engagement", with the surviving principle retained), §8.5, §8.17 operationalisation, Phase 3 / Concern / AT-trace / input-boundary / mechanism-behaviour descriptions corrected; RSSF-retirement annotations left intact (still accurate); incidental "dual-stream engagement" phrasing → "source re-engagement".
- **Row 1 Understanding v1.2 → v1.3** (targeted): §8.5 — the "upper-row signal feed" cross-row mechanism (the dual-stream ancestor) reversed; shared provenance + independent source re-analysis retained; `refines_refs` added as the cross-row requirement-traceability mechanism; §11 glossary leftover fixed.
- **Row 2 Understanding v1.1 → v1.2** (targeted, scoped): two signal-feed references (§3.8, §3.9.3 preconditions) corrected to F83-consistent single-stream; §8.17 / RowScopedSourceFindings / ADR-GOV-012 content left UNTOUCHED — that is the pre-dual-stream RSSF-at-Phase-1 lineage (RSSF retirement is an R2-AMEND-8 change not in this version), outside F83's scope.

**Scope discipline observed:** RSSF retirement is a SEPARATE change from the dual-stream model — F83 reverses the dual-stream model, NOT RSSF retirement. The revert carefully preserved RSSF-retirement annotations (the AnalysisPass remains the evidence artefact) while removing only the stream-2 mechanism.

**Total findings after v0.65:** 93 (F1–F93). None added; F83 annotated (realised in artefacts; stays Open until run).

**NEXT ACTION — the spec/design work is now complete; remaining work is RUNNING and a few deferred items.** (a) RUN the built pipeline on PMT/NQPS — closes the "stays Open" annotations across F82/F83/F85/F87/F88/F89/F90, and the F92 PMT approval-gap regression check. (b) Migrate existing PMT/NQPS requirement data to the triad (ledger v2.13/v2.14 Appendix D). (c) Formalise the deferred state-completeness capability (F91). All require a built implementation + execution, which is a different kind of work from the specification this thread contained.

---

## Document End

End of SysEngage Issues Tracker v0.65. Ninety-three findings (F1–F93); none added — bookkeeping. **Tier 4 dual-stream revert complete:** Row 3 Reanalysis v0.4 + Row 4 Reanalysis v0.2 single-stream; Row 3 Understanding v1.2, Row 1 Understanding v1.3, Row 2 Understanding v1.2 dual-stream definitions corrected (targeted; RSSF lineage preserved). F83 realised in the artefacts (stays Open until run). With the requirements build (v0.64) and this revert, the SysEngage specification/design work is complete; remaining work is building and running the pipeline. F80–F93 substance unchanged.
