"""Small helpers used everywhere."""
import os
from django.utils.text import slugify


def user_upload_path(instance, subfolder, filename):
    """
    Generate an organized upload path:
    <subfolder>/<year>/<month>/<username>_<filename>
    Keeps media/ tidy even with thousands of files.
    """
    from datetime import datetime
    now = datetime.now()
    username = getattr(instance.student, 'username', 'anon') if hasattr(instance, 'student') else 'anon'
    clean_name = f"{username}_{slugify(os.path.splitext(filename)[0])}{os.path.splitext(filename)[1]}"
    return f"{subfolder}/{now.year}/{now.month:02d}/{clean_name}"


def ticket_attachment_path(instance, filename):
    return user_upload_path(instance, 'tickets/attachments', filename)


def notice_attachment_path(instance, filename):
    from datetime import datetime
    now = datetime.now()
    return f"notices/attachments/{now.year}/{now.month:02d}/{filename}"


def document_file_path(instance, filename):
    from datetime import datetime
    now = datetime.now()
    student_id = getattr(instance, 'student_id', 'unknown')
    return f"documents/issued/{now.year}/{now.month:02d}/student_{student_id}_{filename}"


def feedback_image_path(instance, filename):
    from datetime import datetime
    now = datetime.now()
    return f"feedback/images/{now.year}/{now.month:02d}/{filename}"