# from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.utils import timezone

from apps.core.decorators import admin_required
from apps.core.permissions import require_perm, require_any_perm, Perm
from .models import DocumentTemplate, IssuedDocument
from .services import DocumentService
from .renderer import verify_signature


# =====================================================================
# Student views
# =====================================================================

@require_any_perm(Perm.VIEW_OWN_DOCUMENTS, Perm.VIEW_DOCUMENT_VAULT)
def my_documents(request):
    from apps.core.scoping import DataScope
    docs = DataScope.document_queryset(request.user).order_by('-issued_at')
    return render(request, 'documents/my_list.html', {'documents': docs})


@require_perm(Perm.VIEW_OWN_DOCUMENTS)
def document_download(request, pk):
    """Serve the PDF if user is owner or admin."""
    doc = get_object_or_404(IssuedDocument, pk=pk, is_deleted=False)

    # Access control
    if not request.user.is_admin_role() and doc.student_id != request.user.id:
        raise Http404("Not found")

    if doc.is_revoked:
        messages.error(request, "This document has been revoked.")
        return redirect('documents:my_documents')

    if not doc.is_downloadable:
        messages.warning(request, "Document is still being generated.")
        return redirect('documents:my_documents')

    # Serve inline (browser can download or preview)
    response = FileResponse(
        doc.pdf_file.open('rb'),
        content_type='application/pdf',
    )
    response['Content-Disposition'] = (
        f'inline; filename="{doc.doc_type}_{doc.student.username}.pdf"'
    )
    return response


@require_perm(Perm.REQUEST_DOCUMENT)
def request_document(request):
    """Student requests a new document."""
    if request.user.is_admin_role():
        return redirect('dashboard:admin_home')

    # Available document types with active templates
    templates = DocumentTemplate.objects.filter(is_active=True)
    available_types = {}
    for t in templates:
        available_types[t.doc_type] = t

    if request.method == 'POST':
        doc_type = request.POST.get('doc_type')
        purpose = request.POST.get('purpose', '').strip()

        if not doc_type:
            messages.error(request, "Please select a document type.")
        else:
            try:
                doc = DocumentService.issue_document(
                    student=request.user,
                    doc_type=doc_type,
                    title=f"{dict(DocumentTemplate._meta.get_field('doc_type').choices).get(doc_type, doc_type)}",
                )
                messages.success(
                    request,
                    f"Document issued. Download: {doc.title}"
                )
                return redirect('documents:my_documents')
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Failed: {e}")
                import logging
                logging.getLogger(__name__).exception("Document issue failed")

    return render(request, 'documents/request.html', {
        'available_types': available_types.values(),
    })


# =====================================================================
# Public verification
# =====================================================================

def verify_document(request, uuid):
    """
    Public verification page.
    Anyone with the UUID can confirm authenticity.
    """
    doc = IssuedDocument.objects.filter(
        verification_uuid=uuid, is_deleted=False
    ).first()

    if not doc:
        return render(request, 'documents/verify.html', {
            'valid': False,
            'reason': 'No document found with this verification code.',
        })

    if doc.is_revoked:
        return render(request, 'documents/verify.html', {
            'valid': False,
            'reason': f"This document was revoked on "
                      f"{doc.revoked_at.strftime('%d %b %Y')}. Reason: {doc.revoked_reason}",
            'document': doc,
        })

    if doc.render_status != 'ready':
        return render(request, 'documents/verify.html', {
            'valid': False,
            'reason': 'Document is not yet ready.',
        })

    # Re-verify signature
    try:
        pdf_bytes = doc.pdf_file.read()
        doc.pdf_file.seek(0)
        sig_valid = verify_signature(pdf_bytes, doc.signature_hash)
    except Exception:
        sig_valid = False

    return render(request, 'documents/verify.html', {
        'valid': sig_valid,
        'document': doc,
        'signature_ok': sig_valid,
    })


# =====================================================================
# Admin views
# =====================================================================

@require_perm(Perm.VIEW_DOCUMENT_VAULT)
def admin_documents_list(request):
    """Admin: view all issued documents."""
    qs = IssuedDocument.objects.filter(is_deleted=False).select_related(
        'student', 'template', 'issued_by'
    ).order_by('-issued_at')

    # Filters
    doc_type = request.GET.get('type')
    if doc_type:
        qs = qs.filter(doc_type=doc_type)

    status = request.GET.get('status')
    if status:
        qs = qs.filter(render_status=status)

    revoked = request.GET.get('revoked')
    if revoked == '1':
        qs = qs.filter(is_revoked=True)

    return render(request, 'documents/admin_list.html', {
        'documents': qs[:200],
        'filter_type': doc_type,
        'filter_status': status,
    })


@require_perm(Perm.REVOKE_DOCUMENT)
def admin_document_revoke(request, pk):
    doc = get_object_or_404(IssuedDocument, pk=pk)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        DocumentService.revoke(doc, reason=reason, by_user=request.user)
        messages.success(request, f"Document #{doc.id} revoked.")
    return redirect('documents:admin_list')


@require_perm(Perm.ISSUE_DOCUMENT)
def admin_document_reissue(request, pk):
    doc = get_object_or_404(IssuedDocument, pk=pk)
    if request.method == 'POST':
        try:
            DocumentService.reissue(doc, issued_by=request.user)
            messages.success(request, f"Document #{doc.id} re-issued.")
        except Exception as e:
            messages.error(request, f"Re-issue failed: {e}")
    return redirect('documents:admin_list')