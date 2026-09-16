from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.student_home, name='student_home'),
    path('admin/', views.admin_home, name='admin_home'),
    path('admin/refresh-ai/', views.refresh_feedback_ai, name='refresh_feedback_ai'),
    path('admin/ageing/<str:bucket>/', views.ageing_detail, name='ageing_detail'),
]