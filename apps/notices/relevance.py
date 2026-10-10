"""
Compute a personalized priority for each student per notice.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def classify_notice_tags(content):
    """Extract relevance tags from notice content."""
    text = content.lower()
    return {
        'relevant_to_attendance': any(k in text for k in [
            'attendance', 'class cancelled', 'lecture', 'recovery', '75%'
        ]),
        'relevant_to_fees': any(k in text for k in [
            'fee', 'dues', 'payment', 'scholarship', 'refund', 'challan'
        ]),
        'relevant_to_exams': any(k in text for k in [
            'exam', 'mid-sem', 'semester', 'hall ticket', 'result', 'marksheet'
        ]),
        'relevant_to_hostel': any(k in text for k in [
            'hostel', 'mess', 'room', 'block', 'water supply', 'warden'
        ]),
        'relevant_to_placement': any(k in text for k in [
            'placement', 'internship', 'company', 'job', 'recruit', 'campus drive'
        ]),
    }


def personalized_priority(notice, student):
    """
    Return (priority_str, reasons:list, score:int)
    for this student. Considers:
      - Base AI priority
      - Tags matching student's context
      - Attendance/fee state of student
      - Department/batch targeting
      - Expiry
    """
    reasons = []
    score = 0

    base = notice.ai_priority or 'low'
    base_scores = {'low': 10, 'medium': 30, 'high': 60, 'critical': 90}
    score = base_scores.get(base, 10)

    # Expired → lower
    if notice.expires_at and notice.expires_at < timezone.now():
        score -= 30
        reasons.append('Expired')

    # Attendance-related and student is below threshold
    if notice.relevant_to_attendance:
        from apps.attendance.services import get_student_attendance_summary
        summary = get_student_attendance_summary(student)
        if summary['overall_percentage'] < 75:
            score += 25
            reasons.append('Your attendance is below 75%')

    # Fee-related and student has dues
    if notice.relevant_to_fees:
        pending = sum(f.pending for f in student.fee_records.all())
        if pending > 0:
            score += 25
            reasons.append(f'You have ₹{pending} pending fees')

    # Exam-related → always elevate
    if notice.relevant_to_exams:
        score += 15
        reasons.append('Exam-related notice')

    # Hostel-related and student lives in hostel
    if notice.relevant_to_hostel and student.hostel_block and student.hostel_block != 'DAY':
        score += 10
        reasons.append(f'Affects your hostel ({student.hostel_block} Block)')

    # Placement for final-year students
    if notice.relevant_to_placement and student.batch_year in ('2023', '2024'):
        score += 15
        reasons.append('Relevant to your batch')

    # Department targeting
    aud = notice.target_audience or {}
    if aud.get('department') and aud['department'] != student.department:
        score -= 40
        reasons.append('Not targeted to your department')
    if aud.get('batch_year') and aud['batch_year'] != student.batch_year:
        score -= 30
        reasons.append('Not targeted to your batch')

    # Map score back to priority
    if score >= 80:
        priority = 'critical'
    elif score >= 50:
        priority = 'high'
    elif score >= 25:
        priority = 'medium'
    else:
        priority = 'low'

    return priority, reasons, score


def annotate_notices_for_student(notices, student):
    """Enhance a list of notices with per-student priority + reasons."""
    result = []
    for n in notices:
        p, reasons, score = personalized_priority(n, student)
        result.append({
            'notice': n,
            'priority': p,
            'reasons': reasons,
            'score': score,
        })
    result.sort(key=lambda x: x['score'], reverse=True)
    return result