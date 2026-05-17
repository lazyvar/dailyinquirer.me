# Fly.io Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the Django 5.2 `dailyinquirer.me` app to Fly.io, serving on the custom domain, with data migrated from the existing Heroku Postgres dump into SQLite on a Fly volume.

**Architecture:** A Docker image (`python:3.14-slim`) built by Fly. Whitenoise serves static assets baked into the image. SQLite lives on a 1GB Fly volume mounted at `/data`. Migrations run on container start (the volume is unavailable to release-command machines). The app runs as a single machine in region `iad`.

**Tech Stack:** Django 5.2, gunicorn, whitenoise, dj-database-url, SQLite, Fly.io, Docker.

**Spec:** `docs/superpowers/specs/2026-05-17-fly-deployment-design.md`

---

## Notes for the executor

- This is a deployment plan, not a feature with unit tests. Each task ends with a **verification step** — run the command, confirm the expected output before moving on.
- Tasks 1–5 create/modify repo files and get committed. Tasks 6–10 operate on local Docker and remote Fly resources and produce no repo changes.
- `flyctl` v0.4.45 is installed. The Postgres dump is at `~/Documents/backups/dailyinquirer/dailyinquirerdb`.
- The data fixture contains subscriber emails — it stays in `/tmp`, never committed to git.

---

## Task 1: Harden production settings for the Fly proxy

**Files:**
- Modify: `dailyinquirer/settings/prod.py`

- [ ] **Step 1: Replace the contents of `dailyinquirer/settings/prod.py`**

Replace the whole file with:

```python
from .base import *
import dj_database_url

SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)

DEBUG = os.environ.get('DEBUG') == 'True'

ALLOWED_HOSTS = [
    'dailyinquirer.me',
    'www.dailyinquirer.me',
    'dailyinquirer.fly.dev',
]

CSRF_TRUSTED_ORIGINS = [
    'https://dailyinquirer.me',
    'https://www.dailyinquirer.me',
    'https://dailyinquirer.fly.dev',
]

SECURE_SSL_REDIRECT = True

# Fly terminates TLS at its proxy and forwards over plain HTTP with this
# header set. Without it, SECURE_SSL_REDIRECT causes an infinite redirect loop.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# db
db_from_env = dj_database_url.config()

DATABASES['default'].update(db_from_env)

# mailgun email

MAILGUN_ACCESS_KEY = os.environ.get('MAILGUN_ACCESS_KEY', None)

INSTALLED_APPS.append("anymail")

ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_ACCESS_KEY,
    "MAILGUN_SENDER_DOMAIN": 'dailyinquirer.me',
}

EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
```

- [ ] **Step 2: Verify the settings module imports cleanly**

Run:
```bash
.venv/bin/python -c "import django; django.setup()" 2>&1 | head -5
DJANGO_SETTINGS_MODULE=dailyinquirer.settings.prod .venv/bin/python -c "import django; django.setup(); from django.conf import settings; print('proxy:', settings.SECURE_PROXY_SSL_HEADER); print('hosts:', settings.ALLOWED_HOSTS)"
```
Expected: prints `proxy: ('HTTP_X_FORWARDED_PROTO', 'https')` and the three-host list, no traceback.

- [ ] **Step 3: Commit**

```bash
git add dailyinquirer/settings/prod.py
git commit -m "Harden prod settings for the Fly proxy

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Add `.dockerignore`

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Create `.dockerignore`**

```
.venv
.git
.gitignore
.gitattributes
.DS_Store
*.pyc
__pycache__
db.sqlite3
dist
docs
.claude
Procfile
runtime.txt
```

- [ ] **Step 2: Verify the file exists**

Run: `cat .dockerignore`
Expected: prints the contents above.

(No commit yet — committed with Task 5.)

---

## Task 3: Add the `Dockerfile`

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=dailyinquirer.settings.prod

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
```

- [ ] **Step 2: Verify the Dockerfile is syntactically valid**

Run: `cat Dockerfile`
Expected: prints the contents above. (Full build is exercised in Task 7.)

(No commit yet — committed with Task 5.)

---

## Task 4: Add the container entrypoint `start.sh`

**Files:**
- Create: `start.sh`

- [ ] **Step 1: Create `start.sh`**

```sh
#!/bin/sh
set -e

python manage.py migrate --noinput

exec gunicorn dailyinquirer.wsgi --bind 0.0.0.0:8000
```

- [ ] **Step 2: Make it executable and verify**

Run:
```bash
chmod +x start.sh
ls -l start.sh
```
Expected: permissions show `-rwxr-xr-x`.

(No commit yet — committed with Task 5.)

---

## Task 5: Add `fly.toml`

**Files:**
- Create: `fly.toml`

- [ ] **Step 1: Create `fly.toml`**

```toml
app = "dailyinquirer"
primary_region = "iad"

[build]

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 1

[mounts]
  source = "data"
  destination = "/data"

[[vm]]
  size = "shared-cpu-1x"
  memory = "512mb"
```

