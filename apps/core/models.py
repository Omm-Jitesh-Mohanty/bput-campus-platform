# from django.db import models

# Create your models here.
"""
Base abstract models used across the project.
Never create tables — they're abstract.
"""
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Adds created_at, updated_at to any model."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class SoftDeleteModel(models.Model):
    """
    Soft delete: mark as deleted instead of removing row.
    Essential for audit trails on tickets, documents, approvals.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])