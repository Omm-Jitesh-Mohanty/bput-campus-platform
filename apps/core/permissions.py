"""
Central permission registry — single source of truth for RBAC.

Usage:
    from apps.core.permissions import Perm, has_perm, require_perm

    if has_perm(request.user, Perm.MANAGE_CONFIG):
        ...

    @require_perm(Perm.VIEW_ANALYTICS)
    def analytics_view(request): ...

    In templates:
        {% load permissions %}
        {% if user|can:"manage_config" %}...{% endif %}
"""

import logging
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


class Perm:
    SUBMIT_TICKET = 'submit_ticket'
    VIEW_OWN_TICKETS = 'view_own_tickets'
    VIEW_ATTENDANCE = 'view_attendance'
    VIEW_TIMETABLE = 'view_timetable'
    VIEW_OWN_DOCUMENTS = 'view_own_documents'
    REQUEST_DOCUMENT = 'request_document'
    GIVE_FEEDBACK = 'give_feedback'
    USE_CHATBOT_STUDENT = 'use_chatbot_student'
    TRIGGER_SOS = 'trigger_sos'
    MANAGE_OWN_CONTACTS = 'manage_own_contacts'

    VIEW_TICKET_QUEUE = 'view_ticket_queue'
    VIEW_TICKET_DETAIL = 'view_ticket_detail'
    APPROVE_TICKET_STEP = 'approve_ticket_step'
    REJECT_TICKET_STEP = 'reject_ticket_step'
    ADD_TICKET_COMMENT = 'add_ticket_comment'
    ADD_INTERNAL_NOTE = 'add_internal_note'
    ASSIGN_TICKET = 'assign_ticket'

    VIEW_NOTICES = 'view_notices'
    PUBLISH_NOTICE = 'publish_notice'
    DELETE_NOTICE = 'delete_notice'
    VIEW_NOTICE_REACH = 'view_notice_reach'

    SUBMIT_FEEDBACK = 'submit_feedback'
    VIEW_FEEDBACK_DASHBOARD = 'view_feedback_dashboard'
    VIEW_ALL_FEEDBACK = 'view_all_feedback'

    VIEW_DOCUMENT_VAULT = 'view_document_vault'
    ISSUE_DOCUMENT = 'issue_document'
    REVOKE_DOCUMENT = 'revoke_document'

    VIEW_ADMIN_DASHBOARD = 'view_admin_dashboard'
    VIEW_ANALYTICS = 'view_analytics'
    VIEW_PREDICTIONS = 'view_predictions'

    VIEW_MANAGE_PANEL = 'view_manage_panel'

    MANAGE_DEPARTMENTS = 'manage_departments'
    MANAGE_TICKET_TYPES = 'manage_ticket_types'
    MANAGE_SLAS = 'manage_slas'
    MANAGE_PRIORITIES = 'manage_priorities'
    MANAGE_SETTINGS = 'manage_settings'
    MANAGE_PROMPTS = 'manage_prompts'
    MANAGE_WORKFLOWS = 'manage_workflows'
    MANAGE_DOC_TEMPLATES = 'manage_doc_templates'
    MANAGE_NOTIFICATIONS = 'manage_notifications'

    VIEW_AUDIT_TRAIL = 'view_audit_trail'
    EXPORT_DATA = 'export_data'

    VIEW_ALL_USERS = 'view_all_users'
    CREATE_USER = 'create_user'
    EDIT_USER = 'edit_user'
    DEACTIVATE_USER = 'deactivate_user'

    VIEW_ALL_SOS_ALERTS = 'view_all_sos_alerts'
    RESPOND_TO_SOS = 'respond_to_sos'

    USE_CHATBOT_ADMIN = 'use_chatbot_admin'

    ACCESS_DJANGO_ADMIN = 'access_django_admin'


