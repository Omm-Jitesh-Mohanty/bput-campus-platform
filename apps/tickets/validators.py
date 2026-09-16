"""File upload validators for tickets."""
from django.core.exceptions import ValidationError

MAX_UPLOAD_MB = 5
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

ALLOWED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.docx', '.doc']


def validate_upload_size(file):
    if file.size > MAX_UPLOAD_BYTES:
        raise ValidationError(f"File too large. Max {MAX_UPLOAD_MB} MB allowed.")


def validate_upload_extension(file):
    import os
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported file type: {ext}. "
                              f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}")