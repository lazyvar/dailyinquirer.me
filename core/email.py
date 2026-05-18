"""Centralised email sending: one multipart message per call, rendered
from the shared templates in templates/email/."""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from authentication.tokens import account_activation_token, email_change_token


def send_templated_email(*, subject, to, template, context,
                         from_email=None, headers=None):
    """Render email/<template>.html and .txt and send one multipart message."""
    html_body = render_to_string(f'email/{template}.html', context)
    text_body = render_to_string(f'email/{template}.txt', context)
    message = EmailMultiAlternatives(
        subject,
        text_body,
        from_email or settings.DEFAULT_FROM_EMAIL,
        [to],
        headers=headers,
    )
    message.attach_alternative(html_body, 'text/html')
    message.send()
    return message


def send_activation_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    confirm_url = request.build_absolute_uri(
        reverse('activate', kwargs={'uidb64': uid, 'token': token}))
    send_templated_email(
        subject='Activate your Daily Inquirer Account',
        to=user.email,
        template='account_activation',
        context={'user': user, 'confirm_url': confirm_url},
    )


def send_email_change_emails(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_change_token.make_token(user)
    confirm_url = request.build_absolute_uri(
        reverse('confirm_email_change', kwargs={'uidb64': uid, 'token': token}))
    send_templated_email(
        subject='Confirm your new Daily Inquirer email',
        to=user.pending_email,
        template='email_change_confirm',
        context={'pending_email': user.pending_email,
                 'confirm_url': confirm_url},
    )
    send_templated_email(
        subject='Your Daily Inquirer email is being changed',
        to=user.email,
        template='email_change_notice',
        context={'pending_email': user.pending_email},
    )
