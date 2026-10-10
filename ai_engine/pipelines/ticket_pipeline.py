# """
# Ticket pipeline: on ticket creation,
# 1. Classify department + priority (rule-based)
# 2. Classify complaint subtype for workflow selection
# 3. Format the raw input into a formal body (LLM)
# 4. Persist results on the ticket
# """

# import logging

# from ai_engine.llm import generate_text
# from ai_engine.prompts import (
#     FORMATTER_SYSTEM,
#     build_formatter_prompt_with_context,
# )
# from ai_engine.rag import extract_meta


# logger = logging.getLogger("ai_engine")


# def _classify_subtype(text, ticket_type):
#     """Find the best-matching complaint subtype."""

#     if ticket_type != "complaint":
#         return None

#     from apps.core.models import ComplaintSubtype

#     text_l = text.lower()
#     best = None
#     best_score = 0

#     for st in ComplaintSubtype.objects.filter(is_active=True):
#         score = sum(
#             1
#             for kw in (st.routing_keywords or [])
#             if kw in text_l
#         )

#         if score > best_score:
#             best_score = score
#             best = st

#     return best


# def _student_context(student):
#     """Build verified student context for the formatter."""

#     return {
#         "full_name": student.get_full_name() or student.username,
#         "username": student.username,
#         "department": student.department or "",
#         "batch_year": student.batch_year or "",
#         "hostel_block": student.hostel_block or "",
#         "room_number": student.room_number or "",
#         "email": student.email or "",
#         "phone": student.phone or "",
#     }


# def process_new_ticket(ticket, save=True):
#     """
#     Enrich a freshly-created ticket with AI-generated fields.
#     Returns the ticket (possibly modified).
#     """

#     # --- 1. Rule-based meta ---
#     meta = extract_meta(
#         ticket.raw_input + " " + (ticket.subject or "")
#     )

#     ticket.assigned_department = meta["department"]
#     ticket.priority = meta["priority"]

#     # --- 2. Classify complaint subtype for workflow selection ---
#     subtype = _classify_subtype(
#         ticket.raw_input,
#         ticket.ticket_type,
#     )

#     if subtype:
#         ticket.dynamic_data = {
#             **(ticket.dynamic_data or {}),
#             "complaint_subtype": subtype.code,
#         }

#     ticket.ai_metadata = {
#         **(ticket.ai_metadata or {}),
#         "classifier": meta,
#         "subtype": subtype.code if subtype else None,
#     }

#     # --- 3. Build verified student context ---
#     student_ctx = _student_context(ticket.student)

#     # --- 4. LLM formatting with verified DB data ---
#     prompt = build_formatter_prompt_with_context(
#         raw_text=ticket.raw_input,
#         ticket_type=ticket.ticket_type,
#         student_ctx=student_ctx,
#         extra_fields=ticket.dynamic_data or {},
#     )

#     response = generate_text(
#         prompt,
#         system=FORMATTER_SYSTEM,
#         temperature=0.3,
#         max_tokens=500,
#     )

#     if response.success and response.text:
#         ticket.formatted_body = response.text

#         ticket.ai_metadata["formatter"] = {
#             "model": response.model,
#             "latency_ms": response.latency_ms,
#             "source": "llm",
#         }

#     else:
#         # --- 5. Deterministic fallback with verified student data ---
#         ticket.formatted_body = (
#             f"Respected Sir/Madam,\n\n"
#             f"Subject: {ticket.subject}\n\n"
#             f"I, {student_ctx['full_name']} "
#             f"(Roll No. {student_ctx['username']}), "
#             f"a student of {student_ctx['department']} Department, "
#             f"{student_ctx['batch_year']} batch, currently residing in "
#             f"Hostel Block {student_ctx['hostel_block']}, "
#             f"Room {student_ctx['room_number']}, "
#             f"wish to submit the following:\n\n"
#             f"{ticket.raw_input}\n\n"
#             f"Kindly consider this request and take necessary action.\n\n"
#             f"Thanking you,\n"
#             f"Yours sincerely,\n"
#             f"{student_ctx['full_name']}\n"
#             f"Roll No. {student_ctx['username']}\n"
#             f"{student_ctx['department']} · {student_ctx['batch_year']}"
#         )

#         ticket.ai_metadata["formatter"] = {
#             "source": "fallback",
#             "error": response.error,
#         }

