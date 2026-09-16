"""
Notice pipeline: on notice creation,
1. Generate 2-line summary
2. Assign priority
3. Persist on the notice
"""
import json
import logging

from ai_engine.llm import generate_text
from ai_engine.prompts import (
    SUMMARIZER_SYSTEM, build_summary_prompt,
    fallback_summary, fallback_priority,
)

logger = logging.getLogger('ai_engine')


def process_new_notice(notice, language='en', save=True):
    prompt = build_summary_prompt(notice.content, language=language)
    response = generate_text(
        prompt,
        system=SUMMARIZER_SYSTEM,
        json_mode=True,
        temperature=0.2,
        max_tokens=200,
    )

    if response.success and response.text:
        try:
            data = json.loads(response.text)
            notice.ai_summary = data.get('summary', '').strip()
            notice.ai_priority = data.get('priority', 'medium').lower()
            if notice.ai_priority not in ('low', 'medium', 'high'):
                notice.ai_priority = 'medium'
            notice.ai_summary_source = 'llm'  # if you add a field
        except (json.JSONDecodeError, AttributeError):
            logger.warning(f"Notice summary JSON parse failed: {response.text[:100]}")
            notice.ai_summary = fallback_summary(notice.content)
            notice.ai_priority = fallback_priority(notice.content)
    else:
        notice.ai_summary = fallback_summary(notice.content)
        notice.ai_priority = fallback_priority(notice.content)

    if save:
        notice.save(update_fields=['ai_summary', 'ai_priority', 'updated_at'])
    return notice