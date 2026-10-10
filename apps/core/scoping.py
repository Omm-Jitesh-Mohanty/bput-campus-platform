"""
Data scoping — determines what a user is allowed to see.

Two concepts:
  1. QUERYSET SCOPE: which rows a user can query (for lists/dashboards)
  2. OBJECT ACCESS: whether a user can open a specific object (for detail views)

Both are role-based AND hierarchy-based. A HOD can see their department's
tickets. A Dean can see all departments. A Principal can see everything.
"""
import logging
from django.db.models import Q

logger = logging.getLogger(__name__)


class DataScope:
    """
    Computes scoping rules for a user against a given model.

    Usage:
        qs = DataScope.filter(CampusTicket.objects.all(), user)
        if DataScope.can_access(user, ticket):
            ...
    """

    # =================================================================
    # Ticket scoping
    # =================================================================
    @classmethod
    def ticket_queryset(cls, user):
        """
        Return the base queryset of tickets visible to this user.
        """
        from apps.tickets.models import CampusTicket

        # Students see only their own
        if user.role == 'student':
            return CampusTicket.objects.filter(
                student=user,
                is_deleted=False
            )

        # Top-level: everything
        if user.role in ('chairman', 'director', 'principal'):
            return CampusTicket.objects.filter(is_deleted=False)

        # Dean: all tickets
        if user.role == 'dean':
            return CampusTicket.objects.filter(is_deleted=False)

        # AO: administration-wide but not academic
        if user.role == 'ao':
            return CampusTicket.objects.filter(
                is_deleted=False,
                ticket_type__in=['leave', 'document', 'gatepass'],
            )

        # HOD: their department's tickets OR tickets where they have a pending approval step
        if user.role == 'hod':
            return CampusTicket.objects.filter(is_deleted=False).filter(
                Q(assigned_department=user.department)
                | Q(
                    step_executions__workflow_step__role_required='hod',
                    step_executions__status='pending'
                )
                | Q(
                    step_executions__workflow_step__role_required='hod',
                    step_executions__actor=user
                )
            ).distinct()

        # Warden: their hostel block + all leave/gatepass regardless of block
        if user.role == 'warden':
            return CampusTicket.objects.filter(is_deleted=False).filter(
                Q(student__hostel_block=user.hostel_block)
                | Q(ticket_type__in=['leave', 'gatepass'])
            )

        # Asst Prof / Teacher / Lab Asst: their department, only academic
        if user.role in ('asst_prof', 'teacher', 'lab_asst'):
            return CampusTicket.objects.filter(
                is_deleted=False,
                assigned_department=user.department,
            )

        
        # Clerk: tickets assigned directly or awaiting their workflow role
        if user.role == 'clerk':
            return CampusTicket.objects.filter(
                is_deleted=False,
            ).filter(
                Q(assigned_to=user)
                | Q(
                    step_executions__workflow_step__role_required='clerk',
                    step_executions__status='pending',
                )
            ).distinct()

        # Fallback: nothing
        return CampusTicket.objects.none()

    # =================================================================
    # Object access
    # =================================================================
    @classmethod
    def can_access_ticket(cls, user, ticket):
        """Can this user open this specific ticket?"""
        if not user.is_authenticated:
            return False

        # Owner always
        if ticket.student_id == user.id:
            return True

        # Role-based
        if user.role in ('chairman', 'director', 'principal'):
            return True

        if user.role == 'dean':
            return True

        if user.role == 'ao':
            return ticket.ticket_type in ('leave', 'document', 'gatepass')

        if user.role == 'hod':
            if ticket.assigned_department == user.department:
                return True

            # Or if they have a step to act on
            return ticket.step_executions.filter(
                workflow_step__role_required='hod',
                status='pending',
            ).exists()

        if user.role == 'warden':
            # Leave/gatepass = any warden; complaints = same block
            if ticket.ticket_type in ('leave', 'gatepass'):
                return True

            return ticket.student.hostel_block == user.hostel_block

        if user.role in ('asst_prof', 'teacher', 'lab_asst'):
            return ticket.assigned_department == user.department

        
        if user.role == 'clerk':
            if ticket.assigned_to_id == user.id:
                return True

            return ticket.step_executions.filter(
                workflow_step__role_required='clerk',
                status='pending',
            ).exists()

        return False

    # =================================================================
    # Notices
    # =================================================================
    @classmethod
    def notice_queryset(cls, user):
        """
        Notices visible to a user.
        Students: notices targeting them.
        Admins: all published notices + their department's.
        """
        from apps.notices.models import Notice

        base = Notice.objects.filter(
            is_published=True,
            is_deleted=False
        )

        if user.role == 'student':
            # Target filtering is done per-notice in services.
            # Here we return all, and get_notices_for_student filters.
            return base

        # Admins see everything
        return base

    # =================================================================
    # Feedback
    # =================================================================
    @classmethod
    def feedback_queryset(cls, user):
        from apps.feedback.models import Feedback

        if user.role == 'student':
            # Own + anonymous (since anonymous has no owner)
            # from django.db.models import Q
            return Feedback.objects.filter(
                Q(student=user) | Q(is_anonymous=True)
            )

        if user.role in ('chairman', 'director', 'principal', 'dean'):
            return Feedback.objects.all()

        if user.role == 'ao':
            return Feedback.objects.filter(
                category__in=['academic', 'infra']
            )

        if user.role == 'hod':
            return Feedback.objects.filter(
                Q(category='academic') |
                Q(student__department=user.department)
            )

        if user.role == 'warden':
            return Feedback.objects.filter(
                Q(category__in=['mess', 'water', 'hygiene', 'hostel']) |
                Q(student__hostel_block=user.hostel_block)
            )

        return Feedback.objects.none()

    # =================================================================
    # Documents
    # =================================================================
    @classmethod
    def document_queryset(cls, user):
        from apps.documents.models import IssuedDocument

        base = IssuedDocument.objects.filter(is_deleted=False)

        if user.role == 'student':
            return base.filter(student=user)

        if user.role in ('chairman', 'director', 'principal', 'dean', 'ao'):
            return base

        if user.role == 'hod':
            return base.filter(student__department=user.department)

        if user.role == 'warden':
            return base.filter(student__hostel_block=user.hostel_block)

        if user.role == 'clerk':
            # Clerks see what they issued
            return base.filter(issued_by=user)

        if user.role in ('asst_prof', 'teacher', 'lab_asst'):
            return base.filter(student__department=user.department)

        return base.none()

    @classmethod
    def can_access_document(cls, user, doc):
        if user.role in ('chairman', 'director', 'principal', 'dean', 'ao'):
            return True

        if doc.student_id == user.id:
            return True

        if user.role == 'hod':
            return doc.student.department == user.department

        if user.role == 'warden':
            return doc.student.hostel_block == user.hostel_block

        if user.role == 'clerk':
            return doc.issued_by_id == user.id

        if user.role in ('asst_prof', 'teacher', 'lab_asst'):
            return doc.student.department == user.department

        return False

    # =================================================================
    # SOS Alerts
    # =================================================================
    @classmethod
    def sos_queryset(cls, user):
        from apps.emergency.models import EmergencyAlert

        if user.role == 'student':
            return EmergencyAlert.objects.filter(user=user)

        if user.role in ('chairman', 'director', 'principal', 'dean', 'ao'):
            return EmergencyAlert.objects.all()

        if user.role == 'warden':
            return EmergencyAlert.objects.filter(
                user__hostel_block=user.hostel_block
            )

        if user.role == 'hod':
            return EmergencyAlert.objects.filter(
                user__department=user.department
            )

        return EmergencyAlert.objects.none()

    # =================================================================
    # Users (for admin panel)
    # =================================================================
    @classmethod
    def user_queryset(cls, user):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        if user.role in ('chairman', 'director', 'principal', 'dean', 'ao'):
            return User.objects.all()

        if user.role == 'hod':
            return User.objects.filter(
                Q(department=user.department) | Q(id=user.id)
            )

        if user.role == 'warden':
            return User.objects.filter(
                Q(hostel_block=user.hostel_block) | Q(id=user.id)
            )

        # Everyone else sees only themselves
        return User.objects.filter(id=user.id)

    # =================================================================
    # Audit (already in permissions, but also needed for query scoping)
    # =================================================================
    @classmethod
    def audit_queryset(cls, user):
        from .models import AuditLog

        if user.role in ('chairman', 'director', 'principal'):
            return AuditLog.objects.all()

        # Deans see their own actions + their department's
        if user.role == 'dean':
            return AuditLog.objects.filter(
                Q(user=user) | Q(target_model__icontains='student')
            )

        # Everyone else sees only their own actions
        return AuditLog.objects.filter(user=user)