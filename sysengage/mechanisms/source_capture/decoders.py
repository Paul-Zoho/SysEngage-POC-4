"""
Format-specific decoders for Source Capture Pass 0 (Read Witness).

Per Implementation Spec §3.2: separate decoder per supported file format.
Decoders return canonical character stream + byte content. Pass 0 consumes
the abstraction without knowing format details.

Supported formats:
  .txt — plain UTF-8 text (with latin-1 fallback)
  .md  — Markdown treated as plain text (structure preserved for Pass 0A)
  .docx — Word document via python-docx
  .pdf  — PDF via pypdf

Per LPM discipline: decoders MUST NOT modify content. They provide a read-only
character stream. Any normalisation that changes bytes violates LPM.

Implementation note on byte-preservation:
  For .docx and .pdf, the decoder extracts text via the library's canonical
  text extraction. The extracted text is the "decoded character stream" used
  for Source production. The raw binary bytes of the file are hashed and
  counted in Pass 0 (input_hash, byte_count) for integrity verification.
  The character_count reflects the post-decode character count.
"""

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from mechanisms.source_capture.errors import (
    InputAccessError,
    UnsupportedFormatError,
    DecodingError,
)


SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}


@dataclass
class DecodeResult:
    """
    Output of a format-specific decoder.

    text: decoded character stream (verbatim from decoder; no further normalisation)
    input_hash: SHA-256 of raw file bytes
    byte_count: total raw file bytes
    character_count: total characters in decoded text
    read_completion_status: False if decoding failed mid-stream (partial result)
    partial_failure_detail: non-empty if read_completion_status is False
    format_detected: file format used for decoding
    """

    text: str
    input_hash: str
    byte_count: int
    character_count: int
    read_completion_status: bool
    partial_failure_detail: str
    format_detected: str


def decode_file(file_path: Path) -> DecodeResult:
    """
    Decode input file and return DecodeResult.

    Format detection from extension. Fallback to .txt decoder for unknown extensions.
    Raises UnsupportedFormatError if extension unknown AND .txt fallback fails.
    Raises InputAccessError if file cannot be opened.
    """
    if not file_path.exists():
        raise InputAccessError(f"File not found: {file_path}")

    try:
        raw_bytes = file_path.read_bytes()
    except PermissionError as exc:
        raise InputAccessError(f"Permission denied reading {file_path}: {exc}") from exc
    except OSError as exc:
        raise InputAccessError(f"Cannot open {file_path}: {exc}") from exc

    ext = file_path.suffix.lower()

    if ext in (".txt", ".md"):
        return _decode_text(raw_bytes, ext)
    elif ext == ".docx":
        return _decode_docx(raw_bytes, file_path)
    elif ext == ".pdf":
        return _decode_pdf(raw_bytes, file_path)
    else:
        # Unknown extension — attempt .txt fallback per Implementation Spec §4.1.4
        try:
            result = _decode_text(raw_bytes, ".txt")
            result = DecodeResult(
                text=result.text,
                input_hash=result.input_hash,
                byte_count=result.byte_count,
                character_count=result.character_count,
                read_completion_status=result.read_completion_status,
                partial_failure_detail=result.partial_failure_detail,
                format_detected=f"txt-fallback-from-{ext}",
            )
            return result
        except (UnicodeDecodeError, DecodingError) as exc:
            raise UnsupportedFormatError(
                f"Extension {ext!r} is not supported and .txt fallback failed: {exc}"
            ) from exc


def _compute_hash_and_count(raw_bytes: bytes) -> tuple[str, int]:
    """Compute SHA-256 hex digest and byte count of raw file bytes."""
    digest = hashlib.sha256(raw_bytes).hexdigest()
    return digest, len(raw_bytes)


