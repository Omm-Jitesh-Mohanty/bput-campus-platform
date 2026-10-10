import hashlib
import hmac

from django.conf import settings
from django.shortcuts import render, get_object_or_404

from apps.tickets.models import CampusTicket
from apps.workflows.models import TicketStepExecution


def verify_signature(request, ticket_id, step_id):
    ticket = get_object_or_404(CampusTicket, pk=ticket_id)

    signatures = (ticket.ai_metadata or {}).get("signatures", [])
    signature = next(
        (
            item for item in signatures
            if str(item.get("step_id")) == str(step_id)
        ),
        None,
    )

    valid = False
    reason = "Signature not found or could not be verified."

    if signature:
        payload = signature.get("payload", "")
        stored_signature = signature.get("signature", "")
        secret = getattr(settings, "DOC_SIGNING_SECRET", "")

        try:
            execution = TicketStepExecution.objects.select_related(
                "workflow_step", "actor"
            ).get(ticket=ticket, pk=step_id)
        except TicketStepExecution.DoesNotExist:
            execution = None

        parts = payload.split("|") if payload else []

        if (
            execution
            and execution.workflow_step.action_type == "sign"
            and execution.status == "approved"
            and execution.actor_id is not None
            and len(parts) == 4
            and parts[0] == str(ticket.id)
            and parts[1] == str(execution.id)
            and parts[2] == str(execution.actor_id)
            and signature.get("signed_by") == execution.actor.username
            and stored_signature
            and secret
        ):
            expected_signature = hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256,
            ).hexdigest()

            valid = hmac.compare_digest(
                expected_signature,
                stored_signature,
            )

        reason = (
            "Signature verified successfully."
            if valid
            else "Signature is invalid or its verification data is missing."
        )

    return render(
        request,
        "tickets/verify_signature.html",
        {
            "valid": valid,
            "reason": reason,
            "ticket": ticket if valid else None,
            "signature": signature if valid else None,
        },
    )