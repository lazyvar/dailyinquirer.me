from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('messages/', views.on_incoming_message, name='messages'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('settings/', views.settings, name='settings'),
    path('resend_confirmation/', views.resend_confirmation,
         name='resend_confirmation'),
    path('unconfirmed_email/', views.unconfirmed_email,
         name='unconfirmed_email'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
]
