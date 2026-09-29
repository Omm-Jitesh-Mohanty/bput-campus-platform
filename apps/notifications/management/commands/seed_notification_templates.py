from django.core.management.base import BaseCommand
from apps.core.models import NotificationTemplate


TEMPLATES = [
    # ========== Ticket events ==========
    ('ticket.created', 'in_app', 'en', '',
     "Your ticket #{{ ticket_id }} has been received.\n"
     "Type: {{ ticket_type }}\n"
     "Status: {{ ticket_status }}"),

    ('ticket.created', 'email', 'en',
     'Ticket #{{ ticket_id }} received — {{ ticket_subject }}',
     "Dear {{ student_name }},\n\n"
     "Your request has been received and logged as ticket #{{ ticket_id }}.\n\n"
     "Subject: {{ ticket_subject }}\n"
     "Type: {{ ticket_type }}\n"
     "Current status: {{ ticket_status }}\n\n"
     "You will be notified as soon as it is updated.\n\n"
     "— Campus Platform"),

    ('ticket.step_action', 'in_app', 'en', '',
     "Step '{{ step_name }}' was {{ action }} by {{ actor_name }}.\n"
     "{% if comment %}Comment: {{ comment }}{% endif %}"),

    ('ticket.resolved', 'in_app', 'en', '',
     "Your ticket #{{ ticket_id }} has been resolved.\n"
     "{% if resolution_note %}Note: {{ resolution_note }}{% endif %}\n"
     "Please confirm if the issue is fixed."),

    ('ticket.resolved', 'email', 'en',
     'Ticket #{{ ticket_id }} resolved',
     "Dear {{ student_name }},\n\n"
     "Your ticket #{{ ticket_id }} ({{ ticket_subject }}) has been resolved.\n\n"
     "{% if resolution_note %}Resolution note:\n{{ resolution_note }}\n\n{% endif %}"
     "If the issue persists, please log in and reopen the ticket.\n\n"
     "— Campus Platform"),

    ('ticket.escalated', 'in_app', 'en', '',
     "⚠️ Ticket #{{ ticket_id }} has been escalated to {{ escalation_target }} "
     "due to SLA breach."),

    # ========== Workflow step ==========
    ('step.pending', 'in_app', 'en', '',
     "Action needed on ticket #{{ ticket_id }}\n"
     "Step: {{ step_name }}\n"
     "Student: {{ student_name }}\n"
     "{% if instructions %}Note: {{ instructions }}{% endif %}"),

    ('step.pending', 'email', 'en',
     '[Action Required] Ticket #{{ ticket_id }} — {{ step_name }}',
     "A ticket is awaiting your approval:\n\n"
     "Ticket: #{{ ticket_id }}\n"
     "Subject: {{ ticket_subject }}\n"
     "Student: {{ student_name }}\n"
     "Step: {{ step_name }}\n\n"
     "{% if instructions %}Instructions:\n{{ instructions }}\n\n{% endif %}"
     "Open the campus portal to take action.\n\n"
     "— Campus Platform"),

    # ========== Notice ==========
    ('notice.published', 'in_app', 'en', '',
     "📢 {{ notice_title }}\n\n{{ notice_summary }}"),

    ('notice.published', 'email', 'en',
     'New notice: {{ notice_title }}',
     "A new notice has been published:\n\n"
     "{{ notice_title }}\n\n"
     "{{ notice_summary }}\n\n"
     "Posted by: {{ posted_by }}\n\n"
     "— Campus Platform"),

    # ========== Document ==========
    ('document.issued', 'in_app', 'en', '',
     "📄 Your document '{{ document_title }}' is ready for download."),
]


class Command(BaseCommand):
    help = 'Seed notification templates for common events.'

    def handle(self, *args, **options):
        created = 0
        for event, channel, lang, subject, body in TEMPLATES:
            _, was_created = NotificationTemplate.objects.get_or_create(
                event_code=event, channel=channel, language=lang,
                defaults={
                    'subject_template': subject,
                    'body_template': body,
                    'is_active': True,
                }
            )
            if was_created:
                created += 1
                self.stdout.write(f'  + {event}/{channel}/{lang}')

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Notification templates: {created} created, '
            f'{len(TEMPLATES) - created} already existed.'
        ))