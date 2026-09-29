"""
Intent classifier + department router.
Now backed by config-driven Department.routing_keywords.
"""
import logging

logger = logging.getLogger('ai_engine')


def classify_department(text):
    """
    Return the best-matching department CODE for a complaint.
    Reads keywords from Department.routing_keywords (config-driven).
    Falls back to 'general' if no match.
    """
    if not text:
        return 'general'

    from apps.core.services import ConfigService

    dept = ConfigService.route_to_department(text)
    if dept:
        return dept.code

    # Fallback: if a 'general' department exists, use it
    fallback = ConfigService.department_by_code('general')
    if fallback:
        return fallback.code

    # Last resort
    return 'general'


def classify_priority(text, ticket_type=None):
    """
    Return priority CODE ('low' | 'medium' | 'high' | 'urgent').

    Uses keyword heuristics + optional LLM refinement later.
    """
    from apps.core.services import ConfigService

    # Fetch active priority codes in descending urgency
    priorities = ConfigService.priority_levels()  # ordered by -weight
    priority_codes = [p.code for p in priorities]

    text_l = (text or '').lower()

    # Urgent signals
    urgent_kw = ['fire', 'spark', 'shock', 'flood', 'emergency', 'bleeding',
                 'injur', 'gas leak', 'collapse', 'urgent', 'immediately']
    if any(kw in text_l for kw in urgent_kw):
        return 'urgent' if 'urgent' in priority_codes else priority_codes[0]

    # High signals
    high_kw = ['3 days', '4 days', '5 days', 'one week', 'two weeks',
               'repeated', 'again', 'still not', 'no response', 'very bad',
               'severe', 'dangerous']
    if any(kw in text_l for kw in high_kw):
        return 'high' if 'high' in priority_codes else priority_codes[0]

    # Ticket-type defaults
    if ticket_type in ('leave', 'gatepass'):
        return 'medium' if 'medium' in priority_codes else priority_codes[0]

    return 'medium' if 'medium' in priority_codes else priority_codes[0]


def extract_meta(text):
    """Return dict with department, priority, and matched keywords."""
    from apps.core.services import ConfigService

    dept = ConfigService.route_to_department(text or '')
    priority = classify_priority(text)

    dept_keywords = dept.all_keywords() if dept else []
    text_l = (text or '').lower()
    matched = [kw for kw in dept_keywords if kw and kw.lower() in text_l]

    return {
        'department': dept.code if dept else 'general',
        'priority': priority,
        'matched_keywords': matched[:10],
        'classifier': 'config-driven-v2',
    }