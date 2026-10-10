# # # """
# # # WorkflowEngine — attaches workflows to tickets and advances steps.
# # # """
# # # import logging
# # # from django.utils import timezone
# # # from django.db import transaction

# # # from apps.core.audit import AuditService
# # # from .models import Workflow, WorkflowStep, TicketStepExecution
# # # from .condition import evaluate

# # # logger = logging.getLogger(__name__)


# # # class WorkflowEngine:
# # #     """Orchestrates multi-step approvals on tickets."""

# # #     # =================================================================
# # #     # Attach workflow to a newly created ticket
# # #     # =================================================================
# # #     # @classmethod
# # #     # def attach_workflow(cls, ticket):
# # #     #     """
# # #     #     Find a matching workflow for the ticket and create pending step executions.
# # #     #     Skips steps whose conditions don't match.
# # #     #     Returns the attached Workflow or None.
# # #     #     """
# # #     #     workflow = cls._find_workflow(ticket)
# # #     #     if not workflow:
# # #     #         return None

# # #     #     with transaction.atomic():
# # #     #         steps = workflow.steps.order_by('order')
# # #     #         created_count = 0
# # #     #         skipped_count = 0

# # #     #         # for step in steps:
# # #     #         #     should_run = evaluate(step.condition, ticket)
# # #     #         #     execution = TicketStepExecution.objects.create(
# # #     #         #         ticket=ticket,
# # #     #         #         workflow_step=step,
# # #     #         #         status='pending' if should_run else 'skipped',
# # #     #         #         skip_reason='' if should_run else 'Condition not met',
# # #     #         #     )
# # #     #         #     if should_run:
# # #     #         #         created_count += 1
# # #     #         #     else:
# # #     #         #         skipped_count += 1
# # #     #         for step in steps:
# # #     #             execution = TicketStepExecution.objects.create(
# # #     #                 ticket=ticket,
# # #     #                 workflow_step=step,
# # #     #                 status='pending',
# # #     #             )
# # #     #             created_count += 1

# # #     #         AuditService.log_action(
# # #     #             action='create',
# # #     #             target=ticket,
# # #     #             metadata={
# # #     #                 'workflow_attached': workflow.code,
# # #     #                 'steps_pending': created_count,
# # #     #                 'steps_skipped': skipped_count,
# # #     #             },
# # #     #         )

# # #     #     logger.info(
# # #     #         f"Workflow '{workflow.code}' attached to ticket #{ticket.id}: "
# # #     #         f"{created_count} pending, {skipped_count} skipped"
# # #     #     )
# # #     #     return workflow
# # #     @classmethod
# # #     def attach_workflow(cls, ticket):
# # #         workflow = cls._find_workflow(ticket)

# # #         if not workflow:
# # #             return None

# # #         # Prevent duplicate workflow attachment.
# # #         if TicketStepExecution.objects.filter(ticket=ticket).exists():
# # #             logger.warning(
# # #                 f"Workflow already attached to ticket #{ticket.id}"
# # #             )
# # #             return workflow

# # #         with transaction.atomic():

# # #             steps = workflow.steps.order_by('order')

# # #             created_count = 0

# # #             for step in steps:

# # #                 TicketStepExecution.objects.create(
# # #                     ticket=ticket,
# # #                     workflow_step=step,
# # #                     status='pending',
# # #                 )

# # #                 created_count += 1

# # #             AuditService.log_action(
# # #                 action='create',
# # #                 target=ticket,
# # #                 metadata={
# # #                     'workflow_attached': workflow.code,
# # #                     'steps_created': created_count,
# # #                 },
# # #             )

# # #         logger.info(
# # #             f"Workflow '{workflow.code}' attached to "
# # #             f"ticket #{ticket.id}: {created_count} steps created"
# # #         )

# # #         return workflow

# # #     @classmethod
# # #     def _find_workflow(cls, ticket):
# # #         """Find the active workflow for the ticket's type."""
# # #         # Prefer workflow explicitly linked to the ticket type
# # #         wf = Workflow.objects.filter(
# # #             ticket_type__code=ticket.ticket_type,
# # #             is_active=True,
# # #         ).first()

# # #         if wf:
# # #             return wf

# # #         # Fallback to default workflow
# # #         return Workflow.objects.filter(is_active=True, is_default=True).first()

# # #     # =================================================================
# # #     # Current pending step
# # #     # =================================================================
# # #     # @classmethod
# # #     # def current_step(cls, ticket):
# # #     #     """
# # #     #     Return the current pending step execution for the ticket.
# # #     #     Returns None if all steps done (or no workflow attached).
# # #     #     """
# # #     #     return (
# # #     #         TicketStepExecution.objects
# # #     #         .filter(ticket=ticket, status='pending')
# # #     #         .select_related('workflow_step', 'workflow_step__specific_user')
# # #     #         .order_by('workflow_step__order')
# # #     #         .first()
# # #     #     )
# # #     @classmethod
# # #     def current_step(cls, ticket):
# # #         """
# # #         Return the first pending workflow step whose condition is satisfied.

# # #         Conditional steps are evaluated only when the workflow reaches them.
# # #         Steps whose conditions are not satisfied are automatically skipped.
# # #         """

# # #         pending_steps = (
# # #             TicketStepExecution.objects
# # #             .filter(ticket=ticket, status='pending')
# # #             .select_related(
# # #                 'workflow_step',
# # #                 'workflow_step__specific_user',
# # #             )
# # #             .order_by('workflow_step__order')
# # #         )

# # #         for execution in pending_steps:
# # #             step = execution.workflow_step

# # #             if evaluate(step.condition, ticket):
# # #                 return execution

# # #             # Condition is not satisfied.
# # #             execution.status = 'skipped'
# # #             execution.skip_reason = 'Condition not met'
# # #             execution.save(update_fields=['status', 'skip_reason', 'updated_at'])

# # #         return None

# # #     @classmethod
# # #     def all_steps(cls, ticket):
# # #         """Return all step executions for a ticket, ordered."""
# # #         return (
# # #             TicketStepExecution.objects
# # #             .filter(ticket=ticket)
# # #             .select_related('workflow_step', 'actor', 'escalated_to')
# # #             .order_by('workflow_step__order')
# # #         )

# # #     # @classmethod
# # #     # def is_complete(cls, ticket):
# # #     #     """True if all steps are in a terminal state (approved/rejected/skipped)."""
# # #     #     return not TicketStepExecution.objects.filter(
# # #     #         ticket=ticket, status='pending'
# # #     #     ).exists()
# # #     # @classmethod
# # #     # def is_complete(cls, ticket):
# # #     #     return not TicketStepExecution.objects.filter(
# # #     #         ticket=ticket,
# # #     #         status__in=('pending', 'escalated')
# # #     #     ).exists()
# # #     @classmethod
# # #     def is_complete(cls, ticket):
# # #         """
# # #         Workflow is complete when there are no more actionable steps.

# # #         Note: `current_step()` automatically skips non-matching conditional steps,
# # #         so calling it here ensures any remaining steps are properly classified.
# # #         """
# # #         # Triggers skip of any condition-mismatched steps
# # #         next_step = cls.current_step(ticket)
# # #         return next_step is None

# # #     @classmethod
# # #     def is_rejected(cls, ticket):
# # #         return TicketStepExecution.objects.filter(
# # #             ticket=ticket, status='rejected'
# # #         ).exists()

# # #     # =================================================================
# # #     # Acting on a step
# # #     # =================================================================
# # #     # @classmethod
# # #     # def act(cls, ticket, step_execution, actor, action, comment=''):
# # #     #     """
# # #     #     Approve, reject, or skip the given step.
# # #     #     Returns True if the action succeeded.
# # #     #     """
# # #     #     if step_execution.status != 'pending':
# # #     #         logger.warning(f"Step {step_execution.id} is not pending")
# # #     #         return False