def _decode_text(raw_bytes: bytes, ext: str) -> DecodeResult:
    """
    Decode plain text (.txt, .md) — try UTF-8 first, fall back to latin-1.

    Per LPM: no whitespace collapse, no normalisation. The decoded string
    is the verbatim character stream from the file.
    """
    input_hash, byte_count = _compute_hash_and_count(raw_bytes)

    try:
        text = raw_bytes.decode("utf-8")
        read_completion_status = True
        partial_failure_detail = ""
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("latin-1")
            read_completion_status = True
            partial_failure_detail = ""
        except UnicodeDecodeError as exc:
            raise DecodingError(
                f"Cannot decode {ext} file as UTF-8 or latin-1: {exc}"
            ) from exc

    return DecodeResult(
        text=text,
        input_hash=input_hash,
        byte_count=byte_count,
        character_count=len(text),
        read_completion_status=read_completion_status,
        partial_failure_detail=partial_failure_detail,
        format_detected=ext.lstrip(".") or "txt",
    )


def _decode_docx(raw_bytes: bytes, file_path: Path) -> DecodeResult:
    """
    Decode .docx via python-docx.

    Extracts paragraphs preserving structure markers (Heading styles).
    Returns text with paragraph boundaries as newlines; heading paragraphs
    prefixed with '# ' (H1) or '## ' (H2+) for downstream Pass 0A detection.

    Per LPM: paragraph text extracted verbatim; no word-wrap, no cleanup.
    """
    try:
        import docx  # type: ignore[import]
    except ImportError as exc:
        raise DecodingError("python-docx is not installed") from exc

    input_hash, byte_count = _compute_hash_and_count(raw_bytes)

    try:
        doc = docx.Document(io.BytesIO(raw_bytes))
    except Exception as exc:
        return DecodeResult(
            text="",
            input_hash=input_hash,
            byte_count=byte_count,
            character_count=0,
            read_completion_status=False,
            partial_failure_detail=f"docx parse failed: {exc}",
            format_detected="docx",
        )

    lines: list[str] = []
    partial = False
    partial_detail = ""

    try:
        for para in doc.paragraphs:
            style_name = (para.style.name or "").lower()
            text = para.text
            if "heading 1" in style_name:
                lines.append(f"# {text}")
            elif "heading" in style_name:
                lines.append(f"## {text}")
            else:
                lines.append(text)
    except Exception as exc:
        partial = True
        partial_detail = f"docx paragraph extraction failed mid-document: {exc}"

    full_text = "\n".join(lines)

    return DecodeResult(
        text=full_text,
        input_hash=input_hash,
        byte_count=byte_count,
        character_count=len(full_text),
        read_completion_status=not partial,
        partial_failure_detail=partial_detail,
        format_detected="docx",
    )


def _decode_pdf(raw_bytes: bytes, file_path: Path) -> DecodeResult:
    """
    Decode .pdf via pypdf.

    Extracts text page by page. On corrupt/unreadable pages, records
    read_completion_status=False and captures text from successfully-decoded pages.
    Per Implementation Spec §4.1.4: partial decode strategy.
    """
    try:
        from pypdf import PdfReader  # type: ignore[import]
        from pypdf.errors import PdfReadError  # type: ignore[import]
    except ImportError as exc:
        raise DecodingError("pypdf is not installed") from exc

    input_hash, byte_count = _compute_hash_and_count(raw_bytes)

    partial = False
    partial_detail = ""
    pages_text: list[str] = []

    try:
        reader = PdfReader(io.BytesIO(raw_bytes), strict=False)
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                pages_text.append(page_text)
            except Exception as exc:
                partial = True
                partial_detail = f"Failed to extract page {page_num}: {exc}"
    except Exception as exc:
        partial = True
        partial_detail = f"PDF structure corrupt or unreadable: {exc}"

    full_text = "\n".join(pages_text)

    return DecodeResult(
        text=full_text,
        input_hash=input_hash,
        byte_count=byte_count,
        character_count=len(full_text),
        read_completion_status=not partial,
        partial_failure_detail=partial_detail,
        format_detected="pdf",
    )
