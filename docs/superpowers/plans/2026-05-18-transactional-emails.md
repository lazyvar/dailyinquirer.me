# Unified Email Template and Unsubscribe Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every email the site sends one consistent HTML template, and add a proper daily-prompt unsubscribe flow (confirmation page + `List-Unsubscribe` header).

**Architecture:** A shared `templates/email/base.html` provides the chrome (masthead, folder tab, white box, footer); each email extends it. A new `core/email.py` module centralises multipart sending. Unsubscribe links carry a signed token so they work without login, served by a public confirmation page and an RFC 8058 one-click endpoint.

**Tech Stack:** Django 5, Django template inheritance, `django.core.signing`, `EmailMultiAlternatives`, `manage.py test`.

Spec: `docs/superpowers/specs/2026-05-18-transactional-emails-design.md`

---

## File Structure

**New**

- `templates/email/base.html` — shared email chrome; blocks `preheader`, `tab_label`, `content`, `footer`.
- `templates/email/_button.html` — reusable table-based CTA button (`url`, `label`).
- `templates/email/_footer_transactional.html` — Terms · Privacy + "account notice" fine print.
- `templates/email/_footer_daily.html` — Manage notifications · Unsubscribe, then quieter Terms · Privacy.
- `templates/email/account_activation.html` / `.txt`
- `templates/email/email_change_confirm.html` / `.txt`
- `templates/email/email_change_notice.html` / `.txt`
- `templates/email/password_reset.html` / `.txt`
- `templates/email/password_reset_subject.txt`
- `templates/email/daily_prompt.html` / `.txt`
- `core/email.py` — `send_templated_email`, `send_activation_email`, `send_email_change_emails`.
- `core/templates/core/unsubscribe.html` — public confirm/done/error page.

**Modified**

- `dailyinquirer/settings/base.py`, `dailyinquirer/settings/local.py` — `SITE_URL`.
- `core/utils.py` — unsubscribe token helpers; `mail_newsletter` uses `send_templated_email`.
- `core/views.py` — drop the two send-email functions (moved to `core/email.py`); add `unsubscribe`, `unsubscribe_one_click` views.
- `core/urls.py` — two unsubscribe routes.
- `dailyinquirer/urls.py` — `password_reset` override route.
- `core/tests.py` — new test classes.

**Removed**

- `core/templates/core/daily_email.html`
- `templates/registration/confirm_email.html`, `change_email_confirm.html`, `change_email_notice.html`, `password_reset_email.html`

---

## Task 1: `SITE_URL` setting

**Files:**
- Modify: `dailyinquirer/settings/base.py:120` (near `DEFAULT_FROM_EMAIL`)
- Modify: `dailyinquirer/settings/local.py`

- [ ] **Step 1: Add `SITE_URL` to base settings**

In `dailyinquirer/settings/base.py`, directly below the `DEFAULT_FROM_EMAIL` line, add:

```python
# Absolute base URL used when building links inside emails (no request
# is available in the daily-send cron). Overridden per environment.
SITE_URL = 'https://www.dailyinquirer.me'
```

- [ ] **Step 2: Override `SITE_URL` for local development**

In `dailyinquirer/settings/local.py`, append at the end of the file:

```python
SITE_URL = 'http://localhost:8000'
```

- [ ] **Step 3: Verify settings load**

Run: `python manage.py check`
Expected: `System check identified no issues`

- [ ] **Step 4: Commit**

```bash
git add dailyinquirer/settings/base.py dailyinquirer/settings/local.py
git commit -m "feat: add SITE_URL setting for absolute email links"
```

---

## Task 2: Shared email base template and `send_templated_email` helper

This task builds the shared chrome and the sending helper, and converts the **account activation** email to prove them out end to end.

**Files:**
- Create: `templates/email/base.html`
- Create: `templates/email/_button.html`
- Create: `templates/email/_footer_transactional.html`
- Create: `templates/email/account_activation.html`
- Create: `templates/email/account_activation.txt`
- Create: `core/email.py`
- Modify: `core/views.py` (remove `send_activation_email`, import it instead)
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing test**

Append to `core/tests.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.TransactionalEmailTemplateTests -v 2`
Expected: FAIL — the current plain-text email has no `text/html` alternative.

- [ ] **Step 3: Create the base email template**

Create `templates/email/base.html`:

