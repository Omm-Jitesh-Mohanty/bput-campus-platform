"""
Retriever: find similar past tickets for smart-reply generation.
Uses simple keyword Jaccard similarity. Upgradeable to embeddings.
"""
# from tickets.models import CampusTicket
from apps.tickets.models import CampusTicket


def _tokenize(text):
    import re
    text = (text or '').lower()
    tokens = re.findall(r'[a-z]+', text)
    stop = {'the', 'a', 'an', 'is', 'are', 'was', 'of', 'and', 'or', 'in', 'on',
            'for', 'to', 'with', 'this', 'that', 'it', 'my', 'me', 'i', 'at',
            'room', 'please', 'kindly'}
    return {t for t in tokens if t not in stop and len(t) > 2}


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_similar_resolved(ticket, top_k=3, min_score=0.15):
    """
    Find similar resolved tickets for RAG context.
    Match by department + type first, then rank by keyword similarity.
    """
    candidates = CampusTicket.objects.filter(
        status='resolved',
        assigned_department=ticket.assigned_department,
    ).exclude(id=ticket.id)[:50]

    # If none in same dept, widen the net
    if not candidates:
        candidates = CampusTicket.objects.filter(
            status='resolved',
        ).exclude(id=ticket.id)[:50]

    ticket_tokens = _tokenize(ticket.raw_input) | _tokenize(ticket.subject)

    scored = []
    for c in candidates:
        c_tokens = _tokenize(c.raw_input) | _tokenize(c.subject)
        score = _jaccard(ticket_tokens, c_tokens)
        if score >= min_score:
            scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def get_resolution_context(ticket, top_k=3):
    """Return list of resolution note strings for prompt context."""
    similar = find_similar_resolved(ticket, top_k=top_k)
    return [t.resolution_note for t in similar if t.resolution_note]