from django.urls import path
from django.shortcuts import redirect

from . import views, views_executive

app_name = 'dashboard'

urlpatterns = [
    path('', views.student_home, name='home_router'),

    # Student
    path('student/', views.student_home, name='student_home'),

    # Admin unified dashboard
    path('admin/', views_executive.executive_view, name='admin_home'),
    path('dashboard/', views_executive.executive_view, name='executive'),

    # Live dashboard data
    path(
        'data.json',
        views_executive.dashboard_data_ajax,
        name='data_ajax',
    ),

    # Legacy analytics redirects to executive
    path(
        'analytics/',
        lambda request: redirect('dashboard:executive'),
        name='analytics',
    ),

    # Admin dashboard utilities
    path(
        'admin/ageing/<str:bucket>/',
        views.ageing_detail,
        name='ageing_detail',
    ),
    path(
        'admin/refresh-ai/',
        views.refresh_feedback_ai,
        name='refresh_feedback_ai',
    ),
]