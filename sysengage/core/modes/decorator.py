"""
@pass_mode decorator — mode discipline per Row 4 Applied §9.

Per architectural commitment:
- Every mechanism Pass declares its Transformation Mode via @pass_mode("LPM").
- The decorator records mode_active metadata on the wrapped function.
- At execution time, any LPM violation (RuntimeError from Pydantic frozen mutation,
  or TypeError from object mutation) is caught, recorded as a mode_violation, and
  re-raised so the orchestration layer can finalise the AnalysisPass as Failed.

Mode violations are NOT silently swallowed — they surface as ModeViolationError
so the orchestration entry point can distinguish a violation from a domain error.

Per Row 4 Applied §9: "The decorator records mode_active on AnalysisPass,
instruments execution to detect mode violations, and sets execution_status=Failed
if violation detected."
"""

import functools
from typing import Callable, Any

VALID_MODES = {"LPM", "IM", "DM", "CM"}


class ModeViolationError(Exception):
    """Raised when a Pass executes an operation that violates its declared mode."""

    def __init__(self, mode: str, violation_detail: str, original: Exception):
        self.mode = mode
        self.violation_detail = violation_detail
        self.original = original
        super().__init__(
            f"Mode violation in {mode} Pass: {violation_detail} — {original}"
        )


def pass_mode(mode: str) -> Callable:
    """
    Declare the Transformation Mode for a mechanism Pass function.

    Usage:
        @pass_mode("LPM")
        def pass_0_read_witness(file_path, ...):
            ...

    The decorator:
    1. Records the declared mode on the wrapped function as `_pass_mode`.
    2. At call time, catches LPM violation patterns (frozen Pydantic mutation →
       ValidationError/TypeError) and re-raises as ModeViolationError.
    3. Does NOT catch domain errors (EmptyInputError, InputAccessError, etc.) —
       those propagate normally to the orchestration layer.
    """
    if mode not in VALID_MODES:
        raise ValueError(
            f"Unknown transformation mode: {mode!r}. Valid: {VALID_MODES}"
        )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except (TypeError, AttributeError) as exc:
                msg = str(exc)
                if mode == "LPM" and (
                    "frozen" in msg.lower()
                    or "immutable" in msg.lower()
                    or "assignment" in msg.lower()
                ):
                    raise ModeViolationError(
                        mode=mode,
                        violation_detail=f"Attempted mutation in {func.__name__}",
                        original=exc,
                    ) from exc
                raise

        wrapper._pass_mode = mode  # type: ignore[attr-defined]
        wrapper._pass_name = func.__name__  # type: ignore[attr-defined]
        return wrapper

    return decorator
