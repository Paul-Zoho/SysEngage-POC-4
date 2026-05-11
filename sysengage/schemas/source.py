"""
Source Pydantic schema — canonical ledger spec v2.11 §Element Type — Source.

Per Row 4 Applied §7 and Implementation Spec v0.4 §5.1.

Critical: model_config frozen=True enforces LPM byte-preservation discipline.
Any attempt to modify source_text after construction raises ValidationError
(Pydantic v2 frozen model), which the @pass_mode("LPM") decorator detects
and records as a mode_violation on AnalysisPass.

Canonical attributes (v2.11, all serialised at export — F24 fix):
  source_id, source_text, segmentation_context, input_material_ref,
  confidence, parent_source_ref.

Non-canonical attributes (implementation-internal, stripped at export per F24):
  is_non_text, has_decoding_issues, project_id.

NO segment_id field (F24 fix). The canonical relation is Segment.source_refs
(Segment → Source via ARRAY). segment_id was a non-canonical inverted relation
that contradicted v2.11 and has been removed.
"""

import re
from pydantic import BaseModel, ConfigDict, field_validator

SOURCE_ID_PATTERN = re.compile(r"^S\d{3,}$")


class Source(BaseModel):
    """
    Canonical Source entity.

    Represents a traceable excerpt from an immutable input artefact, preserved
    verbatim under LPM. frozen=True enforces immutability — attempted mutation
    raises ValidationError per LPM byte-preservation discipline.
    """

    model_config = ConfigDict(frozen=True)

    source_id: str
    source_text: str
    segmentation_context: str
    input_material_ref: str
    confidence: float = 1.0
    parent_source_ref: str | None = None
    is_non_text: bool = False
    has_decoding_issues: bool = False
    project_id: str

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, v: str) -> str:
        if not SOURCE_ID_PATTERN.match(v):
            raise ValueError(
                f"source_id must match ^S\\d{{3,}}$ (canonical ledger spec v2.11). Got: {v!r}"
            )
        return v

    @field_validator("source_text")
    @classmethod
    def validate_source_text_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("source_text must be non-empty for a captured Source.")
        return v

    @field_validator("input_material_ref")
    @classmethod
    def validate_input_material_ref_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("input_material_ref must be non-empty.")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in 0.0..1.0. Got: {v}")
        return v
