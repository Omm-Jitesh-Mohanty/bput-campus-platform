"""
Embedding generation via Ollama's nomic-embed-text.
Falls back to a deterministic hash-based embedding if unavailable.
"""
import hashlib
import logging
import math

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

EMBED_URL = 'http://localhost:11434/api/embeddings'
EMBED_MODEL = 'nomic-embed-text'
EMBED_DIM = 768


def embed_text(text):
    """Return a list of floats (dim=EMBED_DIM)."""
    try:
        r = requests.post(EMBED_URL, json={
            'model': EMBED_MODEL,
            'prompt': text[:8000],
        }, timeout=15)
        r.raise_for_status()
        emb = r.json().get('embedding')
        if emb and isinstance(emb, list):
            return emb, EMBED_MODEL
    except Exception as e:
        logger.warning(f'Ollama embeddings failed: {e}')

    # Fallback: hash-based pseudo-embedding (consistent but not semantic)
    return _hash_embedding(text), 'hash-fallback'


def _hash_embedding(text):
    """Deterministic vector from SHA-256 of tokens."""
    vec = [0.0] * EMBED_DIM
    for token in text.lower().split():
        h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
        for i in range(4):
            idx = (h >> (i * 16)) % EMBED_DIM
            vec[idx] += 1.0
    # Normalize
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)