ROLE_PERMISSIONS = {
    'student': {
        Perm.SUBMIT_TICKET,
        Perm.VIEW_OWN_TICKETS,
        Perm.VIEW_ATTENDANCE,
        Perm.VIEW_TIMETABLE,
        Perm.VIEW_OWN_DOCUMENTS,
        Perm.REQUEST_DOCUMENT,
        Perm.GIVE_FEEDBACK,
        Perm.VIEW_NOTICES,
        Perm.USE_CHATBOT_STUDENT,
        Perm.TRIGGER_SOS,
        Perm.MANAGE_OWN_CONTACTS,
        Perm.VIEW_TICKET_DETAIL,
        Perm.ADD_TICKET_COMMENT,
    },

    'lab_asst': {
        Perm.VIEW_TICKET_QUEUE,
        Perm.VIEW_TICKET_DETAIL,
        Perm.APPROVE_TICKET_STEP,
        Perm.REJECT_TICKET_STEP,
        Perm.ADD_TICKET_COMMENT,
        Perm.ADD_INTERNAL_NOTE,
        Perm.VIEW_NOTICES,
        Perm.VIEW_ATTENDANCE,
        Perm.VIEW_TIMETABLE,
        Perm.USE_CHATBOT_ADMIN,
    },

    'teacher': {
        Perm.VIEW_TICKET_QUEUE,
        Perm.VIEW_TICKET_DETAIL,
        Perm.APPROVE_TICKET_STEP,
        Perm.REJECT_TICKET_STEP,
        Perm.ADD_TICKET_COMMENT,
        Perm.ADD_INTERNAL_NOTE,
        Perm.VIEW_NOTICES,
        Perm.VIEW_ATTENDANCE,
        Perm.VIEW_TIMETABLE,
        Perm.VIEW_FEEDBACK_DASHBOARD,
        Perm.USE_CHATBOT_ADMIN,
    },

    'asst_prof': {
        Perm.VIEW_TICKET_QUEUE,
        Perm.VIEW_TICKET_DETAIL,
        Perm.APPROVE_TICKET_STEP,
        Perm.REJECT_TICKET_STEP,
        Perm.ADD_TICKET_COMMENT,
        Perm.ADD_INTERNAL_NOTE,
        Perm.VIEW_NOTICES,
        Perm.PUBLISH_NOTICE,
        Perm.VIEW_FEEDBACK_DASHBOARD,
        Perm.VIEW_ATTENDANCE,
        Perm.VIEW_TIMETABLE,
        Perm.USE_CHATBOT_ADMIN,
    },

    'clerk': {
        Perm.VIEW_TICKET_QUEUE,
        Perm.VIEW_TICKET_DETAIL,
        Perm.APPROVE_TICKET_STEP,
        Perm.REJECT_TICKET_STEP,
        Perm.ADD_TICKET_COMMENT,
        Perm.ADD_INTERNAL_NOTE,
        Perm.VIEW_NOTICES,
        Perm.ISSUE_DOCUMENT,
        Perm.VIEW_DOCUMENT_VAULT,
        Perm.USE_CHATBOT_ADMIN,
    },

    'warden': {
        Perm.VIEW_TICKET_QUEUE,
        Perm.VIEW_TICKET_DETAIL,
        Perm.APPROVE_TICKET_STEP,
        Perm.REJECT_TICKET_STEP,
        Perm.ADD_TICKET_COMMENT,
        Perm.ADD_INTERNAL_NOTE,
        Perm.ASSIGN_TICKET,
        Perm.VIEW_NOTICES,
        Perm.PUBLISH_NOTICE,
        Perm.VIEW_NOTICE_REACH,
        Perm.VIEW_FEEDBACK_DASHBOARD,
        Perm.VIEW_DOCUMENT_VAULT,
        Perm.ISSUE_DOCUMENT,
        Perm.VIEW_ALL_SOS_ALERTS,
        Perm.RESPOND_TO_SOS,
        Perm.VIEW_ATTENDANCE,
        Perm.VIEW_TIMETABLE,
        Perm.USE_CHATBOT_ADMIN,
    },

    'hod': {
        Perm.VIEW_TICKET_QUEUE,
        Perm.VIEW_TICKET_DETAIL,
        Perm.APPROVE_TICKET_STEP,
        Perm.REJECT_TICKET_STEP,
        Perm.ADD_TICKET_COMMENT,
        Perm.ADD_INTERNAL_NOTE,
        Perm.ASSIGN_TICKET,
        Perm.VIEW_NOTICES,
        Perm.PUBLISH_NOTICE,
        Perm.VIEW_NOTICE_REACH,
        Perm.VIEW_FEEDBACK_DASHBOARD,
        Perm.VIEW_ALL_FEEDBACK,
        Perm.VIEW_DOCUMENT_VAULT,
        Perm.ISSUE_DOCUMENT,
        Perm.VIEW_ALL_SOS_ALERTS,
        Perm.RESPOND_TO_SOS,
        Perm.VIEW_ATTENDANCE,
        Perm.VIEW_TIMETABLE,
        Perm.VIEW_ALL_USERS,
        Perm.USE_CHATBOT_ADMIN,
    },

    'ao': {
        Perm.VIEW_TICKET_QUEUE,
        Perm.VIEW_TICKET_DETAIL,
        Perm.APPROVE_TICKET_STEP,
        Perm.REJECT_TICKET_STEP,
        Perm.ADD_TICKET_COMMENT,
        Perm.ADD_INTERNAL_NOTE,
        Perm.ASSIGN_TICKET,
        Perm.VIEW_NOTICES,
        Perm.PUBLISH_NOTICE,
        Perm.VIEW_NOTICE_REACH,
        Perm.VIEW_FEEDBACK_DASHBOARD,
        Perm.VIEW_DOCUMENT_VAULT,
        Perm.ISSUE_DOCUMENT,
        Perm.VIEW_ALL_USERS,
        Perm.USE_CHATBOT_ADMIN,
    },

    'dean': {
        Perm.VIEW_TICKET_QUEUE,
        Perm.VIEW_TICKET_DETAIL,
        Perm.APPROVE_TICKET_STEP,
        Perm.REJECT_TICKET_STEP,
        Perm.ADD_TICKET_COMMENT,
        Perm.ADD_INTERNAL_NOTE,
        Perm.ASSIGN_TICKET,
        Perm.VIEW_NOTICES,
        Perm.PUBLISH_NOTICE,
        Perm.DELETE_NOTICE,
        Perm.VIEW_NOTICE_REACH,
        Perm.VIEW_FEEDBACK_DASHBOARD,
        Perm.VIEW_ALL_FEEDBACK,
        Perm.VIEW_DOCUMENT_VAULT,
        Perm.ISSUE_DOCUMENT,
        Perm.REVOKE_DOCUMENT,
        Perm.VIEW_PREDICTIONS,
        Perm.VIEW_ALL_SOS_ALERTS,
        Perm.RESPOND_TO_SOS,
        Perm.VIEW_ALL_USERS,
        Perm.CREATE_USER,
        Perm.EDIT_USER,
        Perm.USE_CHATBOT_ADMIN,
    },

    'principal': {
        Perm.SUBMIT_TICKET,
        Perm.VIEW_OWN_TICKETS,
        Perm.VIEW_ATTENDANCE,
        Perm.VIEW_TIMETABLE,
        Perm.VIEW_OWN_DOCUMENTS,
        Perm.REQUEST_DOCUMENT,
        Perm.GIVE_FEEDBACK,
        Perm.USE_CHATBOT_STUDENT,

        Perm.VIEW_TICKET_QUEUE,
        Perm.VIEW_TICKET_DETAIL,
        Perm.APPROVE_TICKET_STEP,
        Perm.REJECT_TICKET_STEP,
        Perm.ADD_TICKET_COMMENT,
        Perm.ADD_INTERNAL_NOTE,
        Perm.ASSIGN_TICKET,

        Perm.VIEW_NOTICES,
        Perm.PUBLISH_NOTICE,
        Perm.DELETE_NOTICE,
        Perm.VIEW_NOTICE_REACH,

        Perm.VIEW_FEEDBACK_DASHBOARD,
        Perm.VIEW_ALL_FEEDBACK,

        Perm.VIEW_DOCUMENT_VAULT,
        Perm.ISSUE_DOCUMENT,
        Perm.REVOKE_DOCUMENT,

        Perm.VIEW_ADMIN_DASHBOARD,
        Perm.VIEW_ANALYTICS,
        Perm.VIEW_PREDICTIONS,

        Perm.VIEW_MANAGE_PANEL,

        Perm.MANAGE_DEPARTMENTS,
        Perm.MANAGE_TICKET_TYPES,
        Perm.MANAGE_SLAS,
        Perm.MANAGE_PRIORITIES,
        Perm.MANAGE_SETTINGS,
        Perm.MANAGE_PROMPTS,
        Perm.MANAGE_WORKFLOWS,
        Perm.MANAGE_DOC_TEMPLATES,
        Perm.MANAGE_NOTIFICATIONS,

        Perm.VIEW_AUDIT_TRAIL,
        Perm.EXPORT_DATA,

        Perm.VIEW_ALL_USERS,
        Perm.CREATE_USER,
        Perm.EDIT_USER,
        Perm.DEACTIVATE_USER,

        Perm.VIEW_ALL_SOS_ALERTS,
        Perm.RESPOND_TO_SOS,

        Perm.TRIGGER_SOS,
        Perm.MANAGE_OWN_CONTACTS,

        Perm.USE_CHATBOT_ADMIN,
    },

    'director': {
    },

    'chairman': {
    },
}


