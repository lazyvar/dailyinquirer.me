# Onboarding Step + Per-User Send Time Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-page onboarding step every new user must complete (opt-in to the daily email, set timezone, choose the delivery hour), gated by an `onboarded` flag, and let users change their delivery hour afterward in settings.

**Architecture:** A new `onboarded` boolean and a repurposed `mail_time` field live on the `authentication.User` model. New `OnboardingRequiredMiddleware` redirects any authenticated, confirmed, not-yet-onboarded user to a new `/onboarding/` page. The daily-send command reads each user's chosen hour instead of a hardcoded 8am. Signup is trimmed to email + password; timezone moves to onboarding.

**Tech Stack:** Django 5 (Python 3.14), SQLite, Django templates, `python manage.py test`.

---

## Background for the implementer

- This is a Django project. Tests run with `python manage.py test` (NOT pytest). `manage.py` defaults to the `dailyinquirer.settings.local` settings module — SQLite, `DEBUG=True`.
- The custom user model is `authentication.User` (email is the username; no `username` field). It already has an **unused** `mail_time = IntegerField(default=360)` field — minutes-from-midnight. This plan repurposes it as the per-user delivery time.
- `User.local_time()` returns a timezone-aware "now" for the user, or `None` if their `timezone` string is invalid/empty.
- The daily email is sent by the `send_daily_mail` management command, run hourly by cron. It currently sends to every confirmed, subscribed user whose local hour is `>= 8`.
- Run the full test suite with `python manage.py test`. Run one class with `python manage.py test core.tests.ClassName`.

---

## Task 1: Add `onboarded`, repurpose `mail_time`, make `timezone` optional

**Files:**
- Modify: `authentication/models.py`
- Create: `authentication/migrations/0006_onboarding_fields.py` (generated)
- Test: `authentication/tests.py`

- [ ] **Step 1: Write the failing test**

Add to the end of `authentication/tests.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test authentication.tests.UserOnboardingFieldsTests`
Expected: FAIL — `AttributeError: 'User' object has no attribute 'onboarded'` (or a `mail_time` value of 360).

- [ ] **Step 3: Edit the model**

In `authentication/models.py`, change the `timezone` and `mail_time` fields and add `onboarded`. The relevant block of the `User` class becomes:

```python
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    timezone = models.CharField(max_length=64, blank=True, default='')
    confirmed_email = models.BooleanField(default=False)
    mail_time = models.IntegerField(default=480)
    onboarded = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    is_subscribed = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
```

Change `REQUIRED_FIELDS` (timezone is now optional):

```python
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
```

Add a `mail_hour` property — place it right after the `local_time` method:

```python
    @property
    def mail_hour(self):
        """The hour of day (0-23) this user's prompt is sent."""
        return self.mail_time // 60
```

- [ ] **Step 4: Generate the schema migration**

Run: `python manage.py makemigrations authentication --name onboarding_fields`

