"""
Lightweight re-ranker.

Combines:
  - Vector similarity score (from FAISS)
  - Keyword overlap with query
  - Source-type boost (policy > notice > ticket for student queries)

This is a cheap alternative to running a cross-encoder. For a hackathon,
it gives 80% of the benefit at 5% of the compute cost.
"""
import logging
import re

logger = logging.getLogger(__name__)

SOURCE_BOOST = {
    'policy': 0.15,   # policies are always relevant
    'faq': 0.20,      # FAQs are curated
    'notice': 0.05,
    'config': 0.10,
    'ticket': 0.0,
}


def rerank(query, candidates, top_k=5):
    """Re-rank candidates by combined score."""
    if not candidates:
        return []

    query_tokens = _tokenize(query)

    scored = []
    for c in candidates:
        vec_score = c.get('score', 0)
        text = c.get('text', '')
        meta = c.get('metadata', {})

        # Keyword overlap
        text_tokens = _tokenize(text)
        overlap = len(query_tokens & text_tokens) / max(1, len(query_tokens))

        # Source boost
        source = meta.get('source', '')
        source_bonus = SOURCE_BOOST.get(source, 0.0)

        # Title boost — if query terms appear in title
        title = (meta.get('title') or '').lower()
        title_bonus = 0.10 if any(t in title for t in query_tokens) else 0.0

        final = vec_score + (overlap * 0.25) + source_bonus + title_bonus
        scored.append({**c, 'rerank_score': round(final, 4)})

    scored.sort(key=lambda x: x['rerank_score'], reverse=True)
    return scored[:top_k]


def _tokenize(text):
    tokens = re.findall(r'[a-z]{3,}', (text or '').lower())
    stop = {'the', 'and', 'for', 'are', 'was', 'were', 'with', 'this', 'that',
            'how', 'what', 'when', 'where', 'why', 'who', 'from', 'into', 'about',
            'can', 'will', 'would', 'should', 'could', 'may', 'might', 'must',
            'do', 'does', 'did', 'is', 'am', 'be', 'been', 'being'}
    return set(t for t in tokens if t not in stop)