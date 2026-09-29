"""
Document service — issue, re-issue, revoke documents.
"""
import logging

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import DocumentTemplate, IssuedDocument
from .renderer import render_document, RenderError
from apps.core.audit import AuditService

logger = logging.getLogger(__name__)


class DocumentService:

    @classmethod
    def find_template(cls, doc_type):
        return DocumentTemplate.objects.filter(
            doc_type=doc_type, is_active=True
        ).order_by('-version').first()

    @classmethod
    def check_eligibility(cls, student, template):
        """
        Return (is_eligible, reasons: list).
        """
        reasons = []

        if template.requires_fee_clearance:
            pending = sum(f.pending for f in student.fee_records.all())
            if pending > 0:
                reasons.append(f"₹{pending} in pending fees")

        if template.requires_attendance_75:
            from apps.attendance.services import get_student_attendance_summary
            summary = get_student_attendance_summary(student)
            if summary['overall_percentage'] < 75:
                reasons.append(
                    f"Attendance {summary['overall_percentage']}% below 75%"
                )

        return (len(reasons) == 0, reasons)

    @classmethod
    def issue_document(
        cls,
        student,
        doc_type,
        title=None,
        source_ticket=None,
        issued_by=None,
    ):
        """
        Create a document request and attempt to render.

        Returns IssuedDocument instance.
        Raises ValidationError if template missing or eligibility fails.
        """
        template = cls.find_template(doc_type)
        if not template:
            raise ValidationError(f"No active template for '{doc_type}'")

        # Eligibility check
        eligible, reasons = cls.check_eligibility(student, template)
        if not eligible:
            raise ValidationError(
                f"Student not eligible: {', '.join(reasons)}"
            )

        title = title or f"{template.name} — {student.get_full_name() or student.username}"

        doc = IssuedDocument.objects.create(
            student=student,
            doc_type=doc_type,
            title=title,
            template=template,
            source_ticket=source_ticket,
            issued_by=issued_by,
            render_status='generating',
        )

        # Render synchronously (fine for demo; move to Celery for prod)
        try:
            render_document(doc)
            AuditService.log_action(
                action='create',
                target=doc,
                metadata={
                    'doc_type': doc_type,
                    'template': template.name,
                    'template_version': template.version,
                },
                user=issued_by or student,
            )
        except RenderError as e:
            doc.render_status = 'failed'
            doc.render_error = str(e)
            doc.save(update_fields=['render_status', 'render_error', 'updated_at'])
            logger.exception(f"Document render failed for #{doc.id}: {e}")
            raise

        return doc

    @classmethod
    def reissue(cls, doc, issued_by=None):
        """
        Re-render an existing document (e.g., after data change).
        Keeps the same verification UUID; new signature.
        """
        if doc.is_revoked:
            raise ValidationError("Cannot reissue a revoked document")

        doc.render_status = 'generating'
        doc.save(update_fields=['render_status', 'updated_at'])

        try:
            render_document(doc)
            AuditService.log_action(
                action='update',
                target=doc,
                metadata={'reissued': True},
                user=issued_by,
            )
        except RenderError as e:
            doc.render_status = 'failed'
            doc.render_error = str(e)
            doc.save(update_fields=['render_status', 'render_error', 'updated_at'])
            raise

        return doc

    @classmethod
    def revoke(cls, doc, reason='', by_user=None):
        doc.revoke(reason=reason)
        AuditService.log_action(
            action='delete',
            target=doc,
            metadata={'revoked': True, 'reason': reason},
            user=by_user,
        )
        return doc