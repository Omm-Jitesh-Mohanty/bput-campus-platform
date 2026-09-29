# """Lightweight ticket serialization for WebSocket payloads."""


# def serialize_ticket_summary(t):
#     return {
#         'id': t.id,
#         'subject': t.subject,
#         'ticket_type': t.ticket_type,
#         'ticket_type_display': t.get_ticket_type_display(),
#         'priority': t.priority,
#         'priority_display': t.get_priority_display(),
#         'status': t.status,
#         'status_display': t.get_status_display(),
#         'assigned_department': t.assigned_department,
#         'student_name': t.student.get_full_name() or t.student.username,
#         'student_username': t.student.username,
#         'age_hours': t.age_hours,
#         'ageing_color': t.ageing_color,
#         'created_at': t.created_at.isoformat(),
#     }

"""Lightweight ticket serialization for WebSocket payloads."""

from apps.core.services import ConfigService


def serialize_ticket_summary(t):
    ticket_type = ConfigService.ticket_type_by_code(t.ticket_type)
    priority = ConfigService.priority_by_code(t.priority)

    return {
        'id': t.id,
        'subject': t.subject,

        'ticket_type': t.ticket_type,
        'ticket_type_display': (
            ticket_type.name
            if ticket_type
            else t.ticket_type
        ),

        'priority': t.priority,
        'priority_display': (
            priority.name
            if priority
            else t.priority
        ),

        'status': t.status,
        'status_display': t.get_status_display(),

        'assigned_department': t.assigned_department,

        'student_name': (
            t.student.get_full_name()
            or t.student.username
        ),
        'student_username': t.student.username,

        'age_hours': t.age_hours,
        'ageing_color': t.ageing_color,
        'created_at': t.created_at.isoformat(),
    }