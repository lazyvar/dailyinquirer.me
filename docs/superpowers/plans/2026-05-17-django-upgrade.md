# Django 1.11 → 5.2 Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the dailyinquirer Django project from Django 1.11.29 / Python 3.6 to Django 5.2 LTS running on Python 3.14, so the local dev server runs.

**Architecture:** Direct one-shot upgrade (not stepwise). A fresh in-repo `.venv` on Python 3.14, a slimmed `requirements.txt`, and mechanical fixes to the handful of removed-API call sites (`url()`, `is_authenticated()`, `force_text`, `django.utils.six`, `DjangoWhiteNoise`). Verification is Django's system checks plus a running server — there is no test suite and adding one is out of scope.

**Tech Stack:** Python 3.14, Django 5.2 LTS, whitenoise 6, django-anymail (Mailgun), psycopg3, SQLite (dev), pytz (timezone list only).

**Spec:** `docs/superpowers/specs/2026-05-17-django-upgrade-design.md`

**Working branch:** `upgrade-django-5.2` (already checked out).

**Path note:** The Django project root is `dailyinquirer/` inside the repo. All `manage.py` commands run from `/Users/mack/Developer/dailyinquirer.me/dailyinquirer`. The venv lives at the repo root: `/Users/mack/Developer/dailyinquirer.me/.venv`.

**TDD note:** This project has no test suite (spec: out of scope). "Verify" steps below run `python -m py_compile`, `manage.py check`, and the dev server in place of unit tests. Do not add pytest tests.

---

### Task 1: Virtualenv and dependencies

**Files:**
- Create: `.venv/` (repo root, git-ignored — confirm `.gitignore` covers it)
- Modify: `dailyinquirer/requirements.txt`
- Modify: `dailyinquirer/runtime.txt`

- [ ] **Step 1: Create the virtualenv**

```bash
cd /Users/mack/Developer/dailyinquirer.me
python3 --version   # expect Python 3.14.x
python3 -m venv .venv
.venv/bin/python --version   # expect Python 3.14.x
.venv/bin/pip install --upgrade pip
```

- [ ] **Step 2: Confirm `.venv` is git-ignored**

Run: `cd /Users/mack/Developer/dailyinquirer.me && git check-ignore .venv`
Expected: prints `.venv` (it is ignored). If it prints nothing, append a line `.venv/` to `.gitignore`.

- [ ] **Step 3: Rewrite `requirements.txt`**

Replace the entire contents of `dailyinquirer/requirements.txt` with:

```
Django~=5.2
whitenoise~=6.0
django-anymail[mailgun]~=13.0
psycopg[binary]~=3.2
dj-database-url~=2.3
gunicorn~=23.0
pytz~=2025.2
```

- [ ] **Step 4: Install dependencies**

Run: `cd /Users/mack/Developer/dailyinquirer.me && .venv/bin/pip install -r dailyinquirer/requirements.txt`
Expected: all packages install with no build errors.

If a version specifier fails to resolve (e.g. no `django-anymail` 13.x exists), install the latest of that single package with `.venv/bin/pip install <package>`, read the installed version with `.venv/bin/pip show <package>`, and update that line in `requirements.txt` to `~=<major>.<minor>` of what resolved. Re-run the full install to confirm.

If Django 5.2 will not run on Python 3.14 (verified in Step 5), change the `Django~=5.2` line to `Django~=6.0` and re-install. Note this deviation in the commit message.

- [ ] **Step 5: Verify Django imports on Python 3.14**

Run: `cd /Users/mack/Developer/dailyinquirer.me && .venv/bin/python -c "import django; print(django.get_version())"`
Expected: prints `5.2.x` (or `6.0.x` if the fallback was used). No `ImportError` or `SyntaxError`.

- [ ] **Step 6: Update `runtime.txt`**

Replace the entire contents of `dailyinquirer/runtime.txt` with:

```
python-3.14
```

- [ ] **Step 7: Commit**

```bash
cd /Users/mack/Developer/dailyinquirer.me
git add dailyinquirer/requirements.txt dailyinquirer/runtime.txt .gitignore
git commit -m "Slim requirements.txt and target Python 3.14 / Django 5.2"
```

---

### Task 2: Modernize `base.py` settings

**Files:**
- Modify: `dailyinquirer/dailyinquirer/settings/base.py`

- [ ] **Step 1: Add the whitenoise middleware**