# # #     #     if action not in ('approve', 'reject', 'skip'):
# # #     #         logger.warning(f"Invalid action: {action}")
# # #     #         return False

# # #     #     if action == 'skip' and not step_execution.workflow_step.can_skip:
# # #     #         logger.warning(f"Step {step_execution.id} cannot be skipped")
# # #     #         return False

# # #     #     with transaction.atomic():
# # #     #         # Record action
# # #     #         step_execution.status = {
# # #     #             'approve': 'approved',
# # #     #             'reject': 'rejected',
# # #     #             'skip': 'skipped',
# # #     #         }[action]
# # #     #         step_execution.actor = actor
# # #     #         step_execution.acted_at = timezone.now()
# # #     #         step_execution.comment = comment
# # #     #         step_execution.save()

# # #     #         AuditService.log_action(
# # #     #             action={
# # #     #                 'approve': 'approve',
# # #     #                 'reject': 'reject',
# # #     #                 'skip': 'approve',
# # #     #             }[action],
# # #     #             target=ticket,
# # #     #             metadata={
# # #     #                 'step_id': step_execution.id,
# # #     #                 'step_name': step_execution.workflow_step.name,
# # #     #                 'action': action,
# # #     #                 'comment': comment[:200],
# # #     #             },
# # #     #             user=actor,
# # #     #         )

# # #     #         # If rejected → ticket status becomes rejected
# # #     #         if action == 'reject':
# # #     #             ticket.status = 'rejected'
# # #     #             ticket.save(update_fields=['status'])

# # #     #         # If approved → check if workflow complete
# # #     #         elif action == 'approve':
# # #     #             if cls.is_complete(ticket):
# # #     #                 ticket.status = 'resolved'
# # #     #                 ticket.resolved_at = timezone.now()
# # #     #                 ticket.resolved_by = actor
# # #     #                 ticket.save(update_fields=['status', 'resolved_at', 'resolved_by'])
# # #     #             else:
# # #     #                 # Next step becomes active
# # #     #                 next_step = cls.current_step(ticket)
# # #     #                 if next_step:
# # #     #                     cls._notify_next_step(ticket, next_step)

# # #     #         return True
# # #     @classmethod
# # #     def act(cls, ticket, step_execution, actor, action, comment=''):
# # #         """
# # #         Perform an action on the current workflow step.
# # #         """

# # #         # Only the current workflow step can be acted upon.
# # #         current = cls.current_step(ticket)

# # #         if not current or current.id != step_execution.id:
# # #             logger.warning(
# # #                 f"Step {step_execution.id} is not the current step "
# # #                 f"for ticket #{ticket.id}"
# # #             )
# # #             return False

# # #         if step_execution.status != 'pending':
# # #             logger.warning(
# # #                 f"Step {step_execution.id} is not pending"
# # #             )
# # #             return False

# # #         if action not in ('approve', 'reject', 'skip'):
# # #             logger.warning(
# # #                 f"Invalid workflow action: {action}"
# # #             )
# # #             return False

# # #         if action == 'skip' and not step_execution.workflow_step.can_skip:
# # #             logger.warning(
# # #                 f"Step {step_execution.id} cannot be skipped"
# # #             )
# # #             return False

# # #         with transaction.atomic():

# # #             step_execution.status = {
# # #                 'approve': 'approved',
# # #                 'reject': 'rejected',
# # #                 'skip': 'skipped',
# # #             }[action]

# # #             step_execution.actor = actor
# # #             step_execution.acted_at = timezone.now()
# # #             step_execution.comment = comment

# # #             step_execution.save()

# # #             AuditService.log_action(
# # #                 action={
# # #                     'approve': 'approve',
# # #                     'reject': 'reject',
# # #                     'skip': 'approve',
# # #                 }[action],
# # #                 target=ticket,
# # #                 metadata={
# # #                     'step_id': step_execution.id,
# # #                     'step_name': step_execution.workflow_step.name,
# # #                     'action': action,
# # #                     'comment': comment[:200],
# # #                 },
# # #                 user=actor,
# # #             )

# # #             # -----------------------------------------
# # #             # REJECT
# # #             # -----------------------------------------

# # #             if action == 'reject':

# # #                 ticket.status = 'rejected'

# # #                 ticket.save(
# # #                     update_fields=['status']
# # #                 )

# # #                 return True

# # #             # -----------------------------------------
# # #             # APPROVE / SKIP
# # #             # -----------------------------------------

# # #             next_step = cls.current_step(ticket)

# # #             if next_step:

# # #                 cls._notify_next_step(
# # #                     ticket,
# # #                     next_step
# # #                 )

# # #             else:

# # #                 # No executable steps remain.
# # #                 ticket.status = 'resolved'
# # #                 ticket.resolved_at = timezone.now()
# # #                 ticket.resolved_by = actor

# # #                 ticket.save(
# # #                     update_fields=[
# # #                         'status',
# # #                         'resolved_at',
# # #                         'resolved_by',
# # #                     ]
# # #                 )

# # #             return True

# # #     @classmethod
# # #     def _notify_next_step(cls, ticket, step_execution):
# # #         """Send notification to the next step's approver."""
# # #         from apps.workflows.notifications import notify_step_pending
# # #         try:
# # #             notify_step_pending(ticket, step_execution)
# # #         except Exception as e:
# # #             logger.exception(f"Notification failed for step {step_execution.id}: {e}")

# # #     # =================================================================
# # #     # Who can act on a step?
# # #     # =================================================================
# # #     @classmethod
# # #     def can_user_act(cls, user, step_execution):
# # #         """
# # #         Return True if `user` is authorized to act on `step_execution`.
# # #         """
# # #         if step_execution.status != 'pending':
# # #             return False

# # #         step = step_execution.workflow_step

# # #         # Specific user wins
# # #         if step.specific_user_id:
# # #             return user.id == step.specific_user_id

# # #         # Otherwise role check
# # #         if step.role_required:
# # #             return user.role == step.role_required

# # #         # No role specified → any admin
# # #         return user.is_admin_role()

# # """
# # WorkflowEngine — attaches workflows to tickets and advances steps.
# # """
# # import logging
# # from django.utils import timezone
# # from django.db import transaction

# # from apps.core.audit import AuditService
# # from .models import Workflow, WorkflowStep, TicketStepExecution
# # from .condition import evaluate

# # logger = logging.getLogger(__name__)


# # class WorkflowEngine:
# #     """Orchestrates multi-step approvals on tickets."""

# #     # =================================================================
# #     # Attach workflow to a newly created ticket
# #     # =================================================================
# #     @classmethod
# #     def attach_workflow(cls, ticket):
# #         workflow = cls._find_workflow(ticket)

# #         if not workflow:
# #             return None

# #         # Prevent duplicate workflow attachment.
# #         if TicketStepExecution.objects.filter(ticket=ticket).exists():
# #             logger.warning(
# #                 f"Workflow already attached to ticket #{ticket.id}"
# #             )
# #             return workflow

# #         with transaction.atomic():

# #             steps = workflow.steps.order_by('order')

# #             created_count = 0

# #             for step in steps:

# #                 TicketStepExecution.objects.create(
# #                     ticket=ticket,
# #                     workflow_step=step,
# #                     status='pending',
# #                 )

# #                 created_count += 1

# #             AuditService.log_action(
# #                 action='create',
# #                 target=ticket,
# #                 metadata={
# #                     'workflow_attached': workflow.code,
# #                     'steps_created': created_count,
# #                 },
# #             )

# #         logger.info(
# #             f"Workflow '{workflow.code}' attached to "
# #             f"ticket #{ticket.id}: {created_count} steps created"
# #         )

# #         return workflow

# #     @classmethod
# #     def _find_workflow(cls, ticket):
# #         """Find the active workflow for the ticket's type."""