- [ ] **Step 2: Verify `fly.toml` parses**

Run: `fly config validate --local-only 2>&1 || cat fly.toml`
Expected: validation passes, or (if `validate` needs an app) the file contents print cleanly.

- [ ] **Step 3: Commit the deployment files**

```bash
git add .dockerignore Dockerfile start.sh fly.toml
git commit -m "Add Fly.io deployment config

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Build the data fixture from the Heroku Postgres dump

This converts the Postgres custom-format dump into a Django JSON fixture, by
restoring it into an ephemeral Postgres and serializing through the ORM.

**Files:** none (operates on Docker + `/tmp`)

- [ ] **Step 1: Confirm Docker is available**

Run: `docker --version`
Expected: prints a Docker version. If Docker is NOT installed, stop and use a
local Homebrew Postgres instead (`brew services start postgresql`, then adapt
the `pg_restore`/`DATABASE_URL` host accordingly).

- [ ] **Step 2: Start an ephemeral Postgres**

```bash
docker run -d --name di-pg \
  -e POSTGRES_PASSWORD=pw \
  -e POSTGRES_DB=dailyinquirer \
  -p 5433:5432 \
  postgres:13
```
Expected: prints a container ID.

- [ ] **Step 3: Wait until Postgres is ready**

```bash
until docker exec di-pg pg_isready -U postgres -d dailyinquirer; do sleep 1; done
```
Expected: ends with `accepting connections`.

- [ ] **Step 4: Restore the dump**

```bash
docker exec -i di-pg pg_restore -U postgres -d dailyinquirer --no-owner --no-acl \
  < ~/Documents/backups/dailyinquirer/dailyinquirerdb
```
Expected: completes. Warnings about missing roles (e.g. a Heroku role) are
acceptable; an actual failure to create tables is not.

- [ ] **Step 5: Verify tables and row counts**

```bash
docker exec di-pg psql -U postgres -d dailyinquirer -c "\dt"
docker exec di-pg psql -U postgres -d dailyinquirer -c "SELECT count(*) FROM authentication_user;"
```
Expected: lists Django tables (`authentication_user`, `core_*`, `django_*`),
and a non-error user count.

- [ ] **Step 6: Serialize to a Django fixture**

```bash
DATABASE_URL=postgres://postgres:pw@localhost:5433/dailyinquirer \
  .venv/bin/python manage.py dumpdata \
  --settings=dailyinquirer.settings.prod \
  --natural-primary --natural-foreign \
  -e contenttypes -e auth.permission -e sessions -e admin.logentry \
  --indent 2 -o /tmp/dailyinquirer-data.json
```
Expected: completes with no traceback; `/tmp/dailyinquirer-data.json` is created.

- [ ] **Step 7: Verify the fixture**

```bash
.venv/bin/python -c "import json; d=json.load(open('/tmp/dailyinquirer-data.json')); print(len(d), 'objects'); print(sorted({o['model'] for o in d}))"
```
Expected: prints an object count > 0 and the list of models (should include
`authentication.user` and `core.*`).

Leave the `di-pg` container running until Task 8 verifies the data loaded, in
case the fixture needs to be regenerated.

---

## Task 7: Create the Fly app, volume, secrets, and deploy

**Files:** none (operates on Fly)

- [ ] **Step 1: Confirm authenticated to Fly**

Run: `fly auth whoami`
Expected: prints an email. If not, stop and ask the user to run `fly auth login`.

- [ ] **Step 2: Create the app**

Run: `fly apps create dailyinquirer`
Expected: `New app created: dailyinquirer`. If the name is taken, stop and ask
the user for an alternative, then update `app =` in `fly.toml` and the
`*.fly.dev` host in `prod.py`/`fly.toml` to match.

- [ ] **Step 3: Create the volume**

```bash
fly volumes create data --app dailyinquirer --region iad --size 1 --yes
```
Expected: prints a created volume with region `iad`, size `1GB`.

- [ ] **Step 4: Obtain the Mailgun key**

```bash
heroku config:get MAILGUN_ACCESS_KEY -a daily-inquirer
```
Expected: prints the key. If the Heroku CLI is unavailable or not logged in,
stop and ask the user to provide the Mailgun API key.

- [ ] **Step 5: Set secrets**

Substitute `<MAILGUN_KEY>` with the value from Step 4:
```bash
fly secrets set --app dailyinquirer \
  SECRET_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(64))')" \
  DATABASE_URL="sqlite:////data/db.sqlite3" \
  MAILGUN_ACCESS_KEY="<MAILGUN_KEY>"
