"""
Prompts for converting informal student text → formal application.
"""
FORMATTER_SYSTEM = """You are an AI assistant for an Indian engineering college.
Your job: convert a student's informal message into a formal administrative application.

Rules:
- Output ONLY the formal application text — no preamble, no explanation.
- Start with "Respected Sir/Madam,"
- Mention the student's concern professionally.
- Include a polite closing line and signature placeholder.
- Keep it between 80–150 words.
- Do NOT invent details the student didn't provide (dates, amounts, names).
- If the input is a complaint, use a courteous tone, not accusatory.
"""

TEMPLATES = {
    'leave': (
        "Convert this into a formal LEAVE APPLICATION to the Hostel Warden / HOD.\n"
        "Student wrote: \"{raw}\"\n"
        "Formal application:"
    ),
    'gatepass': (
        "Convert this into a formal GATE PASS REQUEST to the Hostel Warden.\n"
        "Student wrote: \"{raw}\"\n"
        "Formal application:"
    ),
    'document': (
        "Convert this into a formal DOCUMENT / CERTIFICATE REQUEST to the Academic Office.\n"
        "Student wrote: \"{raw}\"\n"
        "Formal application:"
    ),
    'complaint': (
        "Convert this into a formal COMPLAINT to the Maintenance Department.\n"
        "Student wrote: \"{raw}\"\n"
        "Formal complaint:"
    ),
}


def build_formatter_prompt(raw_text, ticket_type):
    tpl = TEMPLATES.get(ticket_type, TEMPLATES['complaint'])
    return tpl.format(raw=raw_text.strip())


def fallback_formal_text(raw_text, ticket_type, student_name, department, batch_year):
    """Deterministic fallback if LLM unavailable. Sounds professional enough."""
    type_labels = {
        'leave': 'leave application',
        'gatepass': 'gate pass request',
        'document': 'document request',
        'complaint': 'complaint',
    }
    label = type_labels.get(ticket_type, 'request')

    return (
        f"Respected Sir/Madam,\n\n"
        f"I, {student_name} ({department}, {batch_year}), wish to submit the following {label}:\n\n"
        f"{raw_text.strip()}\n\n"
        f"I kindly request you to look into this matter at your earliest convenience.\n\n"
        f"Thanking you,\n"
        f"Yours sincerely,\n"
        f"{student_name}\n"
        f"{department} — {batch_year}"
    )