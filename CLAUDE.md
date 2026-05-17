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
- `prod` — Fly.io: Postgres via `dj-database-url`, AWS SES email, SSL redirect, `www.` → apex redirect middleware. Used by the `Dockerfile`.

`prod` reads secrets from env vars: `SECRET_KEY`, `INBOUND_SHARED_SECRET`, AWS credentials (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, read automatically by boto3).

## Architecture

Two apps:

- **`authentication`** — custom `User` model (`AUTH_USER_MODEL = 'authentication.User'`). Email is the username; no `username` field. Users carry a `timezone` string; `User.local_time()` returns timezone-aware "now" for that user (returns `None` on an invalid tz — callers must handle this).
- **`core`** — the prompt/entry domain. `Prompt` has a `mail_day` datetime and optional `category`/`override_html`. `Entry` links a `User` author to a `Prompt` with their reply `content`.

Both model files mix in `core.mixins.TimestampedModel` for `created_at`/`updated_at`.

### Daily email send

`core/utils.py:mail_newsletter(user)` looks up the `Prompt` whose `mail_day` matches the user's local calendar date and emails it (multipart text + `core/daily_email.html`). The `send_daily_mail` management command iterates confirmed, subscribed users and sends to anyone whose local time is hour 5 — it is intended to be invoked hourly by an external scheduler, not a worker process.

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
