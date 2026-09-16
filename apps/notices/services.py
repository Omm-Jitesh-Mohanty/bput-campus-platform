"""Notice helpers."""
from apps.accounts.models import User
from .models import Notice, NoticeReadStatus


def get_notices_for_student(student, limit=None):
    """Return notices targeting this student (department/batch/hostel filters)."""
    qs = Notice.objects.filter(is_published=True).order_by('-created_at')
    matching = []
    for notice in qs:
        aud = notice.target_audience or {}
        if aud.get('department') and aud['department'] != student.department:
            continue
        if aud.get('batch_year') and aud['batch_year'] != student.batch_year:
            continue
        if aud.get('hostel_block') and aud['hostel_block'] != student.hostel_block:
            continue
        matching.append(notice)
        if limit and len(matching) >= limit:
            break
    return matching


def mark_as_read(notice, student):
    obj, created = NoticeReadStatus.objects.get_or_create(
        notice=notice, student=student
    )
    return obj, created