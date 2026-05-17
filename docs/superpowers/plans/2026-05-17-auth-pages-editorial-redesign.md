# Auth Pages Editorial Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the 9 authentication web pages to match the editorial design language of the home page.

**Architecture:** Design tokens move to a shared `tokens.css` (`:root`) used by both the home page and the auth pages. The auth pages drop Bootstrap and are styled by a new `.auth-page`-scoped `auth.css`. All 9 pages share `auth_base.html`, so the shell is restyled once and each card's markup is updated to the new class vocabulary.

**Tech Stack:** Django 5.2 templates, plain CSS, no build step. Fonts: self-hosted `Special Elite` (via `fonts.css` `@font-face`) and Google `Open Sans`.

---

## Class vocabulary (used by Tasks 3, 4, 5)

The auth pages use exactly these classes. Tasks must use these names consistently.

- Layout (already on `auth_base.html`): `.auth-page` (body), `.auth-main`, `.auth-wordmark`, `.auth-card`, `.auth-footer`
- Card content: `.auth-title` (h1), `.auth-subtitle` (p), `.auth-fineprint` (small print p)
- Form: `.auth-form`, `.auth-field` (one per label+input), `.auth-label`, `.auth-input` (text/email/password inputs **and** the timezone `<select>`)
- Actions: `.auth-btn` (primary action — used on `<button>`, `<input type="submit">`, and `<a>`)
- Links: `.auth-link` (inline secondary links), `.auth-forgot` (the "Forgot password?" link), `.auth-alt` (centered "No account? …" line)
- Errors: `.auth-error` (the wrapper in `_form_errors.html`)

## Design tokens

`tokens.css` defines these on `:root`:

```css
:root {
  --ink: #1a1a1a;
  --ink-soft: #555;
  --ink-faint: #8a8a8a;
  --rule: #d8d4cc;
  --accent: #009302;
  --accent-rgb: 0, 147, 2;
  --danger: #b22222;
  --danger-rgb: 178, 34, 34;
  --paper: #ffffff;
  --serif: 'Special Elite', Georgia, 'Times New Roman', serif;
  --body: 'Open Sans', system-ui, sans-serif;
}
```

---

## Task 1: Shared tokens.css

Promote the design tokens to a shared `:root` stylesheet so the home and auth pages read one source of truth.

**Files:**
- Create: `dailyinquirer/static/css/tokens.css`
- Modify: `core/templates/core/base.html`
- Modify: `dailyinquirer/static/css/home.css`

- [ ] **Step 1: Create `dailyinquirer/static/css/tokens.css`**

```css
/* Shared design tokens. Loaded by core/base.html and registration/auth_base.html. */
:root {
  --ink: #1a1a1a;
  --ink-soft: #555;
  --ink-faint: #8a8a8a;
  --rule: #d8d4cc;
  --accent: #009302;
  --accent-rgb: 0, 147, 2;
  --danger: #b22222;
  --danger-rgb: 178, 34, 34;
  --paper: #ffffff;
  --serif: 'Special Elite', Georgia, 'Times New Roman', serif;
  --body: 'Open Sans', system-ui, sans-serif;
}
```

- [ ] **Step 2: Load `tokens.css` in `core/base.html`**

In `core/templates/core/base.html`, add the link in `<head>` immediately after the existing `styles.css` link and before `{% block extra_head %}`:

```html
    <link href="/static/css/styles.css" rel="stylesheet">
    <link href="/static/css/tokens.css" rel="stylesheet">
    {% block extra_head %}{% endblock %}
```

- [ ] **Step 3: Remove the local token block from `home.css`**

`dailyinquirer/static/css/home.css` currently begins with a `#home { --ink: …; … }` block (the first rule, ~11 lines, ending at the line with the closing `}` before the `/* ===… HOME PAGE` comment). Delete that entire `#home { … }` block plus the blank line after it, so the file now begins with the `/* ==…` comment header. All `var(--…)` references in the rest of the file are unchanged — they now resolve from `:root`.

- [ ] **Step 4: Verify the home page is unchanged**

