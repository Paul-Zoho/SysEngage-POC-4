"""
Custom exceptions for the Source Capture mechanism.

Per Implementation Spec §4.1.4, §4.2.4 — error taxonomy for mechanism failures.
All errors here are Practitioner-actionable and produce auditable AnalysisPass
failure records per §7.5.
"""


class SourceCaptureError(Exception):
    """Base class for all Source Capture mechanism errors."""


class EmptyInputError(SourceCaptureError):
    """
    Raised when Pass 0 encounters zero-byte input.
    Per Implementation Spec §4.1.4: mechanism aborts; AnalysisPass.failure_reason='empty_input'.
    """


class InputAccessError(SourceCaptureError):
    """
    Raised when the input file cannot be opened (file not found, permission denied).
    Per Implementation Spec §4.1.4.
    """


class UnsupportedFormatError(SourceCaptureError):
    """
    Raised when the file extension is unknown AND the .txt fallback decoder fails.
    Per Implementation Spec §4.1.4: Practitioner-actionable error.
    """


class SegmentationPolicyError(SourceCaptureError):
    """
    Raised when the Segmentation policy configuration is invalid.
    Per Implementation Spec §4.2.4: mechanism aborts.
    """


class DecodingError(SourceCaptureError):
    """
    Raised when a file decoder encounters an unrecoverable error.
    Distinguished from partial decode failures (which set read_completion_status=false
    but do not abort the mechanism).
    """
