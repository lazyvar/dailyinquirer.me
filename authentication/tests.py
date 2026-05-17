from django.test import TestCase
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from authentication.models import User
from core.models import Prompt


class AdminSendPromptTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@example.com', password='mostdope1')
        self.admin.timezone = 'UTC'
        self.admin.save()
        self.client.force_login(self.admin)

        self.target = User.objects.create_user(
            email='reader@example.com', password='mostdope1')
        self.target.timezone = 'UTC'
        self.target.save()

        self.send_url = reverse('admin:authentication_user_send_prompt',
                                args=[self.target.pk])

    def test_sends_email_when_prompt_exists(self):
        Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())

        response = self.client.get(self.send_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reader@example.com', mail.outbox[0].to)

    def test_sends_nothing_when_no_prompt(self):
        response = self.client.get(self.send_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
