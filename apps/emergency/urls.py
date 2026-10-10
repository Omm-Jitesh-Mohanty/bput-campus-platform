from django.urls import path

from . import views


app_name = 'emergency'


urlpatterns = [
    path(
        '',
        views.sos_home,
        name='sos_home'
    ),

    path(
        'trigger/',
        views.trigger_sos,
        name='trigger'
    ),

    path(
        'alert/<int:pk>/',
        views.alert_detail,
        name='alert_detail'
    ),

    path(
        'contacts/',
        views.contact_manage,
        name='contacts'
    ),

    path(
        'contacts/<int:pk>/delete/',
        views.contact_delete,
        name='contact_delete'
    ),

    path(
        'admin/',
        views.admin_alert_list,
        name='admin_list'
    ),

    path(
        'admin/<int:pk>/ack/',
        views.admin_acknowledge,
        name='admin_ack'
    ),

    path(
        'admin/<int:pk>/resolve/',
        views.admin_resolve,
        name='admin_resolve'
    ),

    path(
        'twilio/<int:alert_id>/ack/',
        views.twilio_acknowledge,
        name='twilio_acknowledge'
    ),
]