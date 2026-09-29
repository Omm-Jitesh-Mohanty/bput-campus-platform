"""
Attendance recovery logic — pure math, no AI yet.
AI layer will wrap this in ai_engine/.
"""


def compute_attendance_percentage(attended, total):
    if total <= 0:
        return 0.0
    return round((attended / total) * 100, 2)


def recovery_plan(attended, total, target_pct=None):
    """
    How many consecutive classes must the student attend to hit target_pct?
    Target reads from SystemSetting 'attendance.threshold_pct' if not provided.
    """
    if target_pct is None:
        from apps.core.services import ConfigService
        target_pct = ConfigService.get_attendance_threshold()

    current = compute_attendance_percentage(attended, total)
    if current >= target_pct:
        return {
            'needed': 0,
            'current': current,
            'target': target_pct,
            'message': f"On track — currently at {current}%.",
        }

    if target_pct >= 100:
        return {'needed': None, 'current': current, 'target': target_pct,
                'message': "Target of 100% requires perfect attendance going forward."}

    numerator = target_pct * total - 100 * attended
    denominator = 100 - target_pct
    needed = max(0, int(numerator / denominator) + 1)

    return {
        'needed': needed,
        'current': current,
        'target': target_pct,
        'message': f"Attend the next {needed} classes consecutively to reach {target_pct:.0f}%.",
    }


def get_student_attendance_summary(student):
    """Return per-subject attendance + overall percentage."""
    from .models import AttendanceRecord
    from apps.core.services import ConfigService

    records = AttendanceRecord.objects.filter(student=student)
    total_attended = sum(r.attended_classes for r in records)
    total_held = sum(r.total_classes for r in records)
    overall = compute_attendance_percentage(total_attended, total_held)
    return {
        'records': list(records),
        'overall_percentage': overall,
        'total_attended': total_attended,
        'total_held': total_held,
        'is_safe': overall >= ConfigService.get_attendance_threshold(),
    }