```html
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <title>The Daily Inquirer</title>
    <style type="text/css">
        @font-face {
            font-family: 'Elms Sans';
            font-style: normal;
            font-weight: 400;
            src: url('https://www.dailyinquirer.me/static/font/ElmsSans-latin.woff2') format('woff2');
        }
        @font-face {
            font-family: 'Special Elite';
            font-style: normal;
            font-weight: 400;
            src: url('https://www.dailyinquirer.me/static/font/SpecialElite-latin.woff2') format('woff2');
        }
        body { margin: 0; padding: 0; width: 100% !important; }
        a { color: #009302; }
        @media only screen and (max-width: 620px) {
            .di-container { width: 100% !important; }
            .di-pad { padding-left: 22px !important; padding-right: 22px !important; }
            .di-question { font-size: 21px !important; }
            .di-name { font-size: 32px !important; }
        }
    </style>
</head>

<body style="margin:0; padding:0; background-color:#fbfaf5;">
    <div style="display:none; max-height:0; overflow:hidden; opacity:0; color:#fbfaf5; font-size:1px; line-height:1px;">
        {% block preheader %}A message from The Daily Inquirer.{% endblock %}
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fbfaf5;">
        <tr>
            <td align="center" style="padding:40px 16px;">

                <table role="presentation" class="di-container" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px; max-width:600px;">

                    <!-- Folder tab -->
                    <tr>
                        <td style="padding-left:24px;">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="background-color:#009302; border-radius:7px 7px 0 0; padding:8px 16px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:11px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:#ffffff;">
                                        {% block tab_label %}{% endblock %}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Masthead + content box -->
                    <tr>
                        <td class="di-pad" style="background-color:#ffffff; border:1px solid #d8d4cc; border-left:5px solid #009302; border-radius:8px; padding:34px 30px;">
                            <h1 class="di-name" style="margin:0 0 32px; font-family:'Special Elite',Georgia,'Times New Roman',serif; font-size:38px; line-height:1.05; letter-spacing:-0.5px; color:#1a1a1a;">
                                The Daily Inquirer
                            </h1>
                            {% block content %}{% endblock %}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding:26px 16px 0; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:12px; color:#8a8a8a;">
                            {% block footer %}{% endblock %}
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>
</body>

</html>
```

- [ ] **Step 4: Create the button include**

Create `templates/email/_button.html`:

```html
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:4px 0;">
    <tr>
        <td style="background-color:#009302; border-radius:6px;">
            <a href="{{ url }}" style="display:inline-block; padding:13px 26px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:14px; font-weight:700; color:#ffffff; text-decoration:none;">
                {{ label }}
            </a>
        </td>
    </tr>
</table>
```

- [ ] **Step 5: Create the transactional footer include**

Create `templates/email/_footer_transactional.html`:

```html
<a href="https://www.dailyinquirer.me/terms/" style="color:#8a8a8a; text-decoration:none;">Terms</a>
<span style="color:#cbc6b8;">&nbsp;&middot;&nbsp;</span>
<a href="https://www.dailyinquirer.me/privacy/" style="color:#8a8a8a; text-decoration:none;">Privacy</a>
<div style="padding-top:7px; font-size:10px; color:#b3afa3;">An account notice from The Daily Inquirer.</div>
```

- [ ] **Step 6: Create the account activation HTML template**

Create `templates/email/account_activation.html`:

```html
{% extends "email/base.html" %}

{% block preheader %}Confirm your email to start receiving your daily writing prompt.{% endblock %}
{% block tab_label %}Your Account{% endblock %}

{% block content %}
<h2 style="margin:0 0 14px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:22px; font-weight:600; line-height:1.35; color:#1a1a1a;">
    Confirm your email address
</h2>
<p style="margin:0 0 22px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:14px; line-height:1.6; color:#444444;">
    Welcome! Tap the button below to confirm your email and start receiving your daily writing prompt.
</p>
{% include "email/_button.html" with url=confirm_url label="Confirm my email" %}
<p style="margin:22px 0 0; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:12px; line-height:1.6; color:#8a8a8a;">
    If the button doesn't work, paste this link into your browser:<br>
    <a href="{{ confirm_url }}" style="color:#009302; word-break:break-all;">{{ confirm_url }}</a>
</p>
{% endblock %}

{% block footer %}{% include "email/_footer_transactional.html" %}{% endblock %}
```

- [ ] **Step 7: Create the account activation text template**

Create `templates/email/account_activation.txt`:

```
Confirm your email address

Welcome to The Daily Inquirer! Confirm your email to start receiving
your daily writing prompt:

{{ confirm_url }}

--
An account notice from The Daily Inquirer.
```

