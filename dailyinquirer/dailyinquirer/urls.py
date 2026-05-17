"""dailyinquirer URL Configuration."""
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('', include('core.urls')),
    path('', include('django.contrib.auth.urls')),
]
