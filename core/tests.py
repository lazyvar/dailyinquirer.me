import json
from datetime import datetime

from django.test import TestCase, override_settings
from django.utils import timezone
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from authentication.models import User
from authentication.tokens import account_activation_token

from core.models import Entry, Prompt
from core.utils import mail_newsletter


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


class SettingsPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.confirmed_email = True
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
            'subscribed': 'on', 'timezone': 'America/New_York'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ed-alert--ok')


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.confirmed_email = True
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
