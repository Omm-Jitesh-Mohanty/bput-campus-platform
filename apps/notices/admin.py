# from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Notice, NoticeReadStatus


class NoticeReadStatusInline(admin.TabularInline):
    model = NoticeReadStatus
    extra = 0
    readonly_fields = ('student', 'read_at')
    can_delete = False


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'ai_priority', 'posted_by',
                    'read_count', 'total_targeted', 'read_percentage',
                    'is_published', 'created_at')
    list_filter = ('ai_priority', 'is_published', 'created_at')
    search_fields = ('title', 'content')
    autocomplete_fields = ('posted_by',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [NoticeReadStatusInline]
    date_hierarchy = 'created_at'


@admin.register(NoticeReadStatus)
class NoticeReadStatusAdmin(admin.ModelAdmin):
    list_display = ('notice', 'student', 'read_at')
    list_filter = ('read_at',)
    autocomplete_fields = ('notice', 'student')