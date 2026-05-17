from django.test import TestCase
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from authentication.models import User
from authentication.tokens import account_activation_token


class EmailConfirmationTests(TestCase):
    def test_register_sends_activation_email(self):
        response = self.client.post(reverse('register'), {
            'email': 'newuser@example.com',
            'timezone': 'US/Eastern',
            'password1': 'mostdope1',
            'password2': 'mostdope1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('newuser@example.com', mail.outbox[0].to)

    def test_activation_link_confirms_email_and_logs_in(self):
        user = User.objects.create_user(
            email='pending@example.com', password='mostdope1')
        self.assertFalse(user.confirmed_email)

        url = reverse('activate', kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': account_activation_token.make_token(user),
        })
        response = self.client.get(url)

        user.refresh_from_db()
        self.assertTrue(user.confirmed_email)
        self.assertRedirects(response, reverse('index'))
