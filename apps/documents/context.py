"""
Render context builder for document templates.

Maps placeholder names to values pulled from:
  - student profile
  - ticket data (dynamic_data)
  - system values (date, uuid, etc.)
  - custom overrides
"""
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)


# Available data sources — shown in admin UI dropdowns
DATA_SOURCES = [
    # Student fields
    {'key': 'student.full_name',     'label': 'Student full name'},
    {'key': 'student.username',      'label': 'Student username / roll no'},
    {'key': 'student.email',         'label': 'Student email'},
    {'key': 'student.department',    'label': 'Student department'},
    {'key': 'student.batch_year',    'label': 'Student batch year'},
    {'key': 'student.hostel_block',  'label': 'Student hostel block'},
    {'key': 'student.room_number',   'label': 'Student room number'},
    {'key': 'student.phone',         'label': 'Student phone'},

    # Ticket fields
    {'key': 'ticket.id',             'label': 'Ticket ID'},
    {'key': 'ticket.subject',        'label': 'Ticket subject'},
    {'key': 'ticket.raw_input',      'label': 'Ticket description'},
    {'key': 'ticket.created_at',     'label': 'Ticket created date'},

    # Auto values
    {'key': 'auto.today',            'label': 'Today (DD-MM-YYYY)'},
    {'key': 'auto.today_long',       'label': 'Today (long format)'},
    {'key': 'auto.now',              'label': 'Current time'},
    {'key': 'auto.verification_url', 'label': 'Verification URL'},
    {'key': 'auto.doc_uuid',         'label': 'Document UUID'},

    # System
    {'key': 'system.institute_name', 'label': 'Institute name'},
    {'key': 'system.registrar_name', 'label': 'Registrar name'},
]


def _resolve(dotted_path, student=None, ticket=None, doc_uuid=None, extra=None):
    """Resolve a dotted path like 'student.full_name' against the context."""
    parts = dotted_path.split('.')

    if parts[0] == 'student':
        return _resolve_student(parts[1:], student)
    if parts[0] == 'ticket':
        return _resolve_ticket(parts[1:], ticket)
    if parts[0] == 'auto':
        return _resolve_auto(parts[1:], doc_uuid)
    if parts[0] == 'system':
        return _resolve_system(parts[1:])
    if parts[0] == 'extra' and extra:
        return extra.get('.'.join(parts[1:]), '')

    return ''


def _resolve_student(parts, student):
    if not student:
        return ''
    key = parts[0]
    if key == 'full_name':
        return student.get_full_name() or student.username
    return getattr(student, key, '')


def _resolve_ticket(parts, ticket):
    if not ticket:
        return ''
    key = parts[0]
    if key == 'created_at':
        return ticket.created_at.strftime('%d %b %Y')
    if key in ('id', 'subject', 'raw_input'):
        return getattr(ticket, key, '')
    if key == 'dynamic_data':
        if len(parts) > 1:
            return (ticket.dynamic_data or {}).get(parts[1], '')
    return getattr(ticket, key, '')


def _resolve_auto(parts, doc_uuid):
    key = parts[0]
    today = date.today()
    if key == 'today':
        return today.strftime('%d-%m-%Y')
    if key == 'today_long':
        return today.strftime('%d %B %Y')
    if key == 'now':
        return datetime.now().strftime('%d %b %Y %H:%M')
    if key == 'doc_uuid':
        return str(doc_uuid or '')
    if key == 'verification_url':
        from django.conf import settings
        base = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        return f"{base}/verify/{doc_uuid}/" if doc_uuid else ''
    return ''


def _resolve_system(parts):
    from apps.core.services import ConfigService
    key = parts[0]
    if key == 'institute_name':
        return ConfigService.get_setting('site.name', 'BPUT Campus')
    if key == 'registrar_name':
        return ConfigService.get_setting('site.registrar_name', 'Registrar')
    return ''


def build_context(field_mapping, student=None, ticket=None, doc_uuid=None, extra=None):
    """
    Build the render context dict for a template.

    Args:
        field_mapping: dict from DocumentTemplate.field_mapping
                       {placeholder_name: {'source': 'student.full_name'}}
        student, ticket, doc_uuid, extra

    Returns:
        dict of {placeholder_name: value}
    """
    context = {}
    for placeholder, config in (field_mapping or {}).items():
        if isinstance(config, dict):
            source = config.get('source', '')
            fallback = config.get('fallback', '')
        else:
            source = config  # support shorthand {placeholder: "student.full_name"}
            fallback = ''

        try:
            value = _resolve(source, student=student, ticket=ticket,
                             doc_uuid=doc_uuid, extra=extra)
        except Exception as e:
            logger.warning(f"Resolve failed for {source}: {e}")
            value = ''

        context[placeholder] = value if value not in (None, '') else fallback

    return context