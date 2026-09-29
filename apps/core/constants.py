"""
Shared constants across all apps.
Single source of truth — never hardcode these elsewhere.
"""
"""
⚠️  DEPRECATED — Read from ConfigService instead.

This module now serves two purposes:
  1. As a fallback if the DB config tables are empty (e.g., fresh install)
  2. As a reference for the initial seed data

New code should NOT import from here. Use:

    from apps.core.services import ConfigService

    departments = ConfigService.departments()
    priorities = ConfigService.priority_levels()
    sla = ConfigService.sla_hours_for('complaint', 'urgent')
    threshold = ConfigService.get_attendance_threshold()

If you find yourself importing from constants in new code, pause and
ask: "Can ConfigService provide this?" Almost always, yes.

Existing imports are being migrated gradually. Everything works
either way — no breaking changes.
"""

# ===== Departments =====
DEPARTMENTS = [
    ('CSE', 'Computer Science & Engineering'),
    ('IT', 'Information Technology'),
    ('ECE', 'Electronics & Communication'),
    ('EEE', 'Electrical & Electronics'),
    ('MECH', 'Mechanical Engineering'),
    ('CIVIL', 'Civil Engineering'),
    ('ADMIN', 'Administration'),
    ('GEN', 'General'),
]

DEPARTMENT_CODES = [code for code, _ in DEPARTMENTS]

# ===== Batch Years =====
BATCH_YEARS = [
    ('2022', '2022 Batch'),
    ('2023', '2023 Batch'),
    ('2024', '2024 Batch'),
    ('2025', '2025 Batch'),
    ('2026', '2026 Batch'),
]

# ===== Hostel Blocks =====
HOSTEL_BLOCKS = [
    ('A', 'Block A'),
    ('B', 'Block B'),
    ('C', 'Block C'),
    ('D', 'Block D'),
    ('DAY', 'Day Scholar'),
]

# ===== User Roles =====
ROLE_STUDENT = 'student'
ROLE_TEACHER = 'teacher'
ROLE_WARDEN = 'warden'
ROLE_HOD = 'hod'
ROLE_DEAN = 'dean'
ROLE_PRINCIPAL = 'principal'

ROLE_CHOICES = [
    (ROLE_STUDENT, 'Student'),
    (ROLE_TEACHER, 'Teacher'),
    (ROLE_WARDEN, 'Warden'),
    (ROLE_HOD, 'HOD'),
    (ROLE_DEAN, 'Dean'),
    (ROLE_PRINCIPAL, 'Principal'),
]

ADMIN_ROLES = [ROLE_TEACHER, ROLE_WARDEN, ROLE_HOD, ROLE_DEAN, ROLE_PRINCIPAL]

# ===== Ticket Configuration =====
TICKET_TYPE_LEAVE = 'leave'
TICKET_TYPE_GATEPASS = 'gatepass'
TICKET_TYPE_DOCUMENT = 'document'
TICKET_TYPE_COMPLAINT = 'complaint'

TICKET_TYPE_CHOICES = [
    (TICKET_TYPE_LEAVE, 'Leave Request'),
    (TICKET_TYPE_GATEPASS, 'Gate Pass'),
    (TICKET_TYPE_DOCUMENT, 'Document / Certificate'),
    (TICKET_TYPE_COMPLAINT, 'Complaint'),
]

TICKET_STATUS_PENDING = 'pending'
TICKET_STATUS_IN_PROGRESS = 'in_progress'
TICKET_STATUS_RESOLVED = 'resolved'
TICKET_STATUS_REOPENED = 'reopened'
TICKET_STATUS_REJECTED = 'rejected'

TICKET_STATUS_CHOICES = [
    (TICKET_STATUS_PENDING, 'Pending'),
    (TICKET_STATUS_IN_PROGRESS, 'In Progress'),
    (TICKET_STATUS_RESOLVED, 'Resolved'),
    (TICKET_STATUS_REOPENED, 'Reopened'),
    (TICKET_STATUS_REJECTED, 'Rejected'),
]

