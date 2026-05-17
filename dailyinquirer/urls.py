"""dailyinquirer URL Configuration."""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('', include('core.urls')),
    path('', include('django.contrib.auth.urls')),
]

# Local-only email inbox UI; the app is installed only in dev settings.
if 'django_mail_viewer' in settings.INSTALLED_APPS:
    urlpatterns += [path('mailbox/', include('django_mail_viewer.urls'))]
