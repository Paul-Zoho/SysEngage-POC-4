"""
AnalysisPass Pydantic schema — per Implementation Spec v0.4 §5.1 and §7,
and canonical ledger spec v2.11 §Element Type — AnalysisPass.

AnalysisPass carries the audit trail for one mechanism execution.
All mechanism-internal data lives on outputs (JSONB) per F4/F10 architectural
commitment — NOT on canonical entity types.

Canonical attributes per v2.11 (F25 resolution — all must be serialised at export):
  pass_id, pass_type, mechanism, execution_status, mode_active,
  declared_transformation_modes, outputs, evaluated_scope,
  pass_started_at, pass_completed_at, elapsed_ms, confidence.

Non-canonical attributes (implementation-internal, stripped at export per F24):
  phase_id — kept for multi-Phase tracking (Q7: Possibility 3).
  practitioner_id, project_id — multi-tenancy anchors.
  mode_violations, ai_model_fingerprints — stored in outputs.

outputs sub-structures:
  outputs.read_witness — Pass 0 Read Witness data (per F10).
  outputs.mechanism_data — mechanism-specific counts and traceability.
  outputs.mode_violations — array of violation records.
  outputs.failure_reason / outputs.failure_pass — on Failed execution.
"""

import re
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, field_validator

PASS_ID_PATTERN = re.compile(r"^P\d{3,}$")

VALID_EXECUTION_STATUSES = {"Success", "Failed", "PartialSuccess", "In-Progress"}


class ReadWitness(BaseModel):
    """
    Read Witness sub-structure on AnalysisPass.outputs.read_witness.
    Per Issue F10 architectural commitment — stored here, not as standalone entity.
    """

    input_hash: str
    byte_count: int
    character_count: int
    read_mode: str = "Full"
    read_completion_status: bool


class MechanismData(BaseModel):
    """mechanism_data sub-structure on AnalysisPass.outputs.mechanism_data."""

    source_count: int = 0
    segment_count: int = 0
    source_atom_count: int = 0
    source_ids: list[str] = []
    cross_source_ordering: list[dict[str, Any]] = []
    non_text_source_ids: list[str] = []
    source_with_decoding_issues_ids: list[str] = []


class AnalysisPass(BaseModel):
    """
    Canonical AnalysisPass entity — audit record for one mechanism execution.
    Not frozen: orchestration layer mutates this during execution lifecycle.

    pass_type, mechanism, evaluated_scope, confidence are canonical per v2.11
    (F25 resolution). They MUST be included in canonical JSON export.
    phase_id is non-canonical (stripped at export) but kept for Phase tracking.
    """

    model_config = ConfigDict(frozen=False)

    pass_id: str
    pass_type: str = "Universal"
    mechanism: str = "SourceCapture"
    evaluated_scope: str = "All input material in this project"
    confidence: float = 1.0
    phase_id: str = "PH001"
    pass_started_at: datetime
    pass_completed_at: datetime | None = None
    execution_status: str
    mode_active: str = "LPM"
    declared_transformation_modes: list[str] = ["LPM"]
    mode_violations: list[dict[str, Any]] = []
    ai_model_fingerprints: list[dict[str, Any]] = []
    elapsed_ms: int | None = None
    practitioner_id: str
    project_id: str
    outputs: dict[str, Any] = {}

    @field_validator("pass_id")
    @classmethod
    def validate_pass_id(cls, v: str) -> str:
        if not PASS_ID_PATTERN.match(v):
            raise ValueError(
                f"pass_id must match ^P\\d{{3,}}$ (canonical ledger spec v2.11). Got: {v!r}"
            )
        return v

    @field_validator("execution_status")
    @classmethod
    def validate_execution_status(cls, v: str) -> str:
        if v not in VALID_EXECUTION_STATUSES:
            raise ValueError(
                f"execution_status must be one of {VALID_EXECUTION_STATUSES}. Got: {v!r}"
            )
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in 0.0..1.0. Got: {v}")
        return v