- [ ] **Step 8: Create `core/email.py` with the helper and the activation sender**

Create `core/email.py`:

```python
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
```

- [ ] **Step 9: Replace `send_activation_email` in `core/views.py` with an import**

In `core/views.py`, delete the entire `send_activation_email` function (currently around lines 214-228).

Then update the `core.utils` import line and add a `core.email` import. The import block currently reads:

```python
from core.utils import mail_newsletter
```

Change it to:

```python
from core.utils import mail_newsletter
from core.email import send_activation_email
```

(`send_email_change_emails` is moved in Task 3 — leave its definition in `views.py` for now.)

- [ ] **Step 10: Run the test to verify it passes**

Run: `python manage.py test core.tests.TransactionalEmailTemplateTests -v 2`
Expected: PASS

- [ ] **Step 11: Run the activation regression test**

Run: `python manage.py test core.tests.EmailConfirmationTests -v 2`
Expected: PASS (both tests)

- [ ] **Step 12: Commit**

```bash
git add templates/email/base.html templates/email/_button.html \
  templates/email/_footer_transactional.html \
  templates/email/account_activation.html templates/email/account_activation.txt \
  core/email.py core/views.py core/tests.py
git commit -m "feat: shared HTML email template and account activation email"
```

---

## Task 3: Email-change confirm and notice emails

**Files:**
- Create: `templates/email/email_change_confirm.html` / `.txt`
- Create: `templates/email/email_change_notice.html` / `.txt`
- Modify: `core/email.py` (add `send_email_change_emails`)
- Modify: `core/views.py` (remove the local `send_email_change_emails`, import it)
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing test**

Append to `core/tests.py`:

```python
class EmailChangeEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='owner@example.com', password='mostdope1')
        self.user.confirmed_email = True
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.EmailChangeEmailTests -v 2`
Expected: FAIL — current change emails are plain text, `alternatives` is empty.

- [ ] **Step 3: Create the email-change confirm HTML template**

Create `templates/email/email_change_confirm.html`:

```html
{% extends "email/base.html" %}

{% block preheader %}Confirm the new email address for your Daily Inquirer account.{% endblock %}
{% block tab_label %}Email Change{% endblock %}

{% block content %}
<h2 style="margin:0 0 14px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:22px; font-weight:600; line-height:1.35; color:#1a1a1a;">
    Confirm your new email address
</h2>
<p style="margin:0 0 22px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:14px; line-height:1.6; color:#444444;">
    You asked to change your Daily Inquirer email address to <strong>{{ pending_email }}</strong>. Tap the button below to confirm the change.
</p>
{% include "email/_button.html" with url=confirm_url label="Confirm email change" %}
<p style="margin:22px 0 0; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:12px; line-height:1.6; color:#8a8a8a;">
    If you didn't request this, you can ignore this email &mdash; nothing will change. If the button doesn't work, paste this link into your browser:<br>
    <a href="{{ confirm_url }}" style="color:#009302; word-break:break-all;">{{ confirm_url }}</a>
</p>
{% endblock %}

{% block footer %}{% include "email/_footer_transactional.html" %}{% endblock %}
```

- [ ] **Step 4: Create the email-change confirm text template**

Create `templates/email/email_change_confirm.txt`:

```
Confirm your new email address

You asked to change your Daily Inquirer email address to {{ pending_email }}.
Confirm the change with this link:

{{ confirm_url }}

If you didn't request this, you can ignore this email -- nothing will change.

--
An account notice from The Daily Inquirer.
```

- [ ] **Step 5: Create the email-change notice HTML template**

Create `templates/email/email_change_notice.html`:

```html
{% extends "email/base.html" %}

{% block preheader %}A change was requested to your Daily Inquirer email address.{% endblock %}
{% block tab_label %}Email Change{% endblock %}

{% block content %}
<h2 style="margin:0 0 14px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:22px; font-weight:600; line-height:1.35; color:#1a1a1a;">
    Your email address is being changed
</h2>
<p style="margin:0 0 14px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:14px; line-height:1.6; color:#444444;">
    A request was made to change the email address on your Daily Inquirer account to <strong>{{ pending_email }}</strong>.
</p>
<p style="margin:0 0 14px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:14px; line-height:1.6; color:#444444;">
    If this was you, check that inbox for a confirmation link. The change will not take effect until it is confirmed.
</p>
<p style="margin:0; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:14px; line-height:1.6; color:#444444;">
    If this wasn't you, your account is still safe &mdash; no change has been made. You may want to reset your password.
</p>
{% endblock %}

{% block footer %}{% include "email/_footer_transactional.html" %}{% endblock %}
```

