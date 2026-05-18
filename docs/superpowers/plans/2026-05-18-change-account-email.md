# Change Account Email Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a logged-in user change their account email from the settings page, with a server-side "already taken" check and a verify-the-new-address pending state.

**Architecture:** Add a `pending_email` field to the `User` model. A new view stores a requested address as `pending_email`, emails a single-use confirmation link to the new address and a heads-up notice to the old address. A second view validates that link and swaps `email`. The settings page gains a pencil-toggle editor (native `<details>`, no JavaScript) and a pending banner with Resend/Cancel actions.

**Tech Stack:** Django 5, Python 3.14, SQLite (local), Django template language, `PasswordResetTokenGenerator`-based tokens, `mail.outbox` for email assertions in tests.

**Spec:** `docs/superpowers/specs/2026-05-18-change-account-email-design.md`

**Test commands:** CI runs `python manage.py test`. Run a single class with e.g. `python manage.py test core.tests.EmailChangeViewTests`.

---

## File Structure

- `authentication/models.py` — add `pending_email` field to `User`.
- `authentication/migrations/0006_user_pending_email.py` — generated migration.
- `authentication/tokens.py` — add `EmailChangeTokenGenerator` + `email_change_token`.
- `core/forms.py` — add `ChangeEmailForm`.
- `core/views.py` — add `manage_email_change`, `confirm_email_change`, and the `send_email_change_emails` helper.
- `core/urls.py` — add two URL patterns.
- `templates/registration/change_email_confirm.html` — confirmation email body (new address).
- `templates/registration/change_email_notice.html` — notice email body (old address).
- `templates/registration/change_email_confirmed.html` — result page after the link is clicked.
- `core/templates/core/settings.html` — pencil editor, pending banner, alerts.
- `dailyinquirer/static/css/account.css` — styles for the editor and pending banner.
- `core/tests.py` — `EmailChangeModelTests` and `EmailChangeViewTests`.

---

## Task 1: Add the `pending_email` field

**Files:**
- Modify: `authentication/models.py:49`
- Create: `authentication/migrations/0006_user_pending_email.py` (generated)
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing test**

Append a new class to the end of `core/tests.py`:

```python
class EmailChangeModelTests(TestCase):
    def test_new_user_has_no_pending_email(self):
        user = User.objects.create_user(
            email='m@example.com', password='mostdope1')
        self.assertIsNone(user.pending_email)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test core.tests.EmailChangeModelTests`
Expected: FAIL — `AttributeError: 'User' object has no attribute 'pending_email'`

- [ ] **Step 3: Add the field**

In `authentication/models.py`, add the field directly after the `confirmed_email` line (line 49):

```python
    confirmed_email = models.BooleanField(default=False)
    pending_email = models.EmailField(max_length=255, null=True, blank=True)
```

- [ ] **Step 4: Generate the migration**

Run: `python manage.py makemigrations authentication`
Expected output:
```
Migrations for 'authentication':
  authentication/migrations/0006_user_pending_email.py
    + Add field pending_email to user
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test core.tests.EmailChangeModelTests`
Expected: PASS (the test runner applies migrations automatically).

- [ ] **Step 6: Commit**

```bash
git add authentication/models.py authentication/migrations/0006_user_pending_email.py core/tests.py
git commit -m "Add pending_email field to User"
```

---

## Task 2: Add the email-change token generator

**Files:**
- Modify: `authentication/tokens.py`
- Test: `core/tests.py` (`EmailChangeModelTests`)

- [ ] **Step 1: Write the failing tests**

Add these two methods to the `EmailChangeModelTests` class in `core/tests.py`:

```python
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
```

Add this import near the existing `from authentication.tokens import ...` line at the top of `core/tests.py`:

```python
from authentication.tokens import account_activation_token, email_change_token
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test core.tests.EmailChangeModelTests`
Expected: FAIL — `ImportError: cannot import name 'email_change_token'`

- [ ] **Step 3: Add the token generator**

Append to `authentication/tokens.py`:

```python


class EmailChangeTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.email}{user.pending_email}"


email_change_token = EmailChangeTokenGenerator()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test core.tests.EmailChangeModelTests`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add authentication/tokens.py core/tests.py
git commit -m "Add single-use token generator for email changes"
```

---

## Task 3: Add the email and result-page templates

No tests — these are plain templates exercised by later tasks.

**Files:**
- Create: `templates/registration/change_email_confirm.html`
- Create: `templates/registration/change_email_notice.html`
- Create: `templates/registration/change_email_confirmed.html`

- [ ] **Step 1: Create the confirmation email body**

Create `templates/registration/change_email_confirm.html`:

```
{% autoescape off %}
Hi,

