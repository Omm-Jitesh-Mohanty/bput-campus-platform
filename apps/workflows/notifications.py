"""
Workflow notifications — dispatch via NotificationService.
"""
import logging

logger = logging.getLogger(__name__)


def notify_step_pending(ticket, step_execution):
    """Notify approvers that a step awaits their action."""
    from apps.notifications.services import NotificationService
    from apps.workflows.engine import WorkflowEngine

    try:
        approvers = NotificationService._approvers_for_step(step_execution)
        for approver in approvers:
            NotificationService.notify(
                recipient=approver,
                event_code='step.pending',
                context={
                    **NotificationService._ticket_context(ticket),
                    'step_name': step_execution.workflow_step.name,
                    'instructions': step_execution.workflow_step.instructions or '',
                },
                link_url=f"/tickets/{ticket.id}/resolve/",
                target=ticket,
                priority='high',
            )
    except Exception as e:
        logger.exception(f"notify_step_pending failed: {e}")