- [ ] **Step 6: Create the email-change notice text template**

Create `templates/email/email_change_notice.txt`:

```
Your email address is being changed

A request was made to change the email address on your Daily Inquirer
account to {{ pending_email }}.

If this was you, check that inbox for a confirmation link. The change will
not take effect until it is confirmed.

If this wasn't you, your account is still safe -- no change has been made.
You may want to reset your password.

--
An account notice from The Daily Inquirer.
```

- [ ] **Step 7: Add `send_email_change_emails` to `core/email.py`**

Append to `core/email.py`:

```python
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
```

- [ ] **Step 8: Remove the local `send_email_change_emails` from `core/views.py`**

In `core/views.py`, delete the entire `send_email_change_emails` function (currently around lines 297-322).

Update the `core.email` import line so it reads:

```python
from core.email import send_activation_email, send_email_change_emails
```

- [ ] **Step 9: Remove now-unused imports from `core/views.py`**

With both send functions gone, several imports are no longer used. In `core/views.py`:

- Delete the line `from django.contrib.sites.shortcuts import get_current_site`
- Delete the line `from django.template.loader import render_to_string`
- Delete the line `from django.core.mail import EmailMessage`
- Change `from django.utils.encoding import force_bytes, force_str` to `from django.utils.encoding import force_str`
- Change `from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode` to `from django.utils.http import urlsafe_base64_decode`

- [ ] **Step 10: Run the test to verify it passes**

Run: `python manage.py test core.tests.EmailChangeEmailTests core.tests.EmailConfirmationTests -v 2`
Expected: PASS (the email-change test, plus the activation tests confirming the trimmed imports did not break `activate`/`confirm_email_change`)

- [ ] **Step 11: Commit**

```bash
git add templates/email/email_change_confirm.html templates/email/email_change_confirm.txt \
  templates/email/email_change_notice.html templates/email/email_change_notice.txt \
  core/email.py core/views.py core/tests.py
git commit -m "feat: HTML templates for email-change confirm and notice emails"
```

---

## Task 4: Password reset email restyle

Django's built-in `PasswordResetView` owns sending; we point it at the new templates by overriding the URL.

**Files:**
- Create: `templates/email/password_reset.html` / `.txt`
- Create: `templates/email/password_reset_subject.txt`
- Modify: `dailyinquirer/urls.py`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing test**

Append to `core/tests.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.PasswordResetEmailTests -v 2`
Expected: FAIL — the default reset email is plain text with a different subject.

- [ ] **Step 3: Create the password reset HTML template**

Create `templates/email/password_reset.html`. The reset URL is built from the `protocol`, `domain`, `uid` and `token` that Django's `PasswordResetView` puts in the context, so the button is inlined here rather than using `_button.html`:

```html
{% extends "email/base.html" %}

{% block preheader %}Reset the password on your Daily Inquirer account.{% endblock %}
{% block tab_label %}Password Reset{% endblock %}

{% block content %}
{% url 'password_reset_confirm' uidb64=uid token=token as reset_path %}
<h2 style="margin:0 0 14px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:22px; font-weight:600; line-height:1.35; color:#1a1a1a;">
    Reset your password
</h2>
<p style="margin:0 0 22px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:14px; line-height:1.6; color:#444444;">
    Someone asked to reset the password for your Daily Inquirer account. Tap the button below to choose a new one.
</p>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:4px 0;">
    <tr>
        <td style="background-color:#009302; border-radius:6px;">
            <a href="{{ protocol }}://{{ domain }}{{ reset_path }}" style="display:inline-block; padding:13px 26px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:14px; font-weight:700; color:#ffffff; text-decoration:none;">
                Reset my password
            </a>
        </td>
    </tr>
</table>
<p style="margin:22px 0 0; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:12px; line-height:1.6; color:#8a8a8a;">
    If this wasn't you, just ignore this email &mdash; your password will not change. If the button doesn't work, paste this link into your browser:<br>
    <a href="{{ protocol }}://{{ domain }}{{ reset_path }}" style="color:#009302; word-break:break-all;">{{ protocol }}://{{ domain }}{{ reset_path }}</a>
</p>
{% endblock %}

{% block footer %}{% include "email/_footer_transactional.html" %}{% endblock %}
```

