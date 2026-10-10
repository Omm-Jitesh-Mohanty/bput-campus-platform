from django.urls import path
from . import views

app_name = 'teachers'

urlpatterns = [
    path('', views.teacher_dashboard, name='dashboard'),
    path('classes/', views.my_classes, name='my_classes'),
    path('classes/<int:timetable_id>/cancel/', views.cancel_class, name='cancel_class'),
    path('classes/<int:timetable_id>/attendance/', views.mark_attendance, name='mark_attendance'),
    path('students/', views.my_students, name='my_students'),
]