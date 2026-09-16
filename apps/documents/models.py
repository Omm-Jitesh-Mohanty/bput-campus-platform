# from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel, SoftDeleteModel
from apps.core.utils import document_file_path
from apps.core.constants import DOCUMENT_TYPES


class DocumentTemplate(TimeStampedModel):
    """Blank templates (PDF/DOCX) for various certificates."""
    doc_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES, unique=True)
    name = models.CharField(max_length=100)
    template_file = models.FileField(upload_to='documents/templates/')
    requires_fee_clearance = models.BooleanField(default=True)
    requires_attendance_75 = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class IssuedDocument(TimeStampedModel, SoftDeleteModel):
    """
    A document issued to a student (bonafide, receipt, etc.).
    Contains cryptographic signature + QR for verification.
    """
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='documents')
    doc_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES, db_index=True)
    title = models.CharField(max_length=200)

    # The actual PDF file
    pdf_file = models.FileField(upload_to=document_file_path)

    # Cryptographic signature
    signature_hash = models.CharField(max_length=64, blank=True,
                                      help_text="SHA-256 hash for verification.")
    verification_uuid = models.UUIDField(null=True, blank=True, db_index=True)

    # Link to originating ticket (if issued via ticket)
    source_ticket = models.ForeignKey('tickets.CampusTicket', on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='issued_documents')

    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='issued_documents')
    issued_at = models.DateTimeField(auto_now_add=True)
    is_revoked = models.BooleanField(default=False)
    revoked_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['student', 'doc_type']),
            models.Index(fields=['verification_uuid']),
        ]

    def __str__(self):
        return f"{self.title} — {self.student.username}"