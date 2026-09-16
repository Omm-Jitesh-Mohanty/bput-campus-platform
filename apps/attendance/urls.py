from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.attendance_view, name='list'),
    path('timetable/', views.timetable_view, name='timetable'),
]