In `MIDDLEWARE`, insert `whitenoise.middleware.WhiteNoiseMiddleware` immediately after `SecurityMiddleware`. The list becomes:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

- [ ] **Step 2: Fix the `TEMPLATES` DIRS path**

Change the `'DIRS'` entry from the relative `'./templates/'` to an absolute path:

```python
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
```

(`BASE_DIR` already points at `dailyinquirer/dailyinquirer/`'s parent — i.e. the `dailyinquirer/` project dir that contains `templates/`.)

- [ ] **Step 3: Add `DEFAULT_AUTO_FIELD`**

Immediately after the `BASE_DIR = ...` line near the top of the file, add:

```python
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
```

(Existing migrations use implicit `AutoField`; this prevents Django 5.2 from generating new migrations.)

- [ ] **Step 4: Replace `STATICFILES_STORAGE` with `STORAGES` and drop `STATICFILES_DIRS`**

Delete these two blocks at the end of the file:

```python
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'
```

Replace them with:

```python
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
```

(`STATICFILES_DIRS` is removed because the `static/` directory does not exist; `STATIC_ROOT` / `STATIC_URL` stay as-is.)

- [ ] **Step 5: Verify the file is syntactically valid**

Run: `cd /Users/mack/Developer/dailyinquirer.me && .venv/bin/python -m py_compile dailyinquirer/dailyinquirer/settings/base.py`
Expected: no output, exit code 0.

- [ ] **Step 6: Commit**

```bash
cd /Users/mack/Developer/dailyinquirer.me
git add dailyinquirer/dailyinquirer/settings/base.py
git commit -m "Modernize base settings for Django 5.2 and whitenoise 6"
```

---

### Task 3: Fix `wsgi.py` and `manage.py`

**Files:**
- Modify: `dailyinquirer/dailyinquirer/wsgi.py`
- Modify: `dailyinquirer/manage.py`

- [ ] **Step 1: Rewrite `wsgi.py`**

Replace the entire contents of `dailyinquirer/dailyinquirer/wsgi.py` with:

```python
"""
WSGI config for dailyinquirer project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyinquirer.settings.prod")

application = get_wsgi_application()
```

(Whitenoise is now the `WhiteNoiseMiddleware` added in Task 2 — the `DjangoWhiteNoise` WSGI wrapper was removed in whitenoise 4.)

- [ ] **Step 2: Update the `manage.py` default settings module**

In `dailyinquirer/manage.py`, change the `os.environ.setdefault` line from:

```python
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyinquirer.settings")
```

to:

```python
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyinquirer.settings.local")
```

(`dailyinquirer.settings` is an empty package `__init__.py`; `local` is the dev settings module.)

- [ ] **Step 3: Verify both files are syntactically valid**

Run: `cd /Users/mack/Developer/dailyinquirer.me && .venv/bin/python -m py_compile dailyinquirer/dailyinquirer/wsgi.py dailyinquirer/manage.py`
Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
cd /Users/mack/Developer/dailyinquirer.me
git add dailyinquirer/dailyinquirer/wsgi.py dailyinquirer/manage.py
git commit -m "Drop DjangoWhiteNoise wrapper; default manage.py to local settings"
```

---

### Task 4: Convert URLconf to `path()`

**Files:**
- Modify: `dailyinquirer/dailyinquirer/urls.py`
- Modify: `dailyinquirer/core/urls.py`

- [ ] **Step 1: Rewrite `dailyinquirer/urls.py`**

Replace the entire contents of `dailyinquirer/dailyinquirer/urls.py` with:

```python
"""dailyinquirer URL Configuration."""
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('', include('core.urls')),
    path('', include('django.contrib.auth.urls')),
]
```

(`auth_views.logout` — a function view — was removed in Django 2.1; `LogoutView` replaces it. `core.urls` is included before the auth urls, same as before.)

- [ ] **Step 2: Rewrite `core/urls.py`**

Replace the entire contents of `dailyinquirer/core/urls.py` with:

```python
from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('messages/', views.on_incoming_message, name='messages'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('settings/', views.settings, name='settings'),
    path('resend_confirmation/', views.resend_confirmation,
         name='resend_confirmation'),
    path('unconfirmed_email/', views.unconfirmed_email,
         name='unconfirmed_email'),
    re_path(
        r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/'
        r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.activate, name='activate'),
]
```

(Prefix-match patterns become exact `path()` routes — approved in the spec. The `activate` route keeps its regex via `re_path()` because the token has a structured format.)

- [ ] **Step 3: Verify both files are syntactically valid**

Run: `cd /Users/mack/Developer/dailyinquirer.me && .venv/bin/python -m py_compile dailyinquirer/dailyinquirer/urls.py dailyinquirer/core/urls.py`
Expected: no output, exit code 0.

- [ ] **Step 4: Commit**

```bash
cd /Users/mack/Developer/dailyinquirer.me
git add dailyinquirer/dailyinquirer/urls.py dailyinquirer/core/urls.py
git commit -m "Convert URLconf from url() to path()/re_path()"
```

---

### Task 5: Fix removed APIs in views and tokens

**Files:**
- Modify: `dailyinquirer/core/views.py`
- Modify: `dailyinquirer/authentication/tokens.py`

- [ ] **Step 1: Fix the `force_text` import in `core/views.py`**

Change the import line from:

```python
from django.utils.encoding import force_bytes, force_text
```

to:

```python
from django.utils.encoding import force_bytes, force_str
```

- [ ] **Step 2: Fix the `force_text` call site in `core/views.py`**

In the `activate()` view, change:

```python
        uid = force_text(urlsafe_base64_decode(uidb64))
