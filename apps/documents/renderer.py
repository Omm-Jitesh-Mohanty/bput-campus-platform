"""
PDF rendering pipeline.

Steps:
  1. Load DOCX template
  2. Render with docxtpl (Jinja2-in-DOCX)
  3. Convert DOCX → PDF (LibreOffice or reportlab fallback)
  4. Overlay QR code linking to verification URL
  5. Compute HMAC signature and store
"""
import hashlib
import hmac
import logging
import os
import subprocess
import tempfile
import uuid
from io import BytesIO
from pathlib import Path

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)


class RenderError(Exception):
    pass


# =====================================================================
# DOCX → PDF
# =====================================================================

def _docx_to_pdf_libreoffice(docx_path, output_dir):
    """Convert DOCX to PDF using LibreOffice headless."""
    soffice = getattr(settings, 'LIBREOFFICE_PATH', '') or 'soffice'

    try:
        result = subprocess.run(
            [
                soffice, '--headless', '--convert-to', 'pdf',
                '--outdir', str(output_dir), str(docx_path)
            ],
            capture_output=True,
            timeout=60,
            check=False,
        )
    except FileNotFoundError:
        raise RenderError("LibreOffice (`soffice`) not found in PATH")
    except subprocess.TimeoutExpired:
        raise RenderError("LibreOffice conversion timed out")

    if result.returncode != 0:
        raise RenderError(
            f"LibreOffice failed (code {result.returncode}): "
            f"{result.stderr.decode('utf-8', errors='ignore')[:300]}"
        )

    # LibreOffice names the PDF after the DOCX
    stem = Path(docx_path).stem
    pdf_path = Path(output_dir) / f'{stem}.pdf'

    if not pdf_path.exists():
        raise RenderError(f"LibreOffice produced no output at {pdf_path}")

    return str(pdf_path)


def _docx_to_pdf_reportlab(docx_path, output_dir, context):
    """
    Fallback: generate a simple PDF using reportlab.

    Does not parse DOCX — instead renders context values as a
    plain letterhead-style document. Used when LibreOffice is unavailable.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    stem = Path(docx_path).stem
    pdf_path = Path(output_dir) / f'{stem}.pdf'

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4

    # Header
    c.setFont('Helvetica-Bold', 16)
    c.drawCentredString(width / 2, height - 30 * mm, 'BPUT CAMPUS PLATFORM')

    c.setFont('Helvetica', 10)
    c.drawCentredString(width / 2, height - 38 * mm, 'Official Document')

    c.line(20 * mm, height - 42 * mm, width - 20 * mm, height - 42 * mm)

    # Body
    y = height - 55 * mm
    c.setFont('Helvetica', 12)
    for key, value in (context or {}).items():
        label = key.replace('_', ' ').title()
        c.drawString(25 * mm, y, f'{label}: {value}')
        y -= 8 * mm
        if y < 40 * mm:
            c.showPage()
            y = height - 30 * mm

    c.showPage()
    c.save()
    return str(pdf_path)


def render_docx_to_pdf(docx_path, context, output_dir):
    """Route to the configured renderer."""
    renderer = getattr(settings, 'DOC_RENDERER', 'libreoffice')

    if renderer == 'libreoffice':
        try:
            return _docx_to_pdf_libreoffice(docx_path, output_dir)
        except RenderError as e:
            logger.warning(f"LibreOffice failed, falling back to reportlab: {e}")
            return _docx_to_pdf_reportlab(docx_path, output_dir, context)

    if renderer == 'reportlab':
        return _docx_to_pdf_reportlab(docx_path, output_dir, context)

    raise RenderError(f"Unknown DOC_RENDERER: {renderer}")


# =====================================================================
# QR OVERLAY
# =====================================================================

def generate_qr_png(data, size=200):
    """Return PNG bytes for a QR code."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.read()


