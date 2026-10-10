"""
Add best-case demo data WITHOUT removing existing records.

Usage:
    python manage.py add_demo_data

Safe to run multiple times — skips records that already exist.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.accounts.models import FeeRecord
from apps.attendance.models import AttendanceRecord
from apps.feedback.models import Feedback
from apps.notices.models import Notice
from apps.tickets.models import CampusTicket, TicketComment
from apps.core.models import Department, TicketType

User = get_user_model()

# =====================================================================
# Data pools
# =====================================================================
COMPLAINTS = [
    ("Water cooler on 2nd floor leaking continuously", "plumbing", "high"),
    ("Ceiling fan in room 205 making loud noise", "electrical", "medium"),
    ("Wi-Fi disconnecting frequently in Block B study room", "it_support", "high"),
    ("Broken chair in classroom C-204, unsafe to sit", "civil_works", "urgent"),
    ("Mess food quality degraded this week, 5 students reported", "mess", "high"),
    ("Bathroom on 3rd floor not cleaned since Monday", "housekeeping", "medium"),
    ("Corridor lights on 2nd floor not working", "electrical", "medium"),
    ("Water tap in bathroom near room 302 drip leaking", "plumbing", "medium"),
    ("Room door lock jammed, can't close properly", "civil_works", "high"),
    ("Wi-Fi router on 3rd floor down since yesterday", "it_support", "high"),
    ("Ceiling leak in room 108 during rain", "civil_works", "urgent"),
    ("Mess has stopped serving fruits, please check", "mess", "low"),
    ("Garbage bins on 4th floor overflowing", "housekeeping", "medium"),
    ("Exhaust fan in bathroom not working", "electrical", "low"),
    ("Geyser in common bathroom not heating water", "plumbing", "high"),
]

LEAVES = [
    ("Family function at home, need 4 days leave", "medium", 4),
    ("Medical leave for viral fever, doctor advised rest", "high", 3),
    ("Attending sister's wedding in Bhubaneswar", "medium", 5),
    ("Going home for Diwali festival", "low", 6),
    ("Sports competition at another college", "medium", 2),
    ("Grandmother unwell, need to visit", "high", 4),
    ("Personal work, 1 day leave", "low", 1),
    ("Attending cousin's engagement", "medium", 3),
]

DOCUMENTS = [
    ("Bonafide certificate for passport application", "medium"),
    ("Migration certificate for higher studies", "medium"),
    ("Transcript for foreign university application", "high"),
    ("Bonafide for bank education loan", "high"),
    ("Character certificate for internship", "low"),
    ("Bonafide for scholarship renewal", "medium"),
    ("Fee receipt for tax purposes", "low"),
]

GATEPASSES = [
    ("Weekend home visit, departing Saturday morning", "low"),
    ("Going to hospital for checkup", "high"),
    ("Attending placement drive in Bhubaneswar", "medium"),
    ("Family visit to relative's home", "low"),
    ("Buying books from city bookstore", "low"),
]

NOTICES = [
    ("Mid-semester exam schedule released",
     "Mid-semester examinations begin 15th November. All students must download hall tickets before 12th November. Fee dues must be cleared.",
     "high", {"department": "CSE"}),
    ("Hostel water supply maintenance on Sunday",
     "Water supply to Blocks A and B will be shut down from 10 AM to 2 PM on Sunday for pipeline maintenance. Residents are advised to store water in advance.",
     "medium", {"hostel_block": "A"}),
    ("Annual sports day — registration open",
     "Annual sports day will be held on 20th November. Students interested in cricket, football, badminton, or athletics can register with their class coordinators before 15th November.",
     "low", {}),
    ("Placement drive — Infosys on 18th November",
     "Infosys will conduct a placement drive on 18th November for 2023 and 2024 batches. Eligibility: CGPA 6.5+ with no active backlogs. Registration closes 15th November.",
     "high", {"batch_year": "2023"}),
    ("Anti-ragging awareness session",
     "An anti-ragging awareness session will be conducted on 10th November at 3 PM in the auditorium. All first-year students are required to attend.",
     "high", {"batch_year": "2024"}),
    ("Fee payment deadline extended",
     "The fee payment deadline for the current semester has been extended to 30th November. Late payment penalty will apply after that date.",
     "high", {}),
    ("Library timings extended during exams",
     "Library will remain open until 11 PM from 10th to 20th November to help students prepare for exams.",
     "medium", {}),
]

FEEDBACK_ENTRIES = [
    (5, "mess", "Food quality improved a lot this week. Dal and chapati were excellent."),
    (4, "mess", "New menu rotation is good but evening snacks could be better."),
    (2, "mess", "Found a hair in the rice yesterday. Please improve hygiene."),
    (5, "water", "Water purifier on 2nd floor is working perfectly."),
    (3, "water", "Water tastes slightly odd in the morning."),
    (5, "hygiene", "Bathrooms are being cleaned twice daily. Very good improvement."),
    (2, "hygiene", "Garbage bins overflow on weekends."),
    (4, "hostel", "Wi-Fi has improved after the new router installation."),
    (4, "hostel", "Wardens are responsive to complaints."),
    (3, "academic", "Lectures are fine but we need more practical sessions."),
    (5, "academic", "DBMS professor explains concepts very well."),
    (1, "hostel", "Hot water not available in the morning. Please fix."),
    (5, "mess", "Sunday special thali was delicious."),
    (4, "academic", "Exam preparation sessions were helpful."),
    (3, "mess", "Too much oil in the vegetables recently."),
    (2, "hostel", "Room cleaning staff skip our floor sometimes."),
    (5, "hygiene", "Corridor floors are spotless. Thank you."),
    (4, "water", "Water pressure is good in the mornings."),
]


class Command(BaseCommand):
    help = 'Add best-case demo data without removing existing records.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\nAdding best-case demo data...\n'))
        self.stdout.write(self.style.NOTICE('Existing data is preserved. New records added only.\n'))

        # =============================================================
        # 1. EXTRA STUDENTS
        # =============================================================
        self._create_students()

        # =============================================================
        # 2. EXTRA ADMINS
        # =============================================================
        self._create_admins()

        # =============================================================
        # 3. TICKETS
        # =============================================================
        self._create_tickets()

        # =============================================================
        # 4. NOTICES
        # =============================================================
        self._create_notices()

        # =============================================================
        # 5. FEEDBACK
        # =============================================================
        self._create_feedback()

        # =============================================================
        # 6. ATTENDANCE VARIETY
        # =============================================================
        self._vary_attendance()

        # =============================================================
        # 7. FEE VARIETY
        # =============================================================
        self._vary_fees()

        # =============================================================
        # Summary
        # =============================================================
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Final Counts ==='))
        self.stdout.write(f"  Users:      {User.objects.count()}")
        self.stdout.write(f"  Tickets:    {CampusTicket.objects.count()}")
        self.stdout.write(f"  Notices:    {Notice.objects.count()}")
        self.stdout.write(f"  Feedback:   {Feedback.objects.count()}")
        self.stdout.write(f"  Attendance: {AttendanceRecord.objects.count()}")

        self.stdout.write(self.style.SUCCESS('\n✅ Done. Existing data preserved.'))

    # =================================================================
    # Students
    # =================================================================
    def _create_students(self):
        extra_students = [
            ('arjun',  'Arjun',  'Nayak',    'CSE',  '2023', 'A', '310'),
            ('ishita', 'Ishita', 'Behera',   'IT',   '2023', 'B', '215'),
            ('vikram', 'Vikram', 'Patnaik',  'ECE',  '2023', 'C', '108'),
            ('ananya2','Ananya', 'Mohanty',  'CSE',  '2024', 'A', '405'),
            ('rishi',  'Rishi',  'Sahu',     'MECH', '2023', 'D', '220'),
            ('tanvi',  'Tanvi',  'Panda',    'IT',   '2024', 'B', '118'),
            ('kabir',  'Kabir',  'Das',      'EEE',  '2023', 'C', '312'),
            ('meera',  'Meera',  'Rath',     'CSE',  '2023', 'A', '318'),
        ]

        created = 0
        for username, first, last, dept, batch, block, room in extra_students:
            if User.objects.filter(username=username).exists():
                continue
            u = User.objects.create(
                username=username,
                first_name=first, last_name=last,
                role='student',
                department=dept, batch_year=batch,
                hostel_block=block, room_number=room,
                email=f'{username}@campnova.local',
            )
            u.set_password('demo1234')
            u.save()
            created += 1
        self.stdout.write(f'  ✓ Students: +{created} (total {User.objects.filter(role="student").count()})')

    # =================================================================
    # Admins
    # =================================================================
    def _create_admins(self):
        extra = [
            ('prof_os',   'Prof. S.', 'Nayak',     'asst_prof', 'CSE'),
            ('prof_cn',   'Prof. K.', 'Das',       'asst_prof', 'CSE'),
            ('teacher_ds','Prof. P.', 'Mishra',    'teacher',   'CSE'),
            ('lab_cse2',  'Mr. R.',   'Jena',      'lab_asst',  'CSE'),
            ('warden_c',  'Mr. N.',   'Patra',     'warden',    'ADMIN'),
            ('warden_d',  'Mr. S.',   'Mohanty',   'warden',    'ADMIN'),
        ]
        created = 0
        for username, first, last, role, dept in extra:
            if User.objects.filter(username=username).exists():
                continue
            u = User.objects.create(
                username=username,
                first_name=first, last_name=last,
                role=role, department=dept,
                is_staff=True,
            )
            u.set_password('demo1234')
            u.save()
            created += 1
        self.stdout.write(f'  ✓ Admins: +{created} (total {User.objects.exclude(role="student").count()})')

    # =================================================================
    # Tickets
    # =================================================================
    def _create_tickets(self):
        students = list(User.objects.filter(role='student'))
        if not students:
            self.stdout.write(self.style.WARNING('  ! No students found — skipping tickets'))
            return

        created = 0
        hours_spread = [1, 3, 8, 14, 20, 26, 32, 40, 50, 60, 72, 96, 120, 144, 168]

        # ---- Complaints ----
        for i, (subject, dept, priority) in enumerate(COMPLAINTS):
            # Skip if identical subject exists
            if CampusTicket.objects.filter(subject=subject[:100]).exists():
                continue
            student = students[i % len(students)]
            status = random.choices(
                ['pending', 'in_progress', 'resolved'],
                weights=[4, 3, 3],
            )[0]

            t = CampusTicket.objects.create(
                student=student,
                ticket_type='complaint',
                subject=subject,
                raw_input=subject,
                assigned_department=dept,
                priority=priority,
                status=status,
                is_deleted=False,
                dynamic_data={'complaint_subtype': _subtype_for(dept)},
            )
            self._backdate(t, hours_spread[i % len(hours_spread)])
            if status == 'resolved':
                self._mark_resolved(t)
            created += 1

        # ---- Leaves ----
        for i, (subject, priority, days) in enumerate(LEAVES):
            if CampusTicket.objects.filter(subject=subject[:100]).exists():
                continue
            student = students[(i + 3) % len(students)]
            status = random.choices(
                ['pending', 'in_progress', 'resolved'],
                weights=[3, 2, 5],
            )[0]

            t = CampusTicket.objects.create(
                student=student,
                ticket_type='leave',
                subject=subject,
                raw_input=subject,
                assigned_department='hostel',
                priority=priority,
                status=status,
                is_deleted=False,
                dynamic_data={'duration_days': days},
            )
            self._backdate(t, hours_spread[(i + 5) % len(hours_spread)])
            if status == 'resolved':
                self._mark_resolved(t)
            created += 1

        # ---- Documents ----
        for i, (subject, priority) in enumerate(DOCUMENTS):
            if CampusTicket.objects.filter(subject=subject[:100]).exists():
                continue
            student = students[(i + 1) % len(students)]
            status = random.choices(
                ['pending', 'in_progress', 'resolved'],
                weights=[2, 2, 6],
            )[0]

            t = CampusTicket.objects.create(
                student=student,
                ticket_type='document',
                subject=subject,
                raw_input=subject,
                assigned_department='academic',
                priority=priority,
                status=status,
                is_deleted=False,
            )
            self._backdate(t, hours_spread[(i + 7) % len(hours_spread)])
            if status == 'resolved':
                self._mark_resolved(t)
            created += 1

        # ---- Gate Passes ----
        for i, (subject, priority) in enumerate(GATEPASSES):
            if CampusTicket.objects.filter(subject=subject[:100]).exists():
                continue
            student = students[(i + 5) % len(students)]
            status = random.choices(
                ['pending', 'in_progress', 'resolved'],
                weights=[2, 2, 6],
            )[0]

            t = CampusTicket.objects.create(
                student=student,
                ticket_type='gatepass',
                subject=subject,
                raw_input=subject,
                assigned_department='hostel',
                priority=priority,
                status=status,
                is_deleted=False,
            )
            self._backdate(t, hours_spread[(i + 9) % len(hours_spread)])
            if status == 'resolved':
                self._mark_resolved(t)
            created += 1

        self.stdout.write(f'  ✓ Tickets: +{created} (total {CampusTicket.objects.count()})')

    # =================================================================
    # Notices
    # =================================================================
    def _create_notices(self):
        admin = User.objects.filter(role__in=['principal', 'warden']).first()
        if not admin:
            self.stdout.write(self.style.WARNING('  ! No admin found — skipping notices'))
            return

        created = 0
        for title, content, priority, aud in NOTICES:
            if Notice.objects.filter(title=title).exists():
                continue
            Notice.objects.create(
                title=title,
                content=content,
                ai_summary=content[:140] + '…',
                ai_priority=priority,
                target_audience=aud,
                posted_by=admin,
                is_deleted=False,
            )
            created += 1
        self.stdout.write(f'  ✓ Notices: +{created} (total {Notice.objects.count()})')

    # =================================================================
    # Feedback
    # =================================================================
    def _create_feedback(self):
        students = list(User.objects.filter(role='student'))
        if not students:
            return

        created = 0
        for rating, cat, comment in FEEDBACK_ENTRIES:
            if Feedback.objects.filter(comments=comment).exists():
                continue
            Feedback.objects.create(
                student=random.choice(students),
                category=cat,
                rating=rating,
                comments=comment,
            )
            created += 1
        self.stdout.write(f'  ✓ Feedback: +{created} (total {Feedback.objects.count()})')

    # =================================================================
    # Attendance variety
    # =================================================================
    def _vary_attendance(self):
        """Add attendance records for new students."""
        subjects = [
            ('CS301', 'DBMS'),
            ('CS302', 'Operating Systems'),
            ('CS303', 'Computer Networks'),
            ('CS304', 'Data Structures'),
            ('CS305', 'Software Engineering'),
        ]
        new_students = User.objects.filter(
            role='student', username__in=[
                'arjun', 'ishita', 'vikram', 'ananya2',
                'rishi', 'tanvi', 'kabir', 'meera',
            ]
        )
        created = 0
        for student in new_students:
            for code, name in subjects:
                if AttendanceRecord.objects.filter(student=student, subject_code=code).exists():
                    continue
                total = random.randint(25, 40)
                # Deliberately vary the ratios so dashboard has red/amber/green mix
                ratio = random.choice([0.55, 0.62, 0.70, 0.78, 0.85, 0.90, 0.95])
                AttendanceRecord.objects.create(
                    student=student,
                    subject_code=code,
                    subject_name=name,
                    total_classes=total,
                    attended_classes=int(total * ratio),
                )
                created += 1
        self.stdout.write(f'  ✓ Attendance: +{created} (total {AttendanceRecord.objects.count()})')

    # =================================================================
    # Fee variety
    # =================================================================
    def _vary_fees(self):
        """Ensure new students have varied fee statuses."""
        new_students = User.objects.filter(
            role='student', username__in=[
                'arjun', 'ishita', 'vikram', 'ananya2',
                'rishi', 'tanvi', 'kabir', 'meera',
            ]
        )
        created = 0
        for student in new_students:
            if FeeRecord.objects.filter(student=student, semester='2025-ODD').exists():
                continue
            paid = random.choice([45000, 40000, 30000, 22000, 15000, 0])
            FeeRecord.objects.create(
                student=student,
                semester='2025-ODD',
                total_dues=Decimal('45000.00'),
                paid_amount=Decimal(str(paid)),
                due_date=(timezone.now() + timedelta(days=30)).date(),
            )
            created += 1
        self.stdout.write(f'  ✓ Fee records: +{created} (total {FeeRecord.objects.count()})')

    # =================================================================
    # Helpers
    # =================================================================
    def _backdate(self, ticket, hours_ago):
        created_at = timezone.now() - timedelta(hours=hours_ago)
        CampusTicket.objects.filter(id=ticket.id).update(created_at=created_at)

    def _mark_resolved(self, ticket):
        """Mark a ticket resolved and add a comment for realism."""
        resolved_at = ticket.created_at + timedelta(hours=random.randint(2, 30))
        CampusTicket.objects.filter(id=ticket.id).update(
            resolved_at=resolved_at,
            resolution_note='Issue addressed by team and verified.',
            resolved_by=User.objects.filter(role__in=['warden', 'hod']).first(),
        )
        # Add a comment thread
        if random.random() > 0.5:
            TicketComment.objects.create(
                ticket=ticket,
                author=ticket.student,
                body='Any update on this? It is affecting daily activities.',
            )


def _subtype_for(dept):
    """Map department to subtype code."""
    mapping = {
        'plumbing': 'plumbing_repair',
        'electrical': 'electrical_repair',
        'civil_works': 'civil_repair',
        'it_support': 'wifi_issue',
        'mess': 'mess_quality',
        'housekeeping': 'hostel_facility',
    }
    return mapping.get(dept, 'electrical_repair')