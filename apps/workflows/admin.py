from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Workflow, WorkflowStep, TicketStepExecution


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 1
    fields = ('order', 'name', 'role_required', 'specific_user',
              'action_type', 'condition', 'can_skip')
    ordering = ('order',)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'ticket_type', 'step_count',
                    'is_active', 'is_default')
    list_filter = ('is_active', 'is_default', 'ticket_type')
    search_fields = ('name', 'code', 'description')
    autocomplete_fields = ('ticket_type', 'created_by')
    inlines = [WorkflowStepInline]


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = ('workflow', 'order', 'name', 'role_required',
                    'specific_user', 'action_type')
    list_filter = ('workflow', 'role_required', 'action_type')
    search_fields = ('name',)
    autocomplete_fields = ('workflow', 'specific_user')
    ordering = ('workflow', 'order')


@admin.register(TicketStepExecution)
class TicketStepExecutionAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'workflow_step', 'status',
                    'actor', 'acted_at')
    list_filter = ('status', 'workflow_step__workflow')
    search_fields = ('ticket__subject', 'workflow_step__name')
    autocomplete_fields = ('ticket', 'workflow_step', 'actor', 'escalated_to')
    readonly_fields = ('created_at', 'updated_at', 'acted_at', 'escalated_at')
