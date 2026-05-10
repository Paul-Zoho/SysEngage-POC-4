"""
Sequential orchestrator for SysEngage v1.

Per Implementation Spec §3.1 and replit.md: sequential runner for the
v1 single-mechanism scope. Invokes Source Capture for the v1 build.

No workflow engine or event-driven coordination for v1 — sequential
runner suffices. Downstream mechanisms (Actor Signal Identification,
Row-Lens Source Re-Analysis) will be added in subsequent cycles.
"""

from pathlib import Path
from typing import Any

from mechanisms.source_capture import run_source_capture, SourceCaptureResult


def run_source_capture_for_project(
    file_path: Path,
    *,
    project_id: str,
    practitioner_id: str,
    read_mode: str = "Full",
    segmentation_policy: str = "default",
    re_execution_context: dict[str, Any] | None = None,
) -> SourceCaptureResult:
    """
    Orchestrator entry point for Source Capture.

    For v1, this is the only mechanism. Future mechanisms will be added
    here in sequence. The orchestrator's role is to coordinate mechanism
    invocation and pass project context.

    Args:
        file_path: Absolute or relative path to the input file.
        project_id: Canonical project identifier.
        practitioner_id: Practitioner stakeholder identifier.
        read_mode: "Full" (default) or "Sampling" (Practitioner override).
        segmentation_policy: Segmentation policy name ("default" for v1).
        re_execution_context: If provided, triggers re-execution semantics
            (append new Sources without reprocessing existing ones).

    Returns:
        SourceCaptureResult with pass_id, entity counts, and execution status.
    """
    return run_source_capture(
        file_path,
        project_id=project_id,
        practitioner_id=practitioner_id,
        read_mode=read_mode,
        segmentation_policy=segmentation_policy,
        re_execution_context=re_execution_context,
    )
