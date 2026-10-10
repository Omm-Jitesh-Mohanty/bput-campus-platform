"""
Build the FAISS vector store from all knowledge sources:
  1. Policy PDFs (corpus)
  2. Resolved tickets (as FAQ-like knowledge)
  3. Published notices
  4. Config (departments, SLAs, ticket types)
  5. Static FAQs

Run: python manage.py reindex_rag
"""
import logging
from pathlib import Path

from django.conf import settings

from .embeddings import embed_batch
from .splitter import split_text
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)

CORPUS_DIR = Path(settings.BASE_DIR) / 'ai_engine' / 'rag' / 'corpus' / 'generated'


def _chunk_and_embed(text, base_metadata, chunk_size=800, overlap=150):
    """Split text into chunks and embed each."""
    chunks = split_text(text, chunk_size=chunk_size, chunk_overlap=overlap,
                        metadata=base_metadata)
    if not chunks:
        return [], []

    texts = [c.text for c in chunks]
    embeddings = embed_batch(texts)
    return chunks, embeddings


def index_policies(vs):
    """Index all policy PDFs from the corpus folder."""
    from .corpus.loader import load_all_pdfs

    docs = load_all_pdfs(CORPUS_DIR)
    total = 0

    for doc in docs:
        base_meta = {
            'source': 'policy',
            'doc_name': doc['name'],
            'doc_title': doc['title'],
            'audience': 'both',
        }
        chunks, embeddings = _chunk_and_embed(doc['text'], base_meta, chunk_size=800)
        vs.add(chunks, embeddings)
        total += len(chunks)
        logger.info(f"Indexed policy {doc['name']}: {len(chunks)} chunks")

    return total


# def index_tickets(vs, limit=300):
#     """Index resolved tickets as knowledge."""
#     from apps.tickets.models import CampusTicket

#     qs = CampusTicket.objects.filter(
#         status='resolved', is_deleted=False,
#     ).exclude(resolution_note='')[:limit]

#     total = 0
#     for t in qs:
#         text = (
#             f"Ticket #{t.id}: {t.subject}\n"
#             f"Type: {t.get_ticket_type_display()}\n"
#             f"Department: {t.assigned_department}\n"
#             f"Student's description: {t.raw_input}\n"
#             f"Resolution: {t.resolution_note}\n"
#         )
#         base_meta = {
#             'source': 'ticket',
#             'ticket_id': t.id,
#             'ticket_type': t.ticket_type,
#             'department': t.assigned_department or '',
#             'audience': 'admin',
#             'title': f"Ticket: {t.subject[:80]}",
#         }
#         chunks, embeddings = _chunk_and_embed(text, base_meta, chunk_size=600, overlap=100)
#         vs.add(chunks, embeddings)
#         total += len(chunks)

#     return total

def index_tickets(vs, limit=300):
    """Index resolved tickets as knowledge."""
    from apps.tickets.models import CampusTicket

    qs = (
        CampusTicket.objects
        .filter(
            status='resolved',
            is_deleted=False,
        )
        .exclude(resolution_note='')
        .select_related('student', 'resolved_by', 'assigned_to')[:limit]
    )

    total = 0

    for t in qs:
        student_name = (
            t.student.get_full_name()
            or t.student.username
            or 'Student'
        )

        resolved_by = ''
        if t.resolved_by:
            resolved_by = (
                t.resolved_by.get_full_name()
                or t.resolved_by.username
                or ''
            )

        text = (
            f"Ticket #{t.id}: {t.subject}\n"
            f"Type: {t.ticket_type}\n"
            f"Department: {t.assigned_department}\n"
            f"Student: {student_name}\n"
            f"Student's description: {t.raw_input}\n"
            f"Formal request: {t.formatted_body}\n"
            f"Resolution: {t.resolution_note}\n"
            f"Resolved by: {resolved_by}\n"
        )

        base_meta = {
            'source': 'ticket',
            'ticket_id': t.id,
            'ticket_type': t.ticket_type,
            'department': t.assigned_department or '',
            'audience': 'admin',
            'title': f"Ticket: {t.subject[:80]}",
            'student_id': t.student_id,
            'student_username': t.student.username,
            'resolved_by_id': t.resolved_by_id,
        }

        chunks, embeddings = _chunk_and_embed(
            text,
            base_meta,
            chunk_size=600,
            overlap=100,
        )

        if not chunks:
            continue

        vs.add(chunks, embeddings)
        total += len(chunks)

    logger.info(
        "Indexed %s resolved tickets: %s chunks",
        len(qs),
        total,
    )

    return total


def index_notices(vs, limit=200):
    from apps.notices.models import Notice

    qs = Notice.objects.filter(is_published=True, is_deleted=False)[:limit]
    total = 0
    for n in qs:
        text = f"Notice: {n.title}\n\n{n.content}"
        base_meta = {
            'source': 'notice',
            'notice_id': n.id,
            'audience': 'student',
            'title': n.title,
        }
        chunks, embeddings = _chunk_and_embed(text, base_meta, chunk_size=600, overlap=100)
        vs.add(chunks, embeddings)
        total += len(chunks)

    return total


