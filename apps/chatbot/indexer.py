"""
Build/refresh the knowledge index from various sources.
"""
import logging

from .models import KnowledgeChunk
from .embeddings import embed_text

logger = logging.getLogger(__name__)


def _add_chunk(source_type, audience, title, content, source_id='', metadata=None):
    """Embed and store one chunk (deduped by source_id+source_type)."""
    if source_id:
        existing = KnowledgeChunk.objects.filter(
            source_type=source_type, source_id=source_id
        ).first()
        if existing:
            return existing

    emb, model = embed_text(content)
    return KnowledgeChunk.objects.create(
        source_type=source_type,
        audience=audience,
        source_id=str(source_id),
        title=title[:300],
        content=content,
        metadata=metadata or {},
        embedding=emb,
        embedding_model=model,
    )


def index_tickets():
    """Index resolved tickets as FAQ-like knowledge."""
    from apps.tickets.models import CampusTicket

    qs = CampusTicket.objects.filter(
        status='resolved',
        is_deleted=False,
    ).exclude(
        resolution_note=''
    )[:500]

    count = 0

    for t in qs:
        ticket_type = getattr(t, 'ticket_type', None)

        if ticket_type:
            if hasattr(ticket_type, 'name'):
                ticket_type_name = ticket_type.name
            else:
                ticket_type_name = str(ticket_type)
        else:
            ticket_type_name = 'General'

        content = (
            f"Ticket: {t.subject}\n"
            f"Type: {ticket_type_name}\n"
            f"Department: {t.assigned_department}\n"
            f"Student's description: {t.raw_input}\n"
            f"Resolution: {t.resolution_note}\n"
        )

        _add_chunk(
            'ticket',
            'admin',
            f"Resolution: {t.subject}",
            content,
            source_id=f'ticket_{t.id}',
        )
        count += 1

    logger.info(f'Indexed {count} tickets')
    return count


def index_notices():
    """Index published notices."""
    from apps.notices.models import Notice
    qs = Notice.objects.filter(is_published=True)[:200]

    count = 0
    for n in qs:
        content = f"Notice: {n.title}\n\n{n.content}"
        if _add_chunk('notice', 'student', n.title, content,
                     source_id=f'notice_{n.id}'):
            count += 1
    return count


def index_config():
    """Index config as admin knowledge."""
    from apps.core.models import Department, TicketType, SLAPolicy, SystemSetting

    count = 0
    for d in Department.objects.filter(is_active=True):
        content = (
            f"Department: {d.name} (code: {d.code})\n"
            f"SLA: {d.default_sla_hours} hours\n"
            f"Keywords: {', '.join(d.routing_keywords or [])}\n"
        )
        if _add_chunk('config', 'admin', f'Department {d.name}',
                     content, source_id=f'dept_{d.id}'):
            count += 1

    for tt in TicketType.objects.filter(is_active=True):
        content = (
            f"Ticket type: {tt.name} (code: {tt.code})\n"
            f"Default department: {tt.default_department.name if tt.default_department else '—'}\n"
            f"SLA: {tt.sla_hours} hours\n"
        )
        if _add_chunk('config', 'admin', f'TicketType {tt.name}',
                     content, source_id=f'tt_{tt.id}'):
            count += 1

    for s in SystemSetting.objects.all():
        content = f"Setting {s.key} = {s.value} ({s.description})"
        if _add_chunk('config', 'admin', s.key, content, source_id=f'set_{s.id}'):
            count += 1

    return count


def index_faqs():
    """Seed static FAQs."""
    FAQS = [
        ('How do I apply for a bonafide certificate?',
         'Go to Documents → Request Document → select "Bonafide Certificate" → enter purpose → submit. AI will generate a signed PDF within 3 seconds.',
         'both'),
        ('How do I check my attendance?',
         'From the dashboard, click "Attendance". You will see subject-wise percentages with AI recovery plans for any subject below 75%.',
         'student'),
        ('When does the fee payment deadline fall?',
         'Check the Notice board for the latest fee notices. The AI highlights fee-related notices for you if you have pending dues.',
         'student'),
        ('How do I contact my warden?',
         'Open the Emergency SOS screen (red button) or find the warden\'s contact in the "Hostel" tab of your dashboard.',
         'student'),
        ('How do I add a new department?',
         'Go to Manage Panel → Departments → Add Department. Enter code, name, SLA, and routing keywords. Save.',
         'admin'),
        ('How do I change the SLA for urgent complaints?',
         'Go to Manage Panel → SLA Policies → click the cell for (complaint, urgent) → edit green/yellow/red hours.',
         'admin'),
        ('How can I see which tickets are overdue?',
         'Open the admin dashboard and click "Overdue" on the ageing heatmap. Or use the Analytics page for the full picture.',
         'admin'),
    ]

    count = 0
    for i, (q, a, aud) in enumerate(FAQS):
        content = f"Q: {q}\nA: {a}"
        if _add_chunk('faq', aud, q, content, source_id=f'faq_{i}'):
            count += 1
    return count


def rebuild_all():
    """Rebuild the whole index."""
    return {
        'tickets': index_tickets(),
        'notices': index_notices(),
        'config': index_config(),
        'faqs': index_faqs(),
    }