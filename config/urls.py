"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# from django.contrib import admin
# from django.urls import path

# urlpatterns = [
#     path("admin/", admin.site.urls),
# ]

# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('i18n/', include('django.conf.urls.i18n')),
#     # App URLs will be added in later phases:
#     # path('', include('apps.accounts.urls')),
#     # path('tickets/', include('apps.tickets.urls')),
#     # ...
# ]

# # Serve media files in development
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import RedirectView
from apps.core.views import service_worker
from apps.accounts.admin_access import restricted_admin_site
from django.contrib import admin as django_admin
from apps.core.views_home import home_page
from apps.tickets.views_verify import verify_signature

# for model, model_admin in django_admin.site._registry.items():
#     restricted_admin_site.register(model, model_admin.__class__)
for model, model_admin in django_admin.site._registry.items():
    if model not in restricted_admin_site._registry:
        restricted_admin_site.register(model, model_admin.__class__)

# Non-i18n URLs (admin, i18n switch)
urlpatterns = [
    # path('admin/', admin.site.urls),
    path('admin/', restricted_admin_site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('sw.js', service_worker, name='service_worker'),
    # path('', RedirectView.as_view(url='/accounts/', permanent=False)),
    path('', home_page, name='home'),
    path('app/', include('apps.accounts.urls')),
    path('verify-signature/<int:ticket_id>/<int:step_id>/',verify_signature,name='verify_signature',),
]

from apps.documents import views as doc_views

urlpatterns += [
    path('verify/<uuid:uuid>/', doc_views.verify_document, name='verify_document'),
]

# i18n-prefixed URLs (auto adds /en/, /hi/, /or/)
urlpatterns += i18n_patterns(
    # path('accounts/', include('apps.accounts.urls')),    
    path('dashboard/', include('apps.dashboard.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('tickets/', include('apps.tickets.urls')),
    path('notices/', include('apps.notices.urls')),
    path('feedback/', include('apps.feedback.urls')),
    path('manage/', include('apps.manage_panel.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('documents/', include('apps.documents.urls')),
    path('chat/', include('apps.chatbot.urls')),
    path('emergency/', include('apps.emergency.urls')),
    path('teacher/', include('apps.teachers.urls')),
    # path('', include(('apps.accounts.urls', 'accounts_root'), namespace='root')),
    prefix_default_language=False,
)



# Media & static in dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


handler403 = 'apps.core.views_errors.permission_denied_view'
handler404 = 'apps.core.views_errors.page_not_found_view'
handler500 = 'apps.core.views_errors.server_error_view'
