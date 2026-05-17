import json
from unittest.mock import patch

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from authentication.models import User
from authentication.tokens import account_activation_token

from core.models import Entry, Prompt, PromptSend
from core.utils import mail_newsletter, send_prompt_to_user


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


class HomePageTests(TestCase):
    def test_home_renders_editorial_layout(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="home"')
        self.assertContains(response, 'ed-hero')
        self.assertContains(response, 'ed-prompts')

    def test_home_loads_css(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'home.css')

    def test_home_has_no_theme_switcher(self):
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'data-theme')
        self.assertNotContains(response, 'theme-switch')
        self.assertNotContains(response, 'home-theme.js')
        self.assertNotContains(response, 'broadsheet')

    def test_home_highlights_todays_prompt(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'is-today', count=1)

    def test_other_pages_do_not_load_home_css(self):
        response = self.client.get(reverse('terms'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'home.css')

    def test_home_cta_links_are_correct(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'href="/register/"')
        self.assertContains(response, 'href="/login/"')


class LogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='member@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.save()

    def test_settings_page_logout_control_uses_post(self):
        """The settings page must log out via POST, not a GET link.

        Django's LogoutView only accepts POST; a bare <a href="/logout/">
        issues a GET and the server responds 405 Method Not Allowed.
        """
        self.client.force_login(self.user)
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<a href="/logout/"')
        self.assertContains(response, 'action="/logout/"')

    def test_get_logout_is_rejected(self):
        """A GET to /logout/ is the exact failure from the bug report."""
        self.client.force_login(self.user)
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)

    def test_post_logout_logs_user_out_and_redirects_home(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, '/')
        # The user is anonymous on the next request.
        followup = self.client.get(reverse('settings'))
        self.assertNotEqual(followup.status_code, 200)


class AuthPagesTests(TestCase):
    def _assert_editorial_shell(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'auth.css')
        self.assertNotContains(response, 'bootstrap.css')

    def test_login_page(self):
        self._assert_editorial_shell(self.client.get(reverse('login')))

    def test_register_page(self):
        self._assert_editorial_shell(self.client.get(reverse('register')))

    def test_password_reset_form_page(self):
        self._assert_editorial_shell(self.client.get(reverse('password_reset')))

    def test_password_reset_done_page(self):
        self._assert_editorial_shell(self.client.get(reverse('password_reset_done')))

    def test_password_reset_confirm_page(self):
        url = reverse('password_reset_confirm',
                      kwargs={'uidb64': 'MQ', 'token': 'aaa-bbb'})
        self._assert_editorial_shell(self.client.get(url))

    def test_password_reset_complete_page(self):
        self._assert_editorial_shell(self.client.get(reverse('password_reset_complete')))

    def test_resend_confirmation_page(self):
        self._assert_editorial_shell(self.client.get(reverse('resend_confirmation')))

    def test_unconfirmed_email_page(self):
        self._assert_editorial_shell(self.client.get(reverse('unconfirmed_email')))

    def test_activation_email_sent_page(self):
        response = self.client.post(reverse('register'), {
            'email': 'authtest@example.com',
            'timezone': 'US/Eastern',
            'password1': 'mostdope1',
            'password2': 'mostdope1',
        })
        self._assert_editorial_shell(response)

    def test_login_uses_editorial_form_markup(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'auth-input')
        self.assertContains(response, 'auth-btn')
        self.assertNotContains(response, 'form-control')


@override_settings(INBOUND_SHARED_SECRET='test-secret')
class IncomingMessageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.confirmed_email = True
        self.user.save()
        self.prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())
        self.url = reverse('messages')

    def post(self, payload, secret='test-secret'):
        headers = {}
        if secret is not None:
            headers['HTTP_X_INBOUND_SECRET'] = secret
        return self.client.post(
            self.url, data=json.dumps(payload),
            content_type='application/json', **headers)

    def test_rejects_missing_secret(self):
        response = self.post(
            {'sender': 'writer@example.com', 'stripped-text': 'hi'},
            secret=None)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Entry.objects.count(), 0)

    def test_rejects_wrong_secret(self):
        response = self.post(
            {'sender': 'writer@example.com', 'stripped-text': 'hi'},
            secret='wrong-secret')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Entry.objects.count(), 0)

    def test_creates_entry_for_known_sender(self):
        response = self.post(
            {'sender': 'writer@example.com', 'stripped-text': 'My entry.'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Entry.objects.count(), 1)
        entry = Entry.objects.get()
        self.assertEqual(entry.content, 'My entry.')
        self.assertEqual(entry.author, self.user)
        self.assertEqual(entry.prompt, self.prompt)

    def test_unknown_sender_creates_no_entry(self):
        response = self.post(
            {'sender': 'stranger@example.com', 'stripped-text': 'hi'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Entry.objects.count(), 0)

    def test_missing_fields_returns_400(self):
        response = self.post({'sender': 'writer@example.com'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Entry.objects.count(), 0)

    def test_duplicate_entry_not_created_twice(self):
        Entry.objects.create(
            content='first', author=self.user,
            prompt=self.prompt, pub_date=timezone.now())
        response = self.post(
            {'sender': 'writer@example.com', 'stripped-text': 'second'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Entry.objects.count(), 1)


class MailNewsletterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='nl@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.save()

    def test_returns_prompt_and_sends_when_prompt_exists(self):
        prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())

        result = mail_newsletter(self.user)

        self.assertEqual(result, prompt)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('nl@example.com', mail.outbox[0].to)

    def test_returns_none_and_sends_nothing_when_no_prompt(self):
        result = mail_newsletter(self.user)

        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_returns_none_when_user_has_no_valid_timezone(self):
        self.user.timezone = 'Not/AZone'
        self.user.save()
        Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())

        result = mail_newsletter(self.user)

        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 0)


class PromptSendModelTests(TestCase):
    def test_unique_per_user_and_prompt(self):
        user = User.objects.create_user(
            email='ps@example.com', password='mostdope1')
        prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())

        PromptSend.objects.create(user=user, prompt=prompt)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PromptSend.objects.create(user=user, prompt=prompt)


class SendPromptToUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='p@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.save()
        self.prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())

    def test_sends_and_records_when_not_sent_before(self):
        result = send_prompt_to_user(self.user)

        self.assertEqual(result, self.prompt)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            PromptSend.objects.filter(
                user=self.user, prompt=self.prompt).count(), 1)

    def test_skips_when_already_sent(self):
        PromptSend.objects.create(user=self.user, prompt=self.prompt)

        result = send_prompt_to_user(self.user)

        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(
            PromptSend.objects.filter(user=self.user).count(), 1)

    def test_force_resends_even_when_already_sent(self):
        PromptSend.objects.create(user=self.user, prompt=self.prompt)

        result = send_prompt_to_user(self.user, force=True)

        self.assertEqual(result, self.prompt)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            PromptSend.objects.filter(user=self.user).count(), 1)

    def test_returns_none_when_no_prompt_for_today(self):
        self.prompt.delete()

        result = send_prompt_to_user(self.user)

        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PromptSend.objects.count(), 0)


class SendDailyMailCommandTests(TestCase):
    def _make_user(self, email, timezone_name='UTC'):
        user = User.objects.create_user(email=email, password='mostdope1')
        user.timezone = timezone_name
        user.confirmed_email = True
        user.is_subscribed = True
        user.save()
        return user

    @patch.object(User, 'local_time')
    def test_skips_users_before_8am(self, mock_local_time):
        self._make_user('early@example.com')
        Prompt.objects.create(question='Q', mail_day=timezone.now())
        mock_local_time.return_value = timezone.now().replace(hour=6)

        call_command('send_daily_mail')

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PromptSend.objects.count(), 0)

    @patch.object(User, 'local_time')
    def test_sends_at_or_after_8am(self, mock_local_time):
        user = self._make_user('due@example.com')
        Prompt.objects.create(question='Q', mail_day=timezone.now())
        mock_local_time.return_value = timezone.now().replace(hour=8)

        call_command('send_daily_mail')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(PromptSend.objects.filter(user=user).count(), 1)

    @patch.object(User, 'local_time')
    def test_skips_unconfirmed_and_unsubscribed(self, mock_local_time):
        mock_local_time.return_value = timezone.now().replace(hour=9)
        Prompt.objects.create(question='Q', mail_day=timezone.now())

        unconfirmed = User.objects.create_user(
            email='unconfirmed@example.com', password='mostdope1')
        unconfirmed.timezone = 'UTC'
        unconfirmed.is_subscribed = True
        unconfirmed.save()

        unsubscribed = User.objects.create_user(
            email='unsubscribed@example.com', password='mostdope1')
        unsubscribed.timezone = 'UTC'
        unsubscribed.confirmed_email = True
        unsubscribed.is_subscribed = False
        unsubscribed.save()

        call_command('send_daily_mail')

        self.assertEqual(len(mail.outbox), 0)

    @patch.object(User, 'local_time')
    def test_does_not_resend_when_already_sent(self, mock_local_time):
        user = self._make_user('once@example.com')
        Prompt.objects.create(question='Q', mail_day=timezone.now())
        mock_local_time.return_value = timezone.now().replace(hour=8)

        call_command('send_daily_mail')
        call_command('send_daily_mail')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(PromptSend.objects.filter(user=user).count(), 1)

    @patch.object(User, 'local_time')
    @patch('core.management.commands.send_daily_mail.send_prompt_to_user')
    def test_one_user_failure_does_not_abort_the_run(
            self, mock_send, mock_local_time):
        mock_local_time.return_value = timezone.now().replace(hour=9)
        self._make_user('a@example.com')
        self._make_user('b@example.com')
        mock_send.side_effect = [Exception('boom'), None]

        call_command('send_daily_mail')

        self.assertEqual(mock_send.call_count, 2)
