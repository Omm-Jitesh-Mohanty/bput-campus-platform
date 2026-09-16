# from django.shortcuts import render

# Create your views here.
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render, redirect


# @login_required
# def student_home(request):
#     """Placeholder student dashboard — populated in Step 5."""
#     if request.user.is_admin_role():
#         return redirect('dashboard:admin_home')
#     return render(request, 'dashboard/student_home.html')


# @login_required
# def admin_home(request):
#     """Placeholder admin dashboard — populated in Step 5."""
#     if not request.user.is_admin_role():
#         return redirect('dashboard:student_home')
#     return render(request, 'dashboard/admin_home.html')

# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render, redirect
# from django.utils import timezone
# from django.db.models import Count

# from apps.attendance.services import get_student_attendance_summary
# from apps.tickets.models import CampusTicket
# from apps.notices.services import get_notices_for_student


# @login_required
# def student_home(request):
#     if request.user.is_admin_role():
#         return redirect('dashboard:admin_home')

#     user = request.user

#     # Attendance summary
#     attendance = get_student_attendance_summary(user)

#     # Recent tickets
#     recent_tickets = CampusTicket.objects.filter(student=user).order_by('-created_at')[:5]

#     # Tickets awaiting confirmation
#     awaiting = CampusTicket.objects.filter(
#         student=user, status='resolved', student_confirmed__isnull=True
#     )

#     # Recent notices
#     recent_notices = get_notices_for_student(user, limit=3)

#     # Fee status (if any)
#     fee_records = user.fee_records.all()
#     total_pending = sum(f.pending for f in fee_records)

#     return render(request, 'dashboard/student_home.html', {
#         'attendance': attendance,
#         'recent_tickets': recent_tickets,
#         'awaiting_confirmation': awaiting,
#         'recent_notices': recent_notices,
#         'fee_records': fee_records,
#         'total_pending': total_pending,
#     })


# @login_required
# def admin_home(request):
#     if not request.user.is_admin_role():
#         return redirect('dashboard:student_home')
#     return render(request, 'dashboard/admin_home.html')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.cache import cache

from apps.attendance.services import get_student_attendance_summary
from apps.tickets.models import CampusTicket
from apps.notices.services import get_notices_for_student

from . import services as dash


@login_required
def student_home(request):
    """Student dashboard (already built in Step 5 — unchanged)."""
    if request.user.is_admin_role():
        return redirect('dashboard:admin_home')

    user = request.user
    attendance = get_student_attendance_summary(user)
    recent_tickets = CampusTicket.objects.filter(student=user).order_by('-created_at')[:5]
    awaiting = CampusTicket.objects.filter(
        student=user, status='resolved', student_confirmed__isnull=True
    )
    recent_notices = get_notices_for_student(user, limit=3)
    fee_records = user.fee_records.all()
    total_pending = sum(f.pending for f in fee_records)

    return render(request, 'dashboard/student_home.html', {
        'attendance': attendance,
        'recent_tickets': recent_tickets,
        'awaiting_confirmation': awaiting,
        'recent_notices': recent_notices,
        'fee_records': fee_records,
        'total_pending': total_pending,
    })


@login_required
def admin_home(request):
    """Full admin dashboard with KPIs, heatmap, charts, and insights."""
    if not request.user.is_admin_role():
        return redirect('dashboard:student_home')

    # ---- KPI tiles ----
    kpis = dash.get_ticket_kpis()

    # ---- Department breakdown ----
    dept_breakdown = dash.get_department_breakdown()

    # ---- Ticket type pie ----
    type_breakdown = dash.get_type_breakdown()

    # ---- Ageing buckets ----
    ageing = dash.get_ageing_buckets()

    # ---- Resolution trend (14 days) ----
    resolution_trend = dash.get_resolution_trend(days=14)

    # ---- Recurring issues ----
    recurring = dash.get_recurring_issues(threshold=2)

    # ---- Notice reach ----
    notice_reach = dash.get_notice_reach(limit=5)

    # ---- Feedback summary (quantitative) ----
    feedback_summary = dash.get_feedback_summary()

    # ---- AI feedback insight (cached 10 minutes to avoid hammering Ollama on refresh) ----
    cache_key = 'feedback_ai_insight_v1'
    feedback_ai = cache.get(cache_key)
    if feedback_ai is None:
        from ai_engine.pipelines import analyze_feedback
        feedback_ai = analyze_feedback(limit=20)
        cache.set(cache_key, feedback_ai, timeout=600)

    # ---- Workload ----
    workload = dash.get_workload_distribution()

    # ---- Recent tickets (10 latest for the queue preview) ----
    recent_tickets = CampusTicket.objects.filter(is_deleted=False).order_by('-created_at')[:10]

    return render(request, 'dashboard/admin_home.html', {
        'kpis': kpis,
        'dept_breakdown': dept_breakdown,
        'type_breakdown': type_breakdown,
        'ageing': ageing,
        'resolution_trend': resolution_trend,
        'recurring': recurring,
        'notice_reach': notice_reach,
        'feedback_summary': feedback_summary,
        'feedback_ai': feedback_ai,
        'workload': workload,
        'recent_tickets': recent_tickets,
    })


@login_required
def refresh_feedback_ai(request):
    """Force regenerate the AI feedback insight (bypasses cache)."""
    if not request.user.is_admin_role():
        return redirect('dashboard:student_home')

    cache.delete('feedback_ai_insight_v1')
    return redirect('dashboard:admin_home')

@login_required
def ageing_detail(request, bucket):
    """Show all open tickets in a specific ageing bucket."""
    if not request.user.is_admin_role():
        return redirect('dashboard:student_home')

    if bucket not in ['fresh', 'warning', 'critical', 'overdue']:
        return redirect('dashboard:admin_home')

    buckets = dash.get_ageing_buckets()
    data = buckets.get(bucket, {'tickets': [], 'label': '', 'color': 'gray'})

    return render(request, 'dashboard/ageing_detail.html', {
        'bucket_key': bucket,
        'bucket_label': data['label'],
        'bucket_color': data['color'],
        'tickets': data['tickets'],
    })