# ===== Priority =====
PRIORITY_LOW = 'low'
PRIORITY_MEDIUM = 'medium'
PRIORITY_HIGH = 'high'
PRIORITY_URGENT = 'urgent'

PRIORITY_CHOICES = [
    (PRIORITY_LOW, 'Low'),
    (PRIORITY_MEDIUM, 'Medium'),
    (PRIORITY_HIGH, 'High'),
    (PRIORITY_URGENT, 'Urgent'),
]

# ===== Departments for ticket routing =====
ROUTING_DEPARTMENTS = [
    ('plumbing', 'Plumbing'),
    ('electrical', 'Electrical'),
    ('civil', 'Civil / Furniture'),
    ('mess', 'Mess / Kitchen'),
    ('housekeeping', 'Housekeeping'),
    ('it', 'IT / Network'),
    ('academic', 'Academic Office'),
    ('hostel', 'Hostel Administration'),
    ('accounts', 'Accounts / Fees'),
    ('general', 'General'),
]

# ===== Ageing Thresholds (hours) =====
AGEING_GREEN_HOURS = 24
AGEING_YELLOW_HOURS = 48

# ===== Feedback Categories =====
FEEDBACK_CATEGORIES = [
    ('mess', 'Mess / Food Quality'),
    ('water', 'Water Quality'),
    ('hygiene', 'Hygiene / Cleanliness'),
    ('hostel', 'Hostel Facility'),
    ('academic', 'Academics'),
    ('infra', 'Infrastructure'),
]

# ===== Notice Priority =====
NOTICE_PRIORITY_LOW = 'low'
NOTICE_PRIORITY_MEDIUM = 'medium'
NOTICE_PRIORITY_HIGH = 'high'

# ===== Document Types =====
DOCUMENT_TYPES = [
    ('bonafide', 'Bonafide Certificate'),
    ('transcript', 'Transcript'),
    ('fee_receipt', 'Fee Receipt'),
    ('character', 'Character Certificate'),
    ('migration', 'Migration Certificate'),
    ('noc', 'No Objection Certificate'),
    ('other', 'Other'),
]

# ===== Days of Week (for timetable) =====
DAYS_OF_WEEK = [
    ('Mon', 'Monday'),
    ('Tue', 'Tuesday'),
    ('Wed', 'Wednesday'),
    ('Thu', 'Thursday'),
    ('Fri', 'Friday'),
    ('Sat', 'Saturday'),
]

# ===== Attendance threshold =====
ATTENDANCE_THRESHOLD_PCT = 75.0

# ===== Feedback rating labels =====
RATING_LABELS = {
    1: 'Very Poor',
    2: 'Poor',
    3: 'Average',
    4: 'Good',
    5: 'Excellent',
}

# ===== Leave types (for leave tickets) =====
LEAVE_TYPES = [
    ('sick', 'Sick Leave'),
    ('casual', 'Casual Leave'),
    ('emergency', 'Emergency Leave'),
    ('event', 'Event / Competition'),
    ('other', 'Other'),
]

# =====================================================================
# DEPRECATION TRACKER
# =====================================================================
# The following constants have been migrated to DB config and should NOT
# be used in new code. They remain here only as fallbacks.
#
#   DEPARTMENTS               → ConfigService.departments()
#   ROUTING_DEPARTMENTS       → ConfigService.departments()
#   PRIORITY_CHOICES          → ConfigService.priority_levels()
#   TICKET_TYPE_CHOICES       → ConfigService.ticket_types()
#   AGEING_GREEN_HOURS        → ConfigService.sla_hours_for(...)['green']
#   AGEING_YELLOW_HOURS       → ConfigService.sla_hours_for(...)['yellow']
#   ATTENDANCE_THRESHOLD_PCT  → ConfigService.get_attendance_threshold()
#
# Structural constants still in active use:
#   TICKET_STATUS_*           (state machine, not config)
#   TICKET_TYPE_COMPLAINT etc (slugs, referenced by code)
#   BATCH_YEARS, HOSTEL_BLOCKS (academic structure, not runtime config)
# =====================================================================