# #         # Prefer workflow explicitly linked to the ticket type
# #         wf = Workflow.objects.filter(
# #             ticket_type__code=ticket.ticket_type,
# #             is_active=True,
# #         ).first()

# #         if wf:
# #             return wf

# #         # Fallback to default workflow
# #         return Workflow.objects.filter(
# #             is_active=True,
# #             is_default=True,
# #         ).first()

# #     # =================================================================
# #     # Current pending step
# #     # =================================================================
# #     @classmethod
# #     def current_step(cls, ticket):
# #         """
# #         Return the first pending workflow step whose condition is satisfied.

# #         Conditional steps are evaluated only when the workflow reaches them.
# #         Steps whose conditions are not satisfied are automatically skipped.
# #         """

# #         pending_steps = (
# #             TicketStepExecution.objects
# #             .filter(
# #                 ticket=ticket,
# #                 status='pending',
# #             )
# #             .select_related(
# #                 'workflow_step',
# #                 'workflow_step__specific_user',
# #             )
# #             .order_by('workflow_step__order')
# #         )

# #         for execution in pending_steps:
# #             step = execution.workflow_step

# #             if evaluate(step.condition, ticket):
# #                 return execution

# #             # Condition is not satisfied.
# #             execution.status = 'skipped'
# #             execution.skip_reason = 'Condition not met'
# #             execution.save(
# #                 update_fields=[
# #                     'status',
# #                     'skip_reason',
# #                     'updated_at',
# #                 ]
# #             )

# #         return None

# #     @classmethod
# #     def all_steps(cls, ticket):
# #         """Return all step executions for a ticket, ordered."""

# #         return (
# #             TicketStepExecution.objects
# #             .filter(ticket=ticket)
# #             .select_related(
# #                 'workflow_step',
# #                 'actor',
# #                 'escalated_to',
# #             )
# #             .order_by('workflow_step__order')
# #         )

# #     @classmethod
# #     def is_complete(cls, ticket):
# #         """
# #         Workflow is complete when there are no more actionable steps.

# #         Note: current_step() automatically skips non-matching conditional steps,
# #         so calling it here ensures any remaining steps are properly classified.
# #         """

# #         # Triggers skip of any condition-mismatched steps
# #         next_step = cls.current_step(ticket)

# #         return next_step is None

# #     @classmethod
# #     def is_rejected(cls, ticket):
# #         return TicketStepExecution.objects.filter(
# #             ticket=ticket,
# #             status='rejected',
# #         ).exists()

# #     # =================================================================
# #     # Acting on a step
# #     # =================================================================
# #     @classmethod
# #     def act(cls, ticket, step_execution, actor, action, comment=''):
# #         """
# #         Perform an action on the current workflow step.
# #         """

# #         # Only the current workflow step can be acted upon.
# #         current = cls.current_step(ticket)

# #         if not current or current.id != step_execution.id:
# #             logger.warning(
# #                 f"Step {step_execution.id} is not the current step "
# #                 f"for ticket #{ticket.id}"
# #             )
# #             return False

# #         if step_execution.status != 'pending':
# #             logger.warning(
# #                 f"Step {step_execution.id} is not pending"
# #             )
# #             return False

# #         if action not in ('approve', 'reject', 'skip'):
# #             logger.warning(
# #                 f"Invalid workflow action: {action}"
# #             )
# #             return False

# #         if (
# #             action == 'skip'
# #             and not step_execution.workflow_step.can_skip
# #         ):
# #             logger.warning(
# #                 f"Step {step_execution.id} cannot be skipped"
# #             )
# #             return False

# #         with transaction.atomic():

# #             step_execution.status = {
# #                 'approve': 'approved',
# #                 'reject': 'rejected',
# #                 'skip': 'skipped',
# #             }[action]

# #             step_execution.actor = actor
# #             step_execution.acted_at = timezone.now()
# #             step_execution.comment = comment

# #             step_execution.save()

# #             AuditService.log_action(
# #                 action={
# #                     'approve': 'approve',
# #                     'reject': 'reject',
# #                     'skip': 'approve',
# #                 }[action],
# #                 target=ticket,
# #                 metadata={
# #                     'step_id': step_execution.id,
# #                     'step_name': step_execution.workflow_step.name,
# #                     'action': action,
# #                     'comment': comment[:200],
# #                 },
# #                 user=actor,
# #             )

# #             # Notify (best-effort, non-blocking on failure)
# #             try:
# #                 from apps.notifications.services import NotificationService

# #                 NotificationService.notify_step_action(
# #                     ticket,
# #                     step_execution,
# #                     actor,
# #                     action,
# #                 )
# #             except Exception as e:
# #                 logger.exception(
# #                     f"Workflow notification failed: {e}"
# #                 )

# #             # -----------------------------------------
# #             # REJECT
# #             # -----------------------------------------

# #             if action == 'reject':

# #                 ticket.status = 'rejected'

# #                 ticket.save(
# #                     update_fields=['status']
# #                 )

# #                 return True

# #             # -----------------------------------------
# #             # APPROVE / SKIP
# #             # -----------------------------------------

# #             next_step = cls.current_step(ticket)

# #             if next_step:

# #                 cls._notify_next_step(
# #                     ticket,
# #                     next_step,
# #                 )

# #             else:

# #                 # No executable steps remain.
# #                 ticket.status = 'resolved'
# #                 ticket.resolved_at = timezone.now()
# #                 ticket.resolved_by = actor

# #                 ticket.save(
# #                     update_fields=[
# #                         'status',
# #                         'resolved_at',
# #                         'resolved_by',
# #                     ]
# #                 )

# #             return True

# #     @classmethod
# #     def _notify_next_step(cls, ticket, step_execution):
# #         """Send notification to the next step's approver."""

# #         from apps.workflows.notifications import notify_step_pending

# #         try:
# #             notify_step_pending(
# #                 ticket,
# #                 step_execution,
# #             )
# #         except Exception as e:
# #             logger.exception(
# #                 f"Notification failed for step {step_execution.id}: {e}"
# #             )

# #     # =================================================================
# #     # Who can act on a step?
# #     # =================================================================
# #     @classmethod
# #     def can_user_act(cls, user, step_execution):
# #         """
# #         Return True if `user` is authorized to act on `step_execution`.
# #         """

# #         if step_execution.status != 'pending':
# #             return False

# #         step = step_execution.workflow_step

# #         # Specific user wins
# #         if step.specific_user_id:
# #             return user.id == step.specific_user_id

# #         # Otherwise role check
# #         if step.role_required:
# #             return user.role == step.role_required

# #         # No role specified → any admin
# #         return user.is_admin_role()

# """
# WorkflowEngine — attaches workflows to tickets and advances steps.
# """

# import logging

# from django.db import transaction
# from django.utils import timezone

# from apps.core.audit import AuditService
# from .condition import evaluate
# from .models import TicketStepExecution, Workflow, WorkflowStep


# logger = logging.getLogger(__name__)


# class WorkflowEngine:
#     """Orchestrates multi-step approvals on tickets."""

#     # =================================================================
#     # Attach workflow to a newly created ticket
#     # =================================================================

#     @classmethod
#     def attach_workflow(cls, ticket):
#         workflow = cls._find_workflow(ticket)

#         if not workflow:
#             return None

#         # Prevent duplicate workflow attachment.
#         if TicketStepExecution.objects.filter(ticket=ticket).exists():
#             logger.warning(
#                 f"Workflow already attached to ticket #{ticket.id}"
#             )
#             return workflow

#         with transaction.atomic():
#             steps = workflow.steps.order_by("order")
#             created_count = 0

#             for step in steps:
#                 TicketStepExecution.objects.create(
#                     ticket=ticket,
#                     workflow_step=step,
#                     status="pending",
#                 )

#                 created_count += 1

#             AuditService.log_action(
#                 action="create",
#                 target=ticket,
#                 metadata={
#                     "workflow_attached": workflow.code,
#                     "steps_created": created_count,
#                 },
#             )

