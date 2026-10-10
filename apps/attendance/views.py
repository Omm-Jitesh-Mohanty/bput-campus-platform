# from django.shortcuts import render

# Create your views here.


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime

from apps.core.decorators import student_required
from .models import AttendanceRecord, Timetable, ClassCancellation
from .services import get_student_attendance_summary
from .routine import compute_daily_plan


@login_required
def attendance_view(request):
    """Student's subject-wise attendance + recovery plans."""
    if not request.user.is_student():
        return render(request, 'attendance/not_student.html')

    records = AttendanceRecord.objects.filter(student=request.user)
    summary = get_student_attendance_summary(request.user)

    # Compute recovery plan per subject
    from .services import recovery_plan
    detailed = []
    for r in records:
        plan = recovery_plan(r.attended_classes, r.total_classes)
        detailed.append({
            'record': r,
            'plan': plan,
        })

    return render(request, 'attendance/list.html', {
        'detailed': detailed,
        'summary': summary,
    })


@login_required
def timetable_view(request):
    """Weekly timetable for student's department + batch."""
    if not request.user.is_student():
        return render(request, 'attendance/not_student.html')

    # Group by day
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    timetable_by_day = {}

    for day in days:
        slots = Timetable.objects.filter(
            department=request.user.department,
            batch_year=request.user.batch_year,
            day_of_week=day,
        ).order_by('time_slot')

        # Check for today's cancellations
        today = timezone.localdate()
        if day == datetime.now().strftime('%a')[:3]:
            cancelled_today = ClassCancellation.objects.filter(
                timetable__in=slots, date=today
            ).values_list('timetable_id', flat=True)
        else:
            cancelled_today = []

        timetable_by_day[day] = {
            'slots': slots,
            'cancelled_ids': list(cancelled_today),
        }

    return render(request, 'attendance/timetable.html', {
        'timetable_by_day': timetable_by_day,
        'days': days,
        'today_code': datetime.now().strftime('%a')[:3],
    })


@login_required
def today_plan(request):
    """Personalized daily plan for the current student."""
    if not request.user.is_student():
        return redirect('dashboard:admin_home')

    plan = compute_daily_plan(request.user)
    return render(request, 'attendance/today_plan.html', {'plan': plan})


@login_required
def today_plan_json(request):
    """JSON version for the dashboard widget."""
    if not request.user.is_student():
        return JsonResponse({'error': 'Students only'}, status=403)

    plan = compute_daily_plan(request.user)
    return JsonResponse(plan)