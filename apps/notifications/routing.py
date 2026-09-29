from django.urls import path

from .consumers.notifications import NotificationConsumer
from .consumers.tickets import AdminTicketConsumer, TicketDetailConsumer


websocket_urlpatterns = [
    path('ws/notifications/', NotificationConsumer.as_asgi()),
    path('ws/admin/tickets/', AdminTicketConsumer.as_asgi()),
    path('ws/tickets/<int:ticket_id>/', TicketDetailConsumer.as_asgi()),
]