def index_config(vs):
    """Index config as admin knowledge."""
    from apps.core.models import Department, TicketType, SystemSetting

    total = 0
    for d in Department.objects.filter(is_active=True):
        text = (
            f"Department: {d.name} (code: {d.code})\n"
            f"Default SLA: {d.default_sla_hours} hours\n"
            f"Routing keywords: {', '.join(d.routing_keywords or [])}\n"
            f"Active: {d.is_active}\n"
        )
        base_meta = {
            'source': 'config',
            'config_type': 'department',
            'audience': 'admin',
            'title': f"Department: {d.name}",
        }
        chunks, embeddings = _chunk_and_embed(text, base_meta, chunk_size=400)
        vs.add(chunks, embeddings)
        total += len(chunks)

    for tt in TicketType.objects.filter(is_active=True):
        text = (
            f"Ticket type: {tt.name} (code: {tt.code})\n"
            f"Default department: {tt.default_department.name if tt.default_department else '—'}\n"
            f"SLA: {tt.sla_hours} hours\n"
        )
        base_meta = {
            'source': 'config',
            'config_type': 'ticket_type',
            'audience': 'admin',
            'title': f"Ticket type: {tt.name}",
        }
        chunks, embeddings = _chunk_and_embed(text, base_meta, chunk_size=400)
        vs.add(chunks, embeddings)
        total += len(chunks)

    for s in SystemSetting.objects.all():
        text = f"Setting: {s.key}\nValue: {s.value}\nDescription: {s.description}"
        base_meta = {
            'source': 'config',
            'config_type': 'setting',
            'audience': 'admin',
            'title': f"Setting: {s.key}",
        }
        chunks, embeddings = _chunk_and_embed(text, base_meta, chunk_size=400)
        vs.add(chunks, embeddings)
        total += len(chunks)

    return total


def index_faqs(vs):
    """Static FAQs — high-quality curated answers."""
    FAQS = [
        ('How do I apply for a bonafide certificate?',
         'Go to Documents → Request Document → select "Bonafide Certificate" → '
         'enter the purpose → submit. The AI will generate a signed PDF within '
         '3 seconds. You can download it from the Documents page.',
         'student'),
        ('How do I check my attendance?',
         'From the dashboard, click "Attendance". You will see subject-wise '
         'percentages with AI recovery plans for any subject below 75%. The '
         'recovery plan shows how many classes you must attend consecutively to '
         'reach the threshold.',
         'student'),
        ('What is the attendance requirement for exams?',
         'BPUT requires minimum 75% attendance in each subject for exam '
         'eligibility. Students with 65–75% may apply for condonation with a '
         'medical certificate. Below 65% requires Principal approval, which is '
         'rarely granted.',
         'student'),
        ('How do I file a complaint about hostel facilities?',
         'Go to Requests → New Request → choose Complaint → describe the issue '
         'in your own words. AI will route it to the correct maintenance '
         'department and track its resolution. You will be notified when it is '
         'resolved and can confirm.',
         'student'),
        ('How do I reach the warden urgently?',
         'Press the red SOS button in the navigation bar. It will alert your '
         'emergency contacts and the warden immediately. For non-emergencies, '
         'file a ticket via the Requests page.',
         'student'),
        ('What are the hostel timings?',
         'Main gate closes at 10:00 PM. Late entry requires prior written '
         'permission from the Warden submitted at least 4 hours in advance. '
         'Repeated violations are reported to the Chief Warden.',
         'student'),
        ('How do I add a new department?',
         'Go to Manage Panel → Departments → Add Department. Enter the code, '
         'name, SLA hours, and routing keywords. Save. The system will '
         'immediately route matching tickets to this department.',
         'admin'),
        ('How do I change the SLA for urgent complaints?',
         'Go to Manage Panel → SLA Policies → click the cell at the intersection '
         'of Complaint row and Urgent column → edit green/yellow/red hours → save. '
         'Changes take effect immediately without a restart.',
         'admin'),
        ('Where can I see which tickets are overdue?',
         'Open the admin dashboard and click the "Overdue" card in the Ageing '
         'Heatmap. Or go to Analytics → SLA Breach Risk for a predictive view.',
         'admin'),
        ('How do I approve a ticket?',
         'Open the ticket from your queue or click "My Approvals" in the navbar. '
         'If you are the current approver, you will see an "Action Required" '
         'banner with Approve/Reject options. AI will suggest a reply you can '
         'edit before submitting.',
         'admin'),
    ]

    total = 0
    for i, (q, a, aud) in enumerate(FAQS):
        text = f"Q: {q}\nA: {a}"
        base_meta = {
            'source': 'faq',
            'faq_index': i,
            'audience': aud,
            'title': q,
        }
        chunks, embeddings = _chunk_and_embed(text, base_meta, chunk_size=500)
        vs.add(chunks, embeddings)
        total += len(chunks)

    return total


def rebuild_all():
    """Wipe and rebuild the entire index."""
    vs = get_vector_store()
    vs.clear()

    stats = {
        'policies': index_policies(vs),
        'tickets': index_tickets(vs),
        'notices': index_notices(vs),
        'config': index_config(vs),
        'faqs': index_faqs(vs),
    }
    stats['total'] = sum(stats.values())

    vs.save()
    logger.info(f'Rebuilt RAG index: {stats}')
    return stats