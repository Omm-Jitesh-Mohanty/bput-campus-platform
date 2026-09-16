# from django.contrib import admin

# Register your models here.
# from django.contrib import admin
# from .models import CampusTicket, TicketComment


# class TicketCommentInline(admin.TabularInline):
#     model = TicketComment
#     extra = 0
#     fields = ('author', 'body', 'is_internal', 'created_at')
#     readonly_fields = ('created_at',)


# @admin.register(CampusTicket)
# class CampusTicketAdmin(admin.ModelAdmin):
#     list_display = ('id', 'student', 'ticket_type', 'subject_short',
#                     'assigned_department', 'priority', 'status',
#                     'age_hours', 'ageing_color', 'created_at')
#     list_filter = ('ticket_type', 'status', 'priority',
#                    'assigned_department', 'ageing_color')
#     search_fields = ('subject', 'raw_input', 'student__username')
#     autocomplete_fields = ('student', 'assigned_to', 'resolved_by')
#     readonly_fields = ('created_at', 'updated_at', 'age_hours', 'ageing_color')
#     inlines = [TicketCommentInline]
#     date_hierarchy = 'created_at'

#     fieldsets = (
#         ('Core', {'fields': ('student', 'ticket_type', 'subject')}),
#         ('Content', {'fields': ('raw_input', 'formatted_body', 'attachment')}),
#         ('Routing', {'fields': ('assigned_department', 'assigned_to', 'priority')}),
#         ('Lifecycle', {'fields': ('status', 'resolution_note',
#                                   'resolved_by', 'resolved_at', 'student_confirmed')}),
#         ('AI Metadata', {'fields': ('ai_metadata',), 'classes': ('collapse',)}),
#         ('Timestamps', {'fields': ('created_at', 'updated_at', 'age_hours', 'ageing_color'),
#                         'classes': ('collapse',)}),
#     )

#     def subject_short(self, obj):
#         return obj.subject[:50]
#     subject_short.short_description = 'Subject'


# @admin.register(TicketComment)
# class TicketCommentAdmin(admin.ModelAdmin):
#     list_display = ('ticket', 'author', 'is_internal', 'created_at')
#     list_filter = ('is_internal',)
#     autocomplete_fields = ('ticket', 'author')

from django.contrib import admin
from django.utils import timezone

from .models import CampusTicket, TicketComment


class AgeingColorFilter(admin.SimpleListFilter):
    title = 'Ageing'
    parameter_name = 'ageing_color'

    def lookups(self, request, model_admin):
        return (
            ('green', 'Green'),
            ('yellow', 'Yellow'),
            ('red', 'Red'),
        )

    def queryset(self, request, queryset):
        value = self.value()

        if not value:
            return queryset

        now = timezone.now()

        matching_ids = []

        for ticket in queryset:
            end = ticket.resolved_at or now
            hours = (end - ticket.created_at).total_seconds() / 3600

            if ticket.status == 'resolved':
                color = 'green'
            elif hours < 24:
                color = 'green'
            elif hours < 48:
                color = 'yellow'
            else:
                color = 'red'

            if color == value:
                matching_ids.append(ticket.pk)

        return queryset.filter(pk__in=matching_ids)


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    fields = ('author', 'body', 'is_internal', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(CampusTicket)
class CampusTicketAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'student',
        'ticket_type',
        'subject_short',
        'assigned_department',
        'priority',
        'status',
        'age_hours',
        'ageing_color',
        'created_at',
    )

    list_filter = (
        'ticket_type',
        'status',
        'priority',
        'assigned_department',
        AgeingColorFilter,
    )

    search_fields = (
        'subject',
        'raw_input',
        'student__username',
    )

    autocomplete_fields = (
        'student',
        'assigned_to',
        'resolved_by',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
        'age_hours',
        'ageing_color',
    )

    inlines = [TicketCommentInline]

    date_hierarchy = 'created_at'

    fieldsets = (
        (
            'Core',
            {
                'fields': (
                    'student',
                    'ticket_type',
                    'subject',
                )
            },
        ),
        (
            'Content',
            {
                'fields': (
                    'raw_input',
                    'formatted_body',
                    'attachment',
                )
            },
        ),
        (
            'Routing',
            {
                'fields': (
                    'assigned_department',
                    'assigned_to',
                    'priority',
                )
            },
        ),
        (
            'Lifecycle',
            {
                'fields': (
                    'status',
                    'resolution_note',
                    'resolved_by',
                    'resolved_at',
                    'student_confirmed',
                )
            },
        ),
        (
            'AI Metadata',
            {
                'fields': ('ai_metadata',),
                'classes': ('collapse',),
            },
        ),
        (
            'Timestamps',
            {
                'fields': (
                    'created_at',
                    'updated_at',
                    'age_hours',
                    'ageing_color',
                ),
                'classes': ('collapse',),
            },
        ),
    )

    def subject_short(self, obj):
        return obj.subject[:50]

    subject_short.short_description = 'Subject'


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = (
        'ticket',
        'author',
        'is_internal',
        'created_at',
    )

    list_filter = ('is_internal',)

    autocomplete_fields = (
        'ticket',
        'author',
    )