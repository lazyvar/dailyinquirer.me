# Unified email template and daily-prompt unsubscribe

**Date:** 2026-05-18
**Branch:** `transactional-emails`

## Goal

Give every email the site sends one consistent, professional HTML template, and
add a proper unsubscribe flow for the daily prompt:

- All transactional emails (account activation, password reset, email-change
  confirm, email-change notice) move from plain text to the shared HTML
  template, with a quiet "account notice" line of fine print.
- The daily prompt gains an in-body **Unsubscribe** link (to a confirmation
  page) and a **Manage notifications** link (to settings), plus a
  `List-Unsubscribe` header so inbox clients show their native unsubscribe
  button.
- A public unsubscribe confirmation page that works without login.

## Current state

- **Daily prompt** — `core/templates/core/daily_email.html`, sent multipart by
  `core/utils.py:mail_newsletter`. Footer links Terms / Privacy / Unsubscribe,
  where "Unsubscribe" currently just points at `/settings/`.
- **Transactional emails** — all plain text:
  - Account activation — `templates/registration/confirm_email.html`, sent by
    `core/views.py:send_activation_email` via `EmailMessage`.
  - Email change confirm + notice — `templates/registration/change_email_*.html`,
    sent by `core/views.py:send_email_change_emails` via `EmailMessage`.
  - Password reset — `templates/registration/password_reset_email.html`, sent
    by Django's built-in `PasswordResetView` (wired through
    `django.contrib.auth.urls`).
- Email sending is duplicated across `core/utils.py` and `core/views.py`.

## Design

### 1. Shared email templates

New directory `templates/email/` holding all email templates:

- `base.html` — the shared chrome: cream canvas, green folder tab, masthead,
  white content box with green spine, footer. Carries the `@font-face`
  declarations and responsive `<style>` block currently in `daily_email.html`.
  Defines blocks:
  - `preheader` — hidden inbox-preview text
  - `tab_label` — folder-tab text (a date for the daily prompt, a short label
    for transactional emails)
  - `content` — the white box's inner content
  - `footer` — footer links / fine print
- `_button.html` — a reusable table-based ("bulletproof") CTA button include,
  parameterised with `url` and `label`.
- `_footer_transactional.html` — `Terms · Privacy`, then the fine-print line
  **"An account notice from The Daily Inquirer."**
- `_footer_daily.html` — `Manage notifications · Unsubscribe` on top, then a
  smaller, quieter `Terms · Privacy` line beneath.
- Concrete HTML templates, each `{% extends "email/base.html" %}`:
  - `daily_prompt.html` (replaces `core/daily_email.html`)
  - `account_activation.html`
  - `password_reset.html`
  - `email_change_confirm.html`
  - `email_change_notice.html`
- A plain-text counterpart `.txt` for each concrete template, so every email is
  sent multipart (HTML + text).

Transactional emails use the same masthead as the daily prompt. Their folder-tab
labels: activation → `YOUR ACCOUNT`, password reset → `PASSWORD RESET`,
email-change confirm/notice → `EMAIL CHANGE`.

The daily prompt's footer shows **Manage notifications** (→ `/settings/`) and
**Unsubscribe** (→ the confirmation page, see below). Transactional footers have
no unsubscribe link.

### 2. Email-sending helper

New module `core/email.py` consolidates sending, replacing the ad-hoc
`EmailMessage`/`EmailMultiAlternatives` calls scattered across `utils.py` and
`views.py`:

```python
def send_templated_email(*, subject, to, template, context,
                         from_email=None, headers=None):
    """Render email/<template>.html + .txt and send as one multipart message."""
```

- `mail_newsletter` (in `core/utils.py`) is updated to call this helper.
- `send_activation_email` and `send_email_change_emails` move out of
  `core/views.py` into `core/email.py` and call this helper.
- Password reset stays on Django's `PasswordResetView` machinery (it owns its
  own send), but is pointed at the new templates — see §5.

### 3. Unsubscribe link and tokens

The unsubscribe link must work without login, so it carries a signed token
instead of relying on a session:

- Token = `django.core.signing.dumps(user.pk, salt="unsubscribe")`. No expiry —
  people unsubscribe from old emails. The signature makes it unguessable and
  tamper-proof.
- A `SITE_URL` setting (in `settings/base.py`, overridable per environment) is
  added so email-building code can produce absolute URLs. The daily template
  stops hard-coding `https://www.dailyinquirer.me`.

### 4. Unsubscribe views and pages

Two new routes in `core/urls.py`:

- `unsubscribe/` → `views.unsubscribe`
  - **GET** `?token=…` — validates the token, renders the confirmation page.
    - Valid token, user still subscribed → "confirm" state.
    - Valid token, user already unsubscribed → "done" state directly.
    - Invalid/tampered token → an error state ("This link is no longer valid").
  - **POST** (confirm-button form, token in a hidden field) — sets
    `is_subscribed = False`, renders the "done" state.
