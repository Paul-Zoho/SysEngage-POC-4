"""
Output file naming convention — SysEngage_Test_Output_Naming_Convention_v0_2.

Canonical format:
    {ProjectID}_Ph{phase}_{pass}_{passLabel}_R{row}_Run{n}.{ext}

Public API:
    generate_filename(project_id, phase, pass_, row, out_dir, ext) -> str
    validate_filename(filename) -> bool
    PASS_LABEL_MAP: dict[tuple[str, str], str]
    OutputNamingError: exception class
"""

from __future__ import annotations

import os
import re

VALIDATION_PATTERN = re.compile(
    r"^[A-Z]{2,}_Ph\d{2}(_[0-9][a-z])?_[A-Z][A-Za-z]+_R[1-6]_Run\d+\.(json|md)$"
)

PASS_LABEL_MAP: dict[tuple[str, str], str] = {
    ("01", "0a"): "SourceCapture",
    ("01", "0b"): "SegmentCapture",
    ("03", "3a"): "RowLensSourceReanalysis",
    ("03", "3b"): "CCIConstruction",
    ("03", "3c"): "DomainDerivation",
    ("03", "3d"): "RequirementDerivation",
}

_PROJECT_ID_RE = re.compile(r"^[A-Z]{2,}$")
_ROW_RE = re.compile(r"^[1-6]$")


class OutputNamingError(ValueError):
    """Raised when filename generation inputs violate the naming convention."""


def _validate_project_id(project_id: str) -> None:
    if not _PROJECT_ID_RE.match(project_id):
        raise OutputNamingError(
            f"project_id must be 2 or more uppercase letters (A-Z) only. Got: {project_id!r}"
        )


def _validate_row(row: str) -> None:
    if not _ROW_RE.match(row):
        raise OutputNamingError(
            f"row must be a single digit 1–6. Got: {row!r}"
        )


def _pad_phase(phase: str) -> str:
    try:
        return f"{int(phase):02d}"
    except ValueError:
        raise OutputNamingError(f"phase must be an integer. Got: {phase!r}")


def _lookup_pass_label(phase_padded: str, pass_: str | None) -> str:
    key = (phase_padded, pass_)
    if key not in PASS_LABEL_MAP:
        defined = sorted(f"Ph{p}/{s}" for p, s in PASS_LABEL_MAP)
        raise OutputNamingError(
            f"No passLabel defined for phase={phase_padded!r}, pass={pass_!r}. "
            f"Defined pairs: {defined}"
        )
    return PASS_LABEL_MAP[key]


def _build_base_name(
    project_id: str,
    phase_padded: str,
    pass_: str | None,
    pass_label: str,
    row: str,
) -> str:
    if pass_ is not None:
        return f"{project_id}_Ph{phase_padded}_{pass_}_{pass_label}_R{row}"
    return f"{project_id}_Ph{phase_padded}_{pass_label}_R{row}"


def _next_run_number(out_dir: str, base_name: str) -> int:
    """
    Derive the next run number by counting existing files in *out_dir* whose
    name starts with ``{base_name}_Run``.

    Returns the highest run number found + 1, or 1 if the directory is empty
    or does not yet exist.

    Known constraint (from spec §Run number management): if prior output files
    are deleted, renamed, or stored outside *out_dir*, the counter will not
    account for them. This is acceptable in a controlled test environment.
    """
    if not os.path.isdir(out_dir):
        return 1
    prefix = f"{base_name}_Run"
    highest = 0
    for entry in os.listdir(out_dir):
        if not entry.startswith(prefix):
            continue
        rest = entry[len(prefix):]
        dot = rest.find(".")
        if dot == -1:
            continue
        run_str = rest[:dot]
        if run_str.isdigit():
            highest = max(highest, int(run_str))
    return highest + 1


def generate_filename(
    project_id: str,
    phase: str | int,
    pass_: str | None,
    row: str | int,
    out_dir: str,
    ext: str = "json",
) -> str:
    """
    Generate a spec-conformant output filename (basename only, no directory).

    Parameters
    ----------
    project_id:
        Uppercase letters only, 2+ chars. Example: ``"PMT"``.
    phase:
        Phase number. Zero-padded to 2 digits automatically. Example: ``3`` → ``"03"``.
    pass_:
        Pass identifier within the phase. Example: ``"3a"``. Pass ``None`` only
        for phases that have no sub-passes (none currently defined).
    row:
        Zachman row number, 1–6.
    out_dir:
        Directory where outputs are written. Used to derive the run number by
        counting pre-existing files that match the same base pattern.
    ext:
        File extension without the dot. Default ``"json"``.

    Returns
    -------
    str
        Basename. Example: ``"PMT_Ph03_3a_RowLensSourceReanalysis_R1_Run1.json"``.

    Raises
    ------
    OutputNamingError
        If any input violates the convention (invalid project_id, unknown
        phase/pass pair, row out of range).
    """
    project_id = str(project_id)
    row = str(row)
    phase_padded = _pad_phase(str(phase))

    _validate_project_id(project_id)
    _validate_row(row)

    pass_label = _lookup_pass_label(phase_padded, pass_)
    base_name = _build_base_name(project_id, phase_padded, pass_, pass_label, row)
    run_n = _next_run_number(out_dir, base_name)

    filename = f"{base_name}_Run{run_n}.{ext}"
    assert validate_filename(filename), f"BUG: generated filename failed validation: {filename!r}"
    return filename


def validate_filename(filename: str) -> bool:
    """Return True if *filename* satisfies the spec v0.2 validation regex."""
    return bool(VALIDATION_PATTERN.match(filename))
