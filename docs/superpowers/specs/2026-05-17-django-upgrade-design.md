# Django Upgrade: 1.11 → 5.2 LTS

**Date:** 2026-05-17
**Branch:** `upgrade-django-5.2`

## Problem

The project pins Django 1.11.29 and Python 3.6.2 (`runtime.txt`). The only
Python available is 3.14.5, and Django 1.11 cannot run on it — it depends on
stdlib modules and APIs removed years ago. There is no virtualenv, and the
local dev server cannot start.

## Goal

Fully modernize the project so it runs on Python 3.14 with the current Django
LTS. There is no live production deployment, so production config is updated
for correctness but only the local dev server is verified by running it.

## Approach

Direct jump from Django 1.11 straight to **Django 5.2 LTS** (supported into
2028), not a stepwise 2.2 → 3.2 → 4.2 upgrade. Stepwise upgrades pay off only
with a test suite to catch per-step regressions and a running deployment that
must not break — neither applies here. The codebase is ~530 lines across two
apps with no real tests; the breaking changes are few and mechanical.

Python 3.14 compatibility with Django 5.2 is confirmed at install time. If
5.2 will not run on 3.14, fall back to Django 6.0.

## Dependencies & Environment

Create `.venv` (Python 3.14) inside the repo. Rewrite `requirements.txt` to
runtime dependencies only:

- `Django` → 5.2 LTS
- `whitenoise` → current
- `django-anymail[mailgun]` → current
- `psycopg[binary]` → psycopg3, replacing the unbuildable `psycopg2` 2.7.3.1
- `dj-database-url` → current
- `pytz` → kept, used only to supply the curated `common_timezones` list for
  the settings/register timezone dropdowns
- `gunicorn` → current (prod WSGI server)

Dropped (unused or dev-tooling, not runtime): `xlwt`, `django-excel-response2`,
`django-admin`, `flake8`, `pycodestyle`, `pyflakes`, `mccabe`, `pew`,
`pipenv`, `screen`, `virtualenv`, `virtualenv-clone`, `six`, `certifi`,
`chardet`, `idna`, `urllib3`, `requests`.

`runtime.txt` updated to `python-3.14`.

## Code Changes

| File | Change |
|---|---|
| `dailyinquirer/urls.py` | `url()` → `path()`/`re_path()`; `auth_views.logout` → `LogoutView.as_view(next_page='/')` |
| `core/urls.py` | `url()` → `path()`; prefix-match patterns (`register/`, `messages/`, etc.) become exact `path()` routes; the `activate/<uidb64>/<token>/` regex route stays a `re_path()` |
| `core/views.py` | `request.user.is_authenticated()` → `is_authenticated` (property, no parens) in `index()` and `register()`; `force_text` → `force_str` |
| `authentication/tokens.py` | drop `from django.utils import six`; use plain `str()` |
| `dailyinquirer/wsgi.py` | drop `DjangoWhiteNoise` import/wrapping; whitenoise becomes middleware |
| `dailyinquirer/settings/base.py` | add `whitenoise.middleware.WhiteNoiseMiddleware` to `MIDDLEWARE`; replace `STATICFILES_STORAGE` with a `STORAGES` dict using `whitenoise.storage.CompressedManifestStaticFilesStorage`; add `DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'` (matches existing migrations, avoids generating new ones); make `TEMPLATES['DIRS']` an absolute path; remove the broken `STATICFILES_DIRS` entry (the `static/` dir does not exist) |

URL tightening: `core/urls.py` currently uses prefix matches (no trailing `$`),
so `/register/anything` resolves. These are converted to exact `path()` routes
— the conventional modern form. Approved by the user.

## Settings Files

- `base.py` — changes above; custom `AUTH_USER_MODEL`, `INSTALLED_APPS`,
  password validators unchanged.
- `local.py` — unchanged (DEBUG on, console email backend).
- `dev.py` / `prod.py` — modernize the anymail block against current
  `django-anymail`; `INSTALLED_APPS.append("anymail")` and the `ANYMAIL` dict
  shape stay. `prod.py` keeps `dj_database_url.config()` feeding
  `DATABASES['default']`.
- `manage.py` — change the default `DJANGO_SETTINGS_MODULE` from
  `dailyinquirer.settings` (empty package) to `dailyinquirer.settings.local`,
  so `runserver` works with no env var.
- `wsgi.py` — keeps `dailyinquirer.settings.prod` as its default.

## Verification

- `pip install -r requirements.txt` succeeds on Python 3.14.
- `python manage.py check` reports no errors.
- `python manage.py makemigrations --check --dry-run` confirms no new
  migrations are needed.
- `python manage.py migrate` applies all existing migrations cleanly against
  SQLite.
- `python manage.py runserver` starts; `/` and `/login/` return HTTP 200.

No formal test suite exists (`tests.py` files are empty stubs). Verification is
the running server plus Django's system checks. Adding tests is out of scope
for this upgrade.

## Out of Scope

- Adding a test suite.
- Deploying or verifying production.
- Migrating timezone handling from `pytz` to stdlib `zoneinfo`.
- Any feature changes or refactoring beyond what the upgrade requires.
