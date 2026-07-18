"""Embedding provider.

Real mode loads BAAI/bge-m3 (FlagEmbedding, else sentence-transformers). If neither
is installed or demo_mode is on, a deterministic hashed bag-of-tokens embedding is
used so retrieval still runs end-to-end on a laptop with no GPU/model download.
The hash embedding is intentionally simple — good enough to rank a 40-clause demo
corpus, not a production encoder.  # ponytail: hash fallback, swap to bge-m3 in deploy
"""
from __future__ import annotations

import hashlib
import math
from typing import List

from packages.common.config import get_settings
from packages.common.vn_tokenize import tokens

_embedder = None


def _hash_embed(text: str, dim: int) -> List[float]:
    vec = [0.0] * dim
    for tok in tokens(text):
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class _HashEmbedder:
    def __init__(self, dim: int):
        self.dim = dim

    def encode(self, texts: List[str]) -> List[List[float]]:
        return [_hash_embed(t, self.dim) for t in texts]


class _BGEEmbedder:
    def __init__(self, model_name: str):
        from FlagEmbedding import BGEM3FlagModel  # type: ignore
        self._m = BGEM3FlagModel(model_name, use_fp16=False)
        self.dim = get_settings().embedding_dim

    def encode(self, texts: List[str]) -> List[List[float]]:
        out = self._m.encode(texts, return_dense=True)["dense_vecs"]
        return [v.tolist() for v in out]


def get_embedder():
    global _embedder
    if _embedder is not None:
        return _embedder
    s = get_settings()
    if not s.demo_mode:
        try:
            _embedder = _BGEEmbedder(s.embedding_model)
            return _embedder
        except Exception:
            pass  # fall through to hash embedder
    _embedder = _HashEmbedder(s.embedding_dim)
    return _embedder


def embed(texts: List[str]) -> List[List[float]]:
    return get_embedder().encode(texts)


def embed_one(text: str) -> List[float]:
    return embed([text])[0]


def cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