You asked to change your Daily Inquirer email address to {{ pending_email }}.

Click the link below to confirm the change:

http://{{ domain }}{% url 'confirm_email_change' uidb64=uid token=token %}

If you didn't request this, you can ignore this email — nothing will change.
{% endautoescape %}
```

- [ ] **Step 2: Create the notice email body**

Create `templates/registration/change_email_notice.html`:

```
Hi,

A request was made to change the email address on your Daily Inquirer
account to {{ pending_email }}.

If this was you, check that inbox for a confirmation link. The change will
not take effect until it is confirmed.

If this wasn't you, your account is still safe — no change has been made.
You may want to reset your password.
```

- [ ] **Step 3: Create the result page**

Create `templates/registration/change_email_confirmed.html`:

```html
{% extends "registration/auth_base.html" %}
{% block card %}
{% if taken %}
<h1 class="auth-title">Address unavailable</h1>
<p class="auth-subtitle">We couldn't change your email to {{ new_email }} — that address was claimed by another account before you confirmed. Your account email is unchanged. <a href="/settings/" class="auth-link">Back to settings</a>.</p>
{% else %}
<h1 class="auth-title">Email address updated</h1>
<p class="auth-subtitle">Your Daily Inquirer email address is now {{ new_email }}. <a href="/login/" class="auth-link">Log in</a> to continue.</p>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Commit**

```bash
git add templates/registration/change_email_confirm.html templates/registration/change_email_notice.html templates/registration/change_email_confirmed.html
git commit -m "Add email-change email bodies and result page"
```

---

## Task 4: Add the `manage_email_change` view (request action)

This task adds the form, the URL, the email-sending helper, and the `request`
action of the view. Resend/Cancel come in Task 5; the confirm view in Task 6.

**Files:**
- Modify: `core/forms.py`
- Modify: `core/views.py`
- Modify: `core/urls.py`
- Test: `core/tests.py` (new `EmailChangeViewTests` class)

- [ ] **Step 1: Write the failing tests**

Append a new class to the end of `core/tests.py`:

These tests assert only on model state and the email outbox — they do not
depend on rendered template text, so they pass as soon as Task 4 is done.
Alert-text assertions are added in Task 7 once the template renders them.

```python
class EmailChangeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='old@example.com', password='mostdope1')
        self.client.force_login(self.user)

    def test_request_available_email_sets_pending_and_sends_two_emails(self):
        self.client.post(reverse('manage_email_change'), {
            'action': 'request', 'email': 'new@example.com'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.pending_email, 'new@example.com')
        self.assertEqual(self.user.email, 'old@example.com')
        self.assertEqual(len(mail.outbox), 2)
        recipients = [m.to[0] for m in mail.outbox]
        self.assertIn('new@example.com', recipients)
        self.assertIn('old@example.com', recipients)

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test core.tests.EmailChangeViewTests`
Expected: FAIL — `NoReverseMatch: Reverse for 'manage_email_change' not found`

- [ ] **Step 3: Add the form**

Append to `core/forms.py`:

```python


class ChangeEmailForm(forms.Form):
    email = forms.EmailField(max_length=255)
```

- [ ] **Step 4: Update imports in `core/views.py`**

Change the `authentication.tokens` import line:

```python
from authentication.tokens import account_activation_token, email_change_token
```

Change the `core.forms` import line:

```python
from core.forms import ResendConfirmationForm, SettingsForm, ChangeEmailForm
```

- [ ] **Step 5: Add the helper and the view**

Add to `core/views.py`, after the existing `settings` view (after line 128):