Expected: creates `authentication/migrations/0006_onboarding_fields.py` with an `AddField` for `onboarded`, an `AlterField` for `mail_time`, and an `AlterField` for `timezone`. Open it and confirm it contains exactly those three operations and depends on `'0005_user_timestamps'`.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python manage.py test authentication.tests.UserOnboardingFieldsTests`
Expected: PASS (the test runner applies the new migration to the test database automatically).

- [ ] **Step 6: Commit**

```bash
git add authentication/models.py authentication/migrations/0006_onboarding_fields.py authentication/tests.py
git commit -m "Add onboarded flag, repurpose mail_time, make timezone optional"
```

---

## Task 2: Data migration — onboard existing users

Existing users predate onboarding and the send-time feature. Mark them `onboarded=True` so they skip the new page, and set `mail_time=480` so they keep getting mail at 8am (not the stale 6am implied by the old `360` default).

**Files:**
- Create: `authentication/migrations/0007_onboard_existing_users.py`
- Test: `authentication/tests.py`

- [ ] **Step 1: Write the failing test**

Add these imports to the top of `authentication/tests.py`:

```python
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
```

Add `TransactionTestCase` to the existing `django.test` import line so it reads:

```python
from django.test import TestCase, TransactionTestCase, override_settings
```

Add this test class to the end of `authentication/tests.py`:

```python
class OnboardExistingUsersMigrationTests(TransactionTestCase):
    """0007 marks pre-existing users onboarded and bumps their send time."""

    def test_existing_users_are_marked_onboarded(self):
        app = 'authentication'
        migrate_from = [(app, '0006_onboarding_fields')]
        migrate_to = [(app, '0007_onboard_existing_users')]

        # Roll the test database back to just before the data migration.
        executor = MigrationExecutor(connection)
        executor.migrate(migrate_from)
        old_apps = executor.loader.project_state(migrate_from).apps

        OldUser = old_apps.get_model(app, 'User')
        OldUser.objects.create(
            email='existing@example.com', password='x',
            timezone='UTC', onboarded=False, mail_time=360)

        # Apply the data migration.
        executor = MigrationExecutor(connection)
        executor.migrate(migrate_to)
        new_apps = executor.loader.project_state(migrate_to).apps

        NewUser = new_apps.get_model(app, 'User')
        user = NewUser.objects.get(email='existing@example.com')
        self.assertTrue(user.onboarded)
        self.assertEqual(user.mail_time, 480)

        # Leave the test database fully migrated for any later tests.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test authentication.tests.OnboardExistingUsersMigrationTests`
Expected: FAIL — migration `0007_onboard_existing_users` does not exist (`KeyError` / `NodeNotFoundError`).

- [ ] **Step 3: Write the data migration**

Create `authentication/migrations/0007_onboard_existing_users.py`:

```python
from django.db import migrations


def onboard_existing_users(apps, schema_editor):
    User = apps.get_model('authentication', 'User')
    User.objects.update(onboarded=True, mail_time=480)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0006_onboarding_fields'),
    ]

    operations = [
        migrations.RunPython(onboard_existing_users, noop),
    ]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python manage.py test authentication.tests.OnboardExistingUsersMigrationTests`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add authentication/migrations/0007_onboard_existing_users.py authentication/tests.py
git commit -m "Add data migration onboarding existing users"
```

---

## Task 3: Onboarding form, view, URL, and page

This task builds the onboarding destination. The redirect gate comes in Task 4 — for now the page is reachable directly.

**Files:**
- Modify: `core/forms.py`
- Modify: `core/views.py`
- Modify: `core/urls.py`
- Create: `core/templates/core/onboarding.html`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `core/tests.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.OnboardingPageTests`
Expected: FAIL — `NoReverseMatch: 'onboarding' is not a valid view function or pattern name`.

- [ ] **Step 3: Add `HOUR_CHOICES` and `OnboardingForm` to `core/forms.py`**

Replace the entire contents of `core/forms.py` with:

```python
from datetime import time

from django import forms


# (hour 0-23, human label) — e.g. (8, "8:00 AM"). Shared by the
# onboarding and settings send-time selectors.
HOUR_CHOICES = [
    (h, time(h).strftime('%-I:00 %p')) for h in range(24)
]


class ResendConfirmationForm(forms.Form):
    email = forms.CharField(label='Email', max_length=100)


class OnboardingForm(forms.Form):
    subscribed = forms.BooleanField(required=False, initial=False)
    timezone = forms.CharField(max_length=64)
    mail_hour = forms.ChoiceField(choices=HOUR_CHOICES)


class SettingsForm(forms.Form):
    subscribed = forms.BooleanField(required=False, initial=False)
    timezone = forms.CharField(max_length=64)
```

(`SettingsForm` gets its `mail_hour` field in Task 5.)

- [ ] **Step 4: Add the onboarding view to `core/views.py`**

Change the forms import line in `core/views.py` from:

```python
from core.forms import ResendConfirmationForm, SettingsForm
```

to:

```python
from core.forms import (HOUR_CHOICES, OnboardingForm, ResendConfirmationForm,
                        SettingsForm)
