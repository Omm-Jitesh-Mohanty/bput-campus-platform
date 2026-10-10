# from django.urls import path
# from . import views

# app_name = 'manage_panel'

# urlpatterns = [
#     path('', views.manage_home, name='home'),

#     # Departments
#     path('departments/', views.departments_list, name='departments'),
#     path('departments/new/', views.department_edit, name='department_create'),
#     path('departments/<int:pk>/', views.department_edit, name='department_edit'),
#     path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),

#     # SLAs
#     path('slas/', views.slas_view, name='slas'),
#     path('slas/update/', views.sla_update_ajax, name='sla_update_ajax'),
# ]

from django.urls import path
from . import views

app_name = 'manage_panel'

urlpatterns = [
    # -----------------------------------------------------------------
    # Home
    # -----------------------------------------------------------------
    path(
        '',
        views.manage_home,
        name='home'
    ),

    # -----------------------------------------------------------------
    # Departments
    # -----------------------------------------------------------------
    path(
        'departments/',
        views.departments_list,
        name='departments'
    ),
    path(
        'departments/new/',
        views.department_edit,
        name='department_create'
    ),
    path(
        'departments/<int:pk>/',
        views.department_edit,
        name='department_edit'
    ),
    path(
        'departments/<int:pk>/delete/',
        views.department_delete,
        name='department_delete'
    ),

    # -----------------------------------------------------------------
    # Ticket Types
    # -----------------------------------------------------------------
    path(
        'ticket-types/',
        views.ticket_types_list,
        name='ticket_types'
    ),
    path(
        'ticket-types/new/',
        views.ticket_type_edit,
        name='ticket_type_create'
    ),
    path(
        'ticket-types/<int:pk>/',
        views.ticket_type_edit,
        name='ticket_type_edit'
    ),
    path(
        'ticket-types/<int:pk>/delete/',
        views.ticket_type_delete,
        name='ticket_type_delete'
    ),

    # -----------------------------------------------------------------
    # Priorities
    # -----------------------------------------------------------------
    path(
        'priorities/',
        views.priorities_list,
        name='priorities'
    ),
    path(
        'priorities/new/',
        views.priority_edit,
        name='priority_create'
    ),
    path(
        'priorities/<int:pk>/',
        views.priority_edit,
        name='priority_edit'
    ),
    path(
        'priorities/<int:pk>/delete/',
        views.priority_delete,
        name='priority_delete'
    ),

    # -----------------------------------------------------------------
    # SLA Policies
    # -----------------------------------------------------------------
    path(
        'slas/',
        views.slas_view,
        name='slas'
    ),
    path(
        'slas/update/',
        views.sla_update_ajax,
        name='sla_update_ajax'
    ),

    # -----------------------------------------------------------------
    # System Settings
    # -----------------------------------------------------------------
    path(
        'settings/',
        views.settings_list,
        name='settings'
    ),
    path(
        'settings/new/',
        views.setting_edit,
        name='setting_create'
    ),
    path(
        'settings/<int:pk>/',
        views.setting_edit,
        name='setting_edit'
    ),
    path(
        'settings/<int:pk>/delete/',
        views.setting_delete,
        name='setting_delete'
    ),

    # -----------------------------------------------------------------
    # AI Prompt Templates
    # -----------------------------------------------------------------
    path(
        'prompts/',
        views.prompts_list,
        name='prompts'
    ),
    path(
        'prompts/new/',
        views.prompt_edit,
        name='prompt_create'
    ),
    path(
        'prompts/<int:pk>/',
        views.prompt_edit,
        name='prompt_edit'
    ),
    path(
        'prompts/<int:pk>/delete/',
        views.prompt_delete,
        name='prompt_delete'
    ),

    # -----------------------------------------------------------------
    # Notification Templates
    # -----------------------------------------------------------------
    path(
        'notifications/',
        views.notifications_list,
        name='notifications'
    ),
    path(
        'notifications/new/',
        views.notification_edit,
        name='notification_create'
    ),
    path(
        'notifications/<int:pk>/',
        views.notification_edit,
        name='notification_edit'
    ),
    path(
        'notifications/<int:pk>/delete/',
        views.notification_delete,
        name='notification_delete'
    ),

    # -----------------------------------------------------------------
    # Audit Trail
    # -----------------------------------------------------------------
    path(
        'audit/',
        views.audit_view,
        name='audit'
    ),
    path('ticket-types/', views.ticket_types_list, name='ticket_types'),
    path('ticket-types/new/', views.ticket_type_edit, name='ticket_type_create'),
    path('ticket-types/<int:pk>/', views.ticket_type_edit, name='ticket_type_edit'),
    path('ticket-types/validate-schema/', views.ticket_type_validate_schema, name='ticket_type_validate_schema'),
    path('documents/', views.document_templates_list, name='document_templates'),
    path('documents/new/', views.document_template_edit, name='document_template_create'),
    path('documents/<int:pk>/', views.document_template_edit, name='document_template_edit'),
    path('audit/', views.audit_view, name='audit'),
    path('audit/timeline/<str:model_name>/<str:object_id>/',views.audit_entity_timeline, name='audit_timeline'),
    path('attendance/cancel/<int:timetable_id>/', views.cancel_class, name='cancel_class'),
]
    