```python
def send_email_change_emails(request, user):
    current_site = get_current_site(request)
    confirm_message = render_to_string(
        'registration/change_email_confirm.html', {
            'domain': current_site.domain,
            'pending_email': user.pending_email,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': email_change_token.make_token(user),
        })
    EmailMessage(
        'Confirm your new Daily Inquirer email',
        confirm_message,
        "Beep Boop <beep-boop@dailyinquirer.me>",
        [user.pending_email],
    ).send()

    notice_message = render_to_string(
        'registration/change_email_notice.html', {
            'pending_email': user.pending_email,
        })
    EmailMessage(
        'Your Daily Inquirer email is being changed',
        notice_message,
        "Beep Boop <beep-boop@dailyinquirer.me>",
        [user.email],
    ).send()


@login_required
def manage_email_change(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    user = request.user
    action = request.POST.get('action', 'request')
    context = {'timezones': pytz.common_timezones}

    form = ChangeEmailForm(request.POST)
    if not form.is_valid():
        context['email_change_error'] = 'Enter a valid email address.'
        context['submitted_email'] = request.POST.get('email', '')
        return render(request, 'core/settings.html', context)

    new_email = User.objects.normalize_email(form.cleaned_data['email'])
    if new_email.lower() == user.email.lower():
        context['email_change_error'] = "That's already your email address."
        context['submitted_email'] = new_email
        return render(request, 'core/settings.html', context)

    taken = User.objects.filter(email__iexact=new_email) \
        .exclude(pk=user.pk).exists()
    if taken:
        context['email_change_error'] = 'That email address is already in use.'
        context['submitted_email'] = new_email
        return render(request, 'core/settings.html', context)

    user.pending_email = new_email
    user.save()
    send_email_change_emails(request, user)
    context['email_change_requested'] = True
    return render(request, 'core/settings.html', context)
```

Note: this version handles only the `request` action. Task 5 adds the
`resend`/`cancel` branches before the form parsing. The `action` variable is
read here so Task 5's change is a small insertion.

- [ ] **Step 6: Add the URL**

In `core/urls.py`, add to `urlpatterns` (before the closing `]`):

```python
    path('settings/email/', views.manage_email_change,
         name='manage_email_change'),
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python manage.py test core.tests.EmailChangeViewTests`
Expected: PASS (3 tests). The view renders the existing `core/settings.html`;
the new `email_change_*` context keys are simply undefined-and-falsy in the
template until Task 7, which is harmless.

- [ ] **Step 8: Commit**

```bash
git add core/forms.py core/views.py core/urls.py core/tests.py
git commit -m "Add manage_email_change view for requesting an email change"
```

---

## Task 5: Add Resend and Cancel actions

**Files:**
- Modify: `core/views.py` (`manage_email_change`)
- Test: `core/tests.py` (`EmailChangeViewTests`)

- [ ] **Step 1: Write the failing tests**

Add to the `EmailChangeViewTests` class in `core/tests.py`:

```python
    def test_cancel_clears_pending_email(self):
        self.user.pending_email = 'new@example.com'
        self.user.save()
        response = self.client.post(reverse('manage_email_change'), {
            'action': 'cancel'})
        self.user.refresh_from_db()
        self.assertIsNone(self.user.pending_email)
        self.assertEqual(response.status_code, 200)

    def test_resend_sends_confirmation_again(self):
        self.user.pending_email = 'new@example.com'
        self.user.save()
        response = self.client.post(reverse('manage_email_change'), {
            'action': 'resend'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.pending_email, 'new@example.com')
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test core.tests.EmailChangeViewTests.test_cancel_clears_pending_email core.tests.EmailChangeViewTests.test_resend_sends_confirmation_again`
Expected: FAIL — without the action branches, `cancel`/`resend` fall through to `ChangeEmailForm` parsing (invalid, no `email`), so `pending_email` is not cleared and no emails are sent.

- [ ] **Step 3: Add the resend/cancel branches**

In `core/views.py`, in `manage_email_change`, insert these branches
immediately after the `context = {...}` line and **before** the
`form = ChangeEmailForm(request.POST)` line:

```python
    if action == 'cancel':
        user.pending_email = None
        user.save()
        context['email_change_canceled'] = True
        return render(request, 'core/settings.html', context)

    if action == 'resend':
        if user.pending_email:
            send_email_change_emails(request, user)
            context['email_change_requested'] = True
        return render(request, 'core/settings.html', context)

```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test core.tests.EmailChangeViewTests.test_cancel_clears_pending_email core.tests.EmailChangeViewTests.test_resend_sends_confirmation_again`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/views.py core/tests.py
git commit -m "Add resend and cancel actions to email-change view"
```

---

## Task 6: Add the `confirm_email_change` view

**Files:**
- Modify: `core/views.py`
- Modify: `core/urls.py`
- Test: `core/tests.py` (`EmailChangeViewTests`)

- [ ] **Step 1: Write the failing tests**

Add to the `EmailChangeViewTests` class in `core/tests.py`:

