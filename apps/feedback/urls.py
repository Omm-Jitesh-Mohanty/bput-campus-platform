from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    path('', views.my_feedback, name='my_feedback'),
    path('new/', views.submit_feedback, name='submit'),
]