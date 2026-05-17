# Auth Flow Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the 9 authentication pages to use a centered card with a bottom-pinned footer, plus minor cleanups, with no behavior changes.

**Architecture:** A new standalone base template `templates/registration/auth_base.html` provides a full-viewport flex column: wordmark + centered white card on a gray background, footer pinned to the bottom. The 9 auth page templates are rewritten to extend it and fill a `card` block. A small set of scoped `.auth-*` CSS classes is added to the shared stylesheet; no existing CSS or non-auth template is touched.

**Tech Stack:** Django templates, Bootstrap (local `bootstrap.css`), plain CSS in `dailyinquirer/static/css/styles.css`.

---

## Verification note

These changes are HTML/CSS only — there is no template test suite, so verification is done by rendering pages in the Django dev server. Start it once with:

```bash
python manage.py runserver
```

`DEBUG` must be true so `/static/` files and the redesigned pages serve correctly. Leave the server running across tasks; Django auto-reloads on template/CSS changes.

---

## Task 1: Add scoped auth CSS classes

**Files:**
- Modify: `dailyinquirer/static/css/styles.css` (append at end)

- [ ] **Step 1: Append the auth classes**

Append the following to the end of `dailyinquirer/static/css/styles.css`. Do not modify any existing rule.

```css

/* --- Auth pages --- */
.auth-page {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background-color: #f4f4f6;
}

.auth-main {
    flex: 1 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 16px;
}

.auth-wordmark {
    font-family: 'TypoSlab Irregular Demo', sans-serif;
    font-weight: 700;
    font-size: 1.5rem;
    margin-bottom: 24px;
}

.auth-wordmark a,
.auth-wordmark a:hover {
    color: inherit;
    text-decoration: none;
}

.auth-card {
    width: 100%;
    max-width: 400px;
    background: #fff;
    border: 1px solid #e3e3e6;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.07);
    padding: 32px;
}

.auth-card h1 {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 4px;
}

.auth-subtitle {
    color: #777;
    font-size: 0.85em;
    margin-bottom: 20px;
}

.auth-alt {
    text-align: center;
    font-size: 0.85em;
    color: #777;
    margin-top: 16px;
    margin-bottom: 0;
}

.auth-footer {
    flex-shrink: 0;
    border-top: 1px solid #e3e3e6;
    text-align: center;
    padding: 16px;
}

.auth-footer p {
    margin: 0;
}
```

- [ ] **Step 2: Commit**

```bash
git add dailyinquirer/static/css/styles.css
git commit -m "Add scoped auth-page CSS classes"
```

---

## Task 2: Create the auth base template

**Files:**
- Create: `templates/registration/auth_base.html`

- [ ] **Step 1: Create the file**

Create `templates/registration/auth_base.html` with exactly this content:

```html
<!DOCTYPE html>
<html lang="en">

<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <meta name="description" content="">
    <title>{% block title %}The Daily Inquirer{% endblock %}</title>
    <link href="/static/css/bootstrap.css" rel="stylesheet">
    <link href="/static/css/fonts.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css?family=Open+Sans" rel="stylesheet">
    <link href="/static/css/styles.css" rel="stylesheet">
</head>

<body class="auth-page">
    <main class="auth-main">
        <div class="auth-wordmark"><a href="/">The Daily Inquirer</a></div>
        <div class="auth-card">
            {% block card %}{% endblock %}
        </div>
    </main>
    <footer class="auth-footer">
        <p><a href="/terms/" class="footer-link">Terms</a><a href="/privacy/" class="footer-link">Privacy</a></p>
    </footer>
</body>

</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/registration/auth_base.html
git commit -m "Add centered-card auth base template"
```

(No page extends it yet; visual verification happens in Task 3.)

---

## Task 3: Rewrite the login page

**Files:**
- Modify: `templates/registration/login.html` (full replacement)

- [ ] **Step 1: Replace the file contents**

