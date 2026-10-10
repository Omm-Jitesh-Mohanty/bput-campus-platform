"""
Deterministic workflow selection for campus tickets.
"""
import logging

logger = logging.getLogger(__name__)


TICKET_WORKFLOW_CODES = {
    "document": "document_chain",
    "leave": "leave_chain",
    "gatepass": "gatepass_chain",
    "complaint": "maintenance_chain",
    "maintenance": "maintenance_chain",
    "scholarship": "scholarship_chain",
    "lab_reschedule": "lab_reschedule_chain",
}


def select_workflow(ticket):
    from apps.core.models import TicketType
    from apps.workflows.models import Workflow

    ticket_type_code = str(ticket.ticket_type).strip().lower()
    dynamic_data = ticket.dynamic_data or {}

    ticket_type = TicketType.objects.filter(
        code__iexact=ticket_type_code
    ).first()

    subtype_code = str(
        dynamic_data.get("complaint_subtype", "")
    ).strip().lower()

    if ticket_type and subtype_code:
        subtype = ticket_type.subtypes.filter(
            code__iexact=subtype_code,
            is_active=True,
        ).select_related("workflow").first()

        if subtype and subtype.workflow and subtype.workflow.is_active:
            return subtype.workflow

    if ticket_type:
        default_workflow = getattr(ticket_type, "default_workflow", None)

        if default_workflow and default_workflow.is_active:
            return default_workflow

        configured_workflow = Workflow.objects.filter(
            ticket_type=ticket_type,
            is_active=True,
        ).first()

        if configured_workflow:
            return configured_workflow

    workflow_code = TICKET_WORKFLOW_CODES.get(ticket_type_code)

    if workflow_code:
        workflow = Workflow.objects.filter(
            code=workflow_code,
            is_active=True,
        ).first()

        if workflow:
            return workflow

    logger.error(
        "No matching workflow found for ticket #%s, type=%s",
        ticket.id,
        ticket_type_code,
    )
    return None