```

to:

```python
        uid = force_str(urlsafe_base64_decode(uidb64))
```

- [ ] **Step 3: Fix `is_authenticated()` calls in `core/views.py`**

There are two call sites. In `index()`, change:

```python
    if request.user.is_authenticated():
```

to:

```python
    if request.user.is_authenticated:
```

In `register()`, change:

```python
    if request.user.is_authenticated():
```

to:

```python
    if request.user.is_authenticated:
```

(`is_authenticated` is a property in modern Django, not a callable.)

- [ ] **Step 4: Rewrite `authentication/tokens.py`**

Replace the entire contents of `dailyinquirer/authentication/tokens.py` with:

```python
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.confirmed_email}"


account_activation_token = AccountActivationTokenGenerator()
```

(`django.utils.six` was removed in Django 3.0; `six.text_type` is just `str`, and an f-string reproduces the original concatenation.)

- [ ] **Step 5: Verify both files are syntactically valid**

Run: `cd /Users/mack/Developer/dailyinquirer.me && .venv/bin/python -m py_compile dailyinquirer/core/views.py dailyinquirer/authentication/tokens.py`
Expected: no output, exit code 0.

- [ ] **Step 6: Commit**

```bash
cd /Users/mack/Developer/dailyinquirer.me
git add dailyinquirer/core/views.py dailyinquirer/authentication/tokens.py
git commit -m "Replace removed APIs: force_text, is_authenticated(), six"
```

---

### Task 6: Verify the `dev.py` / `prod.py` anymail settings

**Files:**
- Modify (if needed): `dailyinquirer/dailyinquirer/settings/dev.py`
- Modify (if needed): `dailyinquirer/dailyinquirer/settings/prod.py`

- [ ] **Step 1: Confirm the anymail config shape against current django-anymail**

Read `dailyinquirer/dailyinquirer/settings/dev.py` and `prod.py`. Both contain:

```python
INSTALLED_APPS.append("anymail")

ANYMAIL = {
    "MAILGUN_API_KEY": MAILGUN_ACCESS_KEY,
    "MAILGUN_SENDER_DOMAIN": 'dailyinquirer.me',
}

EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
```

Current django-anymail still uses the app name `anymail`, the `ANYMAIL` setting dict with `MAILGUN_API_KEY` / `MAILGUN_SENDER_DOMAIN` keys, and the backend path `anymail.backends.mailgun.EmailBackend`. This shape is unchanged — leave both files as-is unless Step 2 of Task 7 reports an anymail-related error.

- [ ] **Step 2: Verify both files are syntactically valid**

Run: `cd /Users/mack/Developer/dailyinquirer.me && .venv/bin/python -m py_compile dailyinquirer/dailyinquirer/settings/dev.py dailyinquirer/dailyinquirer/settings/prod.py`
Expected: no output, exit code 0.

- [ ] **Step 3: No commit unless changed**

If neither file was modified, skip the commit. If Task 7 surfaces an anymail error and a file is edited, commit then with message `Fix anymail settings for current django-anymail`.

---

### Task 7: Full verification

**Files:** none modified (verification only, unless a check surfaces a fix).

- [ ] **Step 1: Run Django system checks (default/local settings)**

Run: `cd /Users/mack/Developer/dailyinquirer.me/dailyinquirer && ../.venv/bin/python manage.py check`
Expected: `System check identified no issues (0 silenced).`

If errors appear, fix the reported file, re-run, and commit the fix with a descriptive message before continuing.

- [ ] **Step 2: Run system checks for prod settings**

Run: `cd /Users/mack/Developer/dailyinquirer.me/dailyinquirer && DATABASE_URL=sqlite:///prod-check.sqlite3 ../.venv/bin/python manage.py check --settings=dailyinquirer.settings.prod`
Expected: `System check identified no issues` (deployment warnings about SSL/SECRET_KEY are acceptable — they are `WARNING`s, not `ERROR`s). If an `ERROR` appears, fix it (this is where a Task 6 anymail fix would land), re-run, and commit.

