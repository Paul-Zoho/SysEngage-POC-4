"""
Zachman column vocabulary — permitted classification_type values per column.

Per CCI Construction Mechanism Spec v0.2 §5 and Row 3 Mechanism Spec v0.2 §5.1:
  These are the stable, row-agnostic vocabulary terms for classification_type.
  The AI is explicitly prompted to use these terms.
  Stage 3b validation MUST reject any AI-returned classification_type not in
  this vocabulary for the assigned column.
"""

COLUMN_VOCABULARY: dict[str, list[str]] = {
    "What": ["Entity", "Attribute", "Relationship"],
    "How": ["Process", "Function", "Rule"],
    "Where": ["Location", "Node", "Network"],
    "Who": ["Actor", "Role", "Organisation"],
    "When": ["Event", "Cycle", "Trigger"],
    "Why": ["Goal", "Principle", "Constraint"],
}

COLUMNS: list[str] = ["What", "How", "Where", "Who", "When", "Why"]

VALID_COLUMNS: set[str] = set(COLUMNS)
