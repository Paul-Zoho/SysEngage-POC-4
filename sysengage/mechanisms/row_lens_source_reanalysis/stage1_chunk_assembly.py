"""
Stage 1 — Domain-Driven Chunk Assembly.

Mode: DM. No AI involvement. Fully deterministic.
Per spec §4.1: reads Domains and Requirements from stream 2 (row_target = row_ref-1),
reads all Sources from stream 1, computes token overlap to assign Sources to chunks.

spaCy en_core_web_sm used for noun phrase extraction and lemmatisation.
chunk_match_threshold from ProjectProfile (default 0.6).

Edge cases:
  - Row 1: empty chunk list; all Sources are residual.
  - Row N>1 with no Domains: all Sources are residual (graceful, not failure).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import spacy
from sqlalchemy import select

from core.db import get_session
from models.domain import DomainModel
from models.requirement import RequirementModel
from models.source import SourceModel

_nlp: spacy.language.Language | None = None


def _get_nlp() -> spacy.language.Language:
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


@dataclass
class ChunkAssemblyResult:
    """
    Output of Stage 1 chunk assembly.

    chunks           — ordered list of Domain chunks with matched Sources
    residuals        — Sources not matched to any Domain
    chunk_assignment — {source_id: [domain_id, ...]} (for audit trail + Stage 3)
    sources_by_id    — all Sources keyed by source_id (for referential integrity)
    requirements_by_id — all stream2 Requirements keyed by requirement_id
    stream1_source_count — total number of Sources in stream 1
    stream2_requirement_count — total Requirements in stream 2
    stream2_domain_count — total Domains in stream 2
    """

    chunks: list[dict]
    residuals: list[dict]
    chunk_assignment: dict[str, list[str]]
    sources_by_id: dict[str, object]
    requirements_by_id: dict[str, object]
    stream1_source_count: int
    stream2_requirement_count: int
    stream2_domain_count: int


def assemble_chunks(
    *,
    project_id: str,
    row_ref: int,
    chunk_match_threshold: float,
) -> ChunkAssemblyResult:
    """
    Stage 1 entry point — assemble Domain chunks from Sources.

    At Row 1: returns empty chunk list; all Sources are residual.
    At Row N>1 with no Domains: returns empty chunk list; all Sources residual.
    """
    session = get_session()
    try:
        # --- Read stream 1: all Sources for this project ---
        source_rows = session.execute(
            select(SourceModel)
            .where(SourceModel.project_id == project_id)
            .order_by(SourceModel.source_id)
        ).scalars().all()

        sources_by_id: dict[str, SourceModel] = {s.source_id: s for s in source_rows}
        source_dicts = [
            {"source_id": s.source_id, "source_text": s.source_text}
            for s in source_rows
        ]

        # --- Row 1 early return: stream 2 is empty by definition ---
        if row_ref == 1:
            return ChunkAssemblyResult(
                chunks=[],
                residuals=source_dicts,
                chunk_assignment={},
                sources_by_id=dict(sources_by_id),
                requirements_by_id={},
                stream1_source_count=len(source_dicts),
                stream2_requirement_count=0,
                stream2_domain_count=0,
            )

        # --- Read stream 2: Domains with row_target = str(row_ref - 1) ---
        stream2_row = str(row_ref - 1)
        domain_rows = session.execute(
            select(DomainModel)
            .where(
                DomainModel.project_id == project_id,
                DomainModel.row_target == stream2_row,
            )
            .order_by(DomainModel.domain_id)
        ).scalars().all()

        # --- Read stream 2: Requirements for those Domains ---
        domain_ids = [d.domain_id for d in domain_rows]
        req_rows: list[RequirementModel] = []
        if domain_ids:
            req_rows = session.execute(
                select(RequirementModel)
                .where(
                    RequirementModel.project_id == project_id,
                    RequirementModel.domain_id.in_(domain_ids),
                )
                .order_by(RequirementModel.requirement_id)
            ).scalars().all()

        requirements_by_id: dict[str, RequirementModel] = {
            r.requirement_id: r for r in req_rows
        }

        # --- No Domains: all Sources are residual (EC-1 graceful) ---
        if not domain_rows:
            return ChunkAssemblyResult(
                chunks=[],
                residuals=source_dicts,
                chunk_assignment={},
                sources_by_id=dict(sources_by_id),
                requirements_by_id=dict(requirements_by_id),
                stream1_source_count=len(source_dicts),
                stream2_requirement_count=len(req_rows),
                stream2_domain_count=0,
            )

        # --- Group Requirements by domain_id ---
        reqs_by_domain: dict[str, list[RequirementModel]] = {
            d.domain_id: [] for d in domain_rows
        }
        for r in req_rows:
            if r.domain_id in reqs_by_domain:
                reqs_by_domain[r.domain_id].append(r)

        # --- Build Domain vocabulary sets via spaCy ---
        nlp = _get_nlp()
        domain_vocabularies: dict[str, set[str]] = {}
        for domain in domain_rows:
            vocab: set[str] = set()
            domain_reqs = reqs_by_domain.get(domain.domain_id, [])
            for req in domain_reqs:
                doc = nlp(req.statement)
                for chunk in doc.noun_chunks:
                    for token in chunk:
                        if not token.is_stop and not token.is_punct:
                            vocab.add(token.lemma_.lower())
                for token in doc:
                    if token.pos_ in ("NOUN", "PROPN") and not token.is_stop:
                        vocab.add(token.lemma_.lower())
            domain_vocabularies[domain.domain_id] = vocab

        # --- Match Sources to Domains ---
        chunk_assignment: dict[str, list[str]] = {}
        for source in source_rows:
            doc = nlp(source.source_text)
            source_tokens = {
                t.lemma_.lower()
                for t in doc
                if not t.is_stop and not t.is_punct and t.is_alpha
            }
            if not source_tokens:
                continue
            for domain in domain_rows:
                vocab = domain_vocabularies[domain.domain_id]
                if not vocab:
                    continue
                overlap = len(source_tokens & vocab) / len(source_tokens)
                if overlap >= chunk_match_threshold:
                    chunk_assignment.setdefault(source.source_id, []).append(
                        domain.domain_id
                    )

        # --- Build chunk list (one entry per Domain) ---
        chunks: list[dict] = []
        matched_source_ids: set[str] = set()
        for domain in domain_rows:
            domain_sources = [
                {"source_id": s.source_id, "source_text": s.source_text}
                for s in source_rows
                if domain.domain_id in chunk_assignment.get(s.source_id, [])
            ]
            if not domain_sources:
                continue
            matched_source_ids.update(s["source_id"] for s in domain_sources)
            domain_reqs = reqs_by_domain.get(domain.domain_id, [])
            chunks.append(
                {
                    "domain_id": domain.domain_id,
                    "domain_name": domain.name,
                    "requirements": [
                        {"requirement_id": r.requirement_id, "statement": r.statement}
                        for r in domain_reqs
                    ],
                    "sources": domain_sources,
                }
            )

        # --- Residuals: Sources not assigned to any Domain ---
        residuals = [
            {"source_id": s.source_id, "source_text": s.source_text}
            for s in source_rows
            if s.source_id not in matched_source_ids
        ]

        return ChunkAssemblyResult(
            chunks=chunks,
            residuals=residuals,
            chunk_assignment=chunk_assignment,
            sources_by_id=dict(sources_by_id),
            requirements_by_id=dict(requirements_by_id),
            stream1_source_count=len(source_dicts),
            stream2_requirement_count=len(req_rows),
            stream2_domain_count=len(domain_rows),
        )

    finally:
        session.close()
