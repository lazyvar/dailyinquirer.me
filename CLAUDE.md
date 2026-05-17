# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**dailyinquirer.me** — a Django writing-prompt email service. Subscribers get a writing prompt emailed each morning; email replies are parsed and saved to the site as journal entries viewable on a personal dashboard.

## Commands

```bash
# Setup (Python 3.14)
pip install -r requirements-dev.txt   # dev: includes django-mail-viewer; prod uses requirements.txt only

# Run locally (uses dailyinquirer.settings.local)
python manage.py runserver
./start.sh dev                        # migrate, then runserver on 0.0.0.0:8000

# Tests (CI runs exactly this)
python manage.py test
python manage.py test core.tests.EmailConfirmationTests          # single class
python manage.py test core.tests.EmailConfirmationTests.test_register_sends_activation_email  # single test

# Lambda tests (separate, not part of manage.py test)
cd infra/inbound-email/lambda && python -m pytest

python manage.py migrate
python manage.py send_daily_mail      # see "Daily email" below
```

CI (`.github/workflows/ci.yml`) runs `python manage.py test` on every PR; pushes to `main` additionally deploy to Fly.io via `flyctl deploy`.

## Settings layout

`dailyinquirer/settings/` is split — `base.py` holds shared config, the rest select it via `DJANGO_SETTINGS_MODULE`:

- `local` — `manage.py` default; SQLite, `DEBUG=True`, emails captured in-memory and browsable at `/mailbox/`.
- `dev` — Mailgun email backend.
- `prod` — Fly.io: database from `DATABASE_URL` via `dj-database-url` (deployment uses SQLite on the `/data` Fly volume; Postgres works if `DATABASE_URL` points there), AWS SES email via `django-anymail`, SSL redirect, `www.` → apex redirect middleware. Used by the `Dockerfile`.

`prod` reads secrets from env vars: `SECRET_KEY`, `INBOUND_SHARED_SECRET`, AWS credentials (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, read automatically by boto3).

## Architecture

Two apps:

- **`authentication`** — custom `User` model (`AUTH_USER_MODEL = 'authentication.User'`). Email is the username; no `username` field. Users carry a `timezone` string; `User.local_time()` returns timezone-aware "now" for that user (returns `None` on an invalid tz — callers must handle this).
- **`core`** — the prompt/entry domain. `Prompt` has a `mail_day` datetime and optional `category`/`override_html`. `Entry` links a `User` author to a `Prompt` with their reply `content`. `PromptSend` records one delivery of a `Prompt` to a `User`, with a unique `(user, prompt)` constraint that makes it the dedup ledger for the daily send.

`Prompt`/`Entry` mix in `core.mixins.TimestampedModel` for `created_at`/`updated_at`; `PromptSend` is a plain `models.Model` with its own `sent_at`.

### Daily email send

`core/utils.py:send_prompt_to_user(user, force=False)` is the single entry point: it resolves today's `Prompt` for the user's local date, sends it via `mail_newsletter` (multipart text + `core/daily_email.html`), and records a `PromptSend`. It skips users who already have a `PromptSend` for that prompt unless `force=True`, and returns `None` whenever nothing was sent (no valid tz, no prompt, or already sent).

The `send_daily_mail` management command iterates confirmed, subscribed users and calls `send_prompt_to_user` for anyone whose local hour is ≥ 8. It runs **hourly** so each user is caught when their local clock passes 8am; per-user exceptions are caught and logged so one failure doesn't abort the run. The `PromptSend` dedup means re-running it the same day is a no-op.

In production the cron runs **in-process**: `supercronic` (installed in the `Dockerfile`, pinned) executes the repo-root `crontab` alongside gunicorn, started by `start.sh`. This is why `fly.toml` sets `auto_stop_machines = "off"` — background jobs aren't HTTP traffic, so an autostopped machine would silently skip deliveries.

The User admin (`authentication/admin.py`) adds a custom `send-prompt/<pk>/` URL and "Send today's prompt" button that calls `send_prompt_to_user(user, force=True)`.

### Inbound email (reply-to-prompt)

This is the key cross-system flow:

1. A subscriber replies to a prompt email. AWS SES (receipt rule defined in `infra/inbound-email/template.yaml`) stores the raw MIME to S3 and triggers the Lambda in `infra/inbound-email/lambda/app.py`.
2. The Lambda parses the MIME, strips quoted history/signature (`email-reply-parser`), and `POST`s `{sender, stripped-text}` JSON to `/messages/`, authenticating with the `X-Inbound-Secret` header.
3. `core/views.on_incoming_message` validates that header against `INBOUND_SHARED_SECRET` (constant-time compare), resolves the sender to a `User`, finds today's `Prompt` by the user's local date, and creates an `Entry`.

The `INBOUND_SHARED_SECRET` value must match between the Django app and the Lambda's `SHARED_SECRET` env var. The Lambda is a self-contained codebase with its own `requirements.txt` and tests, deployed separately (AWS SAM `template.yaml`).

### Account activation

Registration sends an activation email using a custom token generator (`authentication/tokens.py`) whose hash includes `confirmed_email`, so a link is single-use once the email is confirmed. Unconfirmed users are logged out and redirected to `/unconfirmed_email/`.

### Dashboard

`core/views._dashboard` renders the logged-in home page: a paginated, filterable list of the user's own entries (text search, date range, category, sort). The `Entry` model has a composite `(author, -pub_date)` index serving this query.

## Templates

Project-level templates live in `templates/` (registration/auth, admin overrides); app templates in `core/templates/core/`. `templates/` is registered via `TEMPLATES['DIRS']`.
