"""
Populate realistic demo data for the hackathon demo.
Run: python manage.py seed_demo
"""
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.attendance.models import AttendanceRecord, Timetable
from apps.tickets.models import CampusTicket
from apps.notices.models import Notice
from apps.feedback.models import Feedback
from apps.accounts.models import FeeRecord

User = get_user_model()

STUDENTS = [
    ('aditya', 'Aditya', 'Patra', 'CSE', '2023', 'A', '302'),
    ('sneha', 'Sneha', 'Mohanty', 'CSE', '2023', 'A', '305'),
    ('rohan', 'Rohan', 'Das', 'CSE', '2023', 'B', '112'),
    ('priya', 'Priya', 'Sahoo', 'IT', '2023', 'B', '108'),
    ('rahul', 'Rahul', 'Pradhan', 'ECE', '2023', 'C', '204'),
    ('ananya', 'Ananya', 'Behera', 'CSE', '2024', 'A', '201'),
    ('karan', 'Karan', 'Jena', 'MECH', '2023', 'C', '310'),
    ('divya', 'Divya', 'Rath', 'IT', '2024', 'B', '205'),
]

ADMINS = [
    ('principal', 'Dr. R. K.', 'Panda', 'principal', 'ADMIN'),
    ('dean', 'Prof. S.', 'Mishra', 'dean', 'ADMIN'),
    ('hod_cse', 'Prof. M.', 'Nayak', 'hod', 'CSE'),
    ('warden_a', 'Mr. B.', 'Sahu', 'warden', 'ADMIN'),
    ('teacher_dbms', 'Prof. A.', 'Mohapatra', 'teacher', 'CSE'),
]

SUBJECTS = [
    ('CS301', 'DBMS', 'Prof. A. Mohapatra'),
    ('CS302', 'Operating Systems', 'Prof. S. Nayak'),
    ('CS303', 'Computer Networks', 'Prof. K. Das'),
    ('CS304', 'Data Structures', 'Prof. P. Mishra'),
]


class Command(BaseCommand):
    help = 'Seed realistic demo data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Seeding demo data...'))

        # ---------- Admins ----------
        for username, first, last, role, dept in ADMINS:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first, 'last_name': last,
                    'role': role, 'department': dept,
                    'is_staff': True,
                }
            )
            if created:
                u.set_password('demo1234')
                u.save()
                self.stdout.write(f"  + admin {username} (pwd: demo1234)")

        # ---------- Students ----------
        student_objs = []
        for username, first, last, dept, batch, block, room in STUDENTS:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first, 'last_name': last,
                    'role': 'student', 'department': dept,
                    'batch_year': batch, 'hostel_block': block,
                    'room_number': room,
                }
            )
            if created:
                u.set_password('demo1234')
                u.save()
            student_objs.append(u)

        self.stdout.write(f"  + {len(student_objs)} students (pwd: demo1234)")

        # ---------- Attendance ----------
        for student in student_objs:
            for code, name, faculty in SUBJECTS:
                total = random.randint(25, 40)
                pct = random.choice([0.55, 0.65, 0.72, 0.78, 0.85, 0.92])
                attended = int(total * pct)
                AttendanceRecord.objects.get_or_create(
                    student=student, subject_code=code,
                    defaults={
                        'subject_name': name,
                        'total_classes': total,
                        'attended_classes': attended,
                        'faculty_name': faculty,
                    }
                )

        # ---------- Timetable ----------
        slots = ['09:00-10:00', '10:00-11:00', '11:15-12:15', '13:00-14:00', '14:00-15:00']
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        for dept in ['CSE', 'IT']:
            for day in days:
                for i, (code, name, faculty) in enumerate(SUBJECTS):
                    Timetable.objects.get_or_create(
                        department=dept, batch_year='2023',
                        day_of_week=day, time_slot=slots[i],
                        defaults={
                            'subject_code': code, 'subject_name': name,
                            'faculty_name': faculty,
                            'room': f'{dept}-{100+i}',
                        }
                    )

        # ---------- Fee Records ----------
        for student in student_objs:
            FeeRecord.objects.get_or_create(
                student=student, semester='2025-ODD',
                defaults={
                    'total_dues': 45000,
                    'paid_amount': random.choice([45000, 30000, 15000, 0]),
                    'due_date': date.today() + timedelta(days=30),
                }
            )

        # ---------- Demo Tickets ----------
        sample_tickets = [
            ('complaint', 'Water tap in room 302 is leaking since 3 days', 'plumbing'),
            ('complaint', 'Ceiling fan in room 305 not working', 'electrical'),
            ('leave', 'Need leave for 2 days due to fever', 'hostel'),
            ('document', 'Bonafide certificate needed for bank loan', 'academic'),
            ('complaint', 'Mess food quality has degraded this week', 'mess'),
            ('complaint', 'WiFi not working in Block B corridor', 'it'),
        ]

        for student in student_objs[:4]:
            for ttype, raw, dept in random.sample(sample_tickets, 3):
                ticket = CampusTicket.objects.create(
                    student=student,
                    ticket_type=ttype,
                    subject=raw[:100],
                    raw_input=raw,
                    assigned_department=dept,
                    priority=random.choice(['low', 'medium', 'high']),
                    status=random.choice(['pending', 'in_progress', 'resolved']),
                )
                # Backdate some
                days_ago = random.randint(0, 5)
                CampusTicket.objects.filter(id=ticket.id).update(
                    created_at=timezone.now() - timedelta(days=days_ago)
                )

        # ---------- Notices ----------
        admin_user = User.objects.get(username='principal')
        notices = [
            ('Mid-semester exam schedule released',
             'Mid-semester exams begin 15th March. All students must check hall tickets. Bring ID cards.',
             'high', {'department': 'CSE'}),
            ('Hostel water supply disruption on Sunday',
             'Water supply will be disrupted on Sunday 10 AM-2 PM for maintenance.',
             'medium', {'hostel_block': 'A'}),
            ('Annual day celebration',
             'Annual day will be held on 25th March. Volunteers needed.',
             'low', {}),
        ]
        for title, content, pri, aud in notices:
            Notice.objects.get_or_create(
                title=title,
                defaults={
                    'content': content,
                    'ai_summary': content[:120] + '...',
                    'ai_priority': pri,
                    'target_audience': aud,
                    'posted_by': admin_user,
                }
            )

        # ---------- Feedback ----------
        for _ in range(20):
            Feedback.objects.create(
                student=random.choice(student_objs),
                category=random.choice(['mess', 'water', 'hygiene', 'hostel', 'academic']),
                rating=random.randint(1, 5),
                comments=random.choice([
                    'Food quality is inconsistent.',
                    'Water tastes fine.',
                    'Hostel cleaning is delayed.',
                    'WiFi speed is good.',
                    'Tap water occasionally has color.',
                    '',
                ]),
            )

        self.stdout.write(self.style.SUCCESS('\n✅ Demo data seeded.'))
        self.stdout.write(self.style.SUCCESS('Login with any username, password: demo1234'))
        self.stdout.write('Try: aditya, sneha, warden_a, hod_cse, principal')