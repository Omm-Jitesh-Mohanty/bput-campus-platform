# from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import DocumentTemplate, IssuedDocument


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'doc_type', 'requires_fee_clearance',
                    'requires_attendance_75', 'created_at')
    list_filter = ('doc_type', 'requires_fee_clearance', 'requires_attendance_75')


@admin.register(IssuedDocument)
class IssuedDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'student', 'doc_type',
                    'issued_by', 'issued_at', 'is_revoked')
    list_filter = ('doc_type', 'is_revoked', 'issued_at')
    search_fields = ('title', 'student__username')
    autocomplete_fields = ('student', 'issued_by', 'source_ticket')
    readonly_fields = ('issued_at', 'signature_hash', 'verification_uuid')
    date_hierarchy = 'issued_at'