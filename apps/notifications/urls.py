from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('recent.json', views.recent_json, name='recent_json'),
    path('unread-count.json', views.unread_count, name='unread_count'),
    path('<int:pk>/mark-read/', views.mark_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
]