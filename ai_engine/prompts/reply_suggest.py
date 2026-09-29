"""
Prompt for suggesting admin replies based on past resolutions (RAG context).
"""
REPLY_SYSTEM = """You are an assistant helping a college administrator write
a short, professional resolution note for a student complaint or request.

Rules:
- Output ONLY the resolution text — no preamble.
- 1–3 sentences. Formal, courteous tone.
- Reference what action is taken (repair, approval, dispatch).
- Do NOT invent specific details like exact dates or staff names.
"""


def build_reply_prompt(ticket, similar_resolutions):
    """similar_resolutions: list of strings from past tickets."""
    context_lines = []
    for i, note in enumerate(similar_resolutions, 1):
        context_lines.append(f"{i}. {note[:200]}")
    context = '\n'.join(context_lines) if context_lines else 'No prior examples.'

    return (
        f"Similar resolved cases:\n{context}\n\n"
        f"New ticket:\n"
        f"- Type: {ticket.ticket_type}\n"
        f"- Department: {ticket.assigned_department or 'unassigned'}\n"
        f"- Subject: {ticket.subject}\n"
        f"- Student's words: {ticket.raw_input[:300]}\n\n"
        f"Write a short resolution note:"
    )

def fallback_reply(ticket):
    """Templated fallback reply."""
    if ticket.ticket_type == 'complaint':
        return (
            f"Your complaint regarding '{ticket.subject}' has been received and "
            f"forwarded to the {ticket.assigned_department or 'relevant'} department. "
            f"The issue will be addressed shortly. Thank you for reporting."
        )
    if ticket.ticket_type == 'leave':
        return (
            "Your leave request has been reviewed and approved as per college policy. "
            "Kindly inform your class coordinator before availing the leave."
        )
    if ticket.ticket_type == 'document':
        return (
            "Your document request has been processed. "
            "Please collect the certificate from the academic office during working hours."
        )
    if ticket.ticket_type == 'gatepass':
        return (
            "Your gate pass request has been approved. "
            "Please carry your ID card while leaving the campus."
        )
    return "Your request has been processed. Please check back for updates."