Run: `.venv/bin/python manage.py test core.tests.HomePageTests`
Expected: PASS (4 tests — they assert markup, not CSS values).

Run: `.venv/bin/python manage.py runserver` and open `http://localhost:8000/`.
Expected: the home page looks exactly as before — green accent, Special Elite headings, card borders. (If anything is unstyled, `tokens.css` is not loading — check the `<link>` path.)

- [ ] **Step 5: Commit**

```bash
git add dailyinquirer/static/css/tokens.css core/templates/core/base.html dailyinquirer/static/css/home.css
git commit -m "Extract design tokens to shared tokens.css"
```

---

## Task 2: Auth shell — restyle auth_base.html, drop Bootstrap

Rewrite the shared auth shell to load the editorial stylesheets instead of Bootstrap, and add the page-level tests.

**Files:**
- Modify: `templates/registration/auth_base.html`
- Create: `dailyinquirer/static/css/auth.css` (placeholder — full styling is Task 5)
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Append to `core/tests.py` (the `from django.urls import reverse` import already exists at the top — do not duplicate it):

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python manage.py test core.tests.AuthPagesTests`
Expected: FAIL — current `auth_base.html` loads `bootstrap.css` and not `auth.css`.

- [ ] **Step 3: Create the placeholder `dailyinquirer/static/css/auth.css`**

```css
/* Editorial auth-page styling. Scoped under .auth-page. Filled in Task 5. */
```

- [ ] **Step 4: Rewrite `templates/registration/auth_base.html`**

Replace the entire file with:

```html
<!DOCTYPE html>
<html lang="en">

<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <meta name="description" content="">
    <title>{% block title %}The Daily Inquirer{% endblock %}</title>
    <link href="/static/css/fonts.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css?family=Open+Sans" rel="stylesheet">
    <link href="/static/css/tokens.css" rel="stylesheet">
    <link href="/static/css/auth.css" rel="stylesheet">
</head>

<body class="auth-page">
    <main class="auth-main">
        <div class="auth-wordmark"><a href="/">The Daily Inquirer</a></div>
        <div class="auth-card">
            {% block card %}{% endblock %}
        </div>
    </main>
    <footer class="auth-footer">
        <p><a href="/terms/">Terms</a><a href="/privacy/">Privacy</a></p>
    </footer>
</body>

</html>
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python manage.py test core.tests.AuthPagesTests`
Expected: PASS (9 tests).

- [ ] **Step 6: Commit**

```bash
git add templates/registration/auth_base.html dailyinquirer/static/css/auth.css core/tests.py
git commit -m "Restyle auth shell: drop Bootstrap, load editorial stylesheets"
```

---

## Task 3: Form-errors partial

Extract the duplicated form-error block into one editorial partial.

**Files:**
- Create: `templates/registration/_form_errors.html`

- [ ] **Step 1: Create `templates/registration/_form_errors.html`**

```html
{% if form.errors %}
<div class="auth-error" role="alert">
  {% for field in form %}{% for error in field.errors %}
  <p>{{ error|escape }}</p>
  {% endfor %}{% endfor %}
  {% for error in form.non_field_errors %}
  <p>{{ error|escape }}</p>
  {% endfor %}
