"""
Zachman column interrogative framing by row.

Per Row 4 Understanding v0.4 §12.2.1:
  All six column interrogatives are presented in every batch prompt.
  The framing communicates what the AI should look for in each column at each
  row's abstraction level.

COLUMN_INTERROGATIVES[row_ref][column] -> framing string
"""

COLUMN_INTERROGATIVES: dict[int, dict[str, str]] = {
    1: {
        "What": "Things of strategic importance to the enterprise",
        "How": "Processes the enterprise performs",
        "Where": "Locations where the enterprise operates",
        "Who": "Stakeholders in the enterprise context",
        "When": "Events and cycles that matter strategically",
        "Why": "Goals and drivers of the enterprise",
    },
    2: {
        "What": "Business entities and data objects",
        "How": "Business processes and workflows",
        "Where": "Business locations and channels",
        "Who": "Business roles and actors",
        "When": "Business events and timing constraints",
        "Why": "Business rules and objectives",
    },
    3: {
        "What": "Logical data entities and relationships",
        "How": "Logical processes and functions",
        "Where": "Logical locations and nodes",
        "Who": "Logical actors and roles",
        "When": "Logical events and state transitions",
        "Why": "Design constraints and principles",
    },
    4: {
        "What": "Physical data structures and schemas",
        "How": "Physical processes and components",
        "Where": "Physical nodes and infrastructure",
        "Who": "Technical actors and system components",
        "When": "Physical events and scheduling",
        "Why": "Technical constraints and standards",
    },
    5: {
        "What": "Detailed data definitions and formats",
        "How": "Detailed procedures and algorithms",
        "Where": "Detailed network and deployment specs",
        "Who": "Detailed user and system interfaces",
        "When": "Detailed timing and sequencing",
        "Why": "Detailed rules and validation criteria",
    },
    6: {
        "What": "Operational data and content",
        "How": "Operational procedures and tasks",
        "Where": "Operational locations and access points",
        "Who": "Operational users and support roles",
        "When": "Operational schedules and triggers",
        "Why": "Operational policies and compliance",
    },
}

ROW_LENS_LABELS: dict[int, str] = {
    1: "Planner (strategic context)",
    2: "Owner (business context)",
    3: "Designer (logical/conceptual context)",
    4: "Builder (physical/technical context)",
    5: "Implementer (detailed specification context)",
    6: "User (operational context)",
}