```
Expected: `Secrets are staged for the first deployment`.

- [ ] **Step 6: Deploy**

Run: `fly deploy --app dailyinquirer`
Expected: the image builds, a machine is created with the volume attached, and
the deploy reports success. If the build fails on the `psycopg[binary]` wheel
(no Python 3.14 wheel), remove the `psycopg[binary]~=3.2` line from
`requirements.txt` — it is unused at runtime with a SQLite `DATABASE_URL` —
commit that change, and re-run `fly deploy`.

- [ ] **Step 7: Verify the machine is running**

Run: `fly status --app dailyinquirer`
Expected: one machine in state `started`.

---

## Task 8: Load the data into the deployed app

**Files:** none (operates on Fly + the fixture in `/tmp`)

- [ ] **Step 1: Upload the fixture to the volume**

Run `fly ssh sftp shell --app dailyinquirer`, then at the prompt:
```
put /tmp/dailyinquirer-data.json /data/data.json
```
Then exit the shell (Ctrl-D).
Expected: `put` reports the file transferred.

- [ ] **Step 2: Load the fixture**

```bash
fly ssh console --app dailyinquirer -C "python /app/manage.py loaddata /data/data.json"
```
Expected: `Installed N object(s) from 1 fixture(s)` with no error.

- [ ] **Step 3: Verify the data is present**

```bash
fly ssh console --app dailyinquirer -C "python /app/manage.py shell -c \"from authentication.models import User; print('users:', User.objects.count())\""
```
Expected: prints a user count matching Step 5 of Task 6.

- [ ] **Step 4: Ensure an admin login exists**

```bash
fly ssh console --app dailyinquirer -C "python /app/manage.py shell -c \"from authentication.models import User; print('superusers:', User.objects.filter(is_superuser=True).count())\""
```
If the count is 0, create one interactively:
```bash
fly ssh console --app dailyinquirer -C "python /app/manage.py createsuperuser"
```
Expected: at least one superuser exists.

- [ ] **Step 5: Tear down the ephemeral Postgres**

```bash
docker rm -f di-pg
rm /tmp/dailyinquirer-data.json
```
Expected: container removed, fixture deleted.

---

## Task 9: Verify the deployment on the Fly hostname

**Files:** none

- [ ] **Step 1: Check the homepage responds**

```bash
curl -sI https://dailyinquirer.fly.dev/
```
Expected: an HTTP `200` or `302` (a `302` to `/login/` is fine) — **not** a
redirect loop and **not** `400 Bad Request` (which would mean an
`ALLOWED_HOSTS` miss).

- [ ] **Step 2: Confirm no redirect loop and check logs**

```bash
curl -sIL --max-redirs 3 https://dailyinquirer.fly.dev/ | grep -i '^HTTP'
fly logs --app dailyinquirer | tail -30
```
Expected: redirects resolve within a few hops; logs show gunicorn serving with
no `DisallowedHost` or infinite-redirect errors.

- [ ] **Step 3: Verify the admin login page renders**

```bash
curl -s https://dailyinquirer.fly.dev/admin/login/ | grep -o '<title>[^<]*</title>'
```
Expected: prints a Django admin `<title>`. Then have the user log in manually
at `https://dailyinquirer.fly.dev/admin/` with the superuser credentials to
confirm CSRF and sessions work over HTTPS.

---

## Task 10: Attach the custom domain

**Files:** none

- [ ] **Step 1: Add certificates**

```bash
fly certs add dailyinquirer.me --app dailyinquirer
fly certs add www.dailyinquirer.me --app dailyinquirer
```
Expected: each prints the DNS records required for validation.

- [ ] **Step 2: Get the app's IP addresses**

```bash
fly ips list --app dailyinquirer
```
If no dedicated IPv4 is listed, allocate one (apex domains need an A record):
```bash
fly ips allocate-v4 --app dailyinquirer
fly ips allocate-v6 --app dailyinquirer
```
Expected: an IPv4 (`v4`) and IPv6 (`v6`) address are listed.

- [ ] **Step 3: Update DNS at the registrar** (user action)

Present these records for the user to set at their DNS provider:
- `A` record, host `@` → the IPv4 from Step 2
- `AAAA` record, host `@` → the IPv6 from Step 2
- `CNAME` record, host `www` → `dailyinquirer.fly.dev`

- [ ] **Step 4: Verify certificates validate**

```bash
fly certs check dailyinquirer.me --app dailyinquirer
fly certs check www.dailyinquirer.me --app dailyinquirer
```
Expected: both report the certificate as issued (may take a few minutes after
DNS propagates).

- [ ] **Step 5: Verify HTTPS on the custom domain**

```bash
curl -sI https://dailyinquirer.me/
curl -sI https://www.dailyinquirer.me/
```
Expected: HTTP `200`/`302` over a valid certificate — no `400` and no cert error.

---

## Done

The app is live on Fly at `dailyinquirer.me`. The Heroku app can be left
running as a fallback and decommissioned by the user once Fly is confirmed
stable. Removing `Procfile`, `runtime.txt`, and the unused `psycopg[binary]`
dependency is optional follow-up cleanup, out of scope for this plan.
```