#         logger.info(
#             f"Workflow '{workflow.code}' attached to "
#             f"ticket #{ticket.id}: {created_count} steps created"
#         )

#         return workflow

#     @classmethod
#     def _find_workflow(cls, ticket):
#         """Find the active workflow for the ticket's type."""

#         # Prefer workflow explicitly linked to the ticket type.
#         workflow = Workflow.objects.filter(
#             ticket_type__code=ticket.ticket_type,
#             is_active=True,
#         ).first()

#         if workflow:
#             return workflow

#         # Fallback to default workflow.
#         return Workflow.objects.filter(
#             is_active=True,
#             is_default=True,
#         ).first()

#     # =================================================================
#     # Current pending step
#     # =================================================================

#     @classmethod
#     def current_step(cls, ticket):
#         """
#         Return the first pending workflow step whose condition is satisfied.

#         Conditional steps are evaluated only when the workflow reaches them.
#         Steps whose conditions are not satisfied are automatically skipped.
#         """

#         pending_steps = (
#             TicketStepExecution.objects
#             .filter(
#                 ticket=ticket,
#                 status="pending",
#             )
#             .select_related(
#                 "workflow_step",
#                 "workflow_step__specific_user",
#             )
#             .order_by("workflow_step__order")
#         )

#         for execution in pending_steps:
#             step = execution.workflow_step

#             if evaluate(step.condition, ticket):
#                 return execution

#             # Condition is not satisfied.
#             execution.status = "skipped"
#             execution.skip_reason = "Condition not met"
#             execution.save(
#                 update_fields=[
#                     "status",
#                     "skip_reason",
#                     "updated_at",
#                 ]
#             )

#         return None

#     @classmethod
#     def all_steps(cls, ticket):
#         """Return all step executions for a ticket, ordered."""

#         return (
#             TicketStepExecution.objects
#             .filter(ticket=ticket)
#             .select_related(
#                 "workflow_step",
#                 "actor",
#                 "escalated_to",
#             )
#             .order_by("workflow_step__order")
#         )

#     @classmethod
#     def is_complete(cls, ticket):
#         """
#         Workflow is complete when there are no more actionable steps.

#         Note: current_step() automatically skips non-matching conditional
#         steps, so calling it here ensures any remaining steps are properly
#         classified.
#         """

#         # Triggers skip of any condition-mismatched steps.
#         next_step = cls.current_step(ticket)

#         return next_step is None

#     @classmethod
#     def is_rejected(cls, ticket):
#         return TicketStepExecution.objects.filter(
#             ticket=ticket,
#             status="rejected",
#         ).exists()

#     # =================================================================
#     # Acting on a step
#     # =================================================================

#     @classmethod
#     def act(cls, ticket, step_execution, actor, action, comment=""):
#         """
#         Perform an action on the current workflow step.
#         """

#         # Only the current workflow step can be acted upon.
#         current = cls.current_step(ticket)

#         if not current or current.id != step_execution.id:
#             logger.warning(
#                 f"Step {step_execution.id} is not the current step "
#                 f"for ticket #{ticket.id}"
#             )
#             return False

#         if step_execution.status != "pending":
#             logger.warning(
#                 f"Step {step_execution.id} is not pending"
#             )
#             return False

#         if action not in ("approve", "reject", "skip"):
#             logger.warning(
#                 f"Invalid workflow action: {action}"
#             )
#             return False

#         if (
#             action == "skip"
#             and not step_execution.workflow_step.can_skip
#         ):
#             logger.warning(
#                 f"Step {step_execution.id} cannot be skipped"
#             )
#             return False

#         with transaction.atomic():
#             step_execution.status = {
#                 "approve": "approved",
#                 "reject": "rejected",
#                 "skip": "skipped",
#             }[action]

#             step_execution.actor = actor
#             step_execution.acted_at = timezone.now()
#             step_execution.comment = comment

#             step_execution.save()

#             AuditService.log_action(
#                 action={
#                     "approve": "approve",
#                     "reject": "reject",
#                     "skip": "approve",
#                 }[action],
#                 target=ticket,
#                 metadata={
#                     "step_id": step_execution.id,
#                     "step_name": step_execution.workflow_step.name,
#                     "action": action,
#                     "comment": comment[:200],
#                 },
#                 user=actor,
#             )

#             # Notify about the step action.
#             try:
#                 from apps.notifications.services import NotificationService

#                 NotificationService.notify_step_action(
#                     ticket,
#                     step_execution,
#                     actor,
#                     action,
#                 )
#             except Exception as e:
#                 logger.exception(
#                     f"Workflow notification failed: {e}"
#                 )

#             # -----------------------------------------
#             # REJECT
#             # -----------------------------------------

#             if action == "reject":
#                 ticket.status = "rejected"

#                 ticket.save(
#                     update_fields=["status"]
#                 )

#                 # Broadcast ticket update after rejection.
#                 try:
#                     from apps.notifications.broadcasters import (
#                         broadcast_ticket_updated,
#                         broadcast_ticket_resolved,
#                     )

#                     if ticket.status == "resolved":
#                         broadcast_ticket_resolved(ticket)
#                     else:
#                         broadcast_ticket_updated(ticket)

#                 except Exception as e:
#                     logger.warning(
#                         f"broadcast failed in workflow: {e}"
#                     )

#                 return True

#             # -----------------------------------------
#             # APPROVE / SKIP
#             # -----------------------------------------

#             next_step = cls.current_step(ticket)

#             if next_step:
#                 cls._notify_next_step(
#                     ticket,
#                     next_step,
#                 )

#                 # Ticket remains active and advances to next step.
#                 try:
#                     from apps.notifications.broadcasters import (
#                         broadcast_ticket_updated,
#                         broadcast_ticket_resolved,
#                     )

#                     if ticket.status == "resolved":
#                         broadcast_ticket_resolved(ticket)
#                     else:
#                         broadcast_ticket_updated(ticket)

#                 except Exception as e:
#                     logger.warning(
#                         f"broadcast failed in workflow: {e}"
#                     )

#             else:
#                 # No executable steps remain.
#                 ticket.status = "resolved"
#                 ticket.resolved_at = timezone.now()
#                 ticket.resolved_by = actor

#                 ticket.save(
#                     update_fields=[
#                         "status",
#                         "resolved_at",
#                         "resolved_by",
#                     ]
#                 )

#                 # Broadcast ticket resolution.
#                 try:
#                     from apps.notifications.broadcasters import (
#                         broadcast_ticket_updated,
#                         broadcast_ticket_resolved,
#                     )

#                     if ticket.status == "resolved":
#                         broadcast_ticket_resolved(ticket)
#                     else:
#                         broadcast_ticket_updated(ticket)

#                 except Exception as e:
#                     logger.warning(
#                         f"broadcast failed in workflow: {e}"
#                     )

#             return True

#     @classmethod
#     def _notify_next_step(cls, ticket, step_execution):
#         """Send notification to the next step's approver."""

#         from apps.workflows.notifications import notify_step_pending

#         try:
#             notify_step_pending(
#                 ticket,
#                 step_execution,
#             )
#         except Exception as e:
#             logger.exception(
#                 f"Notification failed for step {step_execution.id}: {e}"
#             )

#     # =================================================================
#     # Who can act on a step?
#     # =================================================================

#     @classmethod
#     def can_user_act(cls, user, step_execution):
#         """
#         Return True if user is authorized to act on step_execution.
#         """

#         if step_execution.status != "pending":
#             return False

#         step = step_execution.workflow_step

#         # Specific user wins.
#         if step.specific_user_id:
#             return user.id == step.specific_user_id

#         # Otherwise role check.
#         if step.role_required:
#             return user.role == step.role_required

#         # No role specified → any admin.
#         return user.is_admin_role()

