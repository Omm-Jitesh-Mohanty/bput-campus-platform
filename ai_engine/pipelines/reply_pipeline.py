"""
Smart reply: when admin opens a ticket to resolve,
suggest a resolution note based on past resolved tickets.
"""
import logging

from ai_engine.llm import generate_text
from ai_engine.prompts import REPLY_SYSTEM, build_reply_prompt, fallback_reply
from ai_engine.rag import get_resolution_context

logger = logging.getLogger('ai_engine')


def suggest_resolution_reply(ticket):
    """Return {'text': str, 'source': 'llm'|'fallback', 'similar_count': int}"""
    similar_notes = get_resolution_context(ticket, top_k=3)

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