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

from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.my_tickets, name='my_tickets'),
    path('new/', views.submit_ticket, name='submit'),
    path('kiosk/', views.kiosk_new_ticket, name='kiosk_new'),
    path('kiosk/<int:pk>/receipt/', views.kiosk_receipt, name='kiosk_receipt'),
    path('<int:pk>/', views.ticket_detail, name='detail'),
    path('<int:pk>/confirm/', views.confirm_ticket_resolution, name='confirm'),
    path('<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('<int:pk>/resolve/', views.admin_resolve_ticket, name='admin_resolve'),
    path('<int:pk>/assign/', views.admin_assign_ticket, name='admin_assign'),
]