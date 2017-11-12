from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^register/', views.register, name='register'),
    url(r'^messages/', views.on_incoming_message, name='messages'),
    url(r'^terms/', views.terms, name='terms'),
    url(r'^privacy/', views.privacy, name='privacy'),
    url(r'^resend_confirmation/', views.resend_confirmation, name='resend_confirmation'),
    url(r'^unconfirmed_email/', views.unconfirmed_email, name='unconfirmed_email'),
    url(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.activate, name='activate'),
]