</div>
{% endif %}
```

- [ ] **Step 2: Verify it has no template syntax errors**

Run: `.venv/bin/python manage.py check`
Expected: "System check identified no issues".

(The partial is not yet included anywhere — Task 4 wires it in.)

- [ ] **Step 3: Commit**

```bash
git add templates/registration/_form_errors.html
git commit -m "Add editorial form-errors partial"
```

---

## Task 4: Restyle the 9 auth card templates

Update each card's `{% block card %}` markup to the editorial class vocabulary; remove Bootstrap classes; use the errors partial.

**Files:**
- Modify: `templates/registration/login.html`
- Modify: `templates/registration/register.html`
- Modify: `templates/registration/password_reset_form.html`
- Modify: `templates/registration/password_reset_done.html`
- Modify: `templates/registration/password_reset_confirm.html`
- Modify: `templates/registration/password_reset_complete.html`
- Modify: `templates/registration/resend_confirmation.html`
- Modify: `templates/registration/user_unconfirmed.html`
- Modify: `templates/registration/activation_email_sent.html`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing markup test**

Append this method to the `AuthPagesTests` class in `core/tests.py`:

```python
    def test_login_uses_editorial_form_markup(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'auth-input')
        self.assertContains(response, 'auth-btn')
        self.assertNotContains(response, 'form-control')
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python manage.py test core.tests.AuthPagesTests.test_login_uses_editorial_form_markup`
Expected: FAIL — `login.html` still uses `form-control`, not `auth-input`.

- [ ] **Step 3: Replace `templates/registration/login.html`**

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1 class="auth-title">Log in</h1>
<p class="auth-subtitle">Welcome back — enter your email and password to continue.</p>
{% include "registration/_form_errors.html" %}
<form class="auth-form" method="post" action="{% url 'login' %}">
  {% csrf_token %}
  <div class="auth-field">
    <label class="auth-label" for="id_username">Email</label>
    <input class="auth-input" type="text" name="username" id="id_username" placeholder="email@example.com" required>
  </div>
  <div class="auth-field">
    <label class="auth-label" for="id_password">Password</label>
    <input class="auth-input" type="password" name="password" id="id_password" placeholder="Password" required>
  </div>
  <a href="{% url 'password_reset' %}" class="auth-forgot">Forgot password?</a>
  <button type="submit" value="login" class="auth-btn">Log in</button>
  <input type="hidden" name="next" value="{{ next }}">
</form>
<p class="auth-alt">No account? <a href="{% url 'register' %}" class="auth-link">Sign up</a></p>
{% endblock %}
```

- [ ] **Step 4: Replace `templates/registration/register.html`**

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1 class="auth-title">Sign up</h1>
<p class="auth-subtitle">Create your account to get a writing prompt every morning.</p>
{% include "registration/_form_errors.html" %}
<form class="auth-form" method="post" action="">
  {% csrf_token %}
  <div class="auth-field">
    <label class="auth-label" for="id_email">Email</label>
    <input class="auth-input" type="email" name="email" id="id_email" placeholder="email@example.com" required>
  </div>
  <div class="auth-field">
    <label class="auth-label" for="id_password1">Password</label>
    <input class="auth-input" type="password" name="password1" id="id_password1" placeholder="Password" required>
  </div>
  <div class="auth-field">
    <label class="auth-label" for="id_password2">Confirm password</label>
    <input class="auth-input" type="password" name="password2" id="id_password2" placeholder="Confirm password" required>
  </div>
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
  <button type="submit" class="auth-btn">Sign up</button>
  <p class="auth-fineprint">By signing up you agree to the <a href="/terms/" class="auth-link">terms</a> and <a href="/privacy/" class="auth-link">privacy policy</a>.</p>
</form>
<p class="auth-alt">Already have an account? <a href="{% url 'login' %}" class="auth-link">Log in</a></p>
{% endblock %}
```

- [ ] **Step 5: Replace `templates/registration/password_reset_form.html`**

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1 class="auth-title">Reset password</h1>
<p class="auth-subtitle">Enter your email and we'll send you a link to reset your password.</p>
{% include "registration/_form_errors.html" %}
<form class="auth-form" action="" method="post">
  {% csrf_token %}
  <div class="auth-field">
    <label class="auth-label" for="id_email">Email</label>
    <input class="auth-input" type="email" name="email" id="id_email" placeholder="email@example.com" maxlength="254" required>
  </div>
  <button type="submit" class="auth-btn">Send reset link</button>
</form>
<p class="auth-alt">Remembered it? <a href="{% url 'login' %}" class="auth-link">Log in</a></p>
{% endblock %}
```

