"""
Smart reply: when admin opens a ticket to resolve,
suggest a resolution note based on past resolved tickets.
"""

import logging

from ai_engine.llm import generate_text
from ai_engine.prompts import REPLY_SYSTEM, build_reply_prompt, fallback_reply
from ai_engine.rag.retriever import retrieve

logger = logging.getLogger('ai_engine')


def _get_similar_resolved_tickets(ticket, top_k=3):
    """Retrieve similar resolved tickets from the FAISS knowledge base."""

    query_parts = [
        getattr(ticket, 'subject', '') or '',
        getattr(ticket, 'raw_input', '') or '',
        getattr(ticket, 'formatted_body', '') or '',
    ]

    query = ' '.join(
        part.strip()
        for part in query_parts
        if part and part.strip()
    )

    if not query:
        return []

    try:
        results = retrieve(
            query,
            audience='admin',
            top_k=10,
            candidate_k=30,
        )
    except Exception as exc:
        logger.exception(
            'Failed to retrieve similar resolved tickets: %s',
            exc,
        )
        return []

    ticket_results = [
        result
        for result in results
        if result.get('metadata', {}).get('source') == 'ticket'
    ]

    return ticket_results[:top_k]


def suggest_resolution_reply(ticket):
    """Return a suggested resolution reply for an admin ticket."""

    similar_results = _get_similar_resolved_tickets(ticket, top_k=3)

    similar_notes = []

    for result in similar_results:
        text = (result.get('text') or '').strip()

        if text:
            similar_notes.append(text)

    prompt = build_reply_prompt(ticket, similar_notes)

    response = generate_text(
        prompt,
        system=REPLY_SYSTEM,
        temperature=0.4,
        max_tokens=200,
    )

    if response.success and response.text:
        return {
            'text': response.text.strip(),
            'source': 'llm',
            'similar_count': len(similar_notes),
            'latency_ms': response.latency_ms,
        }

    return {
        'text': fallback_reply(ticket),
        'source': 'fallback',
        'similar_count': len(similar_notes),
        'error': response.error,
    }