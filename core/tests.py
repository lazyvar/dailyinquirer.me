import json
from datetime import datetime
from unittest.mock import patch

from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from authentication.models import User
from authentication.tokens import account_activation_token, email_change_token

from core.models import Entry, Prompt, PromptSend
from core.templatetags.entry_extras import unwrap
from core.utils import mail_newsletter, send_prompt_to_user


class EmailConfirmationTests(TestCase):
    def test_register_sends_activation_email(self):
        response = self.client.post(reverse('register'), {
            'email': 'newuser@example.com',
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
        response = self.client.get(url, follow=True)

        user.refresh_from_db()
        self.assertTrue(user.confirmed_email)
        # A freshly-confirmed user has not onboarded yet, so the index
        # redirect is itself gated onward to the onboarding page.
        self.assertRedirects(response, reverse('onboarding'))


class TransactionalEmailTemplateTests(TestCase):
    def test_activation_email_is_multipart_html(self):
        self.client.post(reverse('register'), {
            'email': 'tpl@example.com',
            'password1': 'mostdope1',
            'password2': 'mostdope1',
        })
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        html = dict((mime, body) for body, mime in message.alternatives)
        self.assertIn('text/html', html)
        body = html['text/html']
        self.assertIn('The Daily Inquirer', body)
        self.assertIn('Confirm my email', body)
        self.assertIn('An account notice from The Daily Inquirer.', body)
        self.assertNotIn('Unsubscribe', body)


class UnsubscribePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='sub@example.com', password='mostdope1')
        self.user.is_subscribed = True
        self.user.save()

    def _token(self):
        from core.utils import make_unsubscribe_token
        return make_unsubscribe_token(self.user)

    def test_get_with_valid_token_shows_confirm_state(self):
        response = self.client.get(
            reverse('unsubscribe'), {'token': self._token()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Unsubscribe from the daily prompt?')
        self.assertContains(response, 'sub@example.com')

    def test_get_with_bad_token_shows_error_state(self):
        response = self.client.get(
            reverse('unsubscribe'), {'token': 'not-a-real-token'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no longer valid')

    def test_get_when_already_unsubscribed_shows_done_state(self):
        self.user.is_subscribed = False
        self.user.save()
        response = self.client.get(
            reverse('unsubscribe'), {'token': self._token()})
        self.assertContains(response, "You've been unsubscribed")

    def test_post_with_valid_token_unsubscribes(self):
        response = self.client.post(
            reverse('unsubscribe'), {'token': self._token()})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You've been unsubscribed")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscribed)


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
        # Exactly one prompt card carries the server-rendered highlight.
        self.assertContains(response, 'ed-prompt-card is-today', count=1)

    def test_home_highlights_day_with_local_time_js(self):
        response = self.client.get(reverse('index'))
        # Every prompt card carries its JS weekday number, and a script
        # re-highlights the card for the visitor's local time zone.
        for weekday in range(7):
            self.assertContains(response, 'data-weekday="%d"' % weekday)
        self.assertContains(response, 'new Date().getDay()')

    def test_other_pages_do_not_load_home_css(self):
        response = self.client.get(reverse('terms'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'home.css')

    def test_home_cta_links_are_correct(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'href="/register/"')
        self.assertContains(response, 'href="/login/"')


class AboutPageTests(TestCase):
    def test_about_page_renders(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'About The Daily Inquirer')

    def test_about_page_extends_base_layout(self):
        response = self.client.get(reverse('about'))
        self.assertContains(response, 'bootstrap.css')
        self.assertNotContains(response, 'home.css')


class FooterTests(TestCase):
    def test_public_pages_render_shared_footer(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'footer.css')
        self.assertContains(response, 'site-footer')
        self.assertContains(response, 'href="/about/"')
        self.assertContains(response, 'mailto:hello@dailyinquirer.me')

    def test_old_footer_link_class_is_gone(self):
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'footer-link')

    def test_auth_pages_render_shared_footer(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'footer.css')
        self.assertContains(response, 'site-footer')
        self.assertContains(response, 'href="/about/"')
        self.assertNotContains(response, 'auth-footer')


class LogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='member@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.onboarded = True
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
        # The 0007 seed migration populates 30 days of prompts into every
        # database, the test DB included. Clear them so each test controls
        # exactly which prompt exists for "today".
        Prompt.objects.all().delete()
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

    def test_second_reply_creates_another_entry(self):
        """A prompt accepts multiple replies from the same user."""
        Entry.objects.create(
            content='first', author=self.user,
            prompt=self.prompt, pub_date=timezone.now())
        response = self.post(
            {'sender': 'writer@example.com', 'stripped-text': 'second'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Entry.objects.count(), 2)
        self.assertEqual(Entry.objects.filter(content='second').count(), 1)


class TimestampTests(TestCase):
    """Every model carries created_at/updated_at timestamps."""

    def _make_user(self, email='ts@example.com'):
        user = User.objects.create_user(email=email, password='mostdope1')
        user.timezone = 'UTC'
        user.save()
        return user

    def test_user_gets_timestamps_on_create(self):
        user = self._make_user()
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)

    def test_prompt_gets_timestamps_on_create(self):
        prompt = Prompt.objects.create(
            question='What did you learn today?', mail_day=timezone.now())
        self.assertIsNotNone(prompt.created_at)
        self.assertIsNotNone(prompt.updated_at)

    def test_entry_gets_timestamps_on_create(self):
        user = self._make_user('writer@example.com')
        prompt = Prompt.objects.create(
            question='What did you learn today?', mail_day=timezone.now())
        entry = Entry.objects.create(
            content='An entry.', author=user, prompt=prompt,
            pub_date=timezone.now())
        self.assertIsNotNone(entry.created_at)
        self.assertIsNotNone(entry.updated_at)

    def test_updated_at_advances_on_save_but_created_at_is_stable(self):
        prompt = Prompt.objects.create(
            question='Original question?', mail_day=timezone.now())
        original_created = prompt.created_at
        original_updated = prompt.updated_at

        prompt.question = 'Edited question?'
        prompt.save()
        prompt.refresh_from_db()

        self.assertEqual(prompt.created_at, original_created)
        self.assertGreater(prompt.updated_at, original_updated)

    def test_timestamps_are_required(self):
        for model in (User, Prompt, Entry):
            for field_name in ('created_at', 'updated_at'):
                field = model._meta.get_field(field_name)
                self.assertFalse(
                    field.null,
                    f'{model.__name__}.{field_name} should be NOT NULL')


class MailNewsletterTests(TestCase):
    def setUp(self):
        # Drop the prompts the 0007 seed migration leaves in the test DB.
        Prompt.objects.all().delete()
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
        # Drop the prompts the 0007 seed migration leaves in the test DB.
        Prompt.objects.all().delete()
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
    def setUp(self):
        # Drop the prompts the 0007 seed migration leaves in the test DB.
        Prompt.objects.all().delete()

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


class AdminSendPromptButtonTests(TestCase):
    def setUp(self):
        # Drop the prompts the 0007 seed migration leaves in the test DB.
        Prompt.objects.all().delete()
        self.admin = User.objects.create_superuser(
            email='admin@example.com', password='mostdope1')
        self.target = User.objects.create_user(
            email='target@example.com', password='mostdope1')
        self.target.timezone = 'UTC'
        self.target.confirmed_email = True
        self.target.save()
        self.prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())
        self.client.force_login(self.admin)

    def _send_url(self):
        return reverse('admin:authentication_user_send_prompt',
                       kwargs={'pk': self.target.pk})

    def test_button_sends_and_records_a_promptsend(self):
        response = self.client.get(self._send_url())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            PromptSend.objects.filter(user=self.target).count(), 1)

    def test_button_force_resends_when_already_sent(self):
        PromptSend.objects.create(user=self.target, prompt=self.prompt)

        response = self.client.get(self._send_url())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            PromptSend.objects.filter(user=self.target).count(), 1)


class SettingsPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.onboarded = True
        self.user.save()
        self.client.force_login(self.user)

    def test_settings_renders_editorial_layout(self):
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="settings"')
        self.assertContains(response, 'ed-masthead')
        self.assertContains(response, 'ed-card')

    def test_settings_loads_account_css(self):
        response = self.client.get(reverse('settings'))
        self.assertContains(response, 'account.css')

    def test_settings_update_shows_success_alert(self):
        response = self.client.post(reverse('settings'), {
            'subscribed': 'on', 'timezone': 'America/New_York',
            'mail_hour': '8'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ed-alert--ok')


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.onboarded = True
        self.user.save()
        self.client.force_login(self.user)

    def _entry(self, question='A prompt', category='Reflective',
               content='Some words', day=15):
        prompt = Prompt.objects.create(
            question=question, category=category, mail_day=timezone.now())
        return Entry.objects.create(
            content=content, author=self.user, prompt=prompt,
            pub_date=timezone.make_aware(datetime(2026, 1, day, 12, 0)))

    def test_dashboard_renders_editorial_layout(self):
        self._entry()
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="dashboard"')
        self.assertContains(response, 'ed-masthead')
        self.assertContains(response, 'ed-card')

    def test_dashboard_loads_account_css(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'account.css')

    def test_search_matches_entry_content(self):
        self._entry(content='a story about lighthouses')
        self._entry(content='a note about mountains')
        response = self.client.get(reverse('index'), {'q': 'lighthouse'})
        self.assertContains(response, 'lighthouses')
        self.assertNotContains(response, 'mountains')

    def test_search_matches_prompt_question(self):
        self._entry(question='Describe your first car', content='aaa')
        self._entry(question='Write a haiku', content='bbb')
        response = self.client.get(reverse('index'), {'q': 'haiku'})
        self.assertContains(response, 'bbb')
        self.assertNotContains(response, 'aaa')

    def test_date_range_filters_entries(self):
        self._entry(content='january early entry', day=5)
        self._entry(content='january late entry', day=25)
        response = self.client.get(
            reverse('index'), {'from': '2026-01-10', 'to': '2026-01-31'})
        self.assertContains(response, 'late entry')
        self.assertNotContains(response, 'early entry')

    def test_category_filter(self):
        self._entry(category='Narrative', content='narrative entry')
        self._entry(category='Expository', content='expository entry')
        response = self.client.get(reverse('index'), {'category': 'Narrative'})
        self.assertContains(response, 'narrative entry')
        self.assertNotContains(response, 'expository entry')

    def test_sort_oldest_first(self):
        self._entry(content='older one', day=1)
        self._entry(content='newer one', day=28)
        response = self.client.get(reverse('index'), {'sort': 'oldest'})
        body = response.content.decode()
        self.assertLess(body.index('older one'), body.index('newer one'))

    def test_pagination_caps_page_at_25(self):
        for i in range(26):
            self._entry(content='entry number %d' % i)
        response = self.client.get(reverse('index'))
        self.assertEqual(len(response.context['page_obj'].object_list), 25)

    def test_pagination_second_page(self):
        for i in range(26):
            self._entry(content='entry number %d' % i)
        response = self.client.get(reverse('index'), {'page': 2})
        self.assertEqual(len(response.context['page_obj'].object_list), 1)

    def test_pagination_links_preserve_filters(self):
        for i in range(26):
            self._entry(category='Narrative', content='narrative %d' % i)
        response = self.client.get(reverse('index'), {'category': 'Narrative'})
        self.assertContains(response, 'category=Narrative')
        self.assertContains(response, 'page=2')

    def test_result_count_hidden_without_filters(self):
        self._entry()
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'ed-count')

    def test_result_count_shown_when_searching(self):
        self._entry(content='findable text')
        response = self.client.get(reverse('index'), {'q': 'findable'})
        self.assertContains(response, 'ed-count')

    def test_filter_panel_open_when_filtering(self):
        self._entry()
        response = self.client.get(reverse('index'), {'category': 'Reflective'})
        self.assertContains(response, '<details class="ed-filter-disclosure" open>')

    def test_filter_panel_closed_by_default(self):
        self._entry()
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'ed-filter-disclosure" open')

    def test_empty_state_no_entries(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'No entries yet')

    def test_empty_state_no_matches(self):
        self._entry(content='something')
        response = self.client.get(reverse('index'), {'q': 'zzzznomatch'})
        self.assertContains(response, 'No entries match')


class EntryContentUnwrapTests(TestCase):
    """The `unwrap` filter de-flows email hard-wrapping so entries fill the card."""

    def test_joins_hard_wrapped_lines_within_a_paragraph(self):
        wrapped = ("The night was bright, lit by a proud moon.\n"
                   "The desert town of Winco hasn't\n"
                   "felt a night like this.")
        self.assertEqual(
            unwrap(wrapped),
            "The night was bright, lit by a proud moon. "
            "The desert town of Winco hasn't felt a night like this.",
        )

    def test_keeps_blank_line_paragraph_breaks(self):
        text = "First paragraph one\ntwo\n\nSecond paragraph"
        self.assertEqual(unwrap(text), "First paragraph one two\n\nSecond paragraph")

    def test_leaves_flowing_text_untouched(self):
        flowing = "AWS is a modern marvel and ingenious business move from Amazon."
        self.assertEqual(unwrap(flowing), flowing)

    def test_normalizes_crlf_and_handles_empty(self):
        self.assertEqual(unwrap("a\r\nb"), "a b")
        self.assertEqual(unwrap(""), "")
        self.assertIsNone(unwrap(None))

    def test_dashboard_renders_hard_wrapped_entry_without_inner_br(self):
        user = User.objects.create_user(email='wrap@example.com', password='mostdope1')
        user.timezone = 'UTC'
        user.confirmed_email = True
        user.onboarded = True
        user.save()
        prompt = Prompt.objects.create(question='Tell a story.', mail_day=timezone.now())
        Entry.objects.create(
            author=user, prompt=prompt, pub_date=timezone.now(),
            content="The night was bright.\nThe town slept.\n\nThen dawn came.",
        )
        self.client.force_login(user)
        response = self.client.get(reverse('index'))
        self.assertContains(response, '<p>The night was bright. The town slept.</p>')
        self.assertContains(response, '<p>Then dawn came.</p>')
        self.assertNotContains(response, 'bright.<br>')


class RepairMigrationHistoryTests(TestCase):
    """`repair_migration_history` un-records an orphaned 0007 tip.

    Production once had core.0007_merge / 0007_seed recorded as applied
    while their dependency core.0005_promptsend never was, so `migrate`'s
    consistency check crashed the container on boot. The command removes
    the orphaned ledger rows so `migrate` can replay the chain forward.
    """

    PROMPTSEND = ("core", "0005_promptsend")
    MERGE = ("core", "0007_merge_20260517_2159")
    SEED = ("core", "0007_seed_thirty_days_of_prompts")

    def test_un_records_0007_tip_applied_without_promptsend(self):
        recorder = MigrationRecorder(connection)
        # Simulate the broken production ledger: the 0007 tip is recorded
        # as applied, but its dependency 0005_promptsend never was.
        recorder.record_unapplied(*self.PROMPTSEND)
        applied = recorder.applied_migrations()
        self.assertIn(self.MERGE, applied)
        self.assertIn(self.SEED, applied)

        call_command("repair_migration_history")

        applied = recorder.applied_migrations()
        self.assertNotIn(self.MERGE, applied)
        self.assertNotIn(self.SEED, applied)

    def test_no_op_when_history_is_consistent(self):
        recorder = MigrationRecorder(connection)
        before = set(recorder.applied_migrations())

        call_command("repair_migration_history")

        self.assertEqual(set(recorder.applied_migrations()), before)


class EmailChangeModelTests(TestCase):
    def test_new_user_has_no_pending_email(self):
        user = User.objects.create_user(
            email='m@example.com', password='mostdope1')
        self.assertIsNone(user.pending_email)

    def test_email_change_token_validates_for_pending_user(self):
        user = User.objects.create_user(
            email='old@example.com', password='mostdope1')
        user.pending_email = 'new@example.com'
        user.save()
        token = email_change_token.make_token(user)
        self.assertTrue(email_change_token.check_token(user, token))

    def test_email_change_token_invalid_after_swap(self):
        user = User.objects.create_user(
            email='old@example.com', password='mostdope1')
        user.pending_email = 'new@example.com'
        user.save()
        token = email_change_token.make_token(user)
        user.email = 'new@example.com'
        user.pending_email = None
        user.save()
        self.assertFalse(email_change_token.check_token(user, token))


class EmailChangeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='old@example.com', password='mostdope1')
        self.client.force_login(self.user)

    def test_request_available_email_sets_pending_and_sends_two_emails(self):
        response = self.client.post(reverse('manage_email_change'), {
            'action': 'request', 'email': 'new@example.com'})
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.pending_email, 'new@example.com')
        self.assertEqual(self.user.email, 'old@example.com')
        self.assertEqual(len(mail.outbox), 2)
        by_subject = {m.subject: m for m in mail.outbox}
        confirm = by_subject['Confirm your new Daily Inquirer email']
        notice = by_subject['Your Daily Inquirer email is being changed']
        self.assertEqual(confirm.to, ['new@example.com'])
        self.assertEqual(notice.to, ['old@example.com'])

    def test_request_taken_email_does_not_set_pending(self):
        User.objects.create_user(
            email='taken@example.com', password='mostdope1')
        response = self.client.post(reverse('manage_email_change'), {
            'action': 'request', 'email': 'taken@example.com'})
        self.user.refresh_from_db()
        self.assertIsNone(self.user.pending_email)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(response.status_code, 200)

    def test_request_own_email_does_not_set_pending(self):
        self.client.post(reverse('manage_email_change'), {
            'action': 'request', 'email': 'old@example.com'})
        self.user.refresh_from_db()
        self.assertIsNone(self.user.pending_email)
        self.assertEqual(len(mail.outbox), 0)

    def test_cancel_clears_pending_email(self):
        self.user.pending_email = 'new@example.com'
        self.user.save()
        response = self.client.post(reverse('manage_email_change'), {
            'action': 'cancel'})
        self.user.refresh_from_db()
        self.assertIsNone(self.user.pending_email)
        self.assertEqual(response.status_code, 200)

    def test_cancel_with_no_pending_change_is_a_noop(self):
        response = self.client.post(reverse('manage_email_change'), {
            'action': 'cancel'})
        self.user.refresh_from_db()
        self.assertIsNone(self.user.pending_email)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('email_change_canceled', response.context)

    def test_resend_sends_confirmation_again(self):
        self.user.pending_email = 'new@example.com'
        self.user.save()
        response = self.client.post(reverse('manage_email_change'), {
            'action': 'resend'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.pending_email, 'new@example.com')
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(response.status_code, 200)

    def _confirm_url(self, user):
        return reverse('confirm_email_change', kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': email_change_token.make_token(user),
        })

    def test_confirm_swaps_the_email_address(self):
        self.user.pending_email = 'new@example.com'
        self.user.save()
        response = self.client.get(self._confirm_url(self.user), follow=True)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'new@example.com')
        self.assertIsNone(self.user.pending_email)
        self.assertRedirects(response, '/settings/?email_change=confirmed')
        self.assertContains(response, 'has been updated')

    def test_confirm_link_rejected_after_swap(self):
        self.user.pending_email = 'new@example.com'
        self.user.save()
        url = self._confirm_url(self.user)
        self.user.email = 'new@example.com'
        self.user.pending_email = None
        self.user.save()
        response = self.client.get(url)
        self.assertContains(response, 'invalid')

    def test_confirm_when_address_taken_meanwhile(self):
        self.user.pending_email = 'new@example.com'
        self.user.save()
        url = self._confirm_url(self.user)
        User.objects.create_user(
            email='new@example.com', password='mostdope1')
        response = self.client.get(url, follow=True)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')
        self.assertIsNone(self.user.pending_email)
        self.assertRedirects(response, '/settings/?email_change=unavailable')
        self.assertContains(response, 'no longer available')

    def test_confirm_with_malformed_link_is_rejected(self):
        url = reverse('confirm_email_change', kwargs={
            'uidb64': 'AAAA', 'token': 'bad-token'})
        response = self.client.get(url)
        self.assertContains(response, 'invalid')

    def test_confirm_with_no_pending_change_is_rejected(self):
        token = email_change_token.make_token(self.user)
        url = reverse('confirm_email_change', kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(self.user.pk)),
            'token': token,
        })
        response = self.client.get(url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')
        self.assertContains(response, 'invalid')

    def test_settings_shows_email_with_edit_affordance(self):
        response = self.client.get(reverse('settings'))
        self.assertContains(response, 'old@example.com')
        self.assertContains(response, 'ed-email-edit')

    def test_settings_shows_pending_banner(self):
        self.user.pending_email = 'new@example.com'
        self.user.save()
        response = self.client.get(reverse('settings'))
        self.assertContains(response, 'ed-pending')
        self.assertContains(response, 'new@example.com')

    def test_request_taken_email_renders_error_alert(self):
        User.objects.create_user(
            email='taken@example.com', password='mostdope1')
        response = self.client.post(reverse('manage_email_change'), {
            'action': 'request', 'email': 'taken@example.com'})
        self.assertContains(response, 'already in use')
        self.assertContains(response, '<details class="ed-email-edit" open>')

    def test_request_available_email_renders_pending_alert(self):
        response = self.client.post(reverse('manage_email_change'), {
            'action': 'request', 'email': 'new@example.com'})
        self.assertContains(response, 'ed-alert--ok')
        self.assertContains(response, 'Confirmation sent to new@example.com')


class OnboardingPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='newbie@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.save()
        self.client.force_login(self.user)

    def test_get_renders_the_form(self):
        response = self.client.get(reverse('onboarding'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="subscribed"')
        self.assertContains(response, 'name="timezone"')
        self.assertContains(response, 'name="mail_hour"')

    def test_post_completes_onboarding(self):
        response = self.client.post(reverse('onboarding'), {
            'subscribed': 'on',
            'timezone': 'America/New_York',
            'mail_hour': '9',
        })
        self.assertRedirects(response, reverse('index'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.onboarded)
        self.assertTrue(self.user.is_subscribed)
        self.assertEqual(self.user.timezone, 'America/New_York')
        self.assertEqual(self.user.mail_time, 540)

    def test_post_without_subscribe_opts_the_user_out(self):
        self.client.post(reverse('onboarding'), {
            'timezone': 'UTC', 'mail_hour': '8'})
        self.user.refresh_from_db()
        self.assertTrue(self.user.onboarded)
        self.assertFalse(self.user.is_subscribed)

    def test_already_onboarded_user_is_redirected_to_index(self):
        self.user.onboarded = True
        self.user.save()
        response = self.client.get(reverse('onboarding'))
        self.assertRedirects(response, reverse('index'))

    def test_page_autodetects_timezone_with_js(self):
        response = self.client.get(reverse('onboarding'))
        self.assertContains(response, 'resolvedOptions().timeZone')

    def test_page_offers_morning_day_night_presets(self):
        response = self.client.get(reverse('onboarding'))
        for label in ('Morning', 'Day', 'Night'):
            self.assertContains(response, label)
        # 8am / 12pm / 7pm recommendation buttons drive the mail_hour select.
        for hour in ('8', '12', '19'):
            self.assertContains(response, 'data-hour="%s"' % hour)

    def test_page_keeps_the_full_hour_dropdown(self):
        response = self.client.get(reverse('onboarding'))
        # The presets are only recommendations; every hour is still pickable.
        self.assertContains(response, '<select class="ed-input" name="mail_hour"')
        self.assertContains(response, 'value="15"')

    def test_page_has_a_logout_button(self):
        response = self.client.get(reverse('onboarding'))
        self.assertContains(response, 'action="/logout/"')

    def test_post_with_night_preset_sets_7pm(self):
        self.client.post(reverse('onboarding'), {
            'timezone': 'UTC', 'mail_hour': '19'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.mail_time, 1140)


class OnboardingGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='gated@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.save()

    def test_not_onboarded_user_is_redirected_to_onboarding(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('settings'))
        self.assertRedirects(response, reverse('onboarding'))

    def test_onboarded_user_reaches_the_page(self):
        self.user.onboarded = True
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)

    def test_onboarding_page_itself_is_not_redirected(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('onboarding'))
        self.assertEqual(response.status_code, 200)

    def test_logout_path_is_not_redirected(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('index'))

    def test_anonymous_user_is_not_redirected(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)


class SettingsSendTimeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='clock@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.onboarded = True
        self.user.save()
        self.client.force_login(self.user)

    def test_settings_page_shows_delivery_time_selector(self):
        response = self.client.get(reverse('settings'))
        self.assertContains(response, 'name="mail_hour"')

    def test_post_updates_mail_time(self):
        response = self.client.post(reverse('settings'), {
            'subscribed': 'on',
            'timezone': 'UTC',
            'mail_hour': '7',
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.mail_time, 420)


class SignupWithoutTimezoneTests(TestCase):
    def test_register_succeeds_with_only_email_and_password(self):
        response = self.client.post(reverse('register'), {
            'email': 'notz@example.com',
            'password1': 'mostdope1',
            'password2': 'mostdope1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        user = User.objects.get(email='notz@example.com')
        self.assertEqual(user.timezone, '')
        self.assertFalse(user.onboarded)

    def test_register_page_has_no_timezone_field(self):
        response = self.client.get(reverse('register'))
        self.assertNotContains(response, 'name="timezone"')


class SendDailyMailUsesMailHourTests(TestCase):
    def setUp(self):
        # Drop the prompts the 0007 seed migration leaves in the test DB.
        Prompt.objects.all().delete()

    def _make_user(self, email, mail_time):
        user = User.objects.create_user(email=email, password='mostdope1')
        user.timezone = 'UTC'
        user.confirmed_email = True
        user.onboarded = True
        user.is_subscribed = True
        user.mail_time = mail_time
        user.save()
        return user

    @patch.object(User, 'local_time')
    def test_skips_user_before_their_chosen_hour(self, mock_local_time):
        self._make_user('late@example.com', mail_time=600)  # 10:00
        Prompt.objects.create(question='Q', mail_day=timezone.now())
        mock_local_time.return_value = timezone.now().replace(hour=9)

        call_command('send_daily_mail')

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PromptSend.objects.count(), 0)

    @patch.object(User, 'local_time')
    def test_sends_at_the_user_chosen_hour(self, mock_local_time):
        user = self._make_user('late@example.com', mail_time=600)  # 10:00
        Prompt.objects.create(question='Q', mail_day=timezone.now())
        mock_local_time.return_value = timezone.now().replace(hour=10)

        call_command('send_daily_mail')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(PromptSend.objects.filter(user=user).count(), 1)


class EmailChangeEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.onboarded = True
        self.user.save()
        self.client.force_login(self.user)

    def test_email_change_sends_two_html_emails(self):
        self.client.post(reverse('manage_email_change'), {
            'action': 'request',
            'email': 'new@example.com',
        })
        self.assertEqual(len(mail.outbox), 2)
        for message in mail.outbox:
            html = dict((mime, body) for body, mime in message.alternatives)
            self.assertIn('text/html', html)
            self.assertIn('The Daily Inquirer', html['text/html'])
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ['new@example.com', 'owner@example.com'])


class PasswordResetEmailTests(TestCase):
    def test_password_reset_sends_html_email(self):
        User.objects.create_user(
            email='reset@example.com', password='mostdope1')
        response = self.client.post(reverse('password_reset'), {
            'email': 'reset@example.com',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        html = dict((mime, body) for body, mime in message.alternatives)
        self.assertIn('text/html', html)
        self.assertIn('The Daily Inquirer', html['text/html'])
        self.assertIn('Reset my password', html['text/html'])
        self.assertEqual(message.subject,
                         'Reset your Daily Inquirer password')


class UnsubscribeOneClickTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='oneclick@example.com', password='mostdope1')
        self.user.is_subscribed = True
        self.user.save()

    def _token(self):
        from core.utils import make_unsubscribe_token
        return make_unsubscribe_token(self.user)

    def test_post_with_valid_token_unsubscribes(self):
        response = self.client.post(
            reverse('unsubscribe_one_click') + '?token=' + self._token())
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscribed)

    def test_post_with_bad_token_returns_400(self):
        response = self.client.post(
            reverse('unsubscribe_one_click') + '?token=garbage')
        self.assertEqual(response.status_code, 400)

    def test_get_is_rejected(self):
        response = self.client.get(
            reverse('unsubscribe_one_click') + '?token=' + self._token())
        self.assertEqual(response.status_code, 405)