def overlay_qr_on_pdf(pdf_path, qr_data, output_path=None):
    """
    Overlay a QR code on the bottom-right of the first page of a PDF.
    Uses pypdf + reportlab to draw onto an overlay then merge.
    """
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader

    output_path = output_path or pdf_path

    # Build QR overlay PDF
    qr_bytes = generate_qr_png(qr_data)
    qr_img = ImageReader(BytesIO(qr_bytes))

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4

    # Draw QR bottom-right, 30mm square
    qr_size = 30 * 2.83465  # 30mm in points (1mm ≈ 2.83465pt)
    margin = 15 * 2.83465
    c.drawImage(
        qr_img,
        page_w - qr_size - margin,
        margin,
        width=qr_size,
        height=qr_size,
        mask='auto',
    )

    c.setFont('Helvetica', 6)
    c.drawRightString(
        page_w - margin,
        margin - 6,
        'Verify at /verify/' + qr_data.split('/')[-2] if '/' in qr_data else 'Verify'
    )

    c.save()
    buf.seek(0)

    # Merge with original
    original = PdfReader(pdf_path)
    overlay = PdfReader(buf)
    writer = PdfWriter()

    for i, page in enumerate(original.pages):
        if i == 0:
            page.merge_page(overlay.pages[0])
        writer.add_page(page)

    with open(output_path, 'wb') as f:
        writer.write(f)

    return output_path


# =====================================================================
# SIGNING
# =====================================================================

def compute_signature(pdf_bytes, secret=None):
    """Compute HMAC-SHA256 of the PDF content."""
    secret = secret or getattr(settings, 'DOC_SIGNING_SECRET', 'insecure-default')
    h = hmac.new(
        secret.encode('utf-8'),
        pdf_bytes,
        hashlib.sha256,
    )
    return h.hexdigest()


def verify_signature(pdf_bytes, expected_hash, secret=None):
    """Constant-time compare of signature."""
    actual = compute_signature(pdf_bytes, secret=secret)
    return hmac.compare_digest(actual, expected_hash)


# =====================================================================
# MAIN RENDER PIPELINE
# =====================================================================

def render_document(issued_doc):
    """
    Full pipeline: DOCX → PDF → QR → signature.

    Mutates issued_doc's pdf_file, signature_hash, render_status.
    """
    from docxtpl import DocxTemplate

    template = issued_doc.template
    if not template or not template.template_file:
        raise RenderError("No template attached to document")

    # --- 1. Build context ---
    from .context import build_context
    context = build_context(
        template.field_mapping,
        student=issued_doc.student,
        ticket=issued_doc.source_ticket,
        doc_uuid=issued_doc.verification_uuid,
    )
    context['verification_url'] = (
        f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}"
        f"/verify/{issued_doc.verification_uuid}/"
    )

    # --- 2. Render DOCX with placeholders ---
    with tempfile.TemporaryDirectory() as tmpdir:
        # Docxtpl expects a path
        doc = DocxTemplate(template.template_file.path)
        try:
            doc.render(context)
        except Exception as e:
            raise RenderError(f"Template render failed: {e}")

        rendered_docx = Path(tmpdir) / f'rendered_{issued_doc.id}.docx'
        doc.save(str(rendered_docx))

        # --- 3. Convert to PDF ---
        pdf_path = render_docx_to_pdf(str(rendered_docx), context, tmpdir)

        # --- 4. Overlay QR ---
        qr_data = context['verification_url']
        pdf_with_qr = Path(tmpdir) / 'with_qr.pdf'
        overlay_qr_on_pdf(pdf_path, qr_data, output_path=str(pdf_with_qr))

        # --- 5. Read bytes ---
        with open(pdf_with_qr, 'rb') as f:
            pdf_bytes = f.read()

    # --- 6. Sign ---
    signature = compute_signature(pdf_bytes)

    # --- 7. Save ---
    filename = f'{issued_doc.doc_type}_{issued_doc.student.username}_{issued_doc.id}.pdf'
    issued_doc.pdf_file.save(filename, ContentFile(pdf_bytes), save=False)
    issued_doc.signature_hash = signature
    issued_doc.render_context = context
    issued_doc.render_status = 'ready'
    issued_doc.render_error = ''
    issued_doc.issued_at = timezone.now()
    issued_doc.save()

    return issued_doc