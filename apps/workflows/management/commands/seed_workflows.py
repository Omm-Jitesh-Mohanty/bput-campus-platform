"""
Seed demo workflows for tickets.
Run: python manage.py seed_workflows
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.core.models import TicketType
from apps.workflows.models import Workflow, WorkflowStep

User = get_user_model()


class Command(BaseCommand):
    help = 'Create default workflows for existing ticket types.'

    def handle(self, *args, **options):
        complaint_tt = TicketType.objects.filter(code='complaint').first()
        leave_tt = TicketType.objects.filter(code='leave').first()
        doc_tt = TicketType.objects.filter(code='document').first()
        gatepass_tt = TicketType.objects.filter(code='gatepass').first()

        # ---------- Complaint: staff → HOD → (conditional Dean) ----------
        if complaint_tt:
            wf, created = Workflow.objects.get_or_create(
                code='complaint_default',
                defaults={
                    'name': 'Complaint Approval Chain',
                    'ticket_type': complaint_tt,
                    'is_active': True,
                    'description': 'Maintenance staff → HOD → Dean (if cost > ₹5,000)',
                }
            )
            if created:
                WorkflowStep.objects.create(
                    workflow=wf, order=1,
                    name='Maintenance Review',
                    role_required='warden',
                    action_type='review',
                    instructions='Verify the issue and estimate repair cost.'
                )
                WorkflowStep.objects.create(
                    workflow=wf, order=2,
                    name='HOD Approval',
                    role_required='hod',
                    action_type='approve',
                    instructions='Approve the repair action.'
                )
                WorkflowStep.objects.create(
                    workflow=wf, order=3,
                    name='Dean Sanction (cost > ₹5,000)',
                    role_required='dean',
                    action_type='sign',
                    can_skip=True,
                    condition={
                        'field': 'dynamic_data.estimated_cost',
                        'operator': '>',
                        'value': 5000
                    },
                    instructions='Required only if estimated cost exceeds ₹5,000.'
                )
                self.stdout.write(f'  ✓ {wf.name}')

        # ---------- Leave: warden → (conditional HOD) ----------
        if leave_tt:
            wf, created = Workflow.objects.get_or_create(
                code='leave_default',
                defaults={
                    'name': 'Leave Approval Chain',
                    'ticket_type': leave_tt,
                    'is_active': True,
                    'description': 'Warden → HOD (if duration > 3 days)',
                }
            )
            if created:
                WorkflowStep.objects.create(
                    workflow=wf, order=1,
                    name='Warden Approval',
                    role_required='warden',
                    action_type='approve',
                )
                WorkflowStep.objects.create(
                    workflow=wf, order=2,
                    name='HOD Approval',
                    role_required='hod',
                    action_type='approve',
                    can_skip=True,
                    condition={
                        'field': 'dynamic_data.duration_days',
                        'operator': '>',
                        'value': 3
                    },
                )
                self.stdout.write(f'  ✓ {wf.name}')

        # ---------- Document: HOD → Principal ----------
        if doc_tt:
            wf, created = Workflow.objects.get_or_create(
                code='document_default',
                defaults={
                    'name': 'Certificate Issuance',
                    'ticket_type': doc_tt,
                    'is_active': True,
                    'description': 'HOD → Principal (for official documents)',
                }
            )
            if created:
                WorkflowStep.objects.create(
                    workflow=wf, order=1,
                    name='HOD Verification',
                    role_required='hod',
                    action_type='verify',
                )
                WorkflowStep.objects.create(
                    workflow=wf, order=2,
                    name='Principal Sign-off',
                    role_required='principal',
                    action_type='sign',
                )
                self.stdout.write(f'  ✓ {wf.name}')

        # ---------- Gate Pass: warden only ----------
        if gatepass_tt:
            wf, created = Workflow.objects.get_or_create(
                code='gatepass_default',
                defaults={
                    'name': 'Gate Pass Approval',
                    'ticket_type': gatepass_tt,
                    'is_active': True,
                    'description': 'Warden approval only',
                }
            )
            if created:
                WorkflowStep.objects.create(
                    workflow=wf, order=1,
                    name='Warden Approval',
                    role_required='warden',
                    action_type='approve',
                )
                self.stdout.write(f'  ✓ {wf.name}')

        self.stdout.write(self.style.SUCCESS('\n✓ Demo workflows seeded.'))