```python
    def _confirm_url(self, user):
        return reverse('confirm_email_change', kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': email_change_token.make_token(user),
        })

    def test_confirm_swaps_the_email_address(self):
        self.user.pending_email = 'new@example.com'
        self.user.save()
        response = self.client.get(self._confirm_url(self.user))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'new@example.com')
        self.assertIsNone(self.user.pending_email)
        self.assertContains(response, 'updated')

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
        response = self.client.get(url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'old@example.com')
        self.assertIsNone(self.user.pending_email)
        self.assertContains(response, 'unavailable')
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test core.tests.EmailChangeViewTests.test_confirm_swaps_the_email_address`
Expected: FAIL — `NoReverseMatch: Reverse for 'confirm_email_change' not found`

- [ ] **Step 3: Add the view**

Add to `core/views.py`, after `manage_email_change`:

```python
def confirm_email_change(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if (user is None or not user.pending_email
            or not email_change_token.check_token(user, token)):
        return HttpResponse('Email change link is invalid!')

    new_email = user.pending_email
    taken = User.objects.filter(email__iexact=new_email) \
        .exclude(pk=user.pk).exists()
    if taken:
        user.pending_email = None
        user.save()
        return render(request, 'registration/change_email_confirmed.html',
                      {'taken': True, 'new_email': new_email})

    user.email = new_email
    user.pending_email = None
    user.save()
    return render(request, 'registration/change_email_confirmed.html',
                  {'new_email': new_email})
```

- [ ] **Step 4: Add the URL**

In `core/urls.py`, add to `urlpatterns` (before the closing `]`):

```python
    path('settings/email/confirm/<uidb64>/<token>/',
         views.confirm_email_change, name='confirm_email_change'),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test core.tests.EmailChangeViewTests`
Expected: PASS for all confirm tests (request/resend/cancel tests still pass).

- [ ] **Step 6: Commit**

```bash
git add core/views.py core/urls.py core/tests.py
git commit -m "Add confirm_email_change view to complete the email swap"
```

---

## Task 7: Update the settings page UI

**Files:**
- Modify: `core/templates/core/settings.html`
- Test: `core/tests.py` (`EmailChangeViewTests`)

- [ ] **Step 1: Write the failing tests**

Add to the `EmailChangeViewTests` class in `core/tests.py`:

```python
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

    def test_request_available_email_renders_pending_alert(self):
        response = self.client.post(reverse('manage_email_change'), {
            'action': 'request', 'email': 'new@example.com'})
        self.assertContains(response, 'pending')
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test core.tests.EmailChangeViewTests`
Expected: the four new tests FAIL — `ed-email-edit` / `ed-pending` markup and
the `already in use` / `pending` alert text are not yet in the template. The
Task 4–6 tests still pass.

- [ ] **Step 3: Add the email-change alerts**

In `core/templates/core/settings.html`, immediately after the existing
`{% if form.errors %} ... {% endif %}` block (after line 23, before the first
`<section class="ed-card">`), insert:

```html
  {% if email_change_requested %}
  <div class="ed-alert ed-alert--ok">Confirmation sent to {{ user.pending_email }}. The change is pending until you open the link in that email.</div>
  {% endif %}
  {% if email_change_canceled %}
  <div class="ed-alert ed-alert--ok">The pending email change has been canceled.</div>
  {% endif %}
  {% if email_change_error %}
  <div class="ed-alert ed-alert--error">{{ email_change_error|escape }}</div>
  {% endif %}
```

- [ ] **Step 4: Replace the Account card**

In `core/templates/core/settings.html`, replace the entire Account
`<section>` (lines 52-67, from `<section class="ed-card">` containing
`<h2 class="ed-card__head">Account</h2>` through its closing `</section>`)
with:

