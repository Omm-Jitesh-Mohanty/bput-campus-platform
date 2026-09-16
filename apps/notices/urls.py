from django.urls import path
from . import views

app_name = 'notices'

urlpatterns = [
    path('', views.notice_list, name='list'),
    path('new/', views.publish_notice, name='publish'),
    path('<int:pk>/', views.notice_detail, name='detail'),
]