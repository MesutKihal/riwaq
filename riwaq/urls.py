from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('courses.urls')),  # Course app handles main routes
    path('users/', include('users.urls')),  # Users app for auth
]

# Redirect root to courses home
urlpatterns += [
    path('', RedirectView.as_view(pattern_name='courses:home', permanent=False)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)