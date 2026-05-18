from django.test import TestCase, override_settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from authentication.models import User
from core.models import Prompt


class AdminSendPromptTests(TestCase):
    def setUp(self):
        # The 0007 seed migration populates 30 days of prompts into every
        # database, the test DB included. Clear them so each test controls
        # exactly which prompt exists for "today".
        Prompt.objects.all().delete()
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

    @override_settings(STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    })
    def test_change_page_renders_send_prompt_button(self):
        change_url = reverse('admin:authentication_user_change',
                             args=[self.target.pk])

        response = self.client.get(change_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.send_url)
        self.assertContains(response, "Send today's prompt")


class UserOnboardingFieldsTests(TestCase):
    def test_new_user_defaults(self):
        user = User.objects.create_user(
            email='fresh@example.com', password='mostdope1')
        self.assertFalse(user.onboarded)
        self.assertEqual(user.mail_time, 480)
        self.assertEqual(user.timezone, '')

    def test_mail_hour_property_converts_minutes_to_hour(self):
        user = User.objects.create_user(
            email='hour@example.com', password='mostdope1')
        user.mail_time = 540
        self.assertEqual(user.mail_hour, 9)
