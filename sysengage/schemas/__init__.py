"""
Pydantic schemas — canonical entity in-memory representation.

Per Row 4 Applied §7: Pydantic v2 models mirror canonical ledger spec v2.9.
Schemas live here; SQLAlchemy models live in models/; mappers in mappers/.

Finding F20 (agent): Canonical ledger spec v2.9 uses source_text/atom_text for
content fields. Implementation Spec §5.1 refers to Source.content/SourceAtom.content.
Resolution: canonical field names used here (source_text, atom_text).

Finding F21 (agent): SourceAtom.position is not in canonical spec v2.9 but is
required by Implementation Spec §4.4.3 for atom ordering. Added as implementation
extension; not part of canonical ledger JSON export schema.
"""