ROLE_PERMISSIONS['director'] = ROLE_PERMISSIONS['principal'] | {
    Perm.ACCESS_DJANGO_ADMIN,
}

ROLE_PERMISSIONS['chairman'] = ROLE_PERMISSIONS['director'] | {
    Perm.ACCESS_DJANGO_ADMIN,
}


def has_perm(user, permission):
    """Check if `user` has `permission`."""
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if user.role not in ROLE_PERMISSIONS:
        return False

    return permission in ROLE_PERMISSIONS[user.role]


def user_permissions(user):
    """Return the full set of permissions for `user`."""
    if not user or not user.is_authenticated:
        return set()

    if user.is_superuser:
        return {
            value
            for name, value in vars(Perm).items()
            if not name.startswith('_')
            and isinstance(value, str)
        }

    return set(
        ROLE_PERMISSIONS.get(
            user.role,
            set(),
        )
    )


def has_any_perm(user, *permissions):
    return any(
        has_perm(user, permission)
        for permission in permissions
    )


def has_all_perms(user, *permissions):
    return all(
        has_perm(user, permission)
        for permission in permissions
    )


def require_perm(permission):
    """
    Enforce permission.

    Normal request:
        Redirect unauthorized users to their role-specific home.

    AJAX/HTMX request:
        Return a 403 JSON response.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not has_perm(request.user, permission):
                logger.info(
                    f"Permission denied: user={request.user.username} "
                    f"role={request.user.role} "
                    f"perm={permission} "
                    f"path={request.path}"
                )

                if (
                    request.headers.get('x-requested-with')
                    == 'XMLHttpRequest'
                    or request.headers.get('HX-Request')
                ):
                    from django.http import JsonResponse

                    return JsonResponse(
                        {
                            'error': 'Permission denied',
                            'permission': permission,
                        },
                        status=403,
                    )

                if hasattr(request.user, 'home_redirect'):
                    return redirect(
                        request.user.home_redirect()
                    )

                return redirect('home')

            return view_func(
                request,
                *args,
                **kwargs,
            )

        return _wrapped

    return decorator


def require_any_perm(*permissions):
    """
    Enforce at least one permission.

    Normal request:
        Redirect unauthorized users to their role-specific home.

    AJAX/HTMX request:
        Return a 403 JSON response.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not has_any_perm(
                request.user,
                *permissions,
            ):
                logger.info(
                    f"Permission denied: user={request.user.username} "
                    f"role={request.user.role} "
                    f"perms={permissions} "
                    f"path={request.path}"
                )

                if (
                    request.headers.get('x-requested-with')
                    == 'XMLHttpRequest'
                    or request.headers.get('HX-Request')
                ):
                    from django.http import JsonResponse

                    return JsonResponse(
                        {
                            'error': 'Permission denied',
                            'permissions': permissions,
                        },
                        status=403,
                    )

                if hasattr(request.user, 'home_redirect'):
                    return redirect(
                        request.user.home_redirect()
                    )

                return redirect('home')

            return view_func(
                request,
                *args,
                **kwargs,
            )

        return _wrapped

    return decorator