- [ ] **Step 4: Create the password reset text template**

Create `templates/email/password_reset.txt`:

```
Reset your password

Someone asked to reset the password for your Daily Inquirer account.
Choose a new one with this link:

{{ protocol }}://{{ domain }}{% url 'password_reset_confirm' uidb64=uid token=token %}

If this wasn't you, just ignore this email -- your password will not change.

--
An account notice from The Daily Inquirer.
```

- [ ] **Step 5: Create the password reset subject template**

Create `templates/email/password_reset_subject.txt` (a single line — Django strips newlines from subject templates):

```
Reset your Daily Inquirer password
```

- [ ] **Step 6: Override the `password_reset` URL**

In `dailyinquirer/urls.py`, add the `PasswordResetView` import and a `password_reset/` route **before** the `django.contrib.auth.urls` include. The full file becomes:

```python
"""dailyinquirer URL Configuration."""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LogoutView, PasswordResetView
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('password_reset/',
         PasswordResetView.as_view(
             email_template_name='email/password_reset.txt',
             html_email_template_name='email/password_reset.html',
             subject_template_name='email/password_reset_subject.txt'),
         name='password_reset'),
    path('', include('core.urls')),
    path('', include('django.contrib.auth.urls')),
]

# Local-only email inbox UI; the app is installed only in dev settings.
if 'django_mail_viewer' in settings.INSTALLED_APPS:
    urlpatterns += [path('mailbox/', include('django_mail_viewer.urls'))]
```

- [ ] **Step 7: Run the test to verify it passes**

Run: `python manage.py test core.tests.PasswordResetEmailTests -v 2`
Expected: PASS

- [ ] **Step 8: Run the auth-page regression tests**

Run: `python manage.py test core.tests.AuthPagesTests -v 2`
Expected: PASS (the reset form/done/confirm/complete pages still resolve)

- [ ] **Step 9: Commit**

```bash
git add templates/email/password_reset.html templates/email/password_reset.txt \
  templates/email/password_reset_subject.txt dailyinquirer/urls.py core/tests.py
git commit -m "feat: restyle password reset email with shared template"
```

---

## Task 5: Unsubscribe token helpers and confirmation page

**Files:**
- Modify: `core/utils.py` (add token helpers)
- Modify: `core/views.py` (add `unsubscribe` view)
- Modify: `core/urls.py` (add `unsubscribe` route)
- Create: `core/templates/core/unsubscribe.html`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing test**

Append to `core/tests.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.UnsubscribePageTests -v 2`
Expected: FAIL — `make_unsubscribe_token` and the `unsubscribe` URL do not exist.

- [ ] **Step 3: Add token helpers to `core/utils.py`**

At the top of `core/utils.py`, the imports currently are:

```python
from core.models import Prompt, PromptSend
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
```

Replace that import block with:

```python
from core.models import Prompt, PromptSend
from authentication.models import User
from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from core.email import send_templated_email
```

(`EmailMultiAlternatives` and `render_to_string` are kept for now — the still-unchanged `mail_newsletter` uses them; they are removed in Task 7 when `mail_newsletter` is rewritten.)

Then append to the end of `core/utils.py`:

```python
UNSUBSCRIBE_SALT = 'daily-prompt-unsubscribe'


def make_unsubscribe_token(user):
    """Return a signed, non-expiring token identifying the user."""
    return signing.dumps(user.pk, salt=UNSUBSCRIBE_SALT)


def read_unsubscribe_token(token):
    """Return the User for a valid token, or None if it is invalid."""
    try:
        pk = signing.loads(token, salt=UNSUBSCRIBE_SALT)
    except signing.BadSignature:
        return None
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        return None
```

> Note: `core/utils.py` now imports `send_templated_email`, which is used by `mail_newsletter` only after Task 7. The import is harmless before then.

- [ ] **Step 4: Create the unsubscribe page template**

Create `core/templates/core/unsubscribe.html`:

