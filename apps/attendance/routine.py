"""
Compute a personalized daily plan for a student.

Factors:
  - Today's timetable (with cancellations)
  - Student's attendance (which subjects need recovery)
  - Study preferences
  - Any exams (from notices tagged as exam)
  - Pending assignments (if we add later)
"""
import logging
from datetime import datetime, time
from django.utils import timezone

logger = logging.getLogger(__name__)


def compute_daily_plan(student):
    """
    Return a dict:
      {
        'date': '2026-10-02',
        'slots': [
            {'time': '09:00-10:00', 'subject': 'DBMS', 'status': 'scheduled',
             'room': 'CSE-101', 'faculty': 'Prof. X'},
            {'time': '10:00-11:00', 'subject': 'OS', 'status': 'cancelled',
             'reason': 'Faculty on leave', 'suggestion': 'Attend DBMS recovery session'},
            ...
        ],
        'attendance_urgency': [
            {'subject': 'DBMS', 'percentage': 68, 'classes_needed': 5},
        ],
        'suggestions': [
            'You are below 75% in DBMS. Consider attending the 5 PM review session.',
            'Class of OS is cancelled today — a good slot for revision.',
        ],
      }
    """
    from apps.attendance.models import Timetable, ClassCancellation, AttendanceRecord
    from apps.attendance.services import recovery_plan

    today = timezone.localdate()
    weekday = today.strftime('%a')[:3]  # Mon/Tue/...

    # 1. Get today's scheduled classes
    scheduled = Timetable.objects.filter(
        department=student.department,
        batch_year=student.batch_year,
        day_of_week=weekday,
    ).order_by('time_slot')

    # 2. Get cancellations for today
    cancellations = {
        c.timetable_id: c
        for c in ClassCancellation.objects.filter(
            timetable__in=scheduled, date=today
        )
    }

    # 3. Get attendance urgency per subject
    urgent_subjects = []
    for rec in AttendanceRecord.objects.filter(student=student):
        plan = recovery_plan(rec.attended_classes, rec.total_classes)
        if plan['needed'] > 0:
            urgent_subjects.append({
                'subject': rec.subject_name,
                'subject_code': rec.subject_code,
                'percentage': rec.percentage,
                'classes_needed': plan['needed'],
                'message': plan['message'],
            })

    # 4. Build today's slots
    slots = []
    suggestions = []

    for cls in scheduled:
        cancel = cancellations.get(cls.id)
        slot = {
            'time': cls.time_slot,
            'subject': cls.subject_name,
            'subject_code': cls.subject_code,
            'faculty': cls.faculty_name,
            'room': cls.room,
        }

        if cancel:
            slot['status'] = 'cancelled'
            slot['reason'] = cancel.reason or 'Cancelled'
            if cancel.replacement_slot:
                slot['replacement_slot'] = cancel.replacement_slot
                slot['status'] = 'rescheduled'

            # Generate suggestion for this cancellation
            matching_urgent = next(
                (u for u in urgent_subjects if u['subject_code'] == cls.subject_code),
                None
            )
            if matching_urgent:
                slot['suggestion'] = (
                    f"Class cancelled. Use this slot to recover attendance in "
                    f"{matching_urgent['subject']} (currently {matching_urgent['percentage']}%)."
                )
                suggestions.append(slot['suggestion'])
            else:
                slot['suggestion'] = "Free slot — use for revision or library."
        else:
            slot['status'] = 'scheduled'

        slots.append(slot)

    # 5. System-wide suggestions
    if urgent_subjects:
        for u in urgent_subjects[:3]:
            suggestions.append(
                f"⚠️ {u['subject']}: {u['percentage']}% — attend {u['classes_needed']} more to reach 75%."
            )

    # 6. Exam preparation hints
    from apps.notices.models import Notice
    recent_notices = Notice.objects.filter(
        ai_priority='high',
        created_at__gte=timezone.now() - timezone.timedelta(days=7),
    )
    for n in recent_notices[:2]:
        if 'exam' in (n.title + n.content).lower():
            suggestions.append(f"📚 Exam notice: {n.title}")

    plan = {
        'date': today.isoformat(),
        'weekday': weekday,
        'slots': slots,
        'attendance_urgency': urgent_subjects,
        'suggestions': suggestions,
        'generated_at': timezone.now().isoformat(),
    }

    # Persist
    from apps.attendance.models import StudentRoutine
    routine, _ = StudentRoutine.objects.get_or_create(student=student)
    routine.daily_plan = plan
    routine.last_computed = timezone.now()
    routine.save(update_fields=['daily_plan', 'last_computed', 'updated_at'])

    return plan