```html
  <section class="ed-card">
    <h2 class="ed-card__head">Account</h2>
    <p class="ed-card__sub">Manage access to your account.</p>

    <div class="ed-field">
      <span class="ed-field__label">Email address</span>
      {% if user.pending_email %}
      <div class="ed-pending">
        <p class="ed-pending__text">Change to <strong>{{ user.pending_email }}</strong> is pending &mdash; confirm it via the link we sent to that address.</p>
        <div class="ed-pending__actions">
          <form method="post" action="{% url 'manage_email_change' %}">
            {% csrf_token %}
            <input type="hidden" name="action" value="resend">
            <input type="hidden" name="email" value="{{ user.pending_email }}">
            <button class="ed-btn-ghost" type="submit">Resend confirmation</button>
          </form>
          <form method="post" action="{% url 'manage_email_change' %}">
            {% csrf_token %}
            <input type="hidden" name="action" value="cancel">
            <input type="hidden" name="email" value="{{ user.pending_email }}">
            <button class="ed-btn-ghost" type="submit">Cancel change</button>
          </form>
        </div>
      </div>
      {% else %}
      <details class="ed-email-edit"{% if email_change_error %} open{% endif %}>
        <summary class="ed-email-edit__summary">
          <span class="ed-email-edit__current">{{ user.email }}</span>
          <span class="ed-email-edit__pencil" aria-hidden="true">
            <svg width="14" height="14" viewBox="0 0 16 16"><path d="M11.5 1.5l3 3L5 14H2v-3z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
          </span>
          <span class="ed-email-edit__action">Edit</span>
        </summary>
        <form class="ed-email-edit__form" method="post" action="{% url 'manage_email_change' %}">
          {% csrf_token %}
          <input type="hidden" name="action" value="request">
          <input class="ed-input" type="email" name="email" placeholder="new@email.com" value="{{ submitted_email }}" required>
          <button class="ed-btn" type="submit">Send confirmation</button>
        </form>
      </details>
      {% endif %}
      <p class="ed-hint">Changing your email sends a confirmation link to the new address; the change takes effect once you open it.</p>
    </div>

    <div class="ed-actions">
      <form action="/password_reset/" method="post">
        {% csrf_token %}
        <input type="hidden" name="email" value="{{ user.email }}">
        <button class="ed-btn-ghost" type="submit">Reset password</button>
      </form>
      <form action="/logout/" method="post">
        {% csrf_token %}
        <button class="ed-btn-ghost" type="submit">Log out</button>
      </form>
    </div>
    <p class="ed-hint">Reset password sends a link to {{ user.email }}.</p>
  </section>
```

Note: the resend/cancel forms include a hidden `email` field set to the
pending address. The view's `request` branch parses `ChangeEmailForm` (which
requires `email`), but `resend`/`cancel` return before that parsing — the
hidden field is included only so the form is never missing required data if
the action branches are ever reordered. It is harmless.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test core.tests.EmailChangeViewTests`
Expected: PASS — all `EmailChangeViewTests` (including the Task 4 string
assertions `pending` / `already in use` / `already your email`, which now
resolve against the rendered alerts).

- [ ] **Step 6: Run the full suite**

Run: `python manage.py test`
Expected: PASS — no regressions in existing tests.

- [ ] **Step 7: Commit**

```bash
git add core/templates/core/settings.html core/tests.py
git commit -m "Add email editor and pending banner to settings page"
```

---

## Task 8: Style the email editor and pending banner

No tests — visual styling. Verify by eye with `python manage.py runserver`
and visiting `/settings/`.

**Files:**
- Modify: `dailyinquirer/static/css/account.css`

- [ ] **Step 1: Append the styles**

Append to `dailyinquirer/static/css/account.css`:

```css
.app .ed-email-edit {
  margin-top: 4px;
}

.app .ed-email-edit__summary {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  list-style: none;
  padding: 8px 0;
}

.app .ed-email-edit__summary::-webkit-details-marker {
  display: none;
}

.app .ed-email-edit__current {
  font-weight: 600;
}

.app .ed-email-edit__pencil {
  display: inline-flex;
  color: #6b6b6b;
}

.app .ed-email-edit__action {
  font-size: 0.85rem;
  color: #6b6b6b;
  text-decoration: underline;
}

.app .ed-email-edit[open] .ed-email-edit__action {
  visibility: hidden;
}

.app .ed-email-edit__form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.app .ed-email-edit__form .ed-input {
  flex: 1 1 220px;
}

.app .ed-pending {
  border: 1px dashed #c9b27a;
  background: #fbf6e7;
  border-radius: 6px;
  padding: 12px;
  margin-top: 4px;
}

.app .ed-pending__text {
  margin: 0 0 8px;
}

.app .ed-pending__actions {
  display: flex;
  gap: 8px;
}
```

If the surrounding `account.css` uses different colour tokens or spacing
conventions, match those instead of the literal values above — read the file
first and follow its established palette.

- [ ] **Step 2: Visual check**

Run: `python manage.py runserver`, log in, visit `/settings/`. Confirm the
email row shows a pencil + "Edit", expands to a form, and (after requesting a
change) shows the dashed pending banner with Resend/Cancel.

- [ ] **Step 3: Commit**

```bash
git add dailyinquirer/static/css/account.css
git commit -m "Style the settings email editor and pending banner"
```

---

## Final verification

- [ ] Run the full test suite: `python manage.py test` — expect all tests passing.
- [ ] Confirm `git status` is clean and all eight tasks are committed.
