"""
Reset the entire database to a perfect demo state.

Run before every demo:
    python manage.py reset_demo

This command:
  1. Wipes all demo data (users, tickets, notices, docs)
  2. Preserves config (departments, SLAs, workflows, templates)
  3. Creates demo users
  4. Creates demo content (tickets, notices, feedback)
  5. Verifies the resulting state

For safety, it refuses to run if DEBUG=False.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.accounts.models import FeeRecord
from apps.attendance.models import AttendanceRecord, Timetable
from apps.core.models import Department, TicketType, PriorityLevel
from apps.feedback.models import Feedback
from apps.notices.models import Notice
from apps.tickets.models import CampusTicket, TicketComment
from apps.workflows.models import Workflow, TicketStepExecution
from apps.notifications.models import Notification

User = get_user_model()


STUDENTS = [
    # username, first, last, dept, batch, block, room, fees_pending
    ('aditya',   'Aditya',  'Patra',    'CSE', '2023', 'A', '302', 0),
    ('sneha',    'Sneha',   'Mohanty',  'CSE', '2023', 'A', '305', 15000),
    ('rohan',    'Rohan',   'Das',      'CSE', '2023', 'B', '112', 0),
    ('priya',    'Priya',   'Sahoo',    'IT',  '2023', 'B', '108', 0),
    ('rahul',    'Rahul',   'Pradhan',  'ECE', '2023', 'C', '204', 0),
    ('ananya',   'Ananya',  'Behera',   'CSE', '2024', 'A', '201', 0),
    ('karan',    'Karan',   'Jena',     'MECH','2023', 'C', '310', 0),
    ('divya',    'Divya',   'Rath',     'IT',  '2024', 'B', '205', 0),
]

ADMINS = [
    ('principal',    'Dr. R. K.',  'Panda',    'principal', 'ADMIN'),
    ('dean',         'Prof. S.',   'Mishra',   'dean',      'ADMIN'),
    ('hod_cse',      'Prof. M.',   'Nayak',    'hod',       'CSE'),
    ('warden_a',     'Mr. B.',     'Sahu',     'warden',    'ADMIN'),
    ('teacher_dbms', 'Prof. A.',   'Mohapatra','teacher',   'CSE'),
]

SUBJECTS = [
    ('CS301', 'DBMS',                'Prof. A. Mohapatra'),
    ('CS302', 'Operating Systems',   'Prof. S. Nayak'),
    ('CS303', 'Computer Networks',   'Prof. K. Das'),
    ('CS304', 'Data Structures',     'Prof. P. Mishra'),
]


class Command(BaseCommand):
    help = 'Reset to a clean demo state.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Allow running even with DEBUG=False')

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['force']:
            raise CommandError(
                'Refusing to reset in non-DEBUG mode. Use --force to override.'
            )

        self.stdout.write(self.style.WARNING('\n🔄 Resetting to demo state...\n'))

        with transaction.atomic():
            self._wipe_demo_data()
            self._ensure_config()
            self._create_users()
            self._create_fees()
            self._create_attendance()
            self._create_timetable()
            self._create_tickets()
            self._create_notices()
            self._create_feedback()

        self._verify()
        self.stdout.write(self.style.SUCCESS('\n✅ Demo state ready.\n'))
        self.stdout.write('Login with any username below, password: demo1234\n')
        self.stdout.write('  Student:  aditya, sneha, rohan, priya, rahul...')
        self.stdout.write('  Warden:   warden_a')
        self.stdout.write('  HOD:      hod_cse')
        self.stdout.write('  Dean:     dean')
        self.stdout.write('  Principal: principal\n')

    # =================================================================
    # WIPE
    # =================================================================
    def _wipe_demo_data(self):
        self.stdout.write('  → Wiping demo data...')

        # Order matters for FK constraints
        TicketComment.objects.all().delete()
        TicketStepExecution.objects.all().delete()
        CampusTicket.objects.all().delete()
        Notification.objects.all().delete()
        Feedback.objects.all().delete()
        Notice.objects.all().delete()
        AttendanceRecord.objects.all().delete()
        Timetable.objects.all().delete()
        FeeRecord.objects.all().delete()

        # Delete users (except superuser)
        User.objects.exclude(is_superuser=True).delete()

        # Try to clean up documents if app exists
        try:
            from apps.documents.models import IssuedDocument
            IssuedDocument.objects.all().delete()
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS('    ✓ wiped'))

    # =================================================================
    # CONFIG — ensure but don't overwrite
    # =================================================================
    def _ensure_config(self):
        self.stdout.write('  → Ensuring config...')

        if Department.objects.count() == 0:
            self.stdout.write('    ! No departments. Run bootstrap_config first.')
            self.stdout.write('    Running bootstrap_config now...')
            call_command('bootstrap_config', verbosity=0)

        if Workflow.objects.count() == 0:
            call_command('seed_workflows', verbosity=0)

        self.stdout.write(self.style.SUCCESS('    ✓ config ok'))

    # =================================================================
    # USERS
    # =================================================================
    def _create_users(self):
        self.stdout.write('  → Creating users...')

        for username, first, last, role, dept in ADMINS:
            u = User.objects.create(
                username=username,
                first_name=first,
                last_name=last,
                role=role,
                department=dept,
                is_staff=True,
            )
            u.set_password('demo1234')
            u.save()

        for username, first, last, dept, batch, block, room, _ in STUDENTS:
            u = User.objects.create(
                username=username,
                first_name=first,
                last_name=last,
                role='student',
                department=dept,
                batch_year=batch,
                hostel_block=block,
                room_number=room,
            )
            u.set_password('demo1234')
            u.save()

        self.stdout.write(self.style.SUCCESS(
            f'    ✓ {len(ADMINS)} admins + {len(STUDENTS)} students'
        ))

    # =================================================================
    # FEES
    # =================================================================
    def _create_fees(self):
        self.stdout.write('  → Creating fee records...')
        for username, _, _, _, _, _, _, pending in STUDENTS:
            try:
                student = User.objects.get(username=username)
            except User.DoesNotExist:
                continue

            paid = 45000 - pending
            FeeRecord.objects.create(
                student=student,
                semester='2025-ODD',
                total_dues=Decimal('45000.00'),
                paid_amount=Decimal(str(paid)),
                due_date=(timezone.now() + timedelta(days=30)).date(),
            )
        self.stdout.write(self.style.SUCCESS(f'    ✓ {len(STUDENTS)} records'))

    # =================================================================
    # ATTENDANCE
    # =================================================================
    def _create_attendance(self):
        self.stdout.write('  → Creating attendance...')

        # Deliberately vary attendance for demo
        profiles = {
            'aditya': [0.72, 0.85, 0.90, 0.78],   # borderline
            'sneha':  [0.60, 0.65, 0.70, 0.55],   # low — triggers recovery
            'rohan':  [0.95, 0.92, 0.98, 0.94],   # excellent
            'priya':  [0.88, 0.90, 0.87, 0.91],
            'rahul':  [0.80, 0.78, 0.82, 0.85],
        }

        for student in User.objects.filter(role='student'):
            profile = profiles.get(student.username, [0.85] * 4)
            for (code, name, faculty), ratio in zip(SUBJECTS, profile):
                total = random.randint(30, 40)
                attended = int(total * ratio)
                AttendanceRecord.objects.create(
                    student=student,
                    subject_code=code,
                    subject_name=name,
                    total_classes=total,
                    attended_classes=attended,
                    faculty_name=faculty,
                )

        self.stdout.write(self.style.SUCCESS('    ✓ attendance'))

    # =================================================================
    # TIMETABLE
    # =================================================================
    def _create_timetable(self):
        self.stdout.write('  → Creating timetable...')

        slots = ['09:00-10:00', '10:00-11:00', '11:15-12:15',
                 '13:00-14:00', '14:00-15:00']
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']

        for dept in ['CSE', 'IT']:
            for day in days:
                for i, (code, name, faculty) in enumerate(SUBJECTS):
                    Timetable.objects.create(
                        department=dept,
                        batch_year='2023',
                        day_of_week=day,
                        time_slot=slots[i],
                        subject_code=code,
                        subject_name=name,
                        faculty_name=faculty,
                        room=f'{dept}-{100 + i}',
                    )

        self.stdout.write(self.style.SUCCESS('    ✓ timetable'))

    # =================================================================
    # TICKETS
    # =================================================================
    def _create_tickets(self):
        self.stdout.write('  → Creating tickets...')

        student = User.objects.get(username='aditya')

        # Some pending, some in-progress, some resolved, some overdue
        ticket_specs = [
            ('complaint', 'Water tap in room 302 leaking since 3 days',
             'plumbing', 'high', 'pending'),
            ('complaint', 'Ceiling fan making loud noise in room 305',
             'electrical', 'medium', 'in_progress'),
            ('complaint', 'WiFi not working in Block A corridor',
             'it_support', 'high', 'pending'),
            ('complaint', 'Mess food quality has degraded this week',
             'mess', 'medium', 'pending'),
            ('complaint', 'Garbage not collected from Block A floor 2',
             'housekeeping', 'low', 'pending'),
            ('leave', 'Need leave for 2 days for family function',
             'hostel', 'medium', 'pending'),
            ('document', 'Bonafide certificate for bank loan',
             'academic', 'medium', 'pending'),
            ('gatepass', 'Weekend home visit gate pass',
             'hostel', 'low', 'resolved'),
        ]

        # Distribute across students
        students = list(User.objects.filter(role='student'))

        for i, (ttype, subject, dept, priority, status) in enumerate(ticket_specs):
            s = students[i % len(students)]
            hours_ago = [2, 8, 20, 30, 50, 80, 100, 150][i]

            ticket = CampusTicket.objects.create(
                student=s,
                ticket_type=ttype,
                subject=subject[:100],
                raw_input=subject,
                assigned_department=dept,
                priority=priority,
                status=status,
            )
            # Backdate
            created_at = timezone.now() - timedelta(hours=hours_ago)
            CampusTicket.objects.filter(id=ticket.id).update(
                created_at=created_at,
                formatted_body=f"Respected Sir/Madam,\n\nI, {s.get_full_name()}, wish to submit: {subject}.\n\nYours sincerely,\n{s.get_full_name()}",
            )

            if status == 'resolved':
                CampusTicket.objects.filter(id=ticket.id).update(
                    resolved_at=created_at + timedelta(hours=4),
                    resolution_note='Issue addressed and verified.',
                )

        self.stdout.write(self.style.SUCCESS(
            f'    ✓ {len(ticket_specs)} tickets'
        ))

    # =================================================================
    # NOTICES
    # =================================================================
    def _create_notices(self):
        self.stdout.write('  → Creating notices...')

        principal = User.objects.get(username='principal')

        notices = [
            ('Mid-semester exam schedule released',
             'Mid-semester exams begin 15th March. All students must download hall tickets from the portal before 12th March. Fee dues must be cleared for eligibility.',
             'high', {'department': 'CSE'}),
            ('Hostel water supply disruption Sunday',
             'Water supply to Blocks A and B will be shut down on Sunday 10 AM - 2 PM for pipeline maintenance. Residents are advised to store water in advance.',
             'medium', {'hostel_block': 'A'}),
            ('Annual day celebration — volunteers needed',
             'Annual day will be held on 25th March. Students interested in volunteering should register with their class coordinators.',
             'low', {}),
        ]

        for title, content, priority, aud in notices:
            Notice.objects.create(
                title=title,
                content=content,
                ai_summary=content[:140] + '…',
                ai_priority=priority,
                target_audience=aud,
                posted_by=principal,
            )

        self.stdout.write(self.style.SUCCESS(f'    ✓ {len(notices)} notices'))

    # =================================================================
    # FEEDBACK
    # =================================================================
    def _create_feedback(self):
        self.stdout.write('  → Creating feedback...')

        students = list(User.objects.filter(role='student'))
        comments = [
            (5, 'mess', 'Food quality is excellent this week.'),
            (2, 'mess', 'The dal was watery yesterday.'),
            (4, 'water', 'Water tastes fine.'),
            (3, 'hygiene', 'Hostel cleaning is delayed on weekends.'),
            (5, 'hostel', 'WiFi speed has improved significantly.'),
            (1, 'mess', 'Found a hair in the food today.'),
            (4, 'academic', 'Lectures are well-organized.'),
            (2, 'hygiene', 'Bathrooms need more frequent cleaning.'),
        ]

        for rating, cat, comment in comments:
            Feedback.objects.create(
                student=random.choice(students),
                category=cat,
                rating=rating,
                comments=comment,
            )

        self.stdout.write(self.style.SUCCESS(f'    ✓ {len(comments)} feedback entries'))

    # =================================================================
    # VERIFY
    # =================================================================
    def _verify(self):
        self.stdout.write('  → Verifying state...')

        checks = [
            ('Users', User.objects.filter(is_superuser=False).count(), 13),
            ('Tickets', CampusTicket.objects.count(), 8),
            ('Notices', Notice.objects.count(), 3),
            ('Feedback', Feedback.objects.count(), 8),
            ('Attendance', AttendanceRecord.objects.count(), 32),
        ]

        for name, actual, expected in checks:
            if actual == 0:
                self.stdout.write(self.style.ERROR(
                    f'    ✗ {name}: {actual} (expected {expected})'
                ))
            else:
                self.stdout.write(f'    ✓ {name}: {actual}')

        pending = CampusTicket.objects.filter(status='pending').count()
        overdue = sum(
            1 for t in CampusTicket.objects.filter(status='pending')
            if t.age_hours > 48
        )
        self.stdout.write(f'    → {pending} pending, {overdue} overdue (good for demo)')