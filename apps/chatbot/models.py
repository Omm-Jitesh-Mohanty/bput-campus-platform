# from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class KnowledgeChunk(TimeStampedModel):
    """
    A chunk of indexed knowledge for RAG retrieval.
    """
    SOURCE_TYPES = [
        ('ticket', 'Ticket'),
        ('notice', 'Notice'),
        ('faq', 'FAQ'),
        ('policy', 'Policy'),
        ('config', 'Config'),
    ]
    AUDIENCES = [
        ('student', 'Students'),
        ('admin', 'Admins'),
        ('both', 'Both'),
    ]

    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, db_index=True)
    audience = models.CharField(max_length=10, choices=AUDIENCES, default='both', db_index=True)
    source_id = models.CharField(max_length=64, blank=True, db_index=True)

    title = models.CharField(max_length=300, blank=True)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)

    # Embedding stored as JSON (list of floats)
    embedding = models.JSONField(default=list, blank=True)
    embedding_model = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source_type', 'audience']),
        ]

    def __str__(self):
        return f"[{self.source_type}] {self.title[:60]}"


class ChatSession(TimeStampedModel):
    """A conversation thread."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions'
    )
    mode = models.CharField(max_length=10, default='student')  # student | admin
    title = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} — {self.title or 'Untitled'}"


class ChatMessage(TimeStampedModel):
    """A single message in a session."""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"