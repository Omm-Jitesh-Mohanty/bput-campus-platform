"""
Prompts for notice summarization + priority tagging.
"""
SUMMARIZER_SYSTEM = """You are an AI that summarizes college notices for students.

Output STRICT JSON with this shape:
{
  "summary": "<2 sentences, max 40 words>",
  "priority": "high" | "medium" | "low"
}

Priority rules:
- "high"   → exams, deadlines, safety, fee deadlines, class cancellations
- "medium" → events, hostel maintenance, schedule changes without urgency
- "low"    → general info, cultural events, optional activities

If the language is Hindi or Odia, output the summary in that language.
Do NOT include any text outside the JSON.
"""


def build_summary_prompt(content, language='en'):
    lang_note = ''
    if language == 'hi':
        lang_note = '\n\nRespond in Hindi (हिन्दी).'
    elif language == 'or':
        lang_note = '\n\nRespond in Odia (ଓଡ଼ିଆ).'

    return (
        f"Summarize this notice and assign a priority:\n\n"
        f"---\n{content.strip()}\n---{lang_note}"
    )


def fallback_summary(content, max_words=40):
    """Extractive fallback: first 2 sentences, truncate."""
    import re
    clean = re.sub(r'\s+', ' ', content).strip()
    sentences = re.split(r'(?<=[.!?])\s+', clean)
    summary = ' '.join(sentences[:2])
    words = summary.split()
    if len(words) > max_words:
        summary = ' '.join(words[:max_words]) + '…'
    return summary


def fallback_priority(content):
    """Keyword-based priority fallback."""
    text = content.lower()
    high_kw = ['exam', 'urgent', 'deadline', 'fee', 'cancelled', 'emergency',
               'last date', 'mandatory', 'must', 'fire', 'safety']
    medium_kw = ['maintenance', 'schedule', 'changed', 'notice', 'meeting',
                 'hostel', 'water', 'electricity']
    if any(k in text for k in high_kw):
        return 'high'
    if any(k in text for k in medium_kw):
        return 'medium'
    return 'low'