#     # --- 6. Persist results ---
#     if save:
#         ticket.save(
#             update_fields=[
#                 "assigned_department",
#                 "priority",
#                 "formatted_body",
#                 "dynamic_data",
#                 "ai_metadata",
#                 "updated_at",
#             ]
#         )

#     return ticket

"""
Ticket pipeline: on ticket creation,
1. Classify department + priority (rule-based)
2. Classify complaint subtype for workflow selection
3. Format the raw input into a formal body (LLM)
4. Persist results on the ticket
"""

import logging

from ai_engine.llm import generate_text
from ai_engine.prompts import (
    FORMATTER_SYSTEM,
    build_formatter_prompt_with_context,
    fallback_formal_text,
)
from ai_engine.rag import extract_meta


logger = logging.getLogger("ai_engine")


def _classify_subtype(text, ticket_type):
    """Find the best-matching complaint subtype."""

    if ticket_type != "complaint":
        return None

    from apps.core.models import ComplaintSubtype

    text_l = text.lower()
    best = None
    best_score = 0

    for st in ComplaintSubtype.objects.filter(is_active=True):
        score = sum(
            1
            for kw in (st.routing_keywords or [])
            if kw in text_l
        )

        if score > best_score:
            best_score = score
            best = st

    return best


def _student_context(student):
    """Build verified student context for the formatter."""

    return {
        "full_name": student.get_full_name() or student.username,
        "username": student.username,
        "department": student.department or "",
        "batch_year": student.batch_year or "",
        "hostel_block": student.hostel_block or "",
        "room_number": student.room_number or "",
        "email": student.email or "",
        "phone": student.phone or "",
    }


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

    # --- 2. Classify complaint subtype for workflow selection ---
    subtype = _classify_subtype(
        ticket.raw_input,
        ticket.ticket_type,
    )

    if subtype:
        ticket.dynamic_data = {
            **(ticket.dynamic_data or {}),
            "complaint_subtype": subtype.code,
        }

    ticket.ai_metadata = {
        **(ticket.ai_metadata or {}),
        "classifier": meta,
        "subtype": subtype.code if subtype else None,
    }

    # --- 3. Build verified student context ---
    student_ctx = _student_context(ticket.student)

    # --- 4. Retrieve relevant policy context ---
    try:
        from ai_engine.rag.retriever import retrieve

        policy_query = (
            f"{ticket.ticket_type} policy "
            f"{ticket.raw_input[:200]}"
        )

        policy_chunks = retrieve(
            policy_query,
            audience='both',
            top_k=3,
            candidate_k=10,
        )

        policy_context = '\n\n'.join(
            f"- {c['metadata'].get('title', '')}: {c['text'][:300]}"
            for c in policy_chunks
            if c['metadata'].get('source') == 'policy'
        )

    except Exception:
        policy_context = ''

    # --- 5. Build formatter prompt with policy context ---
    prompt = build_formatter_prompt_with_context(
        raw_text=ticket.raw_input,
        ticket_type=ticket.ticket_type,
        student_ctx=student_ctx,
        extra_fields=ticket.dynamic_data or {},
    )

    if policy_context:
        prompt = f"""Relevant policy excerpts:
{policy_context}

---

{prompt}"""

    # --- 6. LLM formatting with verified DB data ---
    response = generate_text(
        prompt,
        system=FORMATTER_SYSTEM,
        temperature=0.3,
        max_tokens=500,
    )

    if response.success and response.text:
        ticket.formatted_body = response.text

        ticket.ai_metadata["formatter"] = {
            "model": response.model,
            "latency_ms": response.latency_ms,
            "source": "llm",
        }

    else:
        # --- 7. Deterministic fallback with verified student data ---
        ticket.formatted_body = fallback_formal_text(
            raw_text=ticket.raw_input,
            ticket_type=ticket.ticket_type,
            student_name=student_ctx["full_name"],
            department=student_ctx["department"],
            batch_year=student_ctx["batch_year"],
            roll_number=student_ctx["username"],
            hostel=student_ctx["hostel_block"],
            room=student_ctx["room_number"],
        )

        ticket.ai_metadata["formatter"] = {
            "source": "fallback",
            "error": response.error,
        }

    # --- 8. Persist results ---
    if save:
        ticket.save(
            update_fields=[
                "assigned_department",
                "priority",
                "formatted_body",
                "dynamic_data",
                "ai_metadata",
                "updated_at",
            ]
        )

    return ticket