"""
LLM-driven workflow selection.

Given a ticket, decide which approval workflow applies based on:
  - The complaint subtype (from classifier)
  - Priority (from classifier)
  - College rules (from policy PDFs via RAG)
  - Cost/amount fields (from dynamic_data)

Returns a Workflow object or None.
"""
import json
import logging

from ai_engine.llm import generate_text
from ai_engine.rag.retriever import retrieve

logger = logging.getLogger(__name__)


WORKFLOW_SELECTOR_SYSTEM = """You are an approval-routing assistant for an
Indian engineering college.

Given a ticket and the relevant policy excerpts, decide which approval workflow
should be applied.

Output STRICT JSON only:
{
  "workflow_code": "<code from the available list>",
  "reason": "<one-line justification>",
  "escalate_urgency": true | false
}

Rules:
- Match the SUBTYPE and SEVERITY to the correct chain.
- If the ticket involves SAFETY (fire, electric shock, structural damage),
  set escalate_urgency=true.
- If the description mentions cost > ₹5,000 or a large amount, choose a chain
  that includes Dean/Principal approval.
- Do NOT invent workflow codes. Only use what's in the list.
"""


def select_workflow_for_ticket(ticket):
    from apps.workflows.selector import select_workflow

    workflow = select_workflow(ticket)

    if workflow is None:
        logger.error(
            "Workflow selection failed for ticket #%s (%s)",
            ticket.id,
            ticket.ticket_type,
        )
        return None

    metadata = ticket.ai_metadata or {}
    metadata["workflow_selection"] = {
        "chosen": workflow.code,
        "reason": "Selected using deterministic ticket-type routing.",
        "source": "rules",
    }

    ticket.ai_metadata = metadata
    ticket.save(update_fields=["ai_metadata", "updated_at"])

    return workflow