"""
Prompts for aggregating student feedback into actionable insight.
"""
FEEDBACK_SYSTEM = """You are an operations analyst for a college campus.
You receive batches of student feedback and produce concise actionable insight.

Output format (markdown):
**Top Issues**
- Issue 1 (with approx frequency if evident)
- Issue 2

**Recommendations**
- Action 1
- Action 2

Keep total output under 150 words. Be specific and operational. Do NOT invent data.
"""


def build_feedback_prompt(feedback_entries, category=None):
    lines = []
    for f in feedback_entries:
        tag = f"[{f.get_category_display()} | {f.rating}/5]"
        comment = (f.comments or '').strip()[:200]
        if comment:
            lines.append(f"{tag} {comment}")
    batch = '\n'.join(lines) if lines else 'No comments provided.'
    header = f"Category: {category or 'All'}\n\n" if category else ''
    return f"{header}Feedback entries:\n{batch}"


def fallback_feedback_insight(feedback_qs):
    """Rule-based fallback if LLM unavailable."""
    from collections import Counter
    total = feedback_qs.count()
    if total == 0:
        return "No feedback received yet."

    avg = sum(f.rating for f in feedback_qs) / total
    cat_counter = Counter(f.get_category_display() for f in feedback_qs)
    top_cat = cat_counter.most_common(1)[0]

    return (
        f"**Summary**\n"
        f"- {total} feedback entries, average rating {avg:.1f}/5\n"
        f"- Most reviewed: {top_cat[0]} ({top_cat[1]} entries)\n\n"
        f"**Recommendations**\n"
        f"- Review {top_cat[0]} operations\n"
        f"- Follow up on low-rated items"
    )