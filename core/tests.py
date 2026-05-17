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
