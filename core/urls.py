from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dash/', views.dashboard, name='dash'),
    path('entry/<int:pk>/', views.entry_detail, name='entry_detail'),
    path('archived/', views.archived_entries, name='archived_entries'),
    path('register/', views.register, name='register'),
    path('messages/', views.on_incoming_message, name='messages'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('about/', views.about, name='about'),
    path('settings/', views.settings, name='settings'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('resend_confirmation/', views.resend_confirmation,
         name='resend_confirmation'),
    path('unconfirmed_email/', views.unconfirmed_email,
         name='unconfirmed_email'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('settings/email/', views.manage_email_change,
         name='manage_email_change'),
    path('settings/email/confirm/<uidb64>/<token>/',
         views.confirm_email_change, name='confirm_email_change'),
]
