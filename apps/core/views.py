# from django.shortcuts import render

# Create your views here.
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse


def service_worker(request):
    """
    Serve the Service Worker from /sw.js.

    The actual Service Worker file is stored at:
        static/js/sw.js

    Serving it from the root URL allows the Service Worker
    to control the entire Campus Platform.
    """

    sw_path = Path(settings.BASE_DIR) / "static" / "js" / "sw.js"

    if not sw_path.exists():
        return HttpResponse(
            "Service Worker file not found.",
            status=404,
            content_type="text/plain",
        )

    content = sw_path.read_text(encoding="utf-8")

    response = HttpResponse(
        content,
        content_type="application/javascript",
    )

    response["Cache-Control"] = "no-cache, no-store, must-revalidate"

    return response