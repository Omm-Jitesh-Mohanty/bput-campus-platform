# from django.shortcuts import render

# Create your views here.
"""
Teacher-facing views: my classes, mark attendance, class updates, notices.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta

from apps.core.permissions import require_perm, Perm
from apps.core.decorators import admin_required
from apps.attendance.models import Timetable, AttendanceRecord, ClassCancellation
from apps.accounts.models import User


def _teacher_required(user):
    return user.role in ('asst_prof', 'teacher', 'lab_asst', 'hod')


@admin_required
def teacher_dashboard(request):
    """Teacher's home — their classes today."""
    if not _teacher_required(request.user):
        messages.warning(request, "Teacher access required.")
        return redirect('dashboard:home_router')

    today_weekday = datetime.now().strftime('%a')[:3]

    # Get today's classes taught by this teacher
    my_classes = Timetable.objects.filter(
        faculty_name__icontains=request.user.get_full_name() or request.user.username,
        day_of_week=today_weekday,
    ).order_by('time_slot')

    # Fallback: if no match by name, match by department
    if not my_classes.exists():
        my_classes = Timetable.objects.filter(
            department=request.user.department,
            day_of_week=today_weekday,
        ).order_by('time_slot')

    # Get cancellations for today
    cancellations = {
        c.timetable_id: c
        for c in ClassCancellation.objects.filter(
            timetable__in=my_classes, date=timezone.localdate(),
        )
    }

    return render(request, 'teachers/dashboard.html', {
        'my_classes': my_classes,
        'cancellations': cancellations,
        'today': today_weekday,
    })


@admin_required
def my_classes(request):
    """Full weekly schedule for the teacher."""
    if not _teacher_required(request.user):
        return redirect('dashboard:home_router')

    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    by_day = {}

    for day in days:
        slots = Timetable.objects.filter(
            faculty_name__icontains=request.user.get_full_name() or request.user.username,
            day_of_week=day,
        ).order_by('time_slot')

        if not slots.exists():
            slots = Timetable.objects.filter(
                department=request.user.department,
                day_of_week=day,
            ).order_by('time_slot')

        by_day[day] = list(slots)

    return render(request, 'teachers/my_classes.html', {
        'by_day': by_day,
        'days': days,
    })


@admin_required
def cancel_class(request, timetable_id):
    """Teacher cancels a class, optionally with a replacement slot."""
    if not _teacher_required(request.user):
        return redirect('dashboard:home_router')

    tt = get_object_or_404(Timetable, pk=timetable_id)

    if request.method == 'POST':
        date_str = request.POST.get('date') or timezone.localdate().isoformat()
        reason = request.POST.get('reason', '').strip()
        replacement = request.POST.get('replacement_slot', '').strip()

        ClassCancellation.objects.update_or_create(
            timetable=tt, date=date_str,
            defaults={
                'reason': reason,
                'replacement_slot': replacement,
                'announced_by': request.user,
            }
        )
        messages.success(request, f"Cancelled {tt.subject_name} on {date_str}.")
        return redirect('teachers:dashboard')

    return render(request, 'teachers/cancel_class.html', {
        'timetable': tt,
        'existing': ClassCancellation.objects.filter(timetable=tt).order_by('-date')[:10],
    })


@admin_required
def mark_attendance(request, timetable_id):
    """Mark attendance for a specific class."""
    if not _teacher_required(request.user):
        return redirect('dashboard:home_router')

    tt = get_object_or_404(Timetable, pk=timetable_id)

    # Find students in this department + batch
    students = User.objects.filter(
        role='student',
        department=tt.department,
        batch_year=tt.batch_year,
    ).order_by('username')

    if request.method == 'POST':
        date = request.POST.get('date') or timezone.localdate().isoformat()

        present_ids = set(request.POST.getlist('present'))

        # For each student, update or create AttendanceRecord for this subject
        for s in students:
            record, _ = AttendanceRecord.objects.get_or_create(
                student=s,
                subject_code=tt.subject_code,
                defaults={
                    'subject_name': tt.subject_name,
                    'total_classes': 0,
                    'attended_classes': 0,
                    'faculty_name': tt.faculty_name,
                }
            )
            record.total_classes += 1
            if str(s.id) in present_ids:
                record.attended_classes += 1
            record.save()

        messages.success(
            request,
            f"Attendance marked for {tt.subject_name} on {date}. "
            f"{len(present_ids)} present / {students.count()} total."
        )
        return redirect('teachers:dashboard')

    return render(request, 'teachers/mark_attendance.html', {
        'timetable': tt,
        'students': students,
        'today': timezone.localdate(),
    })


@admin_required
def my_students(request):
    """Students in the teacher's department."""
    if not _teacher_required(request.user):
        return redirect('dashboard:home_router')

    students = User.objects.filter(
        role='student',
        department=request.user.department,
    ).order_by('batch_year', 'username')

    return render(request, 'teachers/my_students.html', {'students': students})