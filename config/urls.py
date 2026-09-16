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

# Non-i18n URLs (admin, i18n switch)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('sw.js', service_worker, name='service_worker'),
    path('', RedirectView.as_view(url='/accounts/', permanent=False)),
]

# i18n-prefixed URLs (auto adds /en/, /hi/, /or/)
urlpatterns += i18n_patterns(
    path('accounts/', include('apps.accounts.urls')),     # ← accounts prefix
    path('dashboard/', include('apps.dashboard.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('tickets/', include('apps.tickets.urls')),
    path('notices/', include('apps.notices.urls')),
    path('feedback/', include('apps.feedback.urls')),
    # path('', include(('apps.accounts.urls', 'accounts_root'), namespace='root')),
    prefix_default_language=False,
)

# Media & static in dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
