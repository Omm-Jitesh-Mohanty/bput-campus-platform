"""
Real embeddings via Ollama's nomic-embed-text model.
Falls back to a deterministic hash if Ollama is unavailable.
"""
import hashlib
import logging
import math

import requests

logger = logging.getLogger(__name__)

OLLAMA_EMBED_URL = 'http://localhost:11434/api/embeddings'
EMBED_MODEL = 'nomic-embed-text'
EMBED_DIM = 768
TIMEOUT = 20


def embed_text(text):
    """Return (list[float], model_name). Always succeeds."""
    text = (text or '').strip()
    if not text:
        return [0.0] * EMBED_DIM, 'empty'

    try:
        r = requests.post(OLLAMA_EMBED_URL, json={
            'model': EMBED_MODEL,
            'prompt': text[:8000],
        }, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        emb = data.get('embedding')
        if isinstance(emb, list) and len(emb) > 100:
            return emb, EMBED_MODEL
    except Exception as e:
        logger.warning(f'Embedding failed, using hash fallback: {e}')

    return _hash_embedding(text), 'hash-fallback'


def embed_batch(texts, batch_size=16):
    """Embed a list of texts. Returns list of (embedding, model)."""
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        for t in batch:
            results.append(embed_text(t))
    return results


def _hash_embedding(text):
    """Deterministic fallback — not semantic but stable."""
    vec = [0.0] * EMBED_DIM
    for token in text.lower().split():
        h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
        for i in range(4):
            idx = (h >> (i * 16)) % EMBED_DIM
            vec[idx] += 1.0
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