"""
Document template and issued document models.
"""
import uuid

from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.core.constants import DOCUMENT_TYPES


class DocumentTemplate(TimeStampedModel):
    """
    A DOCX (or other) template for a document type.

    Multiple versions can exist; only one active per doc_type.
    Placeholders in the template use {{ var_name }} syntax (docxtpl).
    """
    doc_type = models.CharField(
        max_length=30, choices=DOCUMENT_TYPES, db_index=True,
        help_text="Type of document this template produces"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # The template file
    template_file = models.FileField(
        upload_to='documents/templates/',
        help_text="DOCX file with {{ placeholders }}"
    )

    # Detected placeholders (auto-scanned on save)
    detected_placeholders = models.JSONField(
        default=list, blank=True,
        help_text="List of placeholder names found in the DOCX"
    )

    # Field mapping: how to fill each placeholder
    # Example:
    #   {
    #     "student_name": {"source": "student.full_name"},
    #     "roll_no": {"source": "student.username"},
    #     "purpose": {"source": "ticket.dynamic_data.purpose"},
    #     "issued_date": {"source": "auto.today"}
    #   }
    field_mapping = models.JSONField(
        default=dict, blank=True,
        help_text="Map placeholder → data source"
    )

    # Requirements before issuing
    requires_fee_clearance = models.BooleanField(default=True)
    requires_attendance_75 = models.BooleanField(default=False)

    # Version control
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='created_document_templates'
    )

    class Meta:
        ordering = ['doc_type', '-version']
        indexes = [
            models.Index(fields=['doc_type', 'is_active']),
        ]
        unique_together = ('doc_type', 'version')

    def __str__(self):
        active = '✓' if self.is_active else ' '
        return f"[{active}] {self.name} ({self.get_doc_type_display()}) v{self.version}"

    def save(self, *args, **kwargs):
        # Ensure only one active template per doc_type
        if self.is_active:
            DocumentTemplate.objects.filter(
                doc_type=self.doc_type, is_active=True
            ).exclude(pk=self.pk).update(is_active=False)

        # Auto-scan placeholders when file is present and changed
        if self.template_file and not self.detected_placeholders:
            self.detected_placeholders = self._scan_placeholders()

        super().save(*args, **kwargs)

    def _scan_placeholders(self):
        """Parse DOCX and extract {{ var }} names."""
        import re
        try:
            from docxtpl import DocxTemplate
            doc = DocxTemplate(self.template_file.path)
            text = "\n".join(p.text for p in doc.get_docx().paragraphs)
            # Also scan tables
            for table in doc.get_docx().tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += "\n" + cell.text
            return sorted(set(re.findall(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}', text)))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Placeholder scan failed for template {self.pk}: {e}"
            )
            return []


class IssuedDocument(TimeStampedModel, SoftDeleteModel):
    """
    A concrete PDF issued to a student.

    Contains a cryptographic signature + verification UUID for authenticity checks.
    """
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
        ('revoked', 'Revoked'),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    doc_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES, db_index=True)
    title = models.CharField(max_length=200)

    # Which template was used
    template = models.ForeignKey(
        DocumentTemplate,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='issued_documents'
    )

    # Rendering
    pdf_file = models.FileField(upload_to='documents/issued/', blank=True)
    render_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='generating'
    )
    render_error = models.TextField(blank=True)

    # Integrity
    signature_hash = models.CharField(
        max_length=128, blank=True,
        help_text="SHA-256 hash of the PDF content, HMAC-signed"
    )
    verification_uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )

    # Data snapshot used to render (for re-issuance + audit)
    render_context = models.JSONField(
        default=dict, blank=True,
        help_text="Data snapshot used when rendering this document"
    )

    # Provenance
    source_ticket = models.ForeignKey(
        'tickets.CampusTicket',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='issued_documents'
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='issued_documents'
    )
    issued_at = models.DateTimeField(null=True, blank=True)

    # Revocation
    is_revoked = models.BooleanField(default=False, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-issued_at', '-created_at']
        indexes = [
            models.Index(fields=['student', 'doc_type']),
            models.Index(fields=['verification_uuid']),
            models.Index(fields=['is_revoked']),
        ]

    def __str__(self):
        status = 'REVOKED' if self.is_revoked else self.render_status
        return f"{self.title} — {self.student.username} [{status}]"

    @property
    def is_downloadable(self):
        return (
            self.render_status == 'ready'
            and not self.is_revoked
            and bool(self.pdf_file)
        )

    def revoke(self, reason=''):
        self.is_revoked = True
        self.revoked_at = timezone.now()
        self.revoked_reason = reason
        self.save(update_fields=['is_revoked', 'revoked_at', 'revoked_reason', 'updated_at'])