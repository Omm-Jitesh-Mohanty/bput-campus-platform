import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.tickets.models import CampusTicket

SAMPLES = [
    ('complaint', 'Water tap leaking in bathroom, floor flooded', 'plumbing'),
    ('complaint', 'Ceiling fan makes loud noise and vibrates', 'electrical'),
    ('complaint', 'WiFi slow in Block B corridor', 'it'),
    ('complaint', 'Mess food quality poor for 3 days', 'mess'),
    ('complaint', 'Room door lock broken, security concern', 'civil'),
    ('complaint', 'Garbage not collected from floor 2', 'housekeeping'),
    ('leave', 'Need leave for 2 days for family function', 'hostel'),
    ('document', 'Bonafide for bank loan application', 'academic'),
    ('gatepass', 'Need gate pass for weekend home visit', 'hostel'),
    ('complaint', 'Streetlight outside Block C not working', 'electrical'),
]


class Command(BaseCommand):
    help = 'Generate bulk demo tickets with varied ages.'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=40)

    def handle(self, *args, **opts):
        students = list(User.objects.filter(role='student'))
        if not students:
            self.stderr.write('No students found. Run seed_demo first.')
            return

        created = 0
        for _ in range(opts['count']):
            ttype, raw, dept = random.choice(SAMPLES)
            student = random.choice(students)
            hours_ago = random.choice([2, 8, 18, 26, 36, 50, 60, 80, 100, 150])
            status = random.choices(
                ['pending', 'in_progress', 'resolved'],
                weights=[5, 3, 2],
            )[0]

            t = CampusTicket.objects.create(
                student=student,
                ticket_type=ttype,
                subject=raw[:100],
                raw_input=raw,
                assigned_department=dept,
                priority=random.choice(['low', 'medium', 'high', 'urgent']),
                status=status,
            )

            # Backdate
            created_at = timezone.now() - timedelta(hours=hours_ago)
            CampusTicket.objects.filter(id=t.id).update(created_at=created_at)

            if status == 'resolved':
                resolved_at = created_at + timedelta(hours=random.randint(2, 48))
                CampusTicket.objects.filter(id=t.id).update(
                    resolved_at=resolved_at,
                    resolution_note='Issue addressed by maintenance team.',
                )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} demo tickets.'))