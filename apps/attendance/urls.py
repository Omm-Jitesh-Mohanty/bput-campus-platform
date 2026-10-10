from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.attendance_view, name='list'),
    path('timetable/', views.timetable_view, name='timetable'),
    path('today/', views.today_plan, name='today_plan'),
    path('today.json', views.today_plan_json, name='today_plan_json'),
]