"""
Ticket pipeline: on ticket creation,
1. Classify department + priority (rule-based)
2. Format the raw input into a formal body (LLM)
3. Persist results on the ticket
"""

import logging

from ai_engine.llm import generate_text
from ai_engine.prompts import (
    FORMATTER_SYSTEM,
    build_formatter_prompt,
    fallback_formal_text,
)
from ai_engine.rag import extract_meta


logger = logging.getLogger("ai_engine")


def process_new_ticket(ticket, save=True):
    """
    Enrich a freshly-created ticket with AI-generated fields.
    Returns the ticket (possibly modified).
    """

    # --- 1. Rule-based meta ---
    meta = extract_meta(
        ticket.raw_input + " " + (ticket.subject or "")
    )

    ticket.assigned_department = meta["department"]
    ticket.priority = meta["priority"]

    ticket.ai_metadata = {
        **(ticket.ai_metadata or {}),
        "classifier": meta,
    }

    # --- 2. Language-aware LLM formatting ---
    student_lang = (
        getattr(ticket.student, "language_pref", "en") or "en"
    )

    prompt = build_formatter_prompt(
        ticket.raw_input,
        ticket.ticket_type,
    )

    if student_lang != "en":
        lang_names = {
            "hi": "Hindi (हिन्दी)",
            "or": "Odia (ଓଡ଼ିଆ)",
        }

        prompt += (
            f"\n\nRespond in "
            f"{lang_names.get(student_lang, 'English')}."
        )

    response = generate_text(
        prompt,
        system=FORMATTER_SYSTEM,
        temperature=0.3,
        max_tokens=400,
    )

    if response.success and response.text:
        ticket.formatted_body = response.text

        ticket.ai_metadata["formatter"] = {
            "model": response.model,
            "latency_ms": response.latency_ms,
            "source": "llm",
        }

    else:
        student = ticket.student

        ticket.formatted_body = fallback_formal_text(
            raw_text=ticket.raw_input,
            ticket_type=ticket.ticket_type,
            student_name=(
                student.get_full_name() or student.username
            ),
            department=student.department or "N/A",
            batch_year=student.batch_year or "N/A",
        )

        ticket.ai_metadata["formatter"] = {
            "source": "fallback",
            "error": response.error,
        }

    if save:
        ticket.save(
            update_fields=[
                "assigned_department",
                "priority",
                "formatted_body",
                "ai_metadata",
                "updated_at",
            ]
        )

    return ticket