# """
# WorkflowEngine — attaches workflows to tickets and advances steps.
# """

# import logging

# from django.db import transaction
# from django.utils import timezone

# from apps.core.audit import AuditService
# from .condition import evaluate
# from .models import TicketStepExecution, Workflow, WorkflowStep


# logger = logging.getLogger(__name__)


# class WorkflowEngine:
#     """Orchestrates multi-step approvals on tickets."""

#     @classmethod
#     def attach_workflow(cls, ticket):
#         workflow = cls._find_workflow(ticket)

#         if not workflow:
#             return None

#         # Prevent duplicate workflow attachment.
#         if TicketStepExecution.objects.filter(ticket=ticket).exists():
#             logger.warning(
#                 f"Workflow already attached to ticket #{ticket.id}"
#             )
#             return workflow

#         with transaction.atomic():
#             steps = workflow.steps.order_by("order")
#             created_count = 0

#             for step in steps:
#                 TicketStepExecution.objects.create(
#                     ticket=ticket,
#                     workflow_step=step,
#                     status="pending",
#                 )

#                 created_count += 1

#             AuditService.log_action(
#                 action="create",
#                 target=ticket,
#                 metadata={
#                     "workflow_attached": workflow.code,
#                     "steps_created": created_count,
#                 },
#             )

#         logger.info(
#             f"Workflow '{workflow.code}' attached to "
#             f"ticket #{ticket.id}: {created_count} steps created"
#         )

#         return workflow

#     @classmethod
#     def _find_workflow(cls, ticket):
#         """Find the active workflow for the ticket's type."""

#         # Prefer workflow explicitly linked to the ticket type.
#         workflow = Workflow.objects.filter(
#             ticket_type__code=ticket.ticket_type,
#             is_active=True,
#         ).first()

#         if workflow:
#             return workflow

#         # Fallback to default workflow.
#         return Workflow.objects.filter(
#             is_active=True,
#             is_default=True,
#         ).first()

#     @classmethod
#     def current_step(cls, ticket):
#         """
#         Return the first pending workflow step whose condition is satisfied.

#         Conditional steps are evaluated only when the workflow reaches them.
#         Steps whose conditions are not satisfied are automatically skipped.
#         """

#         pending_steps = (
#             TicketStepExecution.objects
#             .filter(
#                 ticket=ticket,
#                 status="pending",
#             )
#             .select_related(
#                 "workflow_step",
#                 "workflow_step__specific_user",
#             )
#             .order_by("workflow_step__order")
#         )

#         for execution in pending_steps:
#             step = execution.workflow_step

#             if evaluate(step.condition, ticket):
#                 return execution

#             # Condition is not satisfied.
#             execution.status = "skipped"
#             execution.skip_reason = "Condition not met"
#             execution.save(
#                 update_fields=[
#                     "status",
#                     "skip_reason",
#                     "updated_at",
#                 ]
#             )

#         return None

#     @classmethod
#     def all_steps(cls, ticket):
#         """Return all step executions for a ticket, ordered."""

#         return (
#             TicketStepExecution.objects
#             .filter(ticket=ticket)
#             .select_related(
#                 "workflow_step",
#                 "actor",
#                 "escalated_to",
#             )
#             .order_by("workflow_step__order")
#         )

#     @classmethod
#     def is_complete(cls, ticket):
#         """
#         Workflow is complete when there are no more actionable steps.

#         Note: current_step() automatically skips non-matching conditional
#         steps, so calling it here ensures any remaining steps are properly
#         classified.
#         """

#         # Triggers skip of any condition-mismatched steps.
#         next_step = cls.current_step(ticket)

#         return next_step is None

#     @classmethod
#     def is_rejected(cls, ticket):
#         return TicketStepExecution.objects.filter(
#             ticket=ticket,
#             status="rejected",
#         ).exists()

#     @classmethod
#     def act(cls, ticket, step_execution, actor, action, comment=""):
#         """
#         Perform an action on the current workflow step.
#         """

#         # Only the current workflow step can be acted upon.
#         current = cls.current_step(ticket)

#         if not current or current.id != step_execution.id:
#             logger.warning(
#                 f"Step {step_execution.id} is not the current step "
#                 f"for ticket #{ticket.id}"
#             )
#             return False

#         if step_execution.status != "pending":
#             logger.warning(
#                 f"Step {step_execution.id} is not pending"
#             )
#             return False

#         if action not in ("approve", "reject", "skip"):
#             logger.warning(
#                 f"Invalid workflow action: {action}"
#             )
#             return False

#         if (
#             action == "skip"
#             and not step_execution.workflow_step.can_skip
#         ):
#             logger.warning(
#                 f"Step {step_execution.id} cannot be skipped"
#             )
#             return False

#         with transaction.atomic():
#             step_execution.status = {
#                 "approve": "approved",
#                 "reject": "rejected",
#                 "skip": "skipped",
#             }[action]

#             step_execution.actor = actor
#             step_execution.acted_at = timezone.now()
#             step_execution.comment = comment

#             step_execution.save()

#             AuditService.log_action(
#                 action={
#                     "approve": "approve",
#                     "reject": "reject",
#                     "skip": "approve",
#                 }[action],
#                 target=ticket,
#                 metadata={
#                     "step_id": step_execution.id,
#                     "step_name": step_execution.workflow_step.name,
#                     "action": action,
#                     "comment": comment[:200],
#                 },
#                 user=actor,
#             )

#             # Notify about the step action.
#             try:
#                 from apps.notifications.services import NotificationService

#                 NotificationService.notify_step_action(
#                     ticket,
#                     step_execution,
#                     actor,
#                     action,
#                 )
#             except Exception as e:
#                 logger.exception(
#                     f"Workflow notification failed: {e}"
#                 )

#             # Import ticket broadcasters.
#             from apps.notifications.broadcasters import (
#                 broadcast_ticket_updated,
#                 broadcast_ticket_resolved,
#                 broadcast_ticket_detail_change,
#             )

#             # -----------------------------------------
#             # REJECT
#             # -----------------------------------------

#             if action == "reject":
#                 ticket.status = "rejected"

#                 ticket.save(
#                     update_fields=["status"]
#                 )

#                 broadcast_ticket_detail_change(
#                     ticket,
#                     actor,
#                     step_name=step_execution.workflow_step.name,
#                 )

#                 broadcast_ticket_updated(ticket)

#                 return True

#             # -----------------------------------------
#             # APPROVE / SKIP
#             # -----------------------------------------

#             next_step = cls.current_step(ticket)

#             if next_step:
#                 cls._notify_next_step(
#                     ticket,
#                     next_step,
#                 )

#                 # Ticket remains active and advances to next step.
#                 broadcast_ticket_detail_change(
#                     ticket,
#                     actor,
#                     step_name=step_execution.workflow_step.name,
#                 )

#                 broadcast_ticket_updated(ticket)

#             else:
#                 # No executable steps remain.
#                 ticket.status = "resolved"
#                 ticket.resolved_at = timezone.now()
#                 ticket.resolved_by = actor

#                 ticket.save(
#                     update_fields=[
#                         "status",
#                         "resolved_at",
#                         "resolved_by",
#                     ]
#                 )

#                 # Auto-issue document if applicable.
#                 if ticket.ticket_type == "document":
#                     try:
#                         from apps.documents.services import DocumentService
#                         from apps.documents.models import DocumentTemplate

#                         # Match doc_type from dynamic_data
#                         # or default to bonafide.
#                         doc_type = (
#                             (ticket.dynamic_data or {}).get(
#                                 "document_type",
#                                 "bonafide",
#                             )
#                         )

#                         # Check an active template exists.
#                         if DocumentTemplate.objects.filter(
#                             doc_type=doc_type,
#                             is_active=True,
#                         ).exists():
#                             doc = DocumentService.issue_document(
#                                 student=ticket.student,
#                                 doc_type=doc_type,
#                                 title=f"{ticket.subject}",
#                                 source_ticket=ticket,
#                                 issued_by=actor,
#                             )