- `unsubscribe/one-click/` → `views.unsubscribe_one_click`
  - **POST** only, `@csrf_exempt`. The RFC 8058 endpoint for the
    `List-Unsubscribe` header. Validates the token, sets
    `is_subscribed = False`, returns HTTP 200. No page — mail clients call this
    directly.

New template `core/templates/core/unsubscribe.html` — a public page using the
site's existing `.ed-card` styling and a plain masthead (no nav, no login).
Three states driven by context: **confirm**, **done**, **error**.

- Confirm state — "Unsubscribe from the daily prompt?", names the email
  address being unsubscribed (decoded from the token), explains the journal and
  account are untouched and account emails still arrive. Buttons: **Unsubscribe
  me** (POST form), **Keep my subscription** (link to home).
- Done state — green check, "You've been unsubscribed", single **OK, thanks**
  button (→ home).
- Error state — "This link is no longer valid", with a link to `/settings/`.

### 5. `List-Unsubscribe` header on the daily prompt

`send_templated_email` accepts `headers`; the daily prompt passes:

- `List-Unsubscribe: <https://SITE_URL/unsubscribe/one-click/?token=…>`
- `List-Unsubscribe-Post: List-Unsubscribe=One-Click`

so Gmail / Apple Mail show their native one-click unsubscribe button, handled by
the `unsubscribe/one-click/` endpoint above.

The `mailto:` fallback is intentionally **omitted**: handling it would require
new SES receipt-rule / inbound-mail infrastructure, and every current major mail
client supports the HTTPS one-click form. Flagged here for review.

### 6. Password reset restyle

Add a `password_reset/` route in `dailyinquirer/urls.py` **before** the
`django.contrib.auth.urls` include, using a `PasswordResetView` subclass that
sets:

- `email_template_name = "email/password_reset.txt"`
- `html_email_template_name = "email/password_reset.html"`
- `subject_template_name` → a subject template

This makes the reset email multipart and on-brand without changing Django's
token/flow logic. The existing `password_reset` form post from the settings page
(`core/templates/core/settings.html`) continues to work unchanged.

### 7. From addresses

Unchanged: the daily prompt keeps `The Daily Inquirer <the@dailyinquirer.me>`;
transactional emails keep the `DEFAULT_FROM_EMAIL`
(`Beep Boop <beep-boop@dailyinquirer.me>`).

## Files

**New**

- `templates/email/base.html`, `_button.html`, `_footer_transactional.html`,
  `_footer_daily.html`
- `templates/email/daily_prompt.html`, `account_activation.html`,
  `password_reset.html`, `email_change_confirm.html`, `email_change_notice.html`
  (+ a `.txt` for each)
- `core/email.py`
- `core/templates/core/unsubscribe.html`

**Changed**

- `core/utils.py` — `mail_newsletter` uses `send_templated_email`, passes the
  `List-Unsubscribe` headers.
- `core/views.py` — `send_activation_email` / `send_email_change_emails` move to
  `core/email.py`; add `unsubscribe` and `unsubscribe_one_click` views.
- `core/urls.py` — two unsubscribe routes.
- `dailyinquirer/urls.py` — `password_reset` override route.
- `dailyinquirer/settings/base.py` (+ per-env) — `SITE_URL`.

**Removed**

- `core/templates/core/daily_email.html` (replaced by
  `templates/email/daily_prompt.html`).
- `templates/registration/confirm_email.html`,
  `change_email_confirm.html`, `change_email_notice.html`,
  `password_reset_email.html` (replaced by the `email/` templates).

## Testing

- `send_templated_email` sends a multipart message with both HTML and text
  parts.
- Transactional emails render the account-notice fine print and **no**
  unsubscribe link.
- The daily prompt renders the Manage-notifications and Unsubscribe links and
  carries the `List-Unsubscribe` + `List-Unsubscribe-Post` headers; the
  unsubscribe URL contains a valid signed token.
- `unsubscribe` GET: valid token → confirm state; already-unsubscribed →
  done state; bad token → error state.
- `unsubscribe` POST with a valid token sets `is_subscribed = False` and renders
  the done state.
- `unsubscribe_one_click` POST with a valid token unsubscribes and returns 200;
  with a bad token returns an error status; GET is rejected.
- Password reset sends a multipart email rendered from the `email/` templates.
- Existing email tests (activation, email-change) still pass against the new
  templates.

## Out of scope

- `mailto:` unsubscribe fallback (needs inbound-mail infrastructure).
- Any resubscribe UI beyond the existing `/settings/` checkbox.
- Changes to the inbound reply-to-prompt flow.
