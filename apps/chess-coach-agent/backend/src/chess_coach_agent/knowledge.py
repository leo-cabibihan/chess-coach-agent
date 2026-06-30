from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .embeddings import cosine_similarity, embed_text


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge"


@dataclass
class RetrievedNote:
    title: str
    snippet: str
    score: float
    source: str = ""
    retrieval_method: str = "bm25"


def _tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2]


def _documents() -> list[tuple[str, str, str]]:
    return [
        (path.stem.replace("-", " ").title(), path.read_text(encoding="utf-8"), path.name)
        for path in sorted(DATA_DIR.glob("*.md"))
    ]


def _title_search(query: str, top_k: int) -> list[RetrievedNote]:
    """A deliberately simple baseline used by the retrieval benchmark."""
    terms = set(_tokenize(query))
    notes: list[RetrievedNote] = []
    for title, text, source in _documents():
        score = len(terms.intersection(_tokenize(title)))
        if score:
            snippet = " ".join(line.strip() for line in text.splitlines() if line.strip())[:420]
            notes.append(
                RetrievedNote(title=title, snippet=snippet, score=float(score), source=source, retrieval_method="title")
            )
    return sorted(notes, key=lambda note: note.score, reverse=True)[:top_k]


def _bm25_search(query: str, top_k: int) -> list[RetrievedNote]:
    documents = _documents()
    tokenized = [_tokenize(text) for _, text, _ in documents]
    query_terms = _tokenize(query)
    if not query_terms or not documents:
        return []

    average_length = sum(len(tokens) for tokens in tokenized) / len(tokenized)
    document_frequency = Counter(term for tokens in tokenized for term in set(tokens))
    k1, b = 1.5, 0.75
    notes: list[RetrievedNote] = []
    for (title, text, source), tokens in zip(documents, tokenized, strict=True):
        frequencies = Counter(tokens)
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse_frequency = math.log(
                1 + (len(documents) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5)
            )
            denominator = frequency + k1 * (1 - b + b * len(tokens) / max(average_length, 1))
            score += inverse_frequency * frequency * (k1 + 1) / denominator
        if score:
            snippet = " ".join(line.strip() for line in text.splitlines() if line.strip())[:420]
            notes.append(
                RetrievedNote(
                    title=title,
                    snippet=snippet,
                    score=round(score, 4),
                    source=source,
                    retrieval_method="bm25",
                )
            )
    return sorted(notes, key=lambda note: (-note.score, note.title))[:top_k]


def _vector_search(query: str, top_k: int) -> list[RetrievedNote]:
    query_embedding = embed_text(query)
    notes = []
    for title, text, source in _documents():
        score = cosine_similarity(query_embedding, embed_text(f"{title}\n{text}"))
        notes.append(
            RetrievedNote(
                title=title,
                snippet=" ".join(line.strip() for line in text.splitlines() if line.strip())[:420],
                score=round(score, 4),
                source=source,
                retrieval_method="vector",
            )
        )
    return sorted(notes, key=lambda note: (-note.score, note.title))[:top_k]


def _hybrid_search(query: str, top_k: int) -> list[RetrievedNote]:
    """Fuse lexical and semantic ranks with reciprocal rank fusion (k=60)."""
    lexical = _bm25_search(query, len(_documents()))
    semantic = _vector_search(query, len(_documents()))
    by_title = {note.title: note for note in [*lexical, *semantic]}
    scores: Counter[str] = Counter()
    for ranking in (lexical, semantic):
        for rank, note in enumerate(ranking, start=1):
            scores[note.title] += 1 / (60 + rank)
    results = []
    for title, score in scores.items():
        note = by_title[title]
        results.append(
            RetrievedNote(
                title=title,
                snippet=note.snippet,
                score=round(score, 6),
                source=note.source,
                retrieval_method="hybrid_rrf",
            )
        )
    return sorted(results, key=lambda note: (-note.score, note.title))[:top_k]


def production_strategy() -> Literal["bm25", "hybrid"]:
    """Use hybrid only after the checked-in benchmark has cleared its guardrails."""
    override = os.getenv("RETRIEVAL_STRATEGY", "").lower()
    if override in {"bm25", "hybrid"}:
        return override  # type: ignore[return-value]
    results_path = DATA_DIR.parent / "eval" / "retrieval_results.json"
    if results_path.exists():
        import json

        results = json.loads(results_path.read_text(encoding="utf-8"))
        if results.get("production_strategy") == "hybrid":
            return "hybrid"
    return "bm25"


def retrieve_notes(
    query: str,
    top_k: int = 3,
    strategy: Literal["bm25", "title", "vector", "hybrid", "production"] = "production",
) -> list[RetrievedNote]:
    """Retrieve teaching notes using the benchmark-selected production strategy."""
    if strategy == "production":
        strategy = production_strategy()
    if strategy == "title":
        return _title_search(query, top_k)
    if strategy == "vector":
        return _vector_search(query, top_k)
    if strategy == "hybrid":
        return _hybrid_search(query, top_k)
    return _bm25_search(query, top_k)
