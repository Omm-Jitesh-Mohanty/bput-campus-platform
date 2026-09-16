"""
Feedback pipeline: aggregate feedback → actionable insight.
"""
import logging

from ai_engine.llm import generate_text
from ai_engine.prompts import (
    FEEDBACK_SYSTEM, build_feedback_prompt, fallback_feedback_insight,
)

logger = logging.getLogger('ai_engine')


def analyze_feedback(category=None, limit=30):
    """
    Return {'text': str, 'source': 'llm'|'fallback', 'count': int}
    """
    from apps.feedback.models import Feedback

    qs = Feedback.objects.all()
    if category:
        qs = qs.filter(category=category)
    qs = qs.order_by('-created_at')[:limit]
    feedback_list = list(qs)

    if not feedback_list:
        return {'text': 'No feedback yet.', 'source': 'fallback', 'count': 0}

    prompt = build_feedback_prompt(feedback_list, category=category)
    response = generate_text(
        prompt,
        system=FEEDBACK_SYSTEM,
        temperature=0.4,
        max_tokens=350,
    )

    if response.success and response.text:
        return {
            'text': response.text.strip(),
            'source': 'llm',
            'count': len(feedback_list),
            'latency_ms': response.latency_ms,
        }

    return {
        'text': fallback_feedback_insight(qs),
        'source': 'fallback',
        'count': len(feedback_list),
        'error': response.error,
    }