- [ ] **Step 3: Confirm no new migrations are needed**

Run: `cd /Users/mack/Developer/dailyinquirer.me/dailyinquirer && ../.venv/bin/python manage.py makemigrations --check --dry-run`
Expected: `No changes detected` and exit code 0. If changes are detected, investigate — `DEFAULT_AUTO_FIELD` from Task 2 should prevent this; do not blindly generate migrations.

- [ ] **Step 4: Apply migrations against SQLite**

Run: `cd /Users/mack/Developer/dailyinquirer.me/dailyinquirer && ../.venv/bin/python manage.py migrate`
Expected: all migrations for `core`, `authentication`, `admin`, `auth`, `contenttypes`, `sessions` apply with `OK`. Creates `dailyinquirer/db.sqlite3`.

- [ ] **Step 5: Start the dev server and check two routes**

Run:

```bash
cd /Users/mack/Developer/dailyinquirer.me/dailyinquirer
../.venv/bin/python manage.py runserver 8000 &
SERVER_PID=$!
sleep 4
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/login/
kill $SERVER_PID
```

Expected: both `curl` calls print `200`. If either prints `500`, read the server output for the traceback, fix the offending file, commit the fix, and re-run this step.

- [ ] **Step 6: Confirm `db.sqlite3` stays untracked**

Run: `cd /Users/mack/Developer/dailyinquirer.me && git status --short`
Expected: `db.sqlite3` does NOT appear (it is in `.gitignore`). The `prod-check.sqlite3` from Step 2 should also not appear — if it does, delete it: `rm dailyinquirer/prod-check.sqlite3`. If either DB file appears as untracked, add it to `.gitignore` and commit `.gitignore`.

- [ ] **Step 7: Final commit (only if Steps 1–6 produced fixes not yet committed)**

If all checks passed with no code changes, there is nothing to commit. Otherwise:

```bash
cd /Users/mack/Developer/dailyinquirer.me
git add -A
git commit -m "Fix issues surfaced by Django 5.2 system checks"
```

---

## Self-Review

**Spec coverage:**
- Dependencies & environment → Task 1 ✓
- `runtime.txt` → Task 1 Step 6 ✓
- `dailyinquirer/urls.py` (`url()`, `auth_views.logout`) → Task 4 ✓
- `core/urls.py` (`url()`, prefix→exact) → Task 4 ✓
- `core/views.py` (`is_authenticated`, `force_text`) → Task 5 ✓
- `authentication/tokens.py` (`six`) → Task 5 ✓
- `wsgi.py` (`DjangoWhiteNoise`) → Task 3 ✓
- `base.py` (whitenoise middleware, `STORAGES`, `DEFAULT_AUTO_FIELD`, `TEMPLATES` DIRS, `STATICFILES_DIRS` removal) → Task 2 ✓
- `manage.py` default settings module → Task 3 ✓
- `dev.py` / `prod.py` anymail → Task 6 ✓
- Verification (`check`, `makemigrations --check`, `migrate`, `runserver`, 200s) → Task 7 ✓

All spec items are covered.

**Placeholder scan:** Version pins in Task 1 use `~=` ranges; Step 4 gives a concrete, executable fallback if a pin fails to resolve — not a placeholder. No "TBD"/"TODO" remain.

**Consistency:** `.venv` path (`/Users/mack/Developer/dailyinquirer.me/.venv`) and the `manage.py` working directory (`dailyinquirer/`) are used consistently. `force_str`, `is_authenticated`, `LogoutView`, `path`/`re_path`, and `STORAGES` names match across tasks.