```html
{% extends "core/base.html" %}

{% block extra_head %}
<link href="/static/css/account.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="app" id="unsubscribe">
  <p class="ed-label" style="text-align:center;">The Daily Inquirer</p>

  <section class="ed-card">
    {% if state == 'confirm' %}
      <h2 class="ed-card__head">Unsubscribe from the daily prompt?</h2>
      <p class="ed-card__sub">This stops the daily writing prompt from arriving at <strong>{{ email }}</strong>.</p>
      <p class="ed-card__sub">Your journal and account stay exactly as they are, and you can resubscribe any time. Account emails such as password resets will still reach you.</p>
      <div class="ed-actions">
        <form method="post" action="{% url 'unsubscribe' %}">
          {% csrf_token %}
          <input type="hidden" name="token" value="{{ token }}">
          <button class="ed-btn" type="submit">Unsubscribe me</button>
        </form>
        <a class="ed-btn-ghost" href="/">Keep my subscription</a>
      </div>
    {% elif state == 'done' %}
      <div style="width:38px; height:38px; border-radius:50%; background:#009302; color:#fff; text-align:center; line-height:38px; font-size:20px; margin-bottom:14px;">&#10003;</div>
      <h2 class="ed-card__head">You've been unsubscribed</h2>
      <p class="ed-card__sub">The daily writing prompt will no longer be sent to <strong>{{ email }}</strong>.</p>
      <p class="ed-card__sub">You can resubscribe any time from your settings.</p>
      <div class="ed-actions">
        <a class="ed-btn" href="/">OK, thanks</a>
      </div>
    {% else %}
      <h2 class="ed-card__head">This link is no longer valid</h2>
      <p class="ed-card__sub">We couldn't read this unsubscribe link. You can manage your subscription from your account settings instead.</p>
      <div class="ed-actions">
        <a class="ed-btn" href="/settings/">Go to settings</a>
      </div>
    {% endif %}
  </section>
</div>
{% endblock %}
```

- [ ] **Step 5: Add the `unsubscribe` view to `core/views.py`**

Add to `core/views.py`. First update the `core.utils` import line so it reads:

```python
from core.utils import mail_newsletter, read_unsubscribe_token
```

Then append this view to the file:

```python
def unsubscribe(request):
    token = request.POST.get('token') or request.GET.get('token', '')
    user = read_unsubscribe_token(token)
    if user is None:
        return render(request, 'core/unsubscribe.html', {'state': 'error'})

    if request.method == 'POST':
        if user.is_subscribed:
            user.is_subscribed = False
            user.save()
        return render(request, 'core/unsubscribe.html',
                      {'state': 'done', 'email': user.email})

    state = 'confirm' if user.is_subscribed else 'done'
    return render(request, 'core/unsubscribe.html',
                  {'state': state, 'email': user.email, 'token': token})
```

- [ ] **Step 6: Add the `unsubscribe` route to `core/urls.py`**

In `core/urls.py`, add this entry to `urlpatterns` (place it after the `settings/` route):

```python
    path('unsubscribe/', views.unsubscribe, name='unsubscribe'),
```

- [ ] **Step 7: Run the test to verify it passes**

Run: `python manage.py test core.tests.UnsubscribePageTests -v 2`
Expected: PASS (all four tests)

- [ ] **Step 8: Commit**

```bash
git add core/utils.py core/views.py core/urls.py \
  core/templates/core/unsubscribe.html core/tests.py
git commit -m "feat: signed unsubscribe token and confirmation page"
```

---

## Task 6: One-click unsubscribe endpoint

**Files:**
- Modify: `core/views.py` (add `unsubscribe_one_click` view)
- Modify: `core/urls.py` (add route)
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing test**

Append to `core/tests.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.UnsubscribeOneClickTests -v 2`
Expected: FAIL — the `unsubscribe_one_click` URL does not exist.

- [ ] **Step 3: Add the `unsubscribe_one_click` view to `core/views.py`**

Append to `core/views.py`:

```python
@csrf_exempt
def unsubscribe_one_click(request):
    """RFC 8058 List-Unsubscribe one-click endpoint. Mail clients POST here
    directly; the token is in the query string."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    user = read_unsubscribe_token(request.GET.get('token', ''))
    if user is None:
        return HttpResponseBadRequest('invalid token')

    if user.is_subscribed:
        user.is_subscribed = False
        user.save()
    return HttpResponse('unsubscribed', status=200)
```

(`csrf_exempt`, `HttpResponseNotAllowed`, `HttpResponseBadRequest` and `HttpResponse` are already imported at the top of `core/views.py`.)

- [ ] **Step 4: Add the `unsubscribe/one-click/` route to `core/urls.py`**

In `core/urls.py`, add to `urlpatterns` immediately after the `unsubscribe/` route:

```python
    path('unsubscribe/one-click/', views.unsubscribe_one_click,
         name='unsubscribe_one_click'),
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python manage.py test core.tests.UnsubscribeOneClickTests -v 2`
Expected: PASS (all three tests)

