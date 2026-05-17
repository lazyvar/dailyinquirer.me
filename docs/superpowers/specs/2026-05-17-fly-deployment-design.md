# Fly.io Deployment — dailyinquirer.me

**Date:** 2026-05-17
**Status:** Approved design

## Goal

Deploy the Django 5.2 `dailyinquirer.me` app to Fly.io, replacing the current
Heroku deployment. Serve on the custom domain `dailyinquirer.me` (and `www`).
Persist data in SQLite on a Fly volume, seeded from the existing Heroku
Postgres dump.

## Decisions

| Topic | Decision |
|-------|----------|
| Database | SQLite on a 1GB Fly volume mounted at `/data` |
| Domain | Custom domain `dailyinquirer.me` + `www.dailyinquirer.me` |
| Region | `iad` (US East / Virginia) |
| App name | `dailyinquirer` (`dailyinquirer.fly.dev`) |
| Data | Migrate existing Heroku data from a Postgres custom-format dump |
| Static files | Served by whitenoise from the image (built at image-build time) |

## Source data

The dump at `~/Documents/backups/dailyinquirer/dailyinquirerdb` is a
PostgreSQL custom-format dump (`pg_dump -Fc`, PG 13.6, ~48KB). It cannot load
directly into SQLite, so a one-time conversion through an ephemeral Postgres
is required (see "Data migration" below).

## New files

### `Dockerfile`
- Base image `python:3.14-slim` (matches `runtime.txt`).
- Install OS build deps as needed, then `pip install -r requirements.txt`.
- Copy the project.
- Run `python manage.py collectstatic --noinput` at build time so whitenoise
  serves static assets from the image (`STATIC_ROOT = BASE_DIR/dist`). No
  volume needed for static files.
- `CMD` runs `start.sh`.

### `start.sh` (container entrypoint)
- `python manage.py migrate --noinput`
- `exec gunicorn dailyinquirer.wsgi --bind 0.0.0.0:8000`

Migrations run here, **not** as a Fly `[deploy] release_command`, because
release-command machines do not mount the volume where the SQLite file lives.
Single machine, so running migrate on every boot is safe.

### `fly.toml`
- `app = "dailyinquirer"`, `primary_region = "iad"`.
- `[build]` — uses the Dockerfile.
- `[http_service]` — `internal_port = 8000`, `force_https = true`,
  `auto_stop_machines` / `auto_start_machines` left at defaults, `min_machines_running = 1`.
  Default TCP health check (no HTTP check, to avoid interaction with
  `SECURE_SSL_REDIRECT`).
- `[mounts]` — `source = "data"`, `destination = "/data"`.

### `.dockerignore`
Excludes `.venv`, `.git`, `db.sqlite3`, `__pycache__`, `dist`, `*.pyc`.

## Settings changes — `dailyinquirer/settings/prod.py`

Required for running behind Fly's TLS-terminating proxy:

- `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` — without
  this, `SECURE_SSL_REDIRECT = True` produces an infinite redirect loop
  behind the proxy.
- Add `dailyinquirer.fly.dev` (or `.fly.dev`) to `ALLOWED_HOSTS` so the app is
  reachable on the Fly hostname before DNS cutover.
- Add `CSRF_TRUSTED_ORIGINS = ['https://dailyinquirer.me',
  'https://www.dailyinquirer.me', 'https://*.fly.dev']` — Django 5 requires
  this for admin/login POSTs over HTTPS.
- Change `DEBUG = os.environ.get('DEBUG', False)` to
  `DEBUG = os.environ.get('DEBUG') == 'True'` — the current form treats any
  non-empty env string as truthy.

`DATABASES` already updates from `dj_database_url.config()` (reads
`DATABASE_URL`); no further change needed.

## Fly secrets

Set via `fly secrets set`:

- `SECRET_KEY` — a fresh random key (the hardcoded base key is now public).
- `DATABASE_URL` — `sqlite:////data/db.sqlite3` (four slashes = absolute path).
- `MAILGUN_ACCESS_KEY` — the Mailgun API key.

## Data migration (one-time)

Prerequisite: Docker (preferred) or a local Postgres. Verified at execution
time; falls back to Homebrew `postgresql` if Docker is unavailable.

1. Start an ephemeral Postgres in Docker; `createdb`; `pg_restore --no-owner
   --no-acl` the dump into it.
2. Run `manage.py dumpdata --settings=dailyinquirer.settings.prod` with
   `DATABASE_URL` pointed at the local Postgres, excluding `contenttypes`,
   `auth.permission`, `sessions`, and `admin.logentry`, with
   `--natural-primary --natural-foreign` → a JSON fixture.
3. Deploy the app to Fly. The entrypoint creates the empty SQLite DB on the
   volume and runs migrations.
4. Copy the JSON fixture to the running machine and run `manage.py loaddata`
   over `fly ssh console`.
5. Create an admin superuser if needed (`createsuperuser`), unless one came
   through in the data.
6. Tear down the ephemeral Postgres.

## Custom domain

After the app is verified working on `dailyinquirer.fly.dev`:

1. `fly certs add dailyinquirer.me` and `fly certs add www.dailyinquirer.me`.
2. Point DNS at the registrar to the Fly IPs (`fly ips list`): A + AAAA
   records for the apex, CNAME (or A/AAAA) for `www`. Exact records documented
   during execution.
3. Wait for certs to validate; verify HTTPS on the custom domain.

## Out of scope

- Removing Heroku artifacts (`Procfile`, `runtime.txt`) — harmless, left in place.
- Removing now-unused `psycopg[binary]` from `requirements.txt` — optional cleanup, deferred.
- Multi-machine / horizontal scaling — SQLite is single-machine by design.
- Decommissioning the Heroku app — left to the user after Fly is confirmed good.

## Success criteria

- `dailyinquirer.fly.dev` serves the app over HTTPS with no redirect loop.
- Existing data (users, subscriptions, core content) is present.
- Admin login works.
- `dailyinquirer.me` and `www.dailyinquirer.me` resolve to Fly with valid certs.
