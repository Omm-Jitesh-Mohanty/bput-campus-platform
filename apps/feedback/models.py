# from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel
from apps.core.constants import FEEDBACK_CATEGORIES


class Feedback(TimeStampedModel):
    """Student feedback on campus facilities."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='feedbacks')
    category = models.CharField(max_length=20, choices=FEEDBACK_CATEGORIES, db_index=True)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)],
                                              help_text="1 = very poor, 5 = excellent")
    comments = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=False)
    image = models.ImageField(upload_to='feedback/images/', null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', '-created_at']),
        ]

    def __str__(self):
        who = 'Anonymous' if self.is_anonymous else (self.student.username if self.student else '?')
        return f"{self.get_category_display()} — {self.rating}/5 by {who}"