```

Add this view function. Place it immediately after the `settings` view:

```python
@login_required
def onboarding(request):
    if request.user.onboarded:
        return redirect('index')

    if request.method == 'POST':
        form = OnboardingForm(request.POST)
        if form.is_valid():
            user = request.user
            user.is_subscribed = form.cleaned_data['subscribed']
            user.timezone = form.cleaned_data['timezone']
            user.mail_time = int(form.cleaned_data['mail_hour']) * 60
            user.onboarded = True
            user.save()
            return redirect('index')
        context = {'form': form, 'timezones': pytz.common_timezones,
                   'hours': HOUR_CHOICES}
        return render(request, 'core/onboarding.html', context)

    context = {'timezones': pytz.common_timezones, 'hours': HOUR_CHOICES}
    return render(request, 'core/onboarding.html', context)
```

- [ ] **Step 5: Register the URL in `core/urls.py`**

Add this entry to the `urlpatterns` list, after the `settings` line:

```python
    path('onboarding/', views.onboarding, name='onboarding'),
```

- [ ] **Step 6: Create the onboarding template**

Create `core/templates/core/onboarding.html`:

```html
{% extends "core/base.html" %}

{% block extra_head %}
<link href="/static/css/account.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="app" id="onboarding">
  <p class="ed-label">Welcome</p>

  {% if form.errors %}
    {% for field in form %}{% for error in field.errors %}
    <div class="ed-alert ed-alert--error">{{ error|escape }}</div>
    {% endfor %}{% endfor %}
    {% for error in form.non_field_errors %}
    <div class="ed-alert ed-alert--error">{{ error|escape }}</div>
    {% endfor %}
  {% endif %}

  <section class="ed-card">
    <h2 class="ed-card__head">One quick step before you start</h2>
    <p class="ed-card__sub">
      The Daily Inquirer sends you a writing prompt by email each morning.
      Reply to it and your answer is saved as a journal entry. Tell us how
      you'd like that to work.
    </p>
    <form method="post" action="">
      {% csrf_token %}
      <div class="ed-field">
        <label class="ed-check">
          <input type="checkbox" name="subscribed">
          <span>Email me a writing prompt every day.</span>
        </label>
        <p class="ed-hint">You can change this any time in settings.</p>
      </div>
      <div class="ed-field">
        <label class="ed-field__label" for="id_timezone">Time zone</label>
        <select class="ed-input" name="timezone" id="id_timezone">
          {% for tz in timezones %}
          <option value="{{ tz }}"{% if tz == user.timezone %} selected{% endif %}>{{ tz }}</option>
          {% endfor %}
        </select>
        <p class="ed-hint">We try to detect this automatically.</p>
      </div>
      <div class="ed-field">
        <label class="ed-field__label" for="id_mail_hour">Delivery time</label>
        <select class="ed-input" name="mail_hour" id="id_mail_hour">
          {% for h in hours %}
          <option value="{{ h.0 }}"{% if h.0 == 8 %} selected{% endif %}>{{ h.1 }}</option>
          {% endfor %}
        </select>
        <p class="ed-hint">When your prompt arrives, in your time zone.</p>
      </div>
      <button class="ed-btn" type="submit">Finish setup</button>
    </form>
  </section>
</div>

<script>
  (function () {
    try {
      var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      var select = document.getElementById('id_timezone');
      if (!tz || !select) { return; }
      for (var i = 0; i < select.options.length; i++) {
        if (select.options[i].value === tz) {
          select.selectedIndex = i;
          return;
        }
      }
    } catch (e) { /* leave the server-rendered selection */ }
  })();
