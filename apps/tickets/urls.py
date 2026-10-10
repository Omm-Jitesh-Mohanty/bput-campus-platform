# from django.urls import path
# from . import views

# app_name = 'tickets'

# urlpatterns = [
#     path('', views.my_tickets, name='my_tickets'),
#     path('new/', views.submit_ticket, name='submit'),
#     path('<int:pk>/', views.ticket_detail, name='detail'),
#     path('<int:pk>/confirm/', views.confirm_ticket_resolution, name='confirm'),
#     path('<int:pk>/comment/', views.add_comment, name='add_comment'),
# ]

# from django.urls import path
# from . import views

# app_name = 'tickets'

# urlpatterns = [
#     path('', views.my_tickets, name='my_tickets'),
#     path('new/', views.submit_ticket, name='submit'),
#     path('kiosk/', views.kiosk_new_ticket, name='kiosk_new'),
#     path('kiosk/<int:pk>/receipt/', views.kiosk_receipt, name='kiosk_receipt'),
#     path('<int:pk>/', views.ticket_detail, name='detail'),
#     path('<int:pk>/confirm/', views.confirm_ticket_resolution, name='confirm'),
#     path('<int:pk>/comment/', views.add_comment, name='add_comment'),
#     path('<int:pk>/resolve/', views.admin_resolve_ticket, name='admin_resolve'),
#     path('<int:pk>/assign/', views.admin_assign_ticket, name='admin_assign'),
#     path('type/<slug:code>/fields/', views.ticket_type_fields, name='type_fields'),
#     path('api/preview/', views.preview_formatted_ticket, name='preview'),
#     path('confirm/', views.confirm_submit_ticket, name='confirm'),
#     path('approvals/', views.my_approvals, name='my_approvals'),
#     path('<int:pk>/change-workflow/', views.change_ticket_workflow, name='change_workflow'),
# ]

from django.urls import path
from . import views


app_name = 'tickets'


urlpatterns = [
    path('', views.queue_router, name='queue_router'),

    path('mine/', views.my_tickets, name='my_tickets'),

    path('queue/', views.my_queue, name='my_queue'),

    path('all/', views.all_tickets, name='all_tickets'),

    path('new/', views.submit_ticket, name='submit'),
    path(
        'api/preview/',
        views.preview_formatted_ticket,
        name='preview',
    ),

    path('confirm/', views.confirm_submit_ticket, name='confirm'),

    path(
        'type/<slug:code>/fields/',
        views.ticket_type_fields,
        name='type_fields',
    ),

    path(
        '<int:pk>/',
        views.ticket_detail,
        name='detail',
    ),

    path(
        '<int:pk>/confirm/',
        views.confirm_ticket_resolution,
        name='confirm_resolution',
    ),

    path(
        '<int:pk>/comment/',
        views.add_comment,
        name='add_comment',
    ),

    path(
        '<int:pk>/resolve/',
        views.admin_resolve_ticket,
        name='admin_resolve',
    ),

    path(
        '<int:pk>/assign/',
        views.admin_assign_ticket,
        name='admin_assign',
    ),

    path(
        '<int:pk>/change-workflow/',
        views.change_ticket_workflow,
        name='change_workflow',
    ),
]