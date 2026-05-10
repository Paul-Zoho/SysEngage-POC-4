"""
Mode discipline implementation for SysEngage.

Per Row 4 Applied §9: every mechanism Pass declares its Transformation Mode
via the @pass_mode decorator. The decorator records mode_active on AnalysisPass,
instruments execution to detect mode violations, and propagates failure status.

Modes: LPM (Literal Persistence Mode), IM, DM, CM.
Source Capture is pure LPM throughout.
"""

from core.modes.decorator import pass_mode

__all__ = ["pass_mode"]
