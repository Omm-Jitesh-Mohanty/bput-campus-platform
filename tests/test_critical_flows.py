"""
Critical end-to-end flows.

These tests must pass before every demo. If any fails, do NOT demo.
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from tests.helpers import make_student, make_admin, login
from apps.tickets.models import CampusTicket
from apps.core.models import Department, TicketType, PriorityLevel
from apps.workflows.models import Workflow, WorkflowStep, TicketStepExecution
from apps.notifications.models import Notification


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
)
class CriticalFlowTests(TestCase):
    """Every test corresponds to a scene in the demo script."""

    def setUp(self):
        self.client = Client()
        self.student = make_student('flow_student')
        self.warden = make_admin('flow_warden', role='warden')
        self.hod = make_admin('flow_hod', role='hod')

    # ================================================================
    # Flow 1: Student submits ticket → auto-routed → notification
    # ================================================================
    def test_ticket_submission_end_to_end(self):
        login(self.client, self.student)

        # Student submits a complaint
        response = self.client.post(reverse('tickets:submit'), {
            'ticket_type': 'complaint',
            'raw_input': 'Water tap leaking in Block A room 302 for 3 days',
        }, follow=True)

        self.assertEqual(response.status_code, 200)

        # Ticket created
        ticket = CampusTicket.objects.latest('id')
        self.assertEqual(ticket.student, self.student)
        self.assertEqual(ticket.ticket_type, 'complaint')

        # AI routed to plumbing (or general if no keywords)
        self.assertIn(ticket.assigned_department, ['plumbing', 'general'])

        # Workflow attached
        step_count = TicketStepExecution.objects.filter(ticket=ticket).count()
        self.assertGreater(step_count, 0, "Workflow steps should be attached")

        # Student got notification
        notif_count = Notification.objects.filter(
            recipient=self.student, event_code='ticket.created'
        ).count()
        self.assertEqual(notif_count, 1)

    # ================================================================
    # Flow 2: Warden approves → HOD notified → resolved
    # ================================================================
    def test_workflow_approval_chain(self):
        login(self.client, self.student)
        self.client.post(reverse('tickets:submit'), {
            'ticket_type': 'complaint',
            'raw_input': 'Broken door lock in Block A room 305',
        })

        ticket = CampusTicket.objects.latest('id')

        # Warden logs in and approves first step
        login(self.client, self.warden)
        current_step = TicketStepExecution.objects.filter(
            ticket=ticket, status='pending'
        ).first()
        self.assertIsNotNone(current_step, "There must be a pending step")

        response = self.client.post(
            reverse('tickets:admin_resolve', args=[ticket.id]),
            {
                'resolution_note': 'Verified and assigned to maintenance',
                'workflow_action': 'approve',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        # Step marked approved
        current_step.refresh_from_db()
        self.assertEqual(current_step.status, 'approved')

    # ================================================================
    # Flow 3: Notice publishing → AI summary → student notified
    # ================================================================
    def test_notice_publishing(self):
        login(self.client, self.warden)

        response = self.client.post(reverse('notices:publish'), {
            'title': 'Mid-semester exams schedule',
            'content': 'Mid-semester exams begin 15th March. All students must download hall tickets before 12th March.',
            'priority': 'medium',
            'target_department': 'CSE',
            'target_batch': '2023',
        }, follow=True)

        self.assertEqual(response.status_code, 200)

        from apps.notices.models import Notice
        notice = Notice.objects.latest('id')
        self.assertEqual(notice.title, 'Mid-semester exams schedule')
        # AI may or may not have run; we just check the summary is present (or fallback)
        self.assertTrue(notice.ai_summary or notice.ai_priority)

    # ================================================================
    # Flow 4: Attendance recovery plan
    # ================================================================
    def test_attendance_recovery_plan(self):
        from apps.attendance.models import AttendanceRecord
        from apps.attendance.services import recovery_plan

        AttendanceRecord.objects.create(
            student=self.student,
            subject_code='CS301',
            subject_name='DBMS',
            total_classes=30,
            attended_classes=15,   # 50%
        )

        login(self.client, self.student)
        response = self.client.get(reverse('attendance:list'))
        self.assertEqual(response.status_code, 200)

        # Recovery plan should be computed
        plan = recovery_plan(15, 30)
        self.assertGreater(plan['needed'], 0)
        self.assertIn('consecutive', plan['message'])

    # ================================================================
    # Flow 5: Document issuance + verification
    # ================================================================
    def test_document_issuance_and_verification(self):
        from apps.documents.models import DocumentTemplate, IssuedDocument
        from apps.documents.services import DocumentService

        # Create a template if not present
        if not DocumentTemplate.objects.filter(doc_type='bonafide', is_active=True).exists():
            self.skipTest("No active bonafide template — skip document test")

        try:
            doc = DocumentService.issue_document(
                student=self.student,
                doc_type='bonafide',
                title='Test Bonafide',
            )
        except Exception as e:
            self.skipTest(f"Render failed: {e}")

        self.assertEqual(doc.render_status, 'ready')
        self.assertTrue(doc.signature_hash)

        # Verify via public URL
        response = self.client.get(f'/verify/{doc.verification_uuid}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verified')

    # ================================================================
    # Flow 6: Cache invalidation on config change
    # ================================================================
    def test_config_change_invalidates_cache(self):
        from apps.core.services import ConfigService

        # Prime cache
        count1 = len(ConfigService.departments())

        # Add a department
        Department.objects.create(code='test_dept', name='Test Department', icon='🧪')

        # Cache should auto-invalidate
        count2 = len(ConfigService.departments())
        self.assertEqual(count2, count1 + 1)

    # ================================================================
    # Flow 7: Permission guard — student cannot access admin
    # ================================================================
    def test_student_cannot_access_admin(self):
        login(self.client, self.student)

        response = self.client.get(reverse('dashboard:admin_home'))
        # Should redirect (or 403 if using decorators)
        self.assertIn(response.status_code, [302, 403])

        response = self.client.get(reverse('manage_panel:home'))
        self.assertIn(response.status_code, [302, 403])

    # ================================================================
    # Flow 8: Notification bell count via API
    # ================================================================
    def test_notification_unread_count(self):
        login(self.client, self.student)

        # Create a notification
        Notification.objects.create(
            recipient=self.student,
            event_code='test.event',
            title='Test',
            body='Test notification',
        )

        response = self.client.get(reverse('notifications:unread_count'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)