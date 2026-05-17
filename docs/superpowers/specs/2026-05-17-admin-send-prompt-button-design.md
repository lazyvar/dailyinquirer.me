# Admin "Send today's prompt" button

**Date:** 2026-05-17
**Status:** Approved design

## Goal

Give an admin a one-click way, from the Django admin, to send a user the
daily writing-prompt email for that user's current local-time "today" —
without waiting for the 5am cron. Useful for testing the email pipeline
(including the new inbound reply-to-prompt flow) against a real mailbox.

## Decisions

| Topic | Decision |
|-------|----------|
| Placement | A button on the User change page, in the submit row beside *Save* |
| Trigger style | A link to a dedicated admin URL — not a form submit, so it does not save the user record or run form validation |
| Send logic | Reuse `core.utils.mail_newsletter` — the exact function the 5am cron uses |
| Eligibility | Sends regardless of `confirmed_email` / `is_subscribed` — it is a test trigger |
| Which prompt | The prompt for the user's local-time "today" (whatever `mail_newsletter` already resolves) |

## Components

### 1. `core/utils.py` — `mail_newsletter` refactor

`mail_newsletter(user)` currently returns nothing and calls
`prompt_for_datetime(user.local_time())` unconditionally — if the user has
no valid timezone, `local_time()` returns `None` and `prompt_for_datetime`
raises `AttributeError`.

Change it to:

- Return `None` immediately if `user.local_time()` is `None`.
- Return `None` if there is no prompt for today.
- Otherwise send the email and return the `Prompt` that was sent.

This makes the function safe to call directly and lets the caller report
precise feedback. `send_daily_mail` ignores the return value, so the cron
is unaffected (and is now safe against a timezone-less user).

### 2. `authentication/admin.py` — `UserAdmin`

- Override `get_urls()` to prepend a route
  `send-prompt/<int:pk>/` → `send_prompt_view`, URL name
  `authentication_user_send_prompt`.
- `send_prompt_view(request, pk)`:
  - Resolve the `User` (404 if missing).
  - Call `mail_newsletter(user)` inside a `try`/`except`.
  - Set a message and redirect to that user's change page
    (`admin:authentication_user_change`):
    - send succeeded (prompt returned) → `messages.success`:
      "Sent today's prompt to `<email>`."
    - `mail_newsletter` returned `None` → `messages.warning`:
      "No prompt for today for `<email>` (or the user has no valid
      timezone) — nothing sent."
    - send raised → `messages.error`: "Failed to send: `<exception>`."
  - Wrap the view with `self.admin_site.admin_view` so it is staff-only.

### 3. `templates/admin/authentication/user/change_form.html`

Extends `admin/change_form.html`. Overrides the `submit_buttons_bottom`
block to render `{{ block.super }}` (the normal Save row) followed by an
`<a class="button">` linking to
`{% url 'admin:authentication_user_send_prompt' original.pk %}`.

The template lives under the repo-root `templates/` directory, which is on
the `TEMPLATES['DIRS']` path.

### 4. `authentication/tests.py` (new file)

- Set up a staff/admin `User` and log in with the test client.
- With a `Prompt` for today: GET the send-prompt URL → assert one message
  lands in `django.core.mail.outbox`, and the response redirects to the
  user's change page.
- With no `Prompt` for today: GET the URL → assert `mail.outbox` is empty.

## Error handling

| Situation | Behavior |
|-----------|----------|
| No prompt for today, or user has no valid timezone | `messages.warning`, no email |
| `email.send()` raises (SMTP/SES failure) | `messages.error` with the exception text, caught — no 500 |
| Unknown `pk` | Standard admin 404 |
| Non-staff request | Redirected to admin login by `admin_view` |

## Out of scope

- Bulk sending or a per-row button in the user list.
- Choosing a prompt other than today's.
- Scheduling or previewing the email.
- Changing what the 5am cron does.
