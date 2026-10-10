from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ClassCancellation, StudentRoutine


@receiver(post_save, sender=ClassCancellation)
def recompute_affected_routines(sender, instance, created, **kwargs):
    """When a class is cancelled, mark all affected students' routines for recompute."""
    if not created:
        return

    from apps.accounts.models import User
    affected_students = User.objects.filter(
        role='student',
        department=instance.timetable.department,
        batch_year=instance.timetable.batch_year,
    )

    # Invalidate cached plans
    StudentRoutine.objects.filter(student__in=affected_students).update(
        last_computed=None
    )

    # Notify students
    from apps.notifications.services import NotificationService
    for s in affected_students[:200]:  # cap for safety
        NotificationService.notify(
            recipient=s,
            event_code='class.cancelled',
            context={
                'subject': instance.timetable.subject_name,
                'time': instance.timetable.time_slot,
                'reason': instance.reason or 'Cancelled',
            },
            link_url='/attendance/today/',
            priority='high',
            target=instance.timetable,
        )