"""
Intent classifier + department router.
Rule-based for speed and reliability; upgradeable to embedding-based later.
"""
import re
from apps.core.constants import (
    ROUTING_DEPARTMENTS, PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_URGENT,
)

# Keyword → department mapping
ROUTING_KEYWORDS = {
    'plumbing': ['tap', 'water leak', 'leak', 'pipe', 'toilet', 'flush', 'drain',
                 'bathroom', 'geyser', 'shower', 'nal', 'pani'],
    'electrical': ['fan', 'light', 'bulb', 'tube light', 'electricity', 'power',
                   'socket', 'plug', 'switch', 'wire', 'shock', 'spark', 'meter',
                   'bijli', 'current'],
    'civil': ['wall', 'ceiling', 'floor', 'door', 'window', 'bench', 'chair',
              'table', 'furniture', 'broken', 'crack', 'roof'],
    'mess': ['mess', 'food', 'meal', 'canteen', 'khana', 'lunch', 'dinner',
             'breakfast', 'quality of food', 'stale', 'taste'],
    'housekeeping': ['clean', 'garbage', 'dustbin', 'sweep', 'stink', 'smell',
                     'dirty', 'washroom clean', 'gandagi'],
    'it': ['wifi', 'internet', 'network', 'lan', 'computer', 'printer', 'router',
           'slow net', 'connection'],
    'hostel': ['room', 'warden', 'hostel', 'bed', 'mattress', 'locker', 'wardrobe',
               'roommate', 'allotment'],
    'accounts': ['fee', 'fees', 'refund', 'payment', 'dues', 'receipt', 'challan'],
    'academic': ['certificate', 'bonafide', 'marksheet', 'transcript', 'exam',
                 'marks', 'attendance sheet', 'result'],
}

# Priority signals
URGENT_KW = ['fire', 'spark', 'shock', 'flood', 'emergency', 'bleeding', 'injur',
             'gas leak', 'collapse', 'urgent']
HIGH_KW = ['3 days', '4 days', '5 days', 'one week', 'two weeks', 'repeated',
           'again', 'still not', 'no response', 'very bad', 'severe']


def classify_department(text):
    """
    Return the best-matching department code for a complaint.
    Defaults to 'general' if no match.
    """
    text_l = text.lower()
    scores = {}
    for dept, kws in ROUTING_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in text_l)
        if score > 0:
            scores[dept] = score

    if not scores:
        return 'general'

    # Highest score wins; tie broken by dict order (Python 3.7+ preserves)
    return max(scores, key=scores.get)


def classify_priority(text, ticket_type=None):
    """Return 'low' | 'medium' | 'high' | 'urgent'."""
    text_l = text.lower()

    if any(kw in text_l for kw in URGENT_KW):
        return PRIORITY_URGENT

    if any(kw in text_l for kw in HIGH_KW):
        return PRIORITY_HIGH

    # Complaints about safety = high
    if ticket_type == 'complaint' and any(
        kw in text_l for kw in ['fire', 'electric', 'shock', 'spark', 'gas']
    ):
        return PRIORITY_HIGH

    if ticket_type in ('leave', 'gatepass'):
        return PRIORITY_MEDIUM

    return PRIORITY_MEDIUM


def extract_meta(text):
    """Return dict with detected department, priority, and matched keywords."""
    dept = classify_department(text)
    priority = classify_priority(text)

    text_l = text.lower()
    matched = [
        kw for kws in ROUTING_KEYWORDS.values() for kw in kws if kw in text_l
    ]

    return {
        'department': dept,
        'priority': priority,
        'matched_keywords': list(set(matched))[:10],
        'classifier': 'rule-based-v1',
    }