- [ ] **Step 6: Commit**

```bash
git add core/views.py core/urls.py core/tests.py
git commit -m "feat: RFC 8058 one-click unsubscribe endpoint"
```

---

## Task 7: Daily prompt email on the shared template

**Files:**
- Create: `templates/email/daily_prompt.html` / `.txt`
- Create: `templates/email/_footer_daily.html`
- Modify: `core/utils.py` (rewrite `mail_newsletter`)
- Test: `core/tests.py`
- Remove: `core/templates/core/daily_email.html`

- [ ] **Step 1: Write the failing test**

Append to `core/tests.py`:

```python
class DailyPromptEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='daily@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.is_subscribed = True
        self.user.save()
        Prompt.objects.create(
            question='What did you notice today?',
            mail_day=timezone.now())

    def test_daily_email_uses_shared_template_with_footer_links(self):
        mail_newsletter(self.user)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        html = dict((mime, body) for body, mime in message.alternatives)
        body = html['text/html']
        self.assertIn('The Daily Inquirer', body)
        self.assertIn('Manage notifications', body)
        self.assertIn('Unsubscribe', body)
        self.assertIn('/unsubscribe/?token=', body)

    def test_daily_email_sets_list_unsubscribe_headers(self):
        mail_newsletter(self.user)
        message = mail.outbox[0]
        self.assertIn('List-Unsubscribe', message.extra_headers)
        self.assertIn('/unsubscribe/one-click/?token=',
                      message.extra_headers['List-Unsubscribe'])
        self.assertEqual(message.extra_headers['List-Unsubscribe-Post'],
                         'List-Unsubscribe=One-Click')
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.DailyPromptEmailTests -v 2`
Expected: FAIL — the current daily email has no `List-Unsubscribe` header and no "Manage notifications" link.

- [ ] **Step 3: Create the daily footer include**

Create `templates/email/_footer_daily.html`:

```html
<a href="{{ manage_url }}" style="color:#8a8a8a; text-decoration:none;">Manage notifications</a>
<span style="color:#cbc6b8;">&nbsp;&middot;&nbsp;</span>
<a href="{{ unsubscribe_url }}" style="color:#8a8a8a; text-decoration:none;">Unsubscribe</a>
<div style="padding-top:6px; font-size:10px; color:#aba799;">
    <a href="https://www.dailyinquirer.me/terms/" style="color:#aba799; text-decoration:none;">Terms</a>
    <span style="color:#cbc6b8;">&nbsp;&middot;&nbsp;</span>
    <a href="https://www.dailyinquirer.me/privacy/" style="color:#aba799; text-decoration:none;">Privacy</a>
</div>
```

- [ ] **Step 4: Create the daily prompt HTML template**

Create `templates/email/daily_prompt.html`:

```html
{% extends "email/base.html" %}

{% block preheader %}Today's writing prompt from The Daily Inquirer. Reply to this email to answer.{% endblock %}
{% block tab_label %}{{ prompt.mail_day|date:"l, F j, Y" }}{% endblock %}

{% block content %}
{% if prompt.category %}
<p style="margin:0 0 12px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:11px; font-weight:600; letter-spacing:1.3px; text-transform:uppercase; color:#009302;">
    {{ prompt.category }}
</p>
{% endif %}
<h2 class="di-question" style="margin:0 0 30px; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:23px; font-weight:600; line-height:1.42; color:#1a1a1a;">
    {{ prompt.question }}
</h2>
<p style="margin:0; font-family:'Elms Sans',Helvetica,Arial,sans-serif; font-size:13px; line-height:1.6; color:#8a8a8a;">
    <strong style="color:#555555;">Reply to this email</strong> and your response is saved to your journal.
</p>
{% endblock %}

{% block footer %}{% include "email/_footer_daily.html" %}{% endblock %}
```

- [ ] **Step 5: Create the daily prompt text template**

Create `templates/email/daily_prompt.txt`:

```
{{ prompt.question }}

Reply to this email and your response is saved to your journal.

--
Manage notifications: {{ manage_url }}
Unsubscribe: {{ unsubscribe_url }}
```

- [ ] **Step 6: Rewrite `mail_newsletter` in `core/utils.py`**

First, in the `core/utils.py` import block, delete the two now-unused lines:

```python
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
```

Then replace the entire `mail_newsletter` function in `core/utils.py` with:

```python
def mail_newsletter(user):
    local_time = user.local_time()
    if local_time is None:
        return None

    todays_prompt = prompt_for_datetime(local_time)
    if todays_prompt is None:
        return None

    token = make_unsubscribe_token(user)
    unsubscribe_url = (f"{settings.SITE_URL}{reverse('unsubscribe')}"
                       f"?token={token}")
    one_click_url = (f"{settings.SITE_URL}"
                     f"{reverse('unsubscribe_one_click')}?token={token}")
    manage_url = f"{settings.SITE_URL}{reverse('settings')}"

    send_templated_email(
        subject=todays_prompt.question,
        to=user.email,
        template='daily_prompt',
        from_email='The Daily Inquirer <the@dailyinquirer.me>',
        context={
            'prompt': todays_prompt,
            'unsubscribe_url': unsubscribe_url,
            'manage_url': manage_url,
        },
        headers={
            'List-Unsubscribe': f'<{one_click_url}>',
            'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
        },
    )
    return todays_prompt
```

- [ ] **Step 7: Delete the old daily email template**

Run: `git rm core/templates/core/daily_email.html`

- [ ] **Step 8: Run the test to verify it passes**

Run: `python manage.py test core.tests.DailyPromptEmailTests -v 2`
Expected: PASS (both tests)

- [ ] **Step 9: Run the daily-send regression tests**

Run: `python manage.py test core.tests.MailNewsletterTests core.tests.SendDailyMailTests -v 2`
Expected: PASS. If `SendDailyMailTests` does not exist, run only `MailNewsletterTests` — it must pass.

- [ ] **Step 10: Commit**

```bash
git add templates/email/daily_prompt.html templates/email/daily_prompt.txt \
  templates/email/_footer_daily.html core/utils.py core/tests.py \
  core/templates/core/daily_email.html
git commit -m "feat: daily prompt email on shared template with List-Unsubscribe"
```

---

## Task 8: Remove old templates and full verification

**Files:**
- Remove: `templates/registration/confirm_email.html`, `change_email_confirm.html`, `change_email_notice.html`, `password_reset_email.html`

- [ ] **Step 1: Confirm the old registration email templates are unreferenced**

Run: `grep -rn "registration/confirm_email\|registration/change_email\|registration/password_reset_email" --include=*.py .`
Expected: no output (no Python code references these templates anymore).

- [ ] **Step 2: Delete the obsolete registration email templates**

```bash
git rm templates/registration/confirm_email.html \
  templates/registration/change_email_confirm.html \
  templates/registration/change_email_notice.html \
  templates/registration/password_reset_email.html
```

- [ ] **Step 3: Run the full test suite**

Run: `python manage.py test`
Expected: all tests pass, `OK`.

- [ ] **Step 4: Manual smoke check in local dev**

Run: `python manage.py runserver`

In a browser, with the local email viewer at `/mailbox/`:
- Register a new account → confirm the activation email renders the shared template with the green masthead and "Confirm my email" button.
- From `/settings/`, request a password reset → confirm the reset email renders the shared template.
- Trigger a daily send (admin "Send today's prompt" button on a user, after creating a `Prompt` for today) → confirm the daily email shows the "Manage notifications" and "Unsubscribe" footer links.
- Click the daily email's "Unsubscribe" link → confirm the confirmation page loads, the confirm button unsubscribes, and the done state appears.

- [ ] **Step 5: Commit**

```bash
git add templates/registration/
git commit -m "chore: remove plain-text email templates replaced by shared template"
```

---

## Self-Review Notes

- **Spec coverage:** shared template (Task 2), transactional note (Tasks 2/3/4 footer include), daily-prompt Unsubscribe + Manage notifications links (Task 7), unsubscribe confirmation page with confirm/done/error states (Task 5), one-click endpoint + `List-Unsubscribe` header (Tasks 6/7), signed tokens (Task 5), `core/email.py` consolidation (Tasks 2/3), password reset restyle (Task 4), `SITE_URL` (Task 1), file removals (Tasks 7/8). The `mailto:` fallback is intentionally out of scope per the spec.
- **Type/name consistency:** `send_templated_email`, `make_unsubscribe_token`, `read_unsubscribe_token`, `unsubscribe`, `unsubscribe_one_click` are used with identical signatures and names across all tasks.
- **Ordering:** Task 7 (daily prompt) depends on the unsubscribe URLs from Tasks 5 and 6 and the helper from Task 2, so it runs after them.