Replace the entire contents of `templates/registration/login.html` with:

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1>Log in</h1>
<p class="auth-subtitle">Welcome back! Please enter your email and password to continue.</p>
{% if form.errors %}{% for field in form %}{% for error in field.errors %}
<div class="alert alert-danger"><strong>{{ error|escape }}</strong></div>
{% endfor %}{% endfor %}{% for error in form.non_field_errors %}
<div class="alert alert-danger"><strong>{{ error|escape }}</strong></div>
{% endfor %}{% endif %}
<form method="post" action="{% url 'login' %}">
    {% csrf_token %}
    <div class="form-group">
        <label for="id_username">Email</label>
        <input type="text" name="username" class="form-control" id="id_username" placeholder="email@example.com" required="">
    </div>
    <div class="form-group">
        <label for="id_password">Password</label>
        <input type="password" class="form-control" name="password" id="id_password" placeholder="Password" required="">
    </div>
    <a href="{% url 'password_reset' %}" class="dotted">Forgot password?</a>
    <button type="submit" value="login" class="btn btn-primary btn-block mt-3">Log in</button>
    <input type="hidden" name="next" value="{{ next }}" />
</form>
<p class="auth-alt">No account? <a href="{% url 'register' %}" class="dotted">Sign up</a></p>
{% endblock %}
```

- [ ] **Step 2: Verify in the browser**

Visit `http://127.0.0.1:8000/login/`. Confirm:
- The card is centered horizontally and vertically; the "The Daily Inquirer" wordmark sits above it.
- The footer ("Terms Privacy") is pinned to the bottom of the viewport.
- "Forgot password?" is a plain link (not a gray button); a "No account? Sign up" link shows below the button.

- [ ] **Step 3: Verify the login form still works**

Submit the form with a known account; confirm a successful login redirects as before. Submit with bad credentials; confirm the red error alert renders inside the card.

- [ ] **Step 4: Commit**

```bash
git add templates/registration/login.html
git commit -m "Redesign login page with centered card layout"
```

---

## Task 4: Rewrite the register page

**Files:**
- Modify: `templates/registration/register.html` (full replacement)

- [ ] **Step 1: Replace the file contents**

Replace the entire contents of `templates/registration/register.html` with:

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1>Sign up</h1>
<p class="auth-subtitle">Create your account to get the news every morning.</p>
{% if form.errors %}{% for field in form %}{% for error in field.errors %}
<div class="alert alert-danger"><strong>{{ error|escape }}</strong></div>
{% endfor %}{% endfor %}{% for error in form.non_field_errors %}
<div class="alert alert-danger"><strong>{{ error|escape }}</strong></div>
{% endfor %}{% endif %}
<form method="post" action="">
    {% csrf_token %}
    <div class="form-group">
        <label for="id_email">Email</label>
        <input type="email" class="form-control" id="id_email" placeholder="email@example.com" name="email" required="">
    </div>
    <div class="form-group">
        <label for="id_password1">Password</label>
        <input type="password" class="form-control" id="id_password1" placeholder="Password" name="password1" required="">
    </div>
    <div class="form-group">
        <label for="id_password2">Confirm password</label>
        <input type="password" class="form-control" id="id_password2" placeholder="Confirm password" name="password2" required="">
    </div>
    <div class="form-group">
        <label for="id_timezone">Timezone</label>
        {% load tz %}
        {% with "US/Eastern" as local_tz %}
        <select class="form-control" name="timezone" id="id_timezone">
            {% for tz in timezones %}
            <option value="{{ tz }}"{% if tz == local_tz %} selected{% endif %}>{{ tz }}</option>
            {% endfor %}
        </select>
        {% endwith %}
    </div>
    <button type="submit" class="btn btn-primary btn-block">Sign up</button>
    <p class="auth-subtitle mt-2" style="margin-bottom: 0;">By signing up you agree to the <a href="/terms/" class="dotted">terms</a> and <a href="/privacy/" class="dotted">privacy policy</a>.</p>
</form>
<p class="auth-alt">Already have an account? <a href="{% url 'login' %}" class="dotted">Log in</a></p>
{% endblock %}
```

Note: the `name`/`id` attributes (`email`, `password1`, `password2`, `timezone`) are unchanged from the original so the view's form handling still works. The timezone `<select>` keeps the `{% load tz %}` / `{% with %}` / `{% for %}` logic, with `{% endwith %}` now correctly placed after `</select>`.

- [ ] **Step 2: Verify in the browser**

Visit `http://127.0.0.1:8000/register/`. Confirm the centered card, pinned footer, all four labeled fields (email, password, confirm password, timezone), and the "Already have an account? Log in" link.

- [ ] **Step 3: Verify the register form still works**

Submit with a new email; confirm registration proceeds (confirmation-email-sent page) as before. Submit with mismatched passwords; confirm the error alert renders inside the card.

- [ ] **Step 4: Commit**

