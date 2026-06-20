from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge"


@dataclass
class RetrievedNote:
    title: str
    snippet: str
    score: float


def _tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2]


def _documents() -> list[tuple[str, str]]:
    return [
        (path.stem.replace("-", " ").title(), path.read_text(encoding="utf-8"))
        for path in sorted(DATA_DIR.glob("*.md"))
    ]


def _title_search(query: str, top_k: int) -> list[RetrievedNote]:
    """A deliberately simple baseline used by the retrieval benchmark."""
    terms = set(_tokenize(query))
    notes: list[RetrievedNote] = []
    for title, text in _documents():
        score = len(terms.intersection(_tokenize(title)))
        if score:
            snippet = " ".join(line.strip() for line in text.splitlines() if line.strip())[:420]
            notes.append(RetrievedNote(title=title, snippet=snippet, score=float(score)))
    return sorted(notes, key=lambda note: note.score, reverse=True)[:top_k]


def _bm25_search(query: str, top_k: int) -> list[RetrievedNote]:
    documents = _documents()
    tokenized = [_tokenize(text) for _, text in documents]
    query_terms = _tokenize(query)
    if not query_terms or not documents:
        return []

    average_length = sum(len(tokens) for tokens in tokenized) / len(tokenized)
    document_frequency = Counter(term for tokens in tokenized for term in set(tokens))
    k1, b = 1.5, 0.75
    notes: list[RetrievedNote] = []
    for (title, text), tokens in zip(documents, tokenized, strict=True):
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
            notes.append(RetrievedNote(title=title, snippet=snippet, score=round(score, 4)))
    return sorted(notes, key=lambda note: (-note.score, note.title))[:top_k]


def retrieve_notes(
    query: str,
    top_k: int = 3,
    strategy: Literal["bm25", "title"] = "bm25",
) -> list[RetrievedNote]:
    """Retrieve teaching notes with the benchmark-selected BM25 strategy by default."""
    if strategy == "title":
        return _title_search(query, top_k)
    return _bm25_search(query, top_k)
