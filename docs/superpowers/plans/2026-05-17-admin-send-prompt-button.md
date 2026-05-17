# Admin "Send today's prompt" Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Send today's prompt" button to the Django admin User change page that emails that user the daily writing prompt on demand.

**Architecture:** A custom admin URL on `UserAdmin` runs a view that calls the existing `core.utils.mail_newsletter` and reports the outcome via Django admin messages. A `change_form.html` template override renders the button. `mail_newsletter` is refactored to return the `Prompt` it sent (or `None`) so the view can give precise feedback.

**Tech Stack:** Django 5.2, Django admin, `pytz`.

**Design doc:** `docs/superpowers/specs/2026-05-17-admin-send-prompt-button-design.md`

**Key facts:**
- The Django settings module for `manage.py` (and the test runner) is `dailyinquirer.settings.local`.
- Run tests with `.venv/bin/python manage.py test` (the project virtualenv is at the repo root `.venv`).
- The `User` model (`authentication/models.py`) has no `username`; `USERNAME_FIELD = 'email'`. `is_staff` is a property equal to `is_admin`. `User.objects.create_superuser(email, password)` sets `is_admin=True`. `User.objects.create_user(email, password)` leaves `timezone` as `''`, and `user.local_time()` returns `None` for any unparseable timezone.
- `Prompt` (`core/models.py`) has fields `question` (CharField) and `mail_day` (DateTimeField).
- Repo-root `templates/` is on `TEMPLATES['DIRS']`; `APP_DIRS` is also on.

---

## Task 1: `mail_newsletter` returns the sent prompt

Refactor `core.utils.mail_newsletter` so it returns the `Prompt` it emailed, returns `None` when there is no prompt for today, and returns `None` (instead of crashing) when the user has no valid timezone.

**Files:**
- Modify: `core/utils.py`
- Modify: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

In `core/tests.py`, add these imports below the existing `from authentication.tokens import account_activation_token` line:

```python
from django.utils import timezone

from core.models import Prompt
from core.utils import mail_newsletter
```

Then append this class to the end of `core/tests.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python manage.py test core.tests.MailNewsletterTests -v 2`
Expected: FAIL — `test_returns_prompt_and_sends_when_prompt_exists` fails because the current `mail_newsletter` returns `None` (not the prompt), and `test_returns_none_when_user_has_no_valid_timezone` fails with an `AttributeError` because `prompt_for_datetime(None)` accesses `None.day`.

- [ ] **Step 3: Rewrite `mail_newsletter`**

Replace the entire `mail_newsletter` function in `core/utils.py` with:

```python
def mail_newsletter(user):
    local_time = user.local_time()
    if local_time is None:
        return None

    todays_prompt = prompt_for_datetime(local_time)
    if todays_prompt is None:
        return None

    plain_text = todays_prompt.question
    html_content = render_to_string('core/daily_email.html', {
        'prompt': todays_prompt,
    })
    mail_subject = todays_prompt.question
    to_email = user.email
    from_email = "The Daily Inquirer <the@dailyinquirer.me>"
    email = EmailMultiAlternatives(mail_subject,
                                   plain_text,
                                   from_email,
                                   [to_email])
    email.attach_alternative(html_content, "text/html")
    email.send()
    return todays_prompt
```

`prompt_for_datetime` is unchanged. No import changes are needed in `core/utils.py`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python manage.py test core.tests -v 2`
Expected: PASS — `MailNewsletterTests` plus all pre-existing `core` tests.

- [ ] **Step 5: Commit**

```bash
git add core/utils.py core/tests.py
git commit -m "$(cat <<'EOF'
Make mail_newsletter return the sent prompt and handle bad timezones

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Admin send-prompt URL and view

Add a custom admin URL `send-prompt/<int:pk>/` to `UserAdmin` and a view that calls `mail_newsletter`, reports the outcome via admin messages, and redirects back to the user's change page.

**Files:**
- Modify: `authentication/admin.py`
- Modify: `authentication/tests.py`

- [ ] **Step 1: Write the failing tests**

