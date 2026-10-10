"""
FAISS-based retriever with audience filtering and re-ranking.
"""
import logging

from .vector_store import get_vector_store
from .reranker import rerank

logger = logging.getLogger(__name__)


def retrieve(query, audience='both', top_k=5, candidate_k=20, min_score=0.15):
    """
    Retrieve top_k chunks for a query.

    Args:
        query: search string
        audience: 'student' | 'admin' | 'both'
        top_k: final number of chunks
        candidate_k: initial retrieval count (before re-ranking)
        min_score: minimum cosine similarity

    Returns:
        list of {text, metadata, score, rerank_score}
    """
    vs = get_vector_store()
    if len(vs) == 0:
        logger.warning('Vector store is empty — run reindex_rag')
        return []

    # Stage 1: FAISS retrieval
    candidates = vs.search(query, top_k=candidate_k)

    # Filter by audience and score
    filtered = []
    for c in candidates:
        if c['score'] < min_score:
            continue
        aud = c['metadata'].get('audience', 'both')
        if audience != 'both' and aud not in (audience, 'both'):
            continue
        filtered.append(c)

    if not filtered:
        return []

    # Stage 2: re-rank
    reranked = rerank(query, filtered, top_k=top_k)
    return reranked


def retrieve_for_student(query, top_k=5):
    return retrieve(query, audience='student', top_k=top_k)


def retrieve_for_admin(query, top_k=5):
    return retrieve(query, audience='admin', top_k=top_k)