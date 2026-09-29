from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Student
    path('', views.my_documents, name='my_documents'),
    path('request/', views.request_document, name='request'),
    path('<int:pk>/download/', views.document_download, name='download'),

    # Admin
    path('admin/', views.admin_documents_list, name='admin_list'),
    path('admin/<int:pk>/revoke/', views.admin_document_revoke, name='admin_revoke'),
    path('admin/<int:pk>/reissue/', views.admin_document_reissue, name='admin_reissue'),

    
]