Replace the entire contents of `authentication/tests.py` (currently a 3-line stub) with:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python manage.py test authentication.tests -v 2`
Expected: FAIL — `reverse('admin:authentication_user_send_prompt', ...)` raises `NoReverseMatch` in `setUp` because the URL does not exist yet.

- [ ] **Step 3: Add the imports to `authentication/admin.py`**

At the top of `authentication/admin.py`, below the existing `from authentication.models import User` line, add:

```python
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from core.utils import mail_newsletter
```

- [ ] **Step 4: Add `get_urls` and the view to `UserAdmin`**

In `authentication/admin.py`, inside the `UserAdmin` class, add these two methods (place them after the `filter_horizontal = ()` line, still indented as class members):

```python
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('send-prompt/<int:pk>/',
                 self.admin_site.admin_view(self.send_prompt_view),
                 name='authentication_user_send_prompt'),
        ]
        return custom + urls

    def send_prompt_view(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        try:
            prompt = mail_newsletter(user)
        except Exception as exc:
            messages.error(request, f"Failed to send: {exc}")
        else:
            if prompt is None:
                messages.warning(
                    request,
                    f"No prompt for today for {user.email} "
                    f"(or the user has no valid timezone) — nothing sent.")
            else:
                messages.success(
                    request, f"Sent today's prompt to {user.email}.")
        return redirect('admin:authentication_user_change', pk)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python manage.py test authentication.tests -v 2`
Expected: PASS — both `AdminSendPromptTests` tests.

- [ ] **Step 6: Commit**

```bash
git add authentication/admin.py authentication/tests.py
git commit -m "$(cat <<'EOF'
Add admin send-prompt view to the User admin

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Change-form template button

Add a `change_form.html` override for the User model that renders a "Send today's prompt" button in the submit row, linking to the URL from Task 2.

**Files:**
- Create: `templates/admin/authentication/user/change_form.html`
- Modify: `authentication/tests.py`

- [ ] **Step 1: Write the failing test**

In `authentication/tests.py`, add this method to the `AdminSendPromptTests` class (after `test_sends_nothing_when_no_prompt`):

```python
    def test_change_page_renders_send_prompt_button(self):
        change_url = reverse('admin:authentication_user_change',
                             args=[self.target.pk])

        response = self.client.get(change_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.send_url)
        self.assertContains(response, "Send today's prompt")
```

(The button label is static template text, which Django does not autoescape, so the apostrophe appears literally in the response.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python manage.py test authentication.tests.AdminSendPromptTests.test_change_page_renders_send_prompt_button -v 2`
Expected: FAIL — the change page does not contain the send-prompt URL or button text yet.

- [ ] **Step 3: Create the template override**

Create `templates/admin/authentication/user/change_form.html`:

```html
{% extends "admin/change_form.html" %}

{% block submit_buttons_bottom %}
  {{ block.super }}
  {% if original %}
  <div class="submit-row">
    <a class="button"
       href="{% url 'admin:authentication_user_send_prompt' original.pk %}">
      Send today's prompt
    </a>
  </div>
  {% endif %}
{% endblock %}
```

The `{% if original %}` guard keeps the button off the "add user" page, where `original` is `None`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python manage.py test authentication.tests -v 2`
Expected: PASS — all three `AdminSendPromptTests` tests.

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python manage.py test`
Expected: PASS — every test in the project, no failures.

- [ ] **Step 6: Commit**

```bash
git add templates/admin/authentication/user/change_form.html authentication/tests.py
git commit -m "$(cat <<'EOF'
Render a Send today's prompt button on the User change page

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Notes for the implementer

- All three tasks are local code changes with commits — no deployment.
- The branch is `admin-send-prompt` (already created off the latest `main`). Opening a PR is a separate step after Task 3 — see superpowers:finishing-a-development-branch.
- Manual sanity check after Task 3 (optional): `.venv/bin/python manage.py runserver`, log into `/admin/`, open any user, confirm the "Send today's prompt" button appears beside *Save* and that clicking it shows a green/yellow message banner.
