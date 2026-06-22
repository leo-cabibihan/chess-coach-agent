from __future__ import annotations

import hashlib
import math
import os
import re
from functools import lru_cache


MODEL_NAME = "BAAI/bge-small-en-v1.5"
DIMENSIONS = 384


@lru_cache(maxsize=1)
def _model():
    if os.getenv("ENABLE_LOCAL_EMBEDDINGS", "false").lower() not in {"1", "true", "yes"}:
        return None
    try:
        from fastembed import TextEmbedding

        return TextEmbedding(model_name=MODEL_NAME)
    except Exception:
        return None


def _deterministic_embedding(text: str) -> list[float]:
    values = [0.0] * DIMENSIONS
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:2], "big") % DIMENSIONS
        values[index] += 1.0 if digest[2] % 2 else -1.0
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def embed_text(text: str) -> list[float]:
    model = _model()
    if model is None:
        return _deterministic_embedding(text)
    return list(next(iter(model.embed([text]))))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0