- [ ] **Step 6: Replace `templates/registration/password_reset_done.html`**

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1 class="auth-title">Check your email</h1>
<p class="auth-subtitle">We've emailed you instructions for resetting your password. If they haven't arrived in a few minutes, check your spam folder.</p>
{% if user is not None and not user.is_authenticated %}
<a href="{% url 'login' %}" class="auth-btn">Log in</a>
{% endif %}
{% endblock %}
```

- [ ] **Step 7: Replace `templates/registration/password_reset_confirm.html`**

```html
{% extends "registration/auth_base.html" %}
{% block card %}
{% if validlink %}
<h1 class="auth-title">Set a new password</h1>
<p class="auth-subtitle">Enter and confirm your new password.</p>
{% include "registration/_form_errors.html" %}
<form class="auth-form" action="" method="post">
  {% csrf_token %}
  <div class="auth-field">
    <label class="auth-label" for="id_new_password1">New password</label>
    <input class="auth-input" type="password" name="new_password1" id="id_new_password1" placeholder="New password" maxlength="254" required>
  </div>
  <div class="auth-field">
    <label class="auth-label" for="id_new_password2">Confirm password</label>
    <input class="auth-input" type="password" name="new_password2" id="id_new_password2" placeholder="Confirm password" maxlength="254" required>
  </div>
  <button type="submit" class="auth-btn">Change my password</button>
</form>
{% else %}
<h1 class="auth-title">Password reset failed</h1>
<p class="auth-subtitle">The password reset link was invalid, possibly because it has already been used. Please request a new password reset.</p>
<a href="{% url 'password_reset' %}" class="auth-btn">Request a new link</a>
{% endif %}
{% endblock %}
```

- [ ] **Step 8: Replace `templates/registration/password_reset_complete.html`**

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1 class="auth-title">Password changed</h1>
<p class="auth-subtitle">Your password was successfully changed.</p>
<a href="{% url 'login' %}" class="auth-btn">Log in</a>
{% endblock %}
```

- [ ] **Step 9: Replace `templates/registration/resend_confirmation.html`**

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1 class="auth-title">Resend confirmation</h1>
<p class="auth-subtitle">Enter your email and we'll send another confirmation link.</p>
{% include "registration/_form_errors.html" %}
<form class="auth-form" action="" method="post">
  {% csrf_token %}
  <div class="auth-field">
    <label class="auth-label" for="id_email">Email</label>
    <input class="auth-input" type="email" name="email" id="id_email" placeholder="email@example.com" maxlength="254" required>
  </div>
  <button type="submit" class="auth-btn">Resend confirmation</button>
</form>
{% endblock %}
```

- [ ] **Step 10: Replace `templates/registration/user_unconfirmed.html`**

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1 class="auth-title">Confirm your email</h1>
<p class="auth-subtitle">You must confirm your email before continuing. If you didn't receive an email you can <a href="/resend_confirmation/" class="auth-link">resend it</a>.</p>
{% endblock %}
```

- [ ] **Step 11: Replace `templates/registration/activation_email_sent.html`**

```html
{% extends "registration/auth_base.html" %}
{% block card %}
<h1 class="auth-title">Confirmation email sent</h1>
<p class="auth-subtitle">A confirmation email has been sent to {{ email }}. If you didn't get this email we can <a href="/resend_confirmation/" class="auth-link">resend it</a>.</p>
{% endblock %}
```

- [ ] **Step 12: Run the auth tests**

Run: `.venv/bin/python manage.py test core.tests.AuthPagesTests`
Expected: PASS (10 tests, including `test_login_uses_editorial_form_markup`).

- [ ] **Step 13: Commit**

```bash
git add templates/registration/ core/tests.py
git commit -m "Restyle auth card templates with editorial markup"
```

---

## Task 5: Editorial auth.css

**Before starting this task, invoke the `frontend-design` skill.** This is the creative styling of the auth pages. Replace the placeholder `dailyinquirer/static/css/auth.css` with the full stylesheet. **Every selector MUST be scoped under `.auth-page`** so the styles cannot leak.

**Files:**
- Modify: `dailyinquirer/static/css/auth.css` (replace placeholder with full styles)

The tokens (`--ink`, `--accent`, `--danger`, `--serif`, `--body`, etc.) are provided by `tokens.css` on `:root`; use `var(--…)`, do not hardcode tokenized values. The full class vocabulary is listed at the top of this plan.

- [ ] **Step 1: Write `auth.css`**

