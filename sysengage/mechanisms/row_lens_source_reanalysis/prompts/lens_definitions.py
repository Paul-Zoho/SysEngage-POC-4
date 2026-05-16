"""
Row-specific lens content — single source of truth for Row-Lens classification.

Mirrors Row 3 Mechanism Spec v0.3 §5.2 verbatim.
Keyed by row_ref (int 1-6).

The lens_content string is injected into every classification prompt to
parameterise the analytical abstraction level for that row.
"""

LENS_DEFINITIONS: dict[int, dict[str, str]] = {
    1: {
        "lens_name": "Contextual (Why)",
        "lens_content": (
            "Row 1 — Contextual lens (Why). Zachman Column 1 perspective. "
            "This row addresses the motivation, purpose, and strategic intent of the system. "
            "Relevant content includes: goals, objectives, mission, vision, strategic drivers, "
            "business motivations, policy constraints, organisational context, and stakeholder purpose. "
            "Content is relevant if it addresses WHY the system exists or WHY it must behave as it does. "
            "Content is out-of-scope if it describes HOW the system works, what it does in process terms, "
            "or implementation specifics."
        ),
    },
    2: {
        "lens_name": "Conceptual (What)",
        "lens_content": (
            "Row 2 — Conceptual lens (What). Zachman Column 2 perspective. "
            "This row addresses the conceptual model of the system — what entities, relationships, "
            "and business concepts exist. Relevant content includes: business entities, conceptual "
            "data models, high-level system capabilities, business rules at the concept level, "
            "and stakeholder-facing what-is descriptions. "
            "Content is relevant if it describes WHAT the system deals with in conceptual terms. "
            "Content is out-of-scope if it describes implementation technology, specific algorithms, "
            "code-level constructs, or physical deployment."
        ),
    },
    3: {
        "lens_name": "Logical (How)",
        "lens_content": (
            "Row 3 — Logical lens (How). Zachman Column 3 perspective. "
            "This row addresses the logical design — how the system works in architectural terms. "
            "Relevant content includes: logical data models, process flows, system interfaces, "
            "service definitions, API contracts at the logical level, data transformation logic, "
            "and architectural patterns. "
            "Content is relevant if it describes HOW the system functions logically. "
            "Content is out-of-scope if it is purely motivational (why), purely conceptual (what entities exist), "
            "or implementation-physical (specific technology choices, code)."
        ),
    },
    4: {
        "lens_name": "Physical (With What)",
        "lens_content": (
            "Row 4 — Physical lens (With What). Zachman Column 4 perspective. "
            "This row addresses the physical design — with what technology and infrastructure. "
            "Relevant content includes: technology stack choices, database schemas, deployment "
            "infrastructure, physical data models, programming language choices, framework selection, "
            "and concrete implementation decisions. "
            "Content is relevant if it specifies WHAT TECHNOLOGY is used for implementation. "
            "Content is out-of-scope if it is purely logical design, conceptual, or motivational."
        ),
    },
    5: {
        "lens_name": "Detailed (Who/Where/When)",
        "lens_content": (
            "Row 5 — Detailed lens (Who/Where/When). Zachman Column 5-6 perspective. "
            "This row addresses operational detail — who operates the system, where it runs, "
            "when it executes. Relevant content includes: organisational roles, deployment locations, "
            "operational schedules, SLA definitions, capacity plans, operational runbooks, "
            "and support/maintenance procedures. "
            "Content is relevant if it addresses operational context, roles, timing, or location. "
            "Content is out-of-scope if it is architectural design, conceptual modelling, or purely motivational."
        ),
    },
    6: {
        "lens_name": "Functioning (As-Built)",
        "lens_content": (
            "Row 6 — Functioning lens (As-Built). Zachman Column 6 perspective. "
            "This row addresses the system as it actually functions — the as-built reality. "
            "Relevant content includes: actual implementation code, deployed configuration, "
            "observed behaviour, production metrics, actual (not planned) infrastructure, "
            "and built artefacts. "
            "Content is relevant if it describes the ACTUAL BUILT system, not planned or designed. "
            "Content is out-of-scope if it is planning, design, conceptual, or motivational."
        ),
    },
}


def get_lens_content(row_ref: int) -> str:
    """Return the lens content string for the given row_ref (1-6)."""
    defn = LENS_DEFINITIONS.get(row_ref)
    if not defn:
        raise ValueError(
            f"No lens definition for row_ref={row_ref}. Valid values: 1-6."
        )
    return defn["lens_content"]


def get_lens_name(row_ref: int) -> str:
    """Return the lens name for the given row_ref (1-6)."""
    defn = LENS_DEFINITIONS.get(row_ref)
    if not defn:
        raise ValueError(
            f"No lens definition for row_ref={row_ref}. Valid values: 1-6."
        )
    return defn["lens_name"]
