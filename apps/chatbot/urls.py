from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.chat_home, name='home'),
    path('new/', views.new_session, name='new'),
    path('<int:pk>/', views.chat_session, name='session'),
    path('<int:pk>/send/', views.send_message, name='send'),
    path('<int:pk>/delete/', views.delete_session, name='delete'),
]