Implement CSS achieving this visual intent (exact values chosen via frontend-design judgment), all selectors under `.auth-page`:

- **Page & layout:** `.auth-page` — flex column, `min-height: 100vh`, a soft off-white/light background (slightly tinted, not pure white, so the white card reads as raised). `.auth-main` — flex, centered both axes, `flex: 1 0 auto`, generous padding. `.auth-footer` — `flex-shrink: 0`, hairline `var(--rule)` top border, centered, small links (`.auth-footer a` quiet `var(--ink-faint)`, `var(--accent)` on hover, spaced apart).
- **Wordmark:** `.auth-wordmark` — `var(--serif)`, modest size, `var(--ink)`; its `<a>` inherits color and has no underline.
- **Card:** `.auth-card` — `var(--paper)`, 1px `var(--rule)` border, ~10px radius, a soft shadow, generous padding (~32px), `max-width: ~400px`, full width below that.
- **Heading & text:** `.auth-title` — `var(--serif)`, ~1.6rem, `var(--ink)`, tight line-height. `.auth-subtitle` — `var(--body)`, ~0.85rem, `var(--ink-soft)`, comfortable line-height, bottom margin separating it from the form. `.auth-fineprint` — `var(--body)`, ~0.72rem, `var(--ink-faint)`, placed under the submit button.
- **Form fields:** `.auth-field` — bottom margin between fields. `.auth-label` — `var(--body)`, ~0.75rem, medium weight (600), `var(--ink-soft)`, small bottom margin, block. `.auth-input` — block, full width, `var(--body)`, ~0.9rem, padding ~10–12px, 1px `var(--rule)` border, ~6px radius, white background; `:focus` raises border to `var(--accent)` and adds a faint accent ring (e.g. `box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.12)`), no default outline. The rule must also cover `select.auth-input` (the timezone dropdown) so it matches the text inputs.
- **Primary button:** `.auth-btn` — block, full width, pill (`border-radius: 9999px`), `var(--ink)` background, white text, `var(--body)`, ~0.88rem, weight 600, padding ~13px; hover/focus → `var(--accent)` with a subtle lift (`transform: translateY(-1px)`) and shadow. Must render identically for `<button>`, `<input type="submit">`, and `<a>` — so include `display`, `text-align: center`, `text-decoration: none`, `border: none`, `cursor: pointer`, and `box-sizing: border-box`. Add top margin so it sits clear of the last field; when it follows a `.auth-subtitle` directly (the reset-done / complete / invalid-link pages) it should still have sensible spacing.
- **Links:** `.auth-link` — `var(--accent)`, underline, `var(--ink)`-or-darker on hover (or accent darken). `.auth-forgot` — small, displayed block and right-aligned, with margin so it sits between the last field and the button; `var(--accent)`. `.auth-alt` — centered, ~0.82rem, `var(--ink-soft)`, top margin, sits below the form/card content; its `<a>` uses `.auth-link` styling.
- **Errors:** `.auth-error` — block, `var(--danger)`-tinted background (`rgba(var(--danger-rgb), 0.08)`), a `var(--danger)` left border (~3px), padding, ~6px radius, bottom margin. `.auth-error p` — `var(--body)`, ~0.8rem, `var(--danger)` (a readable dark red), no margin (or tight margin between multiple errors).
- **Motion:** transitions ~150ms on the button and input focus; a `@media (prefers-reduced-motion: reduce)` block disables the button transform.
- **Responsive:** correct from 320px up. On very narrow screens the card padding can reduce slightly; nothing should overflow horizontally.

- [ ] **Step 2: Visual review in the browser**

Run: `.venv/bin/python manage.py runserver` and view each page:
`/login/`, `/register/`, `/password_reset/`, `/password_reset/done/`, `/reset/MQ/aaa-bbb/` (invalid-link branch), `/reset/done/`, `/resend_confirmation/`, `/unconfirmed_email/`.
Expected: each looks like a polished editorial auth page consistent with the home page — Special Elite headings, green accent, pill buttons, clean inputs. No horizontal scroll at ~375px. Submit a login with bad credentials to confirm the `.auth-error` styling.