#                             # Notify student.
#                             from apps.notifications.services import (
#                                 NotificationService,
#                             )

#                             NotificationService.notify(
#                                 recipient=ticket.student,
#                                 event_code="document.issued",
#                                 context={
#                                     "document_title": doc.title,
#                                     "verification_url": (
#                                         f"/verify/"
#                                         f"{doc.verification_uuid}/"
#                                     ),
#                                     "download_url": (
#                                         f"/documents/"
#                                         f"{doc.id}/download/"
#                                     ),
#                                 },
#                                 link_url=(
#                                     f"/documents/"
#                                     f"{doc.id}/download/"
#                                 ),
#                                 target=doc,
#                                 priority="high",
#                             )

#                     except Exception as e:
#                         logger.exception(
#                             f"Auto-issue document failed: {e}"
#                         )

#                 # Broadcast ticket resolution.
#                 broadcast_ticket_detail_change(
#                     ticket,
#                     actor,
#                     step_name=step_execution.workflow_step.name,
#                 )

#                 broadcast_ticket_resolved(ticket)

#             return True

#     @classmethod
#     def _notify_next_step(cls, ticket, step_execution):
#         """Send notification to the next step's approver."""

#         from apps.workflows.notifications import notify_step_pending

#         try:
#             notify_step_pending(
#                 ticket,
#                 step_execution,
#             )
#         except Exception as e:
#             logger.exception(
#                 f"Notification failed for step {step_execution.id}: {e}"
#             )

#     @classmethod
#     def can_user_act(cls, user, step_execution):
#         """
#         Return True if user is authorized to act on step_execution.
#         """

#         if step_execution.status != "pending":
#             return False

#         step = step_execution.workflow_step

#         # Specific user wins.
#         if step.specific_user_id:
#             return user.id == step.specific_user_id

#         # Otherwise role check.
#         if step.role_required:
#             return user.role == step.role_required

#         # No role specified → any admin.
#         return user.is_admin_role()



# 2nd phase 
# """
# WorkflowEngine — attaches workflows to tickets and advances steps.
# """

# import logging

# from django.db import transaction
# from django.utils import timezone

# from apps.core.audit import AuditService

# from .condition import evaluate

# from .models import TicketStepExecution, Workflow, WorkflowStep


# logger = logging.getLogger(__name__)


# class WorkflowEngine:
#     """Orchestrates multi-step approvals on tickets."""

#     @classmethod
#     def attach_workflow(cls, ticket):
#         workflow = cls._find_workflow(ticket)

#         if not workflow:
#             return None

#         # Prevent duplicate workflow attachment.
#         if TicketStepExecution.objects.filter(ticket=ticket).exists():
#             logger.warning(
#                 f"Workflow already attached to ticket #{ticket.id}"
#             )
#             return workflow

#         with transaction.atomic():
#             steps = workflow.steps.order_by("order")
#             created_count = 0

#             for step in steps:
#                 TicketStepExecution.objects.create(
#                     ticket=ticket,
#                     workflow_step=step,
#                     status="pending",
#                 )

#                 created_count += 1

#             AuditService.log_action(
#                 action="create",
#                 target=ticket,
#                 metadata={
#                     "workflow_attached": workflow.code,
#                     "steps_created": created_count,
#                 },
#             )

#         logger.info(
#             f"Workflow '{workflow.code}' attached to "
#             f"ticket #{ticket.id}: {created_count} steps created"
#         )

#         return workflow

#     @classmethod
#     def _find_workflow(cls, ticket):
#         """LLM-driven workflow selection with rule-based fallback."""
#         try:
#             from ai_engine.pipelines.workflow_selector import select_workflow_for_ticket
#             return select_workflow_for_ticket(ticket)
#         except Exception as e:
#             logger.exception(f"LLM workflow selector failed: {e}")

#             # Fallback to rule-based
#             from apps.workflows.selector import select_workflow
#             return select_workflow(ticket)

#     @classmethod
#     def current_step(cls, ticket):
#         """
#         Return the first pending workflow step whose condition is satisfied.

#         Conditional steps are evaluated only when the workflow reaches them.
#         Steps whose conditions are not satisfied are automatically skipped.
#         """

#         pending_steps = (
#             TicketStepExecution.objects
#             .filter(
#                 ticket=ticket,
#                 status="pending",
#             )
#             .select_related(
#                 "workflow_step",
#                 "workflow_step__specific_user",
#             )
#             .order_by("workflow_step__order")
#         )

#         for execution in pending_steps:
#             step = execution.workflow_step

#             if evaluate(step.condition, ticket):
#                 return execution

#             # Condition is not satisfied.
#             execution.status = "skipped"
#             execution.skip_reason = "Condition not met"
#             execution.save(
#                 update_fields=[
#                     "status",
#                     "skip_reason",
#                     "updated_at",
#                 ]
#             )

#         return None

#     @classmethod
#     def all_steps(cls, ticket):
#         """Return all step executions for a ticket, ordered."""

#         return (
#             TicketStepExecution.objects
#             .filter(ticket=ticket)
#             .select_related(
#                 "workflow_step",
#                 "actor",
#                 "escalated_to",
#             )
#             .order_by("workflow_step__order")
#         )

#     @classmethod
#     def is_complete(cls, ticket):
#         """
#         Workflow is complete when there are no more actionable steps.

#         Note: current_step() automatically skips non-matching conditional
#         steps, so calling it here ensures any remaining steps are properly
#         classified.
#         """

#         # Triggers skip of any condition-mismatched steps.
#         next_step = cls.current_step(ticket)

#         return next_step is None

#     @classmethod
#     def is_rejected(cls, ticket):
#         return TicketStepExecution.objects.filter(
#             ticket=ticket,
#             status="rejected",
#         ).exists()

#     @classmethod
#     def act(cls, ticket, step_execution, actor, action, comment=""):
#         """
#         Perform an action on the current workflow step.
#         """

#         # Only the current workflow step can be acted upon.
#         current = cls.current_step(ticket)

#         if not current or current.id != step_execution.id:
#             logger.warning(
#                 f"Step {step_execution.id} is not the current step "
#                 f"for ticket #{ticket.id}"
#             )
#             return False

#         if step_execution.status != "pending":
#             logger.warning(
#                 f"Step {step_execution.id} is not pending"
#             )
#             return False

#         if action not in ("approve", "reject", "skip"):
#             logger.warning(
#                 f"Invalid workflow action: {action}"
#             )
#             return False

#         if (
#             action == "skip"
#             and not step_execution.workflow_step.can_skip
#         ):
#             logger.warning(
#                 f"Step {step_execution.id} cannot be skipped"
#             )
#             return False

#         with transaction.atomic():
#             step_execution.status = {
#                 "approve": "approved",
#                 "reject": "rejected",
#                 "skip": "skipped",
#             }[action]

#             step_execution.actor = actor
#             step_execution.acted_at = timezone.now()
#             step_execution.comment = comment

#             step_execution.save()

#             if step_execution.workflow_step.action_type == "sign":
#                 import hashlib
#                 import hmac

#                 from django.conf import settings

#                 secret = getattr(
#                     settings,
#                     "DOC_SIGNING_SECRET",
#                     "insecure",
#                 )

#                 payload = (
#                     f"{ticket.id}|"
#                     f"{step_execution.id}|"
#                     f"{actor.id}|"
#                     f"{timezone.now().isoformat()}"
#                 )

#                 signature = hmac.new(
#                     secret.encode(),
#                     payload.encode(),
#                     hashlib.sha256,
#                 ).hexdigest()

#                 # Store on the ticket's metadata
#                 sigs = ticket.ai_metadata.get("signatures", [])

