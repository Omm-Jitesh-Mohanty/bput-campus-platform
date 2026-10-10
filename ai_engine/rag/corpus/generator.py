"""
Generate realistic policy PDFs for the RAG corpus.

These mirror real documents a college would have. In production, you'd
upload the actual rulebook PDFs. For the hackathon, we generate them.
"""
import logging
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
)

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / 'generated'


# =====================================================================
# Document definitions
# =====================================================================
POLICIES = {
    'hostel_rules': {
        'title': 'BPUT Hostel Rules & Regulations',
        'sections': [
            ('1. Introduction',
             'These rules apply to all students residing in the hostels of Biju Patnaik '
             'University of Technology and its affiliated colleges. Every resident is '
             'expected to abide by these rules. Violation may attract disciplinary action '
             'including expulsion from the hostel and imposition of fines.'),
            ('2. Timings and Gate Curfew',
             'The main gate of every hostel closes at 10:00 PM. Late entry after 10:00 PM '
             'requires written permission from the Warden, submitted at least 4 hours in '
             'advance. Repeated late entries without approval will be recorded and reported '
             'to the Chief Warden and the Dean of Student Welfare.'),
            ('3. Leave and Absence',
             'Students must inform the Warden before leaving the hostel for more than 24 hours. '
             'Leave requests for up to 3 days are approved by the Warden. Leave of 4 to 10 days '
             'requires HOD approval in addition to Warden. Leave exceeding 10 days requires the '
             'Dean of Student Welfare to sign off. Medical emergencies are exempted from prior '
             'approval but must be reported within 24 hours.'),
            ('4. Visitors',
             'Visitors are allowed in the common area only, between 4:00 PM and 7:00 PM. '
             'No visitors are allowed in residential rooms. Family members may visit with prior '
             'intimation to the Warden. Overnight stays require the Chief Warden\'s written approval.'),
            ('5. Anti-Ragging',
             'Ragging in any form is strictly prohibited. Any student found guilty will be '
             'immediately suspended and a case registered under the UGC Anti-Ragging Regulations 2009. '
             'Students may report incidents to the Anti-Ragging Helpline (1800-180-5522) anonymously.'),
            ('6. Electricity and Water',
             'Do not use personal high-wattage electrical appliances (heaters, induction cooktops) '
             'in rooms. Restricted appliances will be confiscated. Water conservation is mandatory; '
             'report leaks to the Warden immediately. Non-reporting after knowledge of a leak may '
             'attract fines.'),
            ('7. Maintenance Complaints',
             'Complaints about room fixtures, electrical items, plumbing, or furniture must be '
             'submitted through the campus portal. Emergency issues (sparking, flooding, fire) '
             'must be reported to the Warden by phone immediately, then logged in the portal.'),
            ('8. Mess Rules',
             'Mess timings: Breakfast 7:30–9:00 AM, Lunch 12:30–2:00 PM, Evening snacks 5:00–6:00 PM, '
             'Dinner 8:00–9:30 PM. Feedback on food quality may be submitted anonymously through the portal. '
             'Repeated complaints from more than 5 students in a week trigger a formal review by the Mess Committee.'),
        ],
    },

    'fee_policy': {
        'title': 'BPUT Fee Payment, Refund, and Scholarship Policy',
        'sections': [
            ('1. Fee Structure',
             'Semester fees include Tuition, Development, Library, Laboratory, Sports, and Examination '
             'charges. The total fee for the 2025-26 academic year is ₹45,000 for B.Tech programs. '
             'Fees must be paid by the notified deadline.'),
            ('2. Payment Deadlines',
             'Semester fees are due within 15 days of the start of each semester. Late payment '
             'incurs a penalty of ₹500 per week up to a maximum of ₹2,000. Students who fail to '
             'pay by the 30th day will not be permitted to appear for examinations.'),
            ('3. Refund Policy',
             'Full refund: if withdrawal before the start of classes. 80% refund: within 15 days of '
             'class commencement. 50% refund: 16 to 30 days. No refund: after 30 days. Refunds are '
             'processed by the Accounts Office within 45 days of an approved application.'),
            ('4. Scholarships',
             'Merit scholarships cover 50–100% of tuition for students with CGPA ≥ 8.5. SC/ST/OBC '
             'scholarships are processed through the state portal. Need-based scholarships require '
             'income certificate and are renewed annually.'),
            ('5. Fee Waiver for Emergencies',
             'Students facing genuine financial hardship may apply for a partial waiver. Applications '
             'require documentation and are reviewed by a committee comprising the Dean, AO, and HOD. '
             'Waivers are capped at 50% of the semester fee.'),
            ('6. Pending Dues and Certificates',
             'Bonafide, migration, and character certificates will not be issued if fee dues are pending. '
             'Transcripts may be issued with a "dues pending" annotation.'),
        ],
    },

    'exam_rules': {
        'title': 'BPUT Examination Guidelines',
        'sections': [
            ('1. Eligibility',
             'Students must have a minimum 75% attendance in each subject to be eligible for the '
             'end-semester examination. Students with 65–75% may apply for condonation with medical '
             'certificate. Below 65% requires the Principal\'s special approval; typically denied except '
             'in extraordinary circumstances.'),
            ('2. Hall Tickets',
             'Hall tickets are available on the student portal 10 days before the exam. Students must '
             'verify their name, roll number, and subjects. Discrepancies must be reported to the Exam Cell '
             'within 3 days.'),
            ('3. Exam Pattern',
             'Mid-semester exams: 30 marks (20 internal + 10 quiz). End-semester exams: 70 marks. '
             'Practical exams are conducted separately. Pass criteria: minimum 40% in each component '
             'with an aggregate of 50%.'),
            ('4. Malpractice',
             'Use of unfair means during exams results in immediate invalidation of the paper and '
             'suspension of the student for the current semester. Repeat offenses may lead to a 1-year ban.'),
            ('5. Re-evaluation',
             'Students may apply for re-evaluation within 15 days of result declaration, with a fee of '
             '₹500 per subject. Re-evaluation is limited to theory papers. Re-checking of totals is free '
             'and available within 7 days of result declaration.'),
            ('6. Backlogs',
             'Students with backlogs must clear them within the stipulated duration (typically 2 years). '
             'Special supplementary exams are conducted every semester. Grade improvement is allowed once.'),
        ],
    },

    'anti_ragging': {
        'title': 'BPUT Anti-Ragging Policy (UGC Compliant)',
        'sections': [
            ('1. Definition',
             'Ragging includes any conduct by a student, whether by words spoken or written, or by an '
             'act, that has the effect of teasing, treating, or handling with rudeness any other student, '
             'indulging in rowdy or undisciplined activities, or asking a student to do something that '
             'causes shame, annoyance, or psychological harm.'),
            ('2. Zero Tolerance',
             'BPUT follows a strict zero-tolerance policy. Any incident, however minor, will be treated '
             'as a serious offense.'),
            ('3. Reporting Channels',
             'Students may report ragging through: (a) the online portal form, (b) the Anti-Ragging Helpline '
             '1800-180-5522, (c) the Warden, HOD, or Dean directly, (d) the National Anti-Ragging Portal '
             'antiragging.in. All reports are confidential.'),
            ('4. Penalties',
             'First offense: suspension for one semester and a fine of ₹25,000. Second offense: suspension '
             'for one year and entry in the character certificate. Severe offenses: expulsion and FIR under '
             'IPC Section 506 (criminal intimidation).'),
            ('5. Committees',
             'Every college has an Anti-Ragging Committee chaired by the Principal and an Anti-Ragging Squad '
             'for surprise checks. Contact details are published on notice boards and the portal.'),
            ('6. Support for Victims',
             'Victims are offered free counseling, academic support, and assistance in pursuing legal action. '
             'No academic penalty is imposed on victims for absence during the reporting period.'),
        ],
    },

    'leave_gatepass': {
        'title': 'BPUT Leave and Gate Pass Regulations',
        'sections': [
            ('1. Leave Categories',
             'Casual Leave (CL): up to 3 days per month. Medical Leave (ML): based on doctor\'s certificate. '
             'Emergency Leave (EL): for family emergencies, granted retroactively if reported within 24 hours. '
             'Event Leave (EV): for competitions, workshops, and conferences, requires faculty recommendation.'),
            ('2. Application Process',
             'All leave requests must be submitted through the campus portal at least 24 hours in advance, '
             'except emergency cases. The application must state the reason, dates, and contact details.'),
            ('3. Approval Hierarchy',
             'Up to 3 days: Warden approval. 4 to 10 days: Warden + HOD. 11 to 20 days: Warden + HOD + Dean. '
             'Beyond 20 days: Principal approval with documented reason.'),
            ('4. Gate Pass',
             'Daily gate pass for leaving campus and returning the same day: Warden approval sufficient. '
             'Overnight gate pass: same as leave approval. Gate passes must be carried physically or shown '
             'digitally at the gate.'),
            ('5. Emergency Procedures',
             'Medical emergencies do not require prior approval. Notify the Warden by phone immediately. '
             'Submit the application within 24 hours of return.'),
            ('6. Non-Compliance',
             'Absence without approved leave is marked as unauthorized. Repeat offenses attract fines and '
             'may affect the character certificate.'),
        ],
    },

    'complaint_handling': {
        'title': 'BPUT Grievance Redressal Policy',
        'sections': [
            ('1. Scope',
             'This policy covers all student complaints relating to academic matters, hostel facilities, '
             'mess quality, administrative services, and interpersonal issues.'),
            ('2. Complaint Categories and Routing',
             'Facility complaints (electrical, plumbing, civil, wifi): routed to the Maintenance Department. '
             'Mess or food-related: routed to the Mess Committee. Academic grievances: routed to the HOD. '
             'Fee or accounts issues: routed to the AO. Behavioral complaints: routed to the Dean of Student Welfare. '
             'Any complaint involving safety (fire, electrical shock, structural): routed simultaneously to '
             'Warden, Chief Warden, and Principal.'),
            ('3. Resolution Timelines',
             'Standard SLA: Fresh complaints 48 hours to first action, 7 days to resolution. Escalation: if no '
             'action in 48 hours, automatic escalation to HOD. If no resolution in 7 days, escalation to Dean.'),
            ('4. Reopening',
             'If a student is not satisfied with the resolution, the complaint can be reopened once. Reopened '
             'complaints are treated with higher priority and automatically reviewed by a senior authority.'),
            ('5. Recurring Issues',
             'If 3 or more complaints of the same category are received for the same location or department '
             'within 14 days, the system flags it as a recurring issue and alerts the HOD and Dean.'),
            ('6. Anonymous Complaints',
             'Students may submit complaints anonymously, but only for safety and behavioral categories. '
             'Anonymous complaints are still acted upon and tracked.'),
        ],
    },
}


def build_pdf(doc_key, title, sections, output_path):
    """Render a PDF from sections."""
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=18,
                        alignment=TA_CENTER, spaceAfter=20)
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13,
                        spaceAfter=8, spaceBefore=14)
    body = ParagraphStyle('Body', parent=styles['BodyText'], fontSize=11,
                          alignment=TA_JUSTIFY, leading=16)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=title, author='BPUT Campus Platform',
    )

    story = [
        Paragraph(title, h1),
        Spacer(1, 6),
    ]

    for heading, content in sections:
        story.append(Paragraph(heading, h2))
        story.append(Paragraph(content, body))
        story.append(Spacer(1, 8))

    doc.build(story)


def generate_all():
    """Generate all policy PDFs into the generated/ folder."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = []
    for key, data in POLICIES.items():
        path = OUTPUT_DIR / f'{key}.pdf'
        build_pdf(key, data['title'], data['sections'], path)
        generated.append(str(path))
        logger.info(f'Generated: {path}')
    return generated


if __name__ == '__main__':
    generate_all()