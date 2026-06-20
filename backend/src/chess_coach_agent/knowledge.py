from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge"


@dataclass
class RetrievedNote:
    title: str
    snippet: str
    score: int


def retrieve_notes(query: str, top_k: int = 3) -> list[RetrievedNote]:
    terms = [term.strip(".,?!:;()[]").lower() for term in query.split() if len(term) > 3]
    notes: list[RetrievedNote] = []
    for path in DATA_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        score = sum(lower.count(term) for term in terms)
        if score:
            snippet = " ".join(line.strip() for line in text.splitlines() if line.strip())[:420]
            notes.append(RetrievedNote(title=path.stem.replace("-", " ").title(), snippet=snippet, score=score))
    return sorted(notes, key=lambda note: note.score, reverse=True)[:top_k]