- [ ] **Step 3: Confirm scope isolation and tests**

Run: `.venv/bin/python manage.py test`
Expected: PASS (all tests).
Confirm every selector in `auth.css` is under `.auth-page`. Open `/` (home) and `/terms/` — confirm they are visually unchanged (they don't load `auth.css`).

- [ ] **Step 4: Commit**

```bash
git add dailyinquirer/static/css/auth.css
git commit -m "Style the editorial auth pages"
```

---

## Task 6: Remove dead auth CSS from styles.css

The auth pages no longer load `styles.css`, so its `.auth-*` rules are dead.

**Files:**
- Modify: `dailyinquirer/static/css/styles.css`

- [ ] **Step 1: Delete the dead auth rules**

In `dailyinquirer/static/css/styles.css`, delete the entire block that begins with the comment `/* --- Auth pages --- */` and runs to the end of the file (the `.auth-page`, `.auth-main`, `.auth-wordmark`, `.auth-wordmark a`, `.auth-card`, `.auth-card h1`, `.auth-subtitle`, `.auth-alt`, `.auth-footer`, and `.auth-footer p` rules). Leave every rule above that comment intact — `.footer-link`, `.dotted`, `.btn-primary`, etc. are still used by `core/base.html` pages.

- [ ] **Step 2: Verify nothing else references the removed selectors**

Run: `grep -rn "auth-" dailyinquirer/static/css/styles.css core/templates`
Expected: no matches in `styles.css`; no matches in `core/templates` (the `core/*` pages never used `.auth-*`).

Run: `.venv/bin/python manage.py test`
Expected: PASS (all tests).

- [ ] **Step 3: Commit**

```bash
git add dailyinquirer/static/css/styles.css
git commit -m "Remove dead auth styles from styles.css"
```

---

## Task 7: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `.venv/bin/python manage.py test`
Expected: PASS — `HomePageTests`, `AuthPagesTests`, and `EmailConfirmationTests` all green.

- [ ] **Step 2: Manual walkthrough**

Run: `.venv/bin/python manage.py runserver`. Check:
- All 8 directly-reachable auth pages render in the editorial style: `/login/`, `/register/`, `/password_reset/`, `/password_reset/done/`, `/reset/done/`, `/resend_confirmation/`, `/unconfirmed_email/`, and an invalid `/reset/<bad>/<bad>/` link.
- Login with wrong credentials → the `.auth-error` alert shows in red (not green).
- The wordmark links to `/`; footer Terms/Privacy links work.
- The home page (`/`), `/terms/`, and `/privacy/` are visually unchanged.
- Check `/login/` and `/register/` at ~375px width — no horizontal scroll.

- [ ] **Step 3: Confirm a clean tree**

Run: `git status`
Expected: clean (everything committed).

---

## Self-review notes

- **Spec coverage:** `tokens.css` + `--danger` → Task 1 & token list. `home.css` token block removed → Task 1. `auth.css` `.auth-page`-scoped → Tasks 2 & 5. `auth_base.html` head (drop bootstrap/styles, add tokens/auth) → Task 2. `_form_errors.html` partial → Task 3, wired in Task 4. 9 card templates restyled → Task 4. Dead `.auth-*` removed from `styles.css` → Task 6. Tests (`AuthPagesTests`, GET-able pages + activation via POST + markup assertion) → Tasks 2 & 4. Email templates untouched — not referenced by any task. No view/URL/model changes — confirmed.
- **Placeholder scan:** the Task 2 `auth.css` placeholder is deliberate scaffolding, fully replaced in Task 5 — not a residual placeholder.
- **Name consistency:** class vocabulary (`.auth-title`, `.auth-subtitle`, `.auth-form`, `.auth-field`, `.auth-label`, `.auth-input`, `.auth-btn`, `.auth-link`, `.auth-forgot`, `.auth-alt`, `.auth-fineprint`, `.auth-error`) is used identically across the partial (Task 3), the card templates (Task 4), and the stylesheet spec (Task 5). Token names match `tokens.css` (Task 1).