```bash
git add templates/registration/register.html
git commit -m "Redesign register page with centered card layout"
```

---

## Task 5: Rewrite the password-reset form pages

**Files:**
- Modify: `templates/registration/password_reset_form.html` (full replacement)
- Modify: `templates/registration/password_reset_confirm.html` (full replacement)

- [ ] **Step 1: Replace `password_reset_form.html`**

Replace the entire contents of `templates/registration/password_reset_form.html` with:

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1>Reset password</h1>
<p class="auth-subtitle">Enter your email and we'll send you a link to reset your password.</p>
{% if form.errors %}{% for field in form %}{% for error in field.errors %}
<div class="alert alert-danger"><strong>{{ error|escape }}</strong></div>
{% endfor %}{% endfor %}{% for error in form.non_field_errors %}
<div class="alert alert-danger"><strong>{{ error|escape }}</strong></div>
{% endfor %}{% endif %}
<form action="" method="post">
    {% csrf_token %}
    <div class="form-group">
        <label for="id_email">Email</label>
        <input type="email" class="form-control" placeholder="email@example.com" name="email" maxlength="254" id="id_email" required="">
    </div>
    <input type="submit" class="btn btn-primary btn-block" value="Send reset link" />
</form>
<p class="auth-alt">Remembered it? <a href="{% url 'login' %}" class="dotted">Log in</a></p>
{% endblock %}
```

- [ ] **Step 2: Replace `password_reset_confirm.html`**

Replace the entire contents of `templates/registration/password_reset_confirm.html` with:

```html
{% extends "registration/auth_base.html" %}
{% block card %}
{% if validlink %}
<h1>Set a new password</h1>
<p class="auth-subtitle">Enter and confirm your new password.</p>
{% if form.errors %}{% for field in form %}{% for error in field.errors %}
<div class="alert alert-danger"><strong>{{ error|escape }}</strong></div>
{% endfor %}{% endfor %}{% for error in form.non_field_errors %}
<div class="alert alert-danger"><strong>{{ error|escape }}</strong></div>
{% endfor %}{% endif %}
<form action="" method="post">
    {% csrf_token %}
    <div class="form-group">
        <label for="id_new_password1">New password</label>
        <input type="password" class="form-control" placeholder="New password" name="new_password1" maxlength="254" id="id_new_password1" required="">
    </div>
    <div class="form-group">
        <label for="id_new_password2">Confirm password</label>
        <input type="password" class="form-control" placeholder="Confirm password" name="new_password2" maxlength="254" id="id_new_password2" required="">
    </div>
    <input type="submit" class="btn btn-primary btn-block" value="Change my password" />
</form>
{% else %}
<h1>Password reset failed</h1>
<p class="auth-subtitle">The password reset link was invalid, possibly because it has already been used. Please request a new password reset.</p>
<a href="{% url 'password_reset' %}" class="btn btn-primary btn-block">Request a new link</a>
{% endif %}
{% endblock %}
```

Note: the second password input's `id` is corrected from `id_new_password1` (a duplicate-id bug in the original) to `id_new_password2`. Field `name` attributes are unchanged.

- [ ] **Step 3: Verify in the browser**

Visit `http://127.0.0.1:8000/password_reset/` — confirm the centered card and pinned footer. Walk the full reset flow (submit email → open the reset link from the local mailbox at `/mailbox/`) to reach the confirm page, and confirm it renders with both labeled password fields. Visit the confirm URL with a tampered token to confirm the "Password reset failed" branch renders.

- [ ] **Step 4: Commit**

```bash
git add templates/registration/password_reset_form.html templates/registration/password_reset_confirm.html
git commit -m "Redesign password-reset form pages with centered card layout"
```

---

## Task 6: Rewrite the password-reset message pages

**Files:**
- Modify: `templates/registration/password_reset_done.html` (full replacement)
- Modify: `templates/registration/password_reset_complete.html` (full replacement)

- [ ] **Step 1: Replace `password_reset_done.html`**

Replace the entire contents of `templates/registration/password_reset_done.html` with:

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1>Check your email</h1>
<p class="auth-subtitle">We've emailed you instructions for resetting your password. If they haven't arrived in a few minutes, check your spam folder.</p>
{% if user is not None and not user.is_authenticated %}
<a href="{% url 'login' %}" class="btn btn-primary btn-block">Log in</a>
{% endif %}
{% endblock %}
```

- [ ] **Step 2: Replace `password_reset_complete.html`**

Replace the entire contents of `templates/registration/password_reset_complete.html` with:

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1>Password changed</h1>
<p class="auth-subtitle">Your password was successfully changed.</p>
<a href="{% url 'login' %}" class="btn btn-primary btn-block">Log in</a>
{% endblock %}
```