</script>
{% endblock %}
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python manage.py test core.tests.OnboardingPageTests`
Expected: PASS (all 5 tests)

- [ ] **Step 8: Commit**

```bash
git add core/forms.py core/views.py core/urls.py core/templates/core/onboarding.html core/tests.py
git commit -m "Add onboarding page, form, and view"
```

---

## Task 4: Onboarding gate middleware

Redirect any authenticated, confirmed, not-yet-onboarded user to `/onboarding/`. Existing tests that log in confirmed users must be updated to mark those users `onboarded`, since the model default is now `False`.

**Files:**
- Create: `core/middleware.py`
- Modify: `dailyinquirer/settings/base.py:41-50`
- Modify: `core/tests.py` (new tests + update 4 existing setups)

- [ ] **Step 1: Write the failing tests**

Add to the end of `core/tests.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.OnboardingGateTests`
Expected: FAIL — `test_not_onboarded_user_is_redirected_to_onboarding` fails because no middleware redirects yet (settings page returns 200, not a redirect to onboarding).

- [ ] **Step 3: Write the middleware**

Create `core/middleware.py`:

```python
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class OnboardingRequiredMiddleware:
    """Redirect confirmed users who have not finished onboarding.

    Any authenticated user with ``confirmed_email`` set but ``onboarded``
    still False is sent to the onboarding page, except on a small set of
    exempt paths (the onboarding page itself, logout, admin, the inbound
    webhook, and static files).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if (user.is_authenticated and user.confirmed_email
                and not user.onboarded
                and not self._is_exempt(request.path)):
            return redirect('onboarding')
        return self.get_response(request)

    def _is_exempt(self, path):
        exempt = [
            reverse('onboarding'),
            '/logout/',
            '/admin/',
            '/messages/',
            settings.STATIC_URL,
        ]
        return any(prefix and path.startswith(prefix) for prefix in exempt)
```

- [ ] **Step 4: Register the middleware**

In `dailyinquirer/settings/base.py`, add the middleware to the `MIDDLEWARE` list immediately after `AuthenticationMiddleware`. The list becomes:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.OnboardingRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

- [ ] **Step 5: Update existing tests whose logged-in users are now gated**

The model default for `onboarded` is `False`, so confirmed users in existing test setups would now be redirected to onboarding. Add `onboarded = True` in four places in `core/tests.py`.

In `LogoutTests.setUp` — change:

```python
        self.user = User.objects.create_user(
            email='member@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.save()
```

to:

```python
        self.user = User.objects.create_user(
            email='member@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.onboarded = True
        self.user.save()
```

In `SettingsPageTests.setUp` — change:

```python
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.save()
        self.client.force_login(self.user)
```

to:

```python
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.onboarded = True
        self.user.save()
        self.client.force_login(self.user)
```

In `DashboardTests.setUp` — change:

```python
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.save()
        self.client.force_login(self.user)
```

to:

```python
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.onboarded = True
        self.user.save()
        self.client.force_login(self.user)
```

In `test_dashboard_renders_hard_wrapped_entry_without_inner_br` — change:

```python
        user = User.objects.create_user(email='wrap@example.com', password='mostdope1')
        user.timezone = 'UTC'
        user.confirmed_email = True
        user.save()
```

to:

```python
        user = User.objects.create_user(email='wrap@example.com', password='mostdope1')
        user.timezone = 'UTC'
        user.confirmed_email = True
        user.onboarded = True
        user.save()
```

- [ ] **Step 6: Run the full test suite to verify everything passes**

Run: `python manage.py test`
Expected: PASS — all tests, including `OnboardingGateTests`, `OnboardingPageTests`, and every pre-existing test.

If any pre-existing test fails because its logged-in user is redirected to `/onboarding/`, that user's setup needs `onboarded = True` added the same way. (`AdminSendPromptButtonTests` / `AdminSendPromptTests` use superusers whose `confirmed_email` is `False` and the `/admin/` path is exempt, so they need no change.)

- [ ] **Step 7: Commit**

```bash
git add core/middleware.py dailyinquirer/settings/base.py core/tests.py
git commit -m "Gate not-yet-onboarded users with onboarding middleware"
```

---

## Task 5: Send-time control in settings

Let onboarded users change their delivery hour from the settings page.

**Files:**
- Modify: `core/forms.py`
- Modify: `core/views.py` (`settings` view)
- Modify: `core/templates/core/settings.html`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing test**

Add to the end of `core/tests.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.SettingsSendTimeTests`
Expected: FAIL — `test_settings_page_shows_delivery_time_selector` fails (no `mail_hour` in the page).

- [ ] **Step 3: Add `mail_hour` to `SettingsForm`**

In `core/forms.py`, change `SettingsForm` to:

```python
class SettingsForm(forms.Form):
    subscribed = forms.BooleanField(required=False, initial=False)
    timezone = forms.CharField(max_length=64)
    mail_hour = forms.ChoiceField(choices=HOUR_CHOICES)
```

- [ ] **Step 4: Update the `settings` view**

In `core/views.py`, replace the entire `settings` view with:

```python
@login_required
def settings(request):

    if request.method == 'POST':
        form = SettingsForm(request.POST)
        if form.is_valid():
            user = request.user
            user.is_subscribed = form.cleaned_data['subscribed']
            user.timezone = form.cleaned_data['timezone']
            user.mail_time = int(form.cleaned_data['mail_hour']) * 60
            user.save()

            context = {'success': True, 'timezones': pytz.common_timezones,
                       'hours': HOUR_CHOICES}
            return render(request, 'core/settings.html', context)
        else:
            template = 'core/settings.html'
            context = {'form': form, 'timezones': pytz.common_timezones,
                       'hours': HOUR_CHOICES}
            return render(request, template, context)
    else:
        context = {'timezones': pytz.common_timezones, 'hours': HOUR_CHOICES}

    return render(request, 'core/settings.html', context)
```

- [ ] **Step 5: Add the selector to the settings template**

In `core/templates/core/settings.html`, add a new field block inside the first `<form>`, immediately after the timezone `ed-field` block (after its closing `</div>`, before `<button class="ed-btn" type="submit">`):

```html
      <div class="ed-field">
        <label class="ed-field__label" for="id_mail_hour">Delivery time</label>
        <select class="ed-input" name="mail_hour" id="id_mail_hour">
          {% for h in hours %}
          <option value="{{ h.0 }}"{% if h.0 == user.mail_hour %} selected{% endif %}>{{ h.1 }}</option>
          {% endfor %}
        </select>
        <p class="ed-hint">When your daily prompt arrives, in the time zone above.</p>
      </div>
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python manage.py test core.tests.SettingsSendTimeTests`
Expected: PASS

- [ ] **Step 7: Run the existing settings tests**

Run: `python manage.py test core.tests.SettingsPageTests`
Expected: PASS — `test_settings_update_shows_success_alert` posts `subscribed` and `timezone` but not `mail_hour`; the new required `mail_hour` field would make the form invalid. Fix that test by adding `mail_hour` to its POST data. In `core/tests.py`, change:

```python
    def test_settings_update_shows_success_alert(self):
        response = self.client.post(reverse('settings'), {
            'subscribed': 'on', 'timezone': 'America/New_York'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ed-alert--ok')
```

to:

```python
    def test_settings_update_shows_success_alert(self):
        response = self.client.post(reverse('settings'), {
            'subscribed': 'on', 'timezone': 'America/New_York',
            'mail_hour': '8'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ed-alert--ok')
```

Re-run `python manage.py test core.tests.SettingsPageTests` — expected PASS.

- [ ] **Step 8: Commit**

```bash
git add core/forms.py core/views.py core/templates/core/settings.html core/tests.py
git commit -m "Let users change their delivery hour in settings"
```

---

## Task 6: Trim signup to email + password

Timezone moves to onboarding, so the signup form drops it.

**Files:**
- Modify: `authentication/admin.py:22-24` (`UserCreationForm.Meta`)
- Modify: `core/views.py` (`register` view)
- Modify: `templates/registration/register.html`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing test**

Add to the end of `core/tests.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.SignupWithoutTimezoneTests`
Expected: FAIL — `test_register_page_has_no_timezone_field` fails (the register page still renders a timezone `<select>`).

- [ ] **Step 3: Drop `timezone` from `UserCreationForm`**

In `authentication/admin.py`, change the `UserCreationForm.Meta` class from:

```python
    class Meta:
        model = User
        fields = ('email', 'timezone',)
```

to:

```python
    class Meta:
        model = User
        fields = ('email',)
```

- [ ] **Step 4: Remove the timezone block from the register template**

In `templates/registration/register.html`, delete this entire block (the timezone `auth-field`):

```html
  <div class="auth-field">
    <label class="auth-label" for="id_timezone">Timezone</label>
    {% load tz %}
    {% with "US/Eastern" as local_tz %}
    <select class="auth-input" name="timezone" id="id_timezone">
      {% for tz in timezones %}
      <option value="{{ tz }}"{% if tz == local_tz %} selected{% endif %}>{{ tz }}</option>
      {% endfor %}
    </select>
    {% endwith %}
  </div>
```

The form is left with the email, password, and confirm-password fields only.

- [ ] **Step 5: Stop passing `timezones` from the `register` view**

In `core/views.py`, replace the entire `register` view with:

```python
def register(request):
    if request.user.is_authenticated:
        return redirect('index')
    else:
        if request.method == 'POST':
            form = UserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                send_activation_email(request, user)
                template = 'registration/activation_email_sent.html'
                context = {'email': user.email}
                return render(request, template, context)
            else:
                template = 'registration/register.html'
                context = {'form': form}
                return render(request, template, context)
        else:
            template = 'registration/register.html'
            return render(request, template, {})
```

- [ ] **Step 6: Run the new test to verify it passes**

Run: `python manage.py test core.tests.SignupWithoutTimezoneTests`
Expected: PASS

- [ ] **Step 7: Fix the pre-existing register test**

`EmailConfirmationTests.test_register_sends_activation_email` posts a now-removed `timezone` field. Extra POST keys are harmless, but update it for clarity. In `core/tests.py`, change:

```python
    def test_register_sends_activation_email(self):
        response = self.client.post(reverse('register'), {
            'email': 'newuser@example.com',
            'timezone': 'US/Eastern',
            'password1': 'mostdope1',
            'password2': 'mostdope1',
        })
```

to:

```python
    def test_register_sends_activation_email(self):
        response = self.client.post(reverse('register'), {
            'email': 'newuser@example.com',
            'password1': 'mostdope1',
            'password2': 'mostdope1',
        })
```

Run: `python manage.py test core.tests.EmailConfirmationTests`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add authentication/admin.py core/views.py templates/registration/register.html core/tests.py
git commit -m "Trim signup to email and password"
```

---

## Task 7: Daily send respects each user's chosen hour

**Files:**
- Modify: `core/management/commands/send_daily_mail.py:14-17`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `core/tests.py`:

```python
class SendDailyMailUsesMailHourTests(TestCase):
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.SendDailyMailUsesMailHourTests`
Expected: FAIL — `test_skips_user_before_their_chosen_hour` fails: the command still uses the hardcoded `8`, so at 9am it sends the prompt (outbox has 1, expected 0).

- [ ] **Step 3: Update the command**

In `core/management/commands/send_daily_mail.py`, change the `handle` method's loop. Replace:

```python
        for user in User.objects.filter(confirmed_email=True,
                                        is_subscribed=True):
            local_time = user.local_time()
            if local_time is None or local_time.hour < 8:
                continue
```

with:

```python
        for user in User.objects.filter(confirmed_email=True,
                                        is_subscribed=True):
            local_time = user.local_time()
            if local_time is None or local_time.hour < user.mail_hour:
                continue
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python manage.py test core.tests.SendDailyMailUsesMailHourTests`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `python manage.py test`
Expected: PASS — every test. The pre-existing `SendDailyMailCommandTests` still pass because the default `mail_hour` is 8, matching their hardcoded expectations.

- [ ] **Step 6: Commit**

```bash
git add core/management/commands/send_daily_mail.py core/tests.py
git commit -m "Send the daily prompt at each user's chosen hour"
```

---

## Final verification

- [ ] Run the entire test suite: `python manage.py test` — expected: all tests pass.
- [ ] Run `python manage.py makemigrations --check --dry-run` — expected: "No changes detected" (the model and migrations are in sync).
- [ ] Manual smoke test: `python manage.py runserver`, register a new account, confirm via the link printed at `/mailbox/`, and verify you land on `/onboarding/`. Completing the form should take you to the dashboard; visiting `/onboarding/` again should redirect to the dashboard.
