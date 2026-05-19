# Prompt Viewer — Design Spec

**Date:** 2026-05-19
**Branch:** `prompt-viewer`

## Overview

An inbox-style **prompt viewer** for logged-in users: a page listing every past
writing prompt with whether the user has answered it, plus a **prompt detail
page** that shows all of the user's entries for a prompt and lets them write new
entries directly from the web.

Today, entries are created only by replying to the daily email. The detail page
adds the first in-app way to write an entry.

## Goals

- Browse every past prompt the service has sent — never future ones.
- See at a glance which prompts the user has an entry for.
- Open any prompt to read existing entries and add new ones.

## Non-goals

- Public access — the viewer is logged-in only.
- Showing future prompts.
- Editing or deleting prompts.
- Streaks, stats, or "X of Y answered" counters.
- A site-wide navigation bar — entry is a single dashboard link.
- Pagination, search, or filters within a month.

## Pages

### 1. Prompt inbox — `/prompts/`

- View: `core.views.prompts`, `@login_required`, with the same
  unconfirmed-email logout/redirect guard used by `dashboard`.
- Shows **one month at a time**. The displayed month comes from a
  `?month=YYYY-MM` query parameter; missing or invalid → the user's current
  local month.
- Lists every `Prompt` whose `mail_day` falls in the displayed month **and** is
  on or before today (the user's local date). Ordered newest first by
  `mail_day`.
- **Row layout:** date column on the left (e.g. "May 17") · prompt question ·
  status pill on the right. No category shown in the row.
- The status pill reads **"Answered"** when the user has at least one active
  (non-archived) entry for that prompt, otherwise **"No entry"**.
- The whole row links to that prompt's detail page (`/prompts/<id>/`).
- **Month navigation:** Gmail-style `‹` / `›` arrows in the top-right of the
  page.
  - `›` (next month) is disabled when the displayed month is the user's current
    local month — the future is never shown.
  - `‹` (previous month) is disabled when no prompt exists in any earlier month.
- An empty month (rare for a daily service) shows a plain "No prompts this
  month" message.
- Template: `core/templates/core/prompts.html`, extends `core/base.html` and
  renders the shared header with `{% sitenav 'prompts' %}` — the same
  breadcrumb/masthead tag every other logged-in page uses. The footer comes
  from `base.html` like every other page.
- Discoverable via a **"Browse all prompts"** link added to
  `index_logged_in.html`, next to the existing "View archived" link.

### 2. Prompt detail — `/prompts/<int:pk>/`

- View: `core.views.prompt_detail`, `@login_required`, with the same
  unconfirmed-email guard.
- A prompt whose `mail_day` is in the future returns **404** — future prompts
  are never viewable.
- **GET** renders:
  - The prompt: question, date, and category (if set).
  - A list of the user's **active (non-archived)** entries for this prompt,
    rendered with the existing `core/_entry_card.html` partial so it matches the
    dashboard and archive pages.
  - An **"Add entry"** button that reveals an inline textarea form.
- **POST** (`action=add`): validates the entry form; on success creates an
  `Entry` with `author=request.user`, `prompt=<this prompt>`,
  `content=<submitted text>`, `pub_date=timezone.now()`; then redirects back to
  the detail page. On failure, re-renders with the form errors.
- Template: `core/templates/core/prompt_detail.html`, extending `base.html`,
  rendering the shared header with `{% sitenav 'prompt' prompt=prompt %}` and
  the standard footer.

## Data model

No model changes. `Entry` has no unique `(user, prompt)` constraint, so multiple
entries per prompt are already supported. `Prompt.mail_day` already dates each
prompt and is the field used elsewhere (`on_incoming_message`,
`send_prompt_to_user`) to resolve a prompt to a calendar day.

## Implementation notes

- **Current date / month:** derive from `User.local_time()`. Per the existing
  caller contract it returns `None` when the user's timezone is invalid; in that
  case fall back to `django.utils.timezone.localdate()`.
- **"Answered" lookup:** for the prompts in the displayed month, determine the
  pill with an `Exists` subquery against `Entry` filtered by `author=user`,
  `prompt=<prompt>`, `archived_at__isnull=True`. A month holds ~30 prompts, so
  this is cheap.
- **Month parameter:** parse `YYYY-MM`; on any parse failure fall back to the
  current local month rather than erroring.
- **Prev/next months:** computed in the view and passed to the template as
  ready-made `?month=YYYY-MM` query strings (or a disabled flag).
- **URLs:** add to `core/urls.py` —
  `path('prompts/', views.prompts, name='prompts')` and
  `path('prompts/<int:pk>/', views.prompt_detail, name='prompt_detail')`.
- **Add-entry form:** reuse the existing `EntryEditForm` (`content` field) from
  `core/forms.py`.
- Adding an entry from the web does **not** create a `PromptSend` — that record
  is the email-send dedup ledger and is unrelated to entry authorship.

## Edge cases

- A future-dated prompt within the current month is excluded from the list; its
  detail URL returns 404.
- Prompts are not user-scoped — every logged-in user sees the same prompt list.
  Only the *entries* on the detail page are scoped to the requesting user.
- A brand-new user with no prompts yet sees the empty-month message.
- An invalid or malformed `?month=` value falls back to the current month.
- Archived entries are excluded from the detail page's entry list (consistent
  with the dashboard); they remain reachable from the existing archive page.

## Testing

Following the patterns in `core/tests.py`:

- `/prompts/` requires login and redirects an unconfirmed user.
- The list shows past prompts in the displayed month and excludes
  future-dated prompts.
- The `›` arrow is disabled on the current month; a `‹` link is present when
  older prompts exist.
- The status pill reflects whether the requesting user has an active entry;
  another user's entry for the same prompt does not flip it.
- `/prompts/<id>/` lists only the requesting user's active entries.
- `/prompts/<id>/` returns 404 for a future-dated prompt.
- A valid POST to the detail page creates an `Entry` linked to that prompt and
  user.
- `/prompts/<id>/` requires login.

## Future / out of scope

- Pagination, search, or category filters within the viewer.
- Surfacing or restoring archived entries from the detail page.
- Public, unauthenticated browsing of prompts.
