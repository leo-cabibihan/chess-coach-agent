from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

from sqlalchemy import delete

from .db import init_db, session_scope
from .db_models import KnowledgeChunkRow
from .embeddings import embed_text
from .knowledge import DATA_DIR


THEMES = {
    "king-safety": "king_safety",
    "loose-pieces": "loose_pieces",
    "opening-principles": "opening",
    "tactical-vision": "forcing_tactics",
}


def chunk_words(text: str, size: int = 500, overlap: int = 75) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(1, size - overlap)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + size])
        if chunk:
            chunks.append(chunk)
        if start + size >= len(words):
            break
    return chunks


def ingest_knowledge(data_dir: Path = DATA_DIR) -> int:
    init_db()
    rows: list[KnowledgeChunkRow] = []
    for path in sorted(data_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1) if title_match else path.stem.replace("-", " ").title()
        for index, content in enumerate(chunk_words(text)):
            digest = hashlib.sha256(f"{path.name}:{index}:{content}".encode()).hexdigest()[:24]
            rows.append(
                KnowledgeChunkRow(
                    id=digest,
                    source=path.name,
                    title=title,
                    section=title,
                    theme=THEMES.get(path.stem, "general"),
                    difficulty="all",
                    content=content,
                    embedding=embed_text(f"{title}\n{content}"),
                )
            )
    with session_scope() as session:
        expected_ids = {row.id for row in rows}
        if expected_ids:
            session.execute(delete(KnowledgeChunkRow).where(KnowledgeChunkRow.id.not_in(expected_ids)))
        for row in rows:
            session.merge(row)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Idempotently embed curated chess lessons.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    count = ingest_knowledge(args.data_dir)
    print(f"Seeded {count} lesson chunks.")


if __name__ == "__main__":
    main()
