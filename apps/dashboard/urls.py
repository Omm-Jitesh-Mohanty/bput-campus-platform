from django.urls import path

from apps.dashboard import views_analytics
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.student_home, name='student_home'),
    path('admin/', views.admin_home, name='admin_home'),
    path('admin/refresh-ai/', views.refresh_feedback_ai, name='refresh_feedback_ai'),
    path('admin/ageing/<str:bucket>/', views.ageing_detail, name='ageing_detail'),
    path('analytics/', views_analytics.analytics_dashboard, name='analytics'), 
    path('analytics/refresh/', views_analytics.refresh_analytics, name='analytics_refresh'),
]