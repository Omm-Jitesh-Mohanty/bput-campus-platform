"""
Comprehensive RBAC test suite.
Verifies that every role sees exactly what they should — no more, no less.
"""

from django.test import TestCase, Client
from django.urls import reverse

from tests.helpers import make_student, make_admin
from apps.core.permissions import Perm, has_perm
from apps.core.scoping import DataScope


class NavbarVisibilityTests(TestCase):
    """Each role sees only their own links."""

    def setUp(self):
        self.client = Client()

    def _login(self, user):
        user.set_password('test')
        user.save()
        self.client.login(
            username=user.username,
            password='test',
        )

    def _get_navbar(self, user):
        """Fetch a logged-in page that renders the role-specific navbar."""
        self._login(user)

        if user.role == 'student':
            url = reverse('dashboard:student_home')
        elif user.role in ('principal', 'director', 'chairman'):
            url = reverse('dashboard:executive')
        else:
            url = reverse('tickets:my_queue')

        response = self.client.get(
            url,
            follow=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        return response.content.decode()

    def test_student_navbar(self):
        student = make_student('nav_s')

        nav = self._get_navbar(student)

        self.assertIn(
            'Dashboard',
            nav,
        )

        self.assertIn(
            'Attendance',
            nav,
        )

        self.assertIn(
            'Timetable',
            nav,
        )

        self.assertIn(
            'My Requests',
            nav,
        )

        self.assertIn(
            'Notices',
            nav,
        )

        self.assertIn(
            'Documents',
            nav,
        )

        self.assertIn(
            'Feedback',
            nav,
        )

        self.assertIn(
            'Assistant',
            nav,
        )

        self.assertNotIn(
            'Manage',
            nav,
        )

        self.assertNotIn(
            'Audit',
            nav,
        )

        self.assertNotIn(
            'Executive View',
            nav,
        )

        self.assertNotIn(
            'All Requests',
            nav,
        )

    def test_warden_navbar(self):
        warden = make_admin(
            'nav_w',
            role='warden',
            hostel_block='A',
        )

        nav = self._get_navbar(warden)

        self.assertIn(
            'My Queue',
            nav,
        )

        self.assertIn(
            'Notices',
            nav,
        )

        self.assertIn(
            'Publish',
            nav,
        )

        self.assertIn(
            'Assistant',
            nav,
        )

        self.assertNotIn(
            'Manage',
            nav,
        )

        self.assertNotIn(
            'Audit',
            nav,
        )

        self.assertNotIn(
            'Executive View',
            nav,
        )

        self.assertNotIn(
            'All Requests',
            nav,
        )

        self.assertNotIn(
            'Analytics',
            nav,
        )

    def test_hod_navbar(self):
        hod = make_admin(
            'nav_h',
            role='hod',
            department='CSE',
        )

        nav = self._get_navbar(hod)

        self.assertIn(
            'My Queue',
            nav,
        )

        self.assertIn(
            'Notices',
            nav,
        )

        self.assertIn(
            'Publish',
            nav,
        )

        self.assertIn(
            'Assistant',
            nav,
        )

        self.assertNotIn(
            'Manage',
            nav,
        )

        self.assertNotIn(
            'Audit',
            nav,
        )

        self.assertNotIn(
            'Executive View',
            nav,
        )

        self.assertNotIn(
            'All Requests',
            nav,
        )

        self.assertNotIn(
            'Analytics',
            nav,
        )

    def test_dean_navbar(self):
        dean = make_admin(
            'nav_dean',
            role='dean',
        )

        nav = self._get_navbar(dean)

        self.assertIn(
            'My Queue',
            nav,
        )

        self.assertIn(
            'Notices',
            nav,
        )

        self.assertIn(
            'Publish',
            nav,
        )

        self.assertIn(
            'Assistant',
            nav,
        )

        self.assertNotIn(
            'Manage',
            nav,
        )

        self.assertNotIn(
            'Audit',
            nav,
        )

        self.assertNotIn(
            'Executive View',
            nav,
        )

        self.assertNotIn(
            'All Requests',
            nav,
        )

        self.assertNotIn(
            'Analytics',
            nav,
        )

    def test_ao_navbar(self):
        ao = make_admin(
            'nav_ao',
            role='ao',
        )

        nav = self._get_navbar(ao)

        self.assertIn(
            'My Queue',
            nav,
        )

        self.assertIn(
            'Notices',
            nav,
        )

        self.assertIn(
            'Assistant',
            nav,
        )

        self.assertNotIn(
            'Manage',
            nav,
        )

        self.assertNotIn(
            'Audit',
            nav,
        )

        self.assertNotIn(
            'Executive View',
            nav,
        )

        self.assertNotIn(
            'All Requests',
            nav,
        )

        self.assertNotIn(
            'Analytics',
            nav,
        )

    def test_principal_navbar(self):
        principal = make_admin(
            'nav_p',
            role='principal',
        )

        nav = self._get_navbar(principal)

        self.assertIn(
            'Executive View',
            nav,
        )

        self.assertIn(
            'All Requests',
            nav,
        )

        self.assertIn(
            'Notices',
            nav,
        )

        self.assertIn(
            'Publish',
            nav,
        )

        self.assertIn(
            'Manage',
            nav,
        )

        self.assertIn(
            'Audit',
            nav,
        )

        self.assertIn(
            'Assistant',
            nav,
        )

    def test_director_navbar(self):
        director = make_admin(
            'nav_director',
            role='director',
        )

        nav = self._get_navbar(director)

        self.assertIn(
            'Executive View',
            nav,
        )

        self.assertIn(
            'All Requests',
            nav,
        )

        self.assertIn(
            'Manage',
            nav,
        )

        self.assertIn(
            'Audit',
            nav,
        )

        self.assertIn(
            'Assistant',
            nav,
        )

    def test_chairman_navbar(self):
        chairman = make_admin(
            'nav_chairman',
            role='chairman',
        )

        nav = self._get_navbar(chairman)

        self.assertIn(
            'Executive View',
            nav,
        )

        self.assertIn(
            'All Requests',
            nav,
        )

        self.assertIn(
            'Manage',
            nav,
        )

        self.assertIn(
            'Audit',
            nav,
        )

        self.assertIn(
            'Assistant',
            nav,
        )


class PermissionRegistryTests(TestCase):
    """Verify the central permission matrix."""

    def test_student_permissions(self):
        student = make_student(
            'rbac_s1',
        )

        self.assertTrue(
            has_perm(
                student,
                Perm.SUBMIT_TICKET,
            )
        )

        self.assertTrue(
            has_perm(
                student,
                Perm.VIEW_OWN_TICKETS,
            )
        )

        self.assertTrue(
            has_perm(
                student,
                Perm.VIEW_ATTENDANCE,
            )
        )

        self.assertTrue(
            has_perm(
                student,
                Perm.VIEW_TIMETABLE,
            )
        )

        self.assertTrue(
            has_perm(
                student,
                Perm.VIEW_NOTICES,
            )
        )

        self.assertTrue(
            has_perm(
                student,
                Perm.USE_CHATBOT_STUDENT,
            )
        )

        self.assertFalse(
            has_perm(
                student,
                Perm.VIEW_MANAGE_PANEL,
            )
        )

        self.assertFalse(
            has_perm(
                student,
                Perm.VIEW_AUDIT_TRAIL,
            )
        )

        self.assertFalse(
            has_perm(
                student,
                Perm.VIEW_ANALYTICS,
            )
        )

        self.assertFalse(
            has_perm(
                student,
                Perm.VIEW_ADMIN_DASHBOARD,
            )
        )

        self.assertFalse(
            has_perm(
                student,
                Perm.ACCESS_DJANGO_ADMIN,
            )
        )

    def test_warden_permissions(self):
        warden = make_admin(
            'rbac_w1',
            role='warden',
            hostel_block='A',
        )

        self.assertTrue(
            has_perm(
                warden,
                Perm.VIEW_TICKET_QUEUE,
            )
        )

        self.assertTrue(
            has_perm(
                warden,
                Perm.VIEW_TICKET_DETAIL,
            )
        )

        self.assertTrue(
            has_perm(
                warden,
                Perm.APPROVE_TICKET_STEP,
            )
        )

        self.assertTrue(
            has_perm(
                warden,
                Perm.REJECT_TICKET_STEP,
            )
        )

        self.assertTrue(
            has_perm(
                warden,
                Perm.VIEW_NOTICES,
            )
        )

        self.assertTrue(
            has_perm(
                warden,
                Perm.PUBLISH_NOTICE,
            )
        )

        self.assertTrue(
            has_perm(
                warden,
                Perm.VIEW_FEEDBACK_DASHBOARD,
            )
        )

        self.assertTrue(
            has_perm(
                warden,
                Perm.VIEW_DOCUMENT_VAULT,
            )
        )

        self.assertTrue(
            has_perm(
                warden,
                Perm.VIEW_ALL_SOS_ALERTS,
            )
        )

        self.assertTrue(
            has_perm(
                warden,
                Perm.USE_CHATBOT_ADMIN,
            )
        )

        self.assertFalse(
            has_perm(
                warden,
                Perm.VIEW_ADMIN_DASHBOARD,
            )
        )

        self.assertFalse(
            has_perm(
                warden,
                Perm.VIEW_ANALYTICS,
            )
        )

        self.assertFalse(
            has_perm(
                warden,
                Perm.VIEW_PREDICTIONS,
            )
        )

        self.assertFalse(
            has_perm(
                warden,
                Perm.VIEW_MANAGE_PANEL,
            )
        )

        self.assertFalse(
            has_perm(
                warden,
                Perm.VIEW_AUDIT_TRAIL,
            )
        )

        self.assertFalse(
            has_perm(
                warden,
                Perm.ACCESS_DJANGO_ADMIN,
            )
        )

    def test_hod_permissions(self):
        hod = make_admin(
            'rbac_h1',
            role='hod',
            department='CSE',
        )

        self.assertTrue(
            has_perm(
                hod,
                Perm.VIEW_TICKET_QUEUE,
            )
        )

        self.assertTrue(
            has_perm(
                hod,
                Perm.VIEW_TICKET_DETAIL,
            )
        )

        self.assertTrue(
            has_perm(
                hod,
                Perm.APPROVE_TICKET_STEP,
            )
        )

        self.assertTrue(
            has_perm(
                hod,
                Perm.PUBLISH_NOTICE,
            )
        )

        self.assertTrue(
            has_perm(
                hod,
                Perm.VIEW_FEEDBACK_DASHBOARD,
            )
        )

        self.assertTrue(
            has_perm(
                hod,
                Perm.VIEW_ALL_FEEDBACK,
            )
        )

        self.assertTrue(
            has_perm(
                hod,
                Perm.VIEW_DOCUMENT_VAULT,
            )
        )

        self.assertTrue(
            has_perm(
                hod,
                Perm.VIEW_ALL_USERS,
            )
        )

        self.assertTrue(
            has_perm(
                hod,
                Perm.USE_CHATBOT_ADMIN,
            )
        )

        self.assertFalse(
            has_perm(
                hod,
                Perm.VIEW_ADMIN_DASHBOARD,
            )
        )

        self.assertFalse(
            has_perm(
                hod,
                Perm.VIEW_ANALYTICS,
            )
        )

        self.assertFalse(
            has_perm(
                hod,
                Perm.VIEW_PREDICTIONS,
            )
        )

        self.assertFalse(
            has_perm(
                hod,
                Perm.VIEW_MANAGE_PANEL,
            )
        )

        self.assertFalse(
            has_perm(
                hod,
                Perm.VIEW_AUDIT_TRAIL,
            )
        )

        self.assertFalse(
            has_perm(
                hod,
                Perm.ACCESS_DJANGO_ADMIN,
            )
        )

    def test_dean_permissions(self):
        dean = make_admin(
            'rbac_dean',
            role='dean',
        )

        self.assertTrue(
            has_perm(
                dean,
                Perm.VIEW_TICKET_QUEUE,
            )
        )

        self.assertTrue(
            has_perm(
                dean,
                Perm.APPROVE_TICKET_STEP,
            )
        )

        self.assertTrue(
            has_perm(
                dean,
                Perm.PUBLISH_NOTICE,
            )
        )

        self.assertTrue(
            has_perm(
                dean,
                Perm.VIEW_FEEDBACK_DASHBOARD,
            )
        )

        self.assertTrue(
            has_perm(
                dean,
                Perm.VIEW_PREDICTIONS,
            )
        )

        self.assertFalse(
            has_perm(
                dean,
                Perm.VIEW_ADMIN_DASHBOARD,
            )
        )

        self.assertFalse(
            has_perm(
                dean,
                Perm.VIEW_ANALYTICS,
            )
        )

        self.assertFalse(
            has_perm(
                dean,
                Perm.VIEW_MANAGE_PANEL,
            )
        )

        self.assertFalse(
            has_perm(
                dean,
                Perm.VIEW_AUDIT_TRAIL,
            )
        )

        self.assertFalse(
            has_perm(
                dean,
                Perm.ACCESS_DJANGO_ADMIN,
            )
        )

    def test_ao_permissions(self):
        ao = make_admin(
            'rbac_ao',
            role='ao',
        )

        self.assertTrue(
            has_perm(
                ao,
                Perm.VIEW_TICKET_QUEUE,
            )
        )

        self.assertTrue(
            has_perm(
                ao,
                Perm.APPROVE_TICKET_STEP,
            )
        )

        self.assertTrue(
            has_perm(
                ao,
                Perm.PUBLISH_NOTICE,
            )
        )

        self.assertTrue(
            has_perm(
                ao,
                Perm.VIEW_FEEDBACK_DASHBOARD,
            )
        )

        self.assertTrue(
            has_perm(
                ao,
                Perm.VIEW_DOCUMENT_VAULT,
            )
        )

        self.assertFalse(
            has_perm(
                ao,
                Perm.VIEW_ADMIN_DASHBOARD,
            )
        )

        self.assertFalse(
            has_perm(
                ao,
                Perm.VIEW_ANALYTICS,
            )
        )

        self.assertFalse(
            has_perm(
                ao,
                Perm.VIEW_PREDICTIONS,
            )
        )

        self.assertFalse(
            has_perm(
                ao,
                Perm.VIEW_MANAGE_PANEL,
            )
        )

        self.assertFalse(
            has_perm(
                ao,
                Perm.VIEW_AUDIT_TRAIL,
            )
        )

        self.assertFalse(
            has_perm(
                ao,
                Perm.ACCESS_DJANGO_ADMIN,
            )
        )

    def test_asst_prof_permissions(self):
        assistant_professor = make_admin(
            'rbac_asst_prof',
            role='asst_prof',
        )

        self.assertTrue(
            has_perm(
                assistant_professor,
                Perm.VIEW_TICKET_QUEUE,
            )
        )

        self.assertTrue(
            has_perm(
                assistant_professor,
                Perm.APPROVE_TICKET_STEP,
            )
        )

        self.assertTrue(
            has_perm(
                assistant_professor,
                Perm.PUBLISH_NOTICE,
            )
        )

        self.assertTrue(
            has_perm(
                assistant_professor,
                Perm.VIEW_FEEDBACK_DASHBOARD,
            )
        )

        self.assertFalse(
            has_perm(
                assistant_professor,
                Perm.VIEW_ADMIN_DASHBOARD,
            )
        )

        self.assertFalse(
            has_perm(
                assistant_professor,
                Perm.VIEW_ANALYTICS,
            )
        )

        self.assertFalse(
            has_perm(
                assistant_professor,
                Perm.VIEW_PREDICTIONS,
            )
        )

        self.assertFalse(
            has_perm(
                assistant_professor,
                Perm.VIEW_AUDIT_TRAIL,
            )
        )

        self.assertFalse(
            has_perm(
                assistant_professor,
                Perm.ACCESS_DJANGO_ADMIN,
            )
        )

    def test_principal_permissions(self):
        principal = make_admin(
            'rbac_p1',
            role='principal',
        )

        self.assertTrue(
            has_perm(
                principal,
                Perm.VIEW_ADMIN_DASHBOARD,
            )
        )

        self.assertTrue(
            has_perm(
                principal,
                Perm.VIEW_ANALYTICS,
            )
        )

        self.assertTrue(
            has_perm(
                principal,
                Perm.VIEW_PREDICTIONS,
            )
        )

        self.assertTrue(
            has_perm(
                principal,
                Perm.VIEW_MANAGE_PANEL,
            )
        )

        self.assertTrue(
            has_perm(
                principal,
                Perm.MANAGE_SLAS,
            )
        )

        self.assertTrue(
            has_perm(
                principal,
                Perm.VIEW_AUDIT_TRAIL,
            )
        )

        self.assertTrue(
            has_perm(
                principal,
                Perm.VIEW_ALL_USERS,
            )
        )

        self.assertTrue(
            has_perm(
                principal,
                Perm.USE_CHATBOT_ADMIN,
            )
        )

        self.assertFalse(
            has_perm(
                principal,
                Perm.ACCESS_DJANGO_ADMIN,
            )
        )

    def test_director_permissions(self):
        director = make_admin(
            'rbac_director',
            role='director',
        )

        self.assertTrue(
            has_perm(
                director,
                Perm.VIEW_ADMIN_DASHBOARD,
            )
        )

        self.assertTrue(
            has_perm(
                director,
                Perm.VIEW_ANALYTICS,
            )
        )

        self.assertTrue(
            has_perm(
                director,
                Perm.VIEW_AUDIT_TRAIL,
            )
        )

        self.assertTrue(
            has_perm(
                director,
                Perm.MANAGE_SLAS,
            )
        )

        self.assertTrue(
            has_perm(
                director,
                Perm.ACCESS_DJANGO_ADMIN,
            )
        )

    def test_chairman_permissions(self):
        chairman = make_admin(
            'rbac_c1',
            role='chairman',
        )

        self.assertTrue(
            has_perm(
                chairman,
                Perm.VIEW_ADMIN_DASHBOARD,
            )
        )

        self.assertTrue(
            has_perm(
                chairman,
                Perm.VIEW_ANALYTICS,
            )
        )

        self.assertTrue(
            has_perm(
                chairman,
                Perm.VIEW_AUDIT_TRAIL,
            )
        )

        self.assertTrue(
            has_perm(
                chairman,
                Perm.MANAGE_SLAS,
            )
        )

        self.assertTrue(
            has_perm(
                chairman,
                Perm.ACCESS_DJANGO_ADMIN,
            )
        )


class NoForbiddenTests(TestCase):
    """
    Unauthorized users should be redirected by the central
    permission decorators instead of receiving a dead-end 403.
    """

    def setUp(self):
        self.client = Client()

    def _login(self, user):
        user.set_password('test')
        user.save()

        self.client.login(
            username=user.username,
            password='test',
        )

    def test_student_manage_redirects(self):
        student = make_student(
            'nf_s',
        )

        self._login(student)

        response = self.client.get(
            reverse('manage_panel:home'),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_warden_manage_redirects(self):
        warden = make_admin(
            'nf_w',
            role='warden',
            hostel_block='A',
        )

        self._login(warden)

        response = self.client.get(
            reverse('manage_panel:home'),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_hod_manage_redirects(self):
        hod = make_admin(
            'nf_h',
            role='hod',
            department='CSE',
        )

        self._login(hod)

        response = self.client.get(
            reverse('manage_panel:home'),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_dean_manage_redirects(self):
        dean = make_admin(
            'nf_dean',
            role='dean',
        )

        self._login(dean)

        response = self.client.get(
            reverse('manage_panel:home'),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_ao_manage_redirects(self):
        ao = make_admin(
            'nf_ao',
            role='ao',
        )

        self._login(ao)

        response = self.client.get(
            reverse('manage_panel:home'),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_warden_analytics_redirects(self):
        warden = make_admin(
            'nf_w_analytics',
            role='warden',
            hostel_block='A',
        )

        self._login(warden)

        response = self.client.get(
            reverse('dashboard:analytics'),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_hod_analytics_redirects(self):
        hod = make_admin(
            'nf_h_analytics',
            role='hod',
            department='CSE',
        )

        self._login(hod)

        response = self.client.get(
            reverse('dashboard:analytics'),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_dean_analytics_redirects(self):
        dean = make_admin(
            'nf_dean_analytics',
            role='dean',
        )

        self._login(dean)

        response = self.client.get(
            reverse('dashboard:analytics'),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_ao_analytics_redirects(self):
        ao = make_admin(
            'nf_ao_analytics',
            role='ao',
        )

        self._login(ao)

        response = self.client.get(
            reverse('dashboard:analytics'),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_student_analytics_redirects(self):
        student = make_student(
            'nf_s_analytics',
        )

        self._login(student)

        response = self.client.get(
            reverse('dashboard:analytics'),
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_principal_manage_200(self):
        principal = make_admin(
            'nf_p',
            role='principal',
        )

        self._login(principal)

        response = self.client.get(
            reverse('manage_panel:home'),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_principal_analytics_200(self):
        principal = make_admin(
            'nf_p_analytics',
            role='principal',
        )

        self._login(principal)

        response = self.client.get(
            reverse('dashboard:analytics'),
        )

        self.assertEqual(
            response.status_code,
            200,
        )


class DjangoAdminAccessTests(TestCase):
    """Verify access to the restricted Django admin."""

    def setUp(self):
        self.client = Client()

    def _login(self, user):
        user.set_password('test')
        user.save()

        self.client.login(
            username=user.username,
            password='test',
        )

    def test_warden_django_admin_denied(self):
        warden = make_admin(
            'django_warden',
            role='warden',
            hostel_block='A',
        )

        warden.is_staff = True
        warden.is_superuser = False
        warden.save()

        self._login(warden)

        response = self.client.get(
            '/admin/',
        )

        self.assertIn(
            response.status_code,
            [302, 403],
        )

    def test_hod_django_admin_denied(self):
        hod = make_admin(
            'django_hod',
            role='hod',
            department='CSE',
        )

        hod.is_staff = True
        hod.is_superuser = False
        hod.save()

        self._login(hod)

        response = self.client.get(
            '/admin/',
        )

        self.assertIn(
            response.status_code,
            [302, 403],
        )

    def test_principal_django_admin_denied(self):
        principal = make_admin(
            'django_principal',
            role='principal',
        )

        principal.is_staff = True
        principal.is_superuser = False
        principal.save()

        self._login(principal)

        response = self.client.get(
            '/admin/',
        )

        self.assertIn(
            response.status_code,
            [302, 403],
        )

    def test_director_django_admin_allowed(self):
        director = make_admin(
            'django_director',
            role='director',
        )

        director.is_staff = True
        director.is_superuser = False
        director.save()

        self._login(director)

        response = self.client.get(
            '/admin/',
        )

        self.assertNotEqual(
            response.status_code,
            403,
        )

    def test_chairman_django_admin_allowed(self):
        chairman = make_admin(
            'django_chairman',
            role='chairman',
        )

        chairman.is_staff = True
        chairman.is_superuser = False
        chairman.save()

        self._login(chairman)

        response = self.client.get(
            '/admin/',
        )

        self.assertNotEqual(
            response.status_code,
            403,
        )


class QueueScopeTests(TestCase):
    """Queue shows only tickets within the user's data scope."""

    def setUp(self):
        from apps.tickets.models import CampusTicket

        self.client = Client()

        self.warden_a = make_admin(
            'qs_wa',
            role='warden',
            hostel_block='A',
        )

        self.student_a = make_student(
            'qs_sa',
            hostel_block='A',
        )

        self.student_b = make_student(
            'qs_sb',
            hostel_block='B',
        )

        self.ticket_a = CampusTicket.objects.create(
            student=self.student_a,
            ticket_type='leave',
            subject='Leave from Block A',
            raw_input='test',
            status='pending',
            is_deleted=False,
        )

        self.ticket_b = CampusTicket.objects.create(
            student=self.student_b,
            ticket_type='leave',
            subject='Leave from Block B',
            raw_input='test',
            status='pending',
            is_deleted=False,
        )

    def test_warden_queue_is_scoped(self):
        self.warden_a.set_password(
            'test',
        )

        self.warden_a.save()

        self.client.login(
            username=self.warden_a.username,
            password='test',
        )

        queryset = DataScope.ticket_queryset(
            self.warden_a,
        )

        ids = list(
            queryset.values_list(
                'id',
                flat=True,
            )
        )

        self.assertIn(
            self.ticket_a.id,
            ids,
        )

        self.assertNotIn(
            self.ticket_b.id,
            ids,
        )


class DataScopeTests(TestCase):
    """Verify querysets are properly scoped."""

    def setUp(self):
        from apps.tickets.models import CampusTicket

        self.student_a = make_student(
            'scope_sA',
            hostel_block='A',
        )

        self.student_b = make_student(
            'scope_sB',
            hostel_block='B',
        )

        self.warden_a = make_admin(
            'scope_wA',
            role='warden',
            hostel_block='A',
        )

        self.hod_cse = make_admin(
            'scope_hCSE',
            role='hod',
            department='CSE',
        )

        self.principal = make_admin(
            'scope_pri',
            role='principal',
        )

        self.ticket_a = CampusTicket.objects.create(
            student=self.student_a,
            ticket_type='complaint',
            subject='Block A complaint',
            raw_input='test',
            assigned_department='plumbing',
            status='pending',
            is_deleted=False,
        )

        self.ticket_b = CampusTicket.objects.create(
            student=self.student_b,
            ticket_type='complaint',
            subject='Block B complaint',
            raw_input='test',
            assigned_department='plumbing',
            status='pending',
            is_deleted=False,
        )

    def test_student_sees_own_tickets(self):
        queryset = DataScope.ticket_queryset(
            self.student_a,
        )

        self.assertEqual(
            queryset.count(),
            1,
        )

        self.assertEqual(
            queryset.first().id,
            self.ticket_a.id,
        )

    def test_warden_a_sees_only_block_a(self):
        queryset = DataScope.ticket_queryset(
            self.warden_a,
        )

        ids = list(
            queryset.values_list(
                'id',
                flat=True,
            )
        )

        self.assertIn(
            self.ticket_a.id,
            ids,
        )

        self.assertNotIn(
            self.ticket_b.id,
            ids,
        )

    def test_principal_sees_all(self):
        queryset = DataScope.ticket_queryset(
            self.principal,
        )

        self.assertGreaterEqual(
            queryset.count(),
            2,
        )

    def test_hod_cse_cannot_see_plumbing(self):
        queryset = DataScope.ticket_queryset(
            self.hod_cse,
        )

        self.assertEqual(
            queryset.count(),
            0,
        )