- [ ] **Step 3: Verify in the browser**

Continue the reset flow from Task 5: after submitting the request, confirm the "Check your email" page renders with the centered card; after changing the password, confirm the "Password changed" page renders with a working "Log in" button.

- [ ] **Step 4: Commit**

```bash
git add templates/registration/password_reset_done.html templates/registration/password_reset_complete.html
git commit -m "Redesign password-reset message pages with centered card layout"
```

---

## Task 7: Rewrite the email-confirmation pages

**Files:**
- Modify: `templates/registration/resend_confirmation.html` (full replacement)
- Modify: `templates/registration/activation_email_sent.html` (full replacement)
- Modify: `templates/registration/user_unconfirmed.html` (full replacement)

- [ ] **Step 1: Replace `resend_confirmation.html`**

Replace the entire contents of `templates/registration/resend_confirmation.html` with:

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1>Resend confirmation</h1>
<p class="auth-subtitle">Enter your email and we'll send another confirmation link.</p>
{% if form.errors %}{% for field in form %}{% for error in field.errors %}
<div class="alert alert-danger"><strong>{{ error|escape }}</strong></div>
{% endfor %}{% endfor %}{% for error in form.non_field_errors %}
<div class="alert alert-danger"><strong>{{ error|escape }}</strong></div>
{% endfor %}{% endif %}
<form action="" method="post">
    {% csrf_token %}
    <div class="form-group">
        <label for="id_email">Email</label>
        <input type="email" class="form-control" placeholder="email@example.com" name="email" maxlength="254" id="id_email" required="">
    </div>
    <input type="submit" class="btn btn-primary btn-block" value="Resend confirmation" />
</form>
{% endblock %}
```

- [ ] **Step 2: Replace `activation_email_sent.html`**

Replace the entire contents of `templates/registration/activation_email_sent.html` with:

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1>Confirmation email sent</h1>
<p class="auth-subtitle" style="margin-bottom: 0;">A confirmation email has been sent to {{ email }}. If you did not get this email we can <a href="/resend_confirmation/" class="dotted">resend it</a>.</p>
{% endblock %}
```

- [ ] **Step 3: Replace `user_unconfirmed.html`**

Replace the entire contents of `templates/registration/user_unconfirmed.html` with:

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1>Confirm your email</h1>
<p class="auth-subtitle" style="margin-bottom: 0;">You must confirm your email before continuing. If you did not receive an email you can <a href="/resend_confirmation/" class="dotted">resend it</a>.</p>
{% endblock %}
```

- [ ] **Step 4: Verify in the browser**

Visit `http://127.0.0.1:8000/resend_confirmation/` and confirm the centered card with the labeled email field. Trigger a registration to see the "Confirmation email sent" page, and visit `http://127.0.0.1:8000/unconfirmed_email/` to see the "Confirm your email" page — both should show the centered card and pinned footer.

- [ ] **Step 5: Commit**

```bash
git add templates/registration/resend_confirmation.html templates/registration/activation_email_sent.html templates/registration/user_unconfirmed.html
git commit -m "Redesign email-confirmation pages with centered card layout"
```

---

## Task 8: Full-flow verification

**Files:** none (verification only)

- [ ] **Step 1: Confirm non-auth pages are unchanged**

Visit `/`, `/terms/`, and `/privacy/`. Confirm they look exactly as before (they still use `core/base.html`; no `.auth-*` class affects them).

- [ ] **Step 2: Confirm the footer pins on short and tall content**

On each auth page, confirm the footer sits at the bottom of the viewport even when the card is short. Resize the window narrow (mobile width) and confirm the card stays centered and does not overflow.

- [ ] **Step 3: Confirm `confirm_email.html` was not touched**

Run `git status` and confirm `templates/registration/confirm_email.html` is not in the diff — it is a plain-text email body and is intentionally left unchanged.

- [ ] **Step 4: Final review**

Run `git log --oneline` and confirm one commit per task (Tasks 1, 3, 4, 5, 6, 7) plus this plan's source spec. No further commit needed for this task.