#                 sigs.append(
#                     {
#                         "step_id": step_execution.id,
#                         "step_name": step_execution.workflow_step.name,
#                         "signed_by": actor.username,
#                         "signed_by_name": (
#                             actor.get_full_name()
#                             or actor.username
#                         ),
#                         "signed_by_role": actor.get_role_display(),
#                         "signed_at": timezone.now().isoformat(),
#                         "signature": signature,
#                         "signature_short": signature[:16].upper(),
#                     }
#                 )

#                 ticket.ai_metadata["signatures"] = sigs

#                 ticket.save(
#                     update_fields=[
#                         "ai_metadata",
#                         "updated_at",
#                     ]
#                 )

#             AuditService.log_action(
#                 action={
#                     "approve": "approve",
#                     "reject": "reject",
#                     "skip": "approve",
#                 }[action],
#                 target=ticket,
#                 metadata={
#                     "step_id": step_execution.id,
#                     "step_name": step_execution.workflow_step.name,
#                     "action": action,
#                     "comment": comment[:200],
#                 },
#                 user=actor,
#             )

#             # Notify about the step action.
#             try:
#                 from apps.notifications.services import NotificationService

#                 NotificationService.notify_step_action(
#                     ticket,
#                     step_execution,
#                     actor,
#                     action,
#                 )
#             except Exception as e:
#                 logger.exception(
#                     f"Workflow notification failed: {e}"
#                 )

#             # Import ticket broadcasters.
#             from apps.notifications.broadcasters import (
#                 broadcast_ticket_updated,
#                 broadcast_ticket_resolved,
#                 broadcast_ticket_detail_change,
#             )

#             # -----------------------------------------
#             # REJECT
#             # -----------------------------------------

#             if action == "reject":
#                 ticket.status = "rejected"

#                 ticket.save(
#                     update_fields=["status"]
#                 )

#                 broadcast_ticket_detail_change(
#                     ticket,
#                     actor,
#                     step_name=step_execution.workflow_step.name,
#                 )

#                 broadcast_ticket_updated(ticket)

#                 return True

#             # -----------------------------------------
#             # APPROVE / SKIP
#             # -----------------------------------------

#             next_step = cls.current_step(ticket)

#             if next_step:
#                 cls._notify_next_step(
#                     ticket,
#                     next_step,
#                 )

#                 # Ticket remains active and advances to next step.
#                 broadcast_ticket_detail_change(
#                     ticket,
#                     actor,
#                     step_name=step_execution.workflow_step.name,
#                 )

#                 broadcast_ticket_updated(ticket)

#             else:
#                 # No executable steps remain.
#                 ticket.status = "resolved"
#                 ticket.resolved_at = timezone.now()
#                 ticket.resolved_by = actor

#                 ticket.save(
#                     update_fields=[
#                         "status",
#                         "resolved_at",
#                         "resolved_by",
#                     ]
#                 )

#                 # Auto-issue document if applicable.
#                 if ticket.ticket_type == "document":
#                     try:
#                         from apps.documents.services import DocumentService
#                         from apps.documents.models import DocumentTemplate

#                         # Match doc_type from dynamic_data
#                         # or default to bonafide.
#                         doc_type = (
#                             (ticket.dynamic_data or {}).get(
#                                 "document_type",
#                                 "bonafide",
#                             )
#                         )

#                         # Check an active template exists.
#                         if DocumentTemplate.objects.filter(
#                             doc_type=doc_type,
#                             is_active=True,
#                         ).exists():
#                             doc = DocumentService.issue_document(
#                                 student=ticket.student,
#                                 doc_type=doc_type,
#                                 title=f"{ticket.subject}",
#                                 source_ticket=ticket,
#                                 issued_by=actor,
#                             )

#                             # Notify student.
#                             from apps.notifications.services import (
#                                 NotificationService,
#                             )

#                             NotificationService.notify(
#                                 recipient=ticket.student,
#                                 event_code="document.issued",
#                                 context={
#                                     "document_title": doc.title,
#                                     "verification_url": (
#                                         f"/verify/"
#                                         f"{doc.verification_uuid}/"
#                                     ),
#                                     "download_url": (
#                                         f"/documents/"
#                                         f"{doc.id}/download/"
#                                     ),
#                                 },
#                                 link_url=(
#                                     f"/documents/"
#                                     f"{doc.id}/download/"
#                                 ),
#                                 target=doc,
#                                 priority="high",
#                             )

#                     except Exception as e:
#                         logger.exception(
#                             f"Auto-issue document failed: {e}"
#                         )

#                 # Broadcast ticket resolution.
#                 broadcast_ticket_detail_change(
#                     ticket,
#                     actor,
#                     step_name=step_execution.workflow_step.name,
#                 )

#                 broadcast_ticket_resolved(ticket)

#             return True

#     @classmethod
#     def _notify_next_step(cls, ticket, step_execution):
#         """Send notification to the next step's approver."""

#         from apps.workflows.notifications import notify_step_pending

#         try:
#             notify_step_pending(
#                 ticket,
#                 step_execution,
#             )
#         except Exception as e:
#             logger.exception(
#                 f"Notification failed for step {step_execution.id}: {e}"
#             )

#     @classmethod
#     def can_user_act(cls, user, step_execution):
#         """Return True if user is authorized to act on step_execution."""

#         if step_execution.status != "pending":
#             return False

#         step = step_execution.workflow_step

#         # Specific user
#         if step.specific_user_id:
#             return user.id == step.specific_user_id

#         # Role-based — but now with hierarchy
#         if step.role_required:
#             # Direct match OR higher rank
#             return (
#                 user.role == step.role_required
#                 or user.has_rank_at_least(step.role_required)
#             )

#         # Fallback: any admin
#         return user.is_admin_role()

"""
WorkflowEngine — attaches workflows to tickets and advances steps.
"""

import logging
import base64
import hashlib
import hmac
from io import BytesIO

import qrcode

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.audit import AuditService

from .condition import evaluate
from .models import TicketStepExecution, Workflow, WorkflowStep


logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Orchestrates multi-step approvals on tickets."""

    @classmethod
    def attach_workflow(cls, ticket):
        workflow = cls._find_workflow(ticket)

        if not workflow:
            return None

        if TicketStepExecution.objects.filter(ticket=ticket).exists():
            logger.warning(
                f"Workflow already attached to ticket #{ticket.id}"
            )
            return workflow

        with transaction.atomic():
            steps = workflow.steps.order_by("order")
            created_count = 0

            for step in steps:
                TicketStepExecution.objects.create(
                    ticket=ticket,
                    workflow_step=step,
                    status="pending",
                )
                created_count += 1

            AuditService.log_action(
                action="create",
                target=ticket,
                metadata={
                    "workflow_attached": workflow.code,
                    "steps_created": created_count,
                },
            )

        logger.info(
            f"Workflow '{workflow.code}' attached to "
            f"ticket #{ticket.id}: {created_count} steps created"
        )

        return workflow

    @classmethod
    def _find_workflow(cls, ticket):
        """LLM-driven workflow selection with rule-based fallback."""
        try:
            from ai_engine.pipelines.workflow_selector import (
                select_workflow_for_ticket,
            )
            return select_workflow_for_ticket(ticket)
        except Exception as e:
            logger.exception(f"LLM workflow selector failed: {e}")

            from apps.workflows.selector import select_workflow
            return select_workflow(ticket)

    @classmethod
    def current_step(cls, ticket):
        """
        Return the first pending workflow step whose condition is satisfied.

        Conditional steps are evaluated only when the workflow reaches them.
        Steps whose conditions are not satisfied are automatically skipped.
        """
        pending_steps = (
            TicketStepExecution.objects
            .filter(ticket=ticket, status="pending")
            .select_related(
                "workflow_step",
                "workflow_step__specific_user",
            )
            .order_by("workflow_step__order")
        )

        for execution in pending_steps:
            step = execution.workflow_step

            if evaluate(step.condition, ticket):
                return execution

            execution.status = "skipped"
            execution.skip_reason = "Condition not met"
            execution.save(
                update_fields=[
                    "status",
                    "skip_reason",
                    "updated_at",
                ]
            )

        return None

    @classmethod
    def all_steps(cls, ticket):
        """Return all step executions for a ticket, ordered."""
        return (
            TicketStepExecution.objects
            .filter(ticket=ticket)
            .select_related(
                "workflow_step",
                "actor",
                "escalated_to",
            )
            .order_by("workflow_step__order")
        )

    @classmethod
    def is_complete(cls, ticket):
        """
        Workflow is complete when there are no more actionable steps.

        current_step() automatically skips conditional steps that do not match.
        """
        next_step = cls.current_step(ticket)
        return next_step is None

    @classmethod
    def is_rejected(cls, ticket):
        return TicketStepExecution.objects.filter(
            ticket=ticket,
            status="rejected",
        ).exists()

    @classmethod
    def act(cls, ticket, step_execution, actor, action, comment=""):
        """Perform an action on the current workflow step."""

        current = cls.current_step(ticket)

        if not current or current.id != step_execution.id:
            logger.warning(
                f"Step {step_execution.id} is not the current step "
                f"for ticket #{ticket.id}"
            )
            return False

        if step_execution.status != "pending":
            logger.warning(
                f"Step {step_execution.id} is not pending"
            )
            return False

        if action not in ("approve", "reject", "skip"):
            logger.warning(
                f"Invalid workflow action: {action}"
            )
            return False

        if (
            action == "skip"
            and not step_execution.workflow_step.can_skip
        ):
            logger.warning(
                f"Step {step_execution.id} cannot be skipped"
            )
            return False

        with transaction.atomic():
            step_execution.status = {
                "approve": "approved",
                "reject": "rejected",
                "skip": "skipped",
            }[action]

            step_execution.actor = actor
            step_execution.acted_at = timezone.now()
            step_execution.comment = comment
            step_execution.save()

            if (
                action == "approve"
                and step_execution.workflow_step.action_type == "sign"
            ):
                secret = getattr(
                    settings,
                    "DOC_SIGNING_SECRET",
                    "insecure",
                )

                signed_at = timezone.now().isoformat()
                payload = (
                    f"{ticket.id}|"
                    f"{step_execution.id}|"
                    f"{actor.id}|"
                    f"{signed_at}"
                )

                signature = hmac.new(
                    secret.encode(),
                    payload.encode(),
                    hashlib.sha256,
                ).hexdigest()

                base_url = getattr(
                    settings,
                    "SITE_URL",
                    "http://localhost:8000",
                ).rstrip("/")

                verify_url = (
                    f"{base_url}/verify-signature/"
                    f"{ticket.id}/{step_execution.id}/"
                )

                qr = qrcode.QRCode(
                    version=None,
                    box_size=6,
                    border=2,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                )
                qr.add_data(verify_url)
                qr.make(fit=True)

                img = qr.make_image(
                    fill_color="#4d0f18",
                    back_color="white",
                )

                buf = BytesIO()
                img.save(buf, format="PNG")
                qr_b64 = base64.b64encode(
                    buf.getvalue()
                ).decode("ascii")

                metadata = ticket.ai_metadata or {}
                sigs = metadata.get("signatures", [])

                sigs.append({
                    "step_id": step_execution.id,
                    "step_name": step_execution.workflow_step.name,
                    "signed_by": actor.username,
                    "signed_by_name": (
                        actor.get_full_name() or actor.username
                    ),
                    "signed_by_role": actor.get_role_display(),
                    "signed_at": signed_at,
                    "payload": payload,
                    "signature": signature,
                    "signature_short": signature[:16].upper(),
                    "verify_url": verify_url,
                    "qr_b64": qr_b64,
                })

                metadata["signatures"] = sigs
                ticket.ai_metadata = metadata

                ticket.save(
                    update_fields=[
                        "ai_metadata",
                        "updated_at",
                    ]
                )

            AuditService.log_action(
                action={
                    "approve": "approve",
                    "reject": "reject",
                    "skip": "approve",
                }[action],
                target=ticket,
                metadata={
                    "step_id": step_execution.id,
                    "step_name": step_execution.workflow_step.name,
                    "action": action,
                    "comment": comment[:200],
                },
                user=actor,
            )

            try:
                from apps.notifications.services import NotificationService

                NotificationService.notify_step_action(
                    ticket,
                    step_execution,
                    actor,
                    action,
                )
            except Exception as e:
                logger.exception(
                    f"Workflow notification failed: {e}"
                )

            from apps.notifications.broadcasters import (
                broadcast_ticket_updated,
                broadcast_ticket_resolved,
                broadcast_ticket_detail_change,
            )

            if action == "reject":
                ticket.status = "rejected"
                ticket.save(update_fields=["status"])

                broadcast_ticket_detail_change(
                    ticket,
                    actor,
                    step_name=step_execution.workflow_step.name,
                )
                broadcast_ticket_updated(ticket)
                return True

            next_step = cls.current_step(ticket)

            if next_step:
                cls._notify_next_step(ticket, next_step)

                broadcast_ticket_detail_change(
                    ticket,
                    actor,
                    step_name=step_execution.workflow_step.name,
                )
                broadcast_ticket_updated(ticket)

            else:
                ticket.status = "resolved"
                ticket.resolved_at = timezone.now()
                ticket.resolved_by = actor

                ticket.save(
                    update_fields=[
                        "status",
                        "resolved_at",
                        "resolved_by",
                    ]
                )

                if ticket.ticket_type == "document":
                    try:
                        from apps.documents.services import DocumentService
                        from apps.documents.models import DocumentTemplate

                        doc_type = (
                            (ticket.dynamic_data or {}).get(
                                "document_type",
                                "bonafide",
                            )
                        )

                        if DocumentTemplate.objects.filter(
                            doc_type=doc_type,
                            is_active=True,
                        ).exists():
                            doc = DocumentService.issue_document(
                                student=ticket.student,
                                doc_type=doc_type,
                                title=f"{ticket.subject}",
                                source_ticket=ticket,
                                issued_by=actor,
                            )

                            from apps.notifications.services import (
                                NotificationService,
                            )

                            NotificationService.notify(
                                recipient=ticket.student,
                                event_code="document.issued",
                                context={
                                    "document_title": doc.title,
                                    "verification_url": (
                                        f"/verify/"
                                        f"{doc.verification_uuid}/"
                                    ),
                                    "download_url": (
                                        f"/documents/"
                                        f"{doc.id}/download/"
                                    ),
                                },
                                link_url=(
                                    f"/documents/"
                                    f"{doc.id}/download/"
                                ),
                                target=doc,
                                priority="high",
                            )

                    except Exception as e:
                        logger.exception(
                            f"Auto-issue document failed: {e}"
                        )

                broadcast_ticket_detail_change(
                    ticket,
                    actor,
                    step_name=step_execution.workflow_step.name,
                )
                broadcast_ticket_resolved(ticket)

            return True

    @classmethod
    def _notify_next_step(cls, ticket, step_execution):
        """Send notification to the next step's approver."""
        from apps.workflows.notifications import notify_step_pending

        try:
            notify_step_pending(ticket, step_execution)
        except Exception as e:
            logger.exception(
                f"Notification failed for step {step_execution.id}: {e}"
            )

    @classmethod
    def can_user_act(cls, user, step_execution):
        """Return True if user is authorized to act on step_execution."""

        if step_execution.status != "pending":
            return False

        step = step_execution.workflow_step

        if step.specific_user_id:
            return user.id == step.specific_user_id

        if step.role_required:
            return (
                user.role == step.role_required
                or user.has_rank_at_least(step.role_required)
            )

        return user.is_admin_role()