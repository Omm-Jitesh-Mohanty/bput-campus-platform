from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.core.decorators import admin_required
from apps.core.permissions import require_perm, Perm
from apps.core.services import ConfigService
from .models import Notice, NoticeReadStatus
from .services import get_notices_for_student, mark_as_read
from apps.core.constants import BATCH_YEARS, HOSTEL_BLOCKS


@require_perm(Perm.VIEW_NOTICES)
def notice_list(request):
    from apps.core.scoping import DataScope
    from .relevance import annotate_notices_for_student

    qs = DataScope.notice_queryset(request.user)

    if request.user.is_student():
        from .services import get_notices_for_student
        raw = get_notices_for_student(request.user)
        notices = annotate_notices_for_student(raw, request.user)
    else:
        notices = [{'notice': n, 'priority': n.ai_priority, 'reasons': [], 'score': 100}
                   for n in qs.order_by('-created_at')]

    return render(request, 'notices/list.html', {'notices': notices})


@login_required
def notice_detail(request, pk):
    notice = get_object_or_404(Notice, pk=pk)

    # Mark as read if student
    if request.user.is_student():
        mark_as_read(notice, request.user)

    return render(request, 'notices/detail.html', {'notice': notice})


@admin_required
def publish_notice(request):
    """Admin: create a new notice."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        target_dept = request.POST.get('target_department', '').strip()
        target_batch = request.POST.get('target_batch', '').strip()
        target_hostel = request.POST.get('target_hostel', '').strip()

        if not title or not content:
            messages.error(request, "Title and content are required.")
        else:
            audience = {}

            if target_dept:
                audience['department'] = target_dept

            if target_batch:
                audience['batch_year'] = target_batch

            if target_hostel:
                audience['hostel_block'] = target_hostel

            notice = Notice.objects.create(
                title=title,
                content=content,
                target_audience=audience,
                posted_by=request.user,
            )

            from ai_engine.pipelines import process_new_notice

            process_new_notice(
                notice,
                language=request.user.language_pref or 'en',
                save=True
            )

            # Notify targeted students only
            from apps.accounts.models import User
            from apps.notifications.services import NotificationService

            targeted = User.objects.filter(
                role='student',
                is_active=True
            )

            aud = notice.target_audience or {}

            if aud.get('department'):
                targeted = targeted.filter(
                    department=aud['department']
                )

            if aud.get('batch_year'):
                targeted = targeted.filter(
                    batch_year=aud['batch_year']
                )

            if aud.get('hostel_block'):
                targeted = targeted.filter(
                    hostel_block=aud['hostel_block']
                )

            NotificationService.notify_notice_published(
                notice,
                list(targeted)
            )

            messages.success(
                request,
                f"Notice published (ID: {notice.id}) — AI tagged it as "
                f"{notice.get_ai_priority_display() if hasattr(notice, 'get_ai_priority_display') else notice.ai_priority}."
            )

            return redirect('notices:detail', pk=notice.id)

    from apps.core.constants import BATCH_YEARS, HOSTEL_BLOCKS

    return render(request, 'notices/publish.html', {
        'departments': ConfigService.department_choices(),
        'batch_years': BATCH_YEARS,
        'hostel_blocks': HOSTEL_BLOCKS,
    })