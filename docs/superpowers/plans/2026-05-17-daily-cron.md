# Daily Prompt Cron Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver each day's writing prompt to every confirmed, subscribed user at 8am in their own timezone, exactly once.

**Architecture:** An hourly in-process cron (`supercronic`, running inside the always-on Fly web container alongside gunicorn) invokes the `send_daily_mail` management command. The command sends to any eligible user whose local time is at or past 8am and who has not already received today's prompt. A new `PromptSend` table records deliveries and guarantees exactly-once.

**Tech Stack:** Django 5.2, Python 3.14, SQLite (on a Fly volume), `supercronic`, AWS SES via `django-anymail`. Tests run with Django's test runner (`python manage.py test`).

---

## File Structure

- `core/models.py` — add the `PromptSend` model.
- `core/migrations/0005_promptsend.py` — generated migration for `PromptSend`.
- `core/utils.py` — add `send_prompt_to_user(user, force=False)`; keep `mail_newsletter` and `prompt_for_datetime` as-is.
- `core/management/commands/send_daily_mail.py` — rewrite as a thin loop using `send_prompt_to_user`.
- `authentication/admin.py` — `send_prompt_view` calls `send_prompt_to_user(user, force=True)`.
- `core/tests.py` — add test classes for the model, helper, command, and admin button.
- `crontab` (repo root) — hourly schedule for `supercronic`.
- `Dockerfile` — install the `supercronic` binary.
- `start.sh` — launch `supercronic` in the background before `exec gunicorn`.

---

## Task 1: `PromptSend` model

**Files:**
- Modify: `core/models.py`
- Create: `core/migrations/0005_promptsend.py` (generated)
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing test**

Add to the end of `core/tests.py`. Add `from django.db import IntegrityError, transaction` to the imports at the top of the file, and add `PromptSend` to the existing `from core.models import ...` line (making it `from core.models import Entry, Prompt, PromptSend`).

```python
class PromptSendModelTests(TestCase):
    def test_unique_per_user_and_prompt(self):
        user = User.objects.create_user(
            email='ps@example.com', password='mostdope1')
        prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())

        PromptSend.objects.create(user=user, prompt=prompt)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PromptSend.objects.create(user=user, prompt=prompt)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test core.tests.PromptSendModelTests -v 2`
Expected: FAIL — `ImportError: cannot import name 'PromptSend'`.

- [ ] **Step 3: Add the model**

In `core/models.py`, change the top imports to include `timezone`:

```python
from django.db import models
from django.utils import timezone
from django.utils.formats import date_format

from authentication.models import User
```

Append this model to the end of `core/models.py`:

```python
class PromptSend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'prompt')

    def __str__(self):
        return f"{self.user.email} - {self.prompt.question[:12]}"
```

- [ ] **Step 4: Generate the migration**

Run: `python manage.py makemigrations core`
Expected: creates `core/migrations/0005_promptsend.py`.

- [ ] **Step 5: Run test to verify it passes**

Run: `python manage.py test core.tests.PromptSendModelTests -v 2`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/models.py core/migrations/0005_promptsend.py core/tests.py
git commit -m "Add PromptSend model to track daily prompt deliveries"
```

---

## Task 2: `send_prompt_to_user` helper

**Files:**
- Modify: `core/utils.py`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `core/tests.py`. Add `send_prompt_to_user` to the existing `from core.utils import ...` line (making it `from core.utils import mail_newsletter, send_prompt_to_user`).

```python
class SendPromptToUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='p@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.save()
        self.prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())

    def test_sends_and_records_when_not_sent_before(self):
        result = send_prompt_to_user(self.user)

        self.assertEqual(result, self.prompt)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            PromptSend.objects.filter(
                user=self.user, prompt=self.prompt).count(), 1)

    def test_skips_when_already_sent(self):
        PromptSend.objects.create(user=self.user, prompt=self.prompt)

        result = send_prompt_to_user(self.user)

        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(
            PromptSend.objects.filter(user=self.user).count(), 1)

    def test_force_resends_even_when_already_sent(self):
        PromptSend.objects.create(user=self.user, prompt=self.prompt)

        result = send_prompt_to_user(self.user, force=True)

        self.assertEqual(result, self.prompt)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            PromptSend.objects.filter(user=self.user).count(), 1)

    def test_returns_none_when_no_prompt_for_today(self):
        self.prompt.delete()

        result = send_prompt_to_user(self.user)

        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PromptSend.objects.count(), 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test core.tests.SendPromptToUserTests -v 2`
Expected: FAIL — `ImportError: cannot import name 'send_prompt_to_user'`.

- [ ] **Step 3: Implement the helper**

In `core/utils.py`, change the top imports to:

```python
from core.models import Prompt, PromptSend
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
```

Append this function to the end of `core/utils.py`:

```python
def send_prompt_to_user(user, force=False):
    """Send today's prompt to one user, recording the delivery.

    Skips the user if they have already received today's prompt, unless
    ``force`` is True. Returns the Prompt that was sent, or None when there
    is nothing to send (no valid timezone, no prompt for today, or already
    sent and not forced).
    """
    local_time = user.local_time()
    if local_time is None:
        return None

    todays_prompt = prompt_for_datetime(local_time)
    if todays_prompt is None:
        return None

    already_sent = PromptSend.objects.filter(
        user=user, prompt=todays_prompt).exists()
    if already_sent and not force:
        return None

    sent_prompt = mail_newsletter(user)
    if sent_prompt is None:
        return None

    PromptSend.objects.update_or_create(
        user=user, prompt=sent_prompt,
        defaults={'sent_at': timezone.now()})
    return sent_prompt
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test core.tests.SendPromptToUserTests -v 2`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add core/utils.py core/tests.py
git commit -m "Add send_prompt_to_user helper with delivery dedup"
```

---

## Task 3: Rewrite the `send_daily_mail` command

**Files:**
- Modify: `core/management/commands/send_daily_mail.py`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `core/tests.py`. Add these imports to the top of the file:

```python
from unittest.mock import patch
from django.core.management import call_command
```

Then add:

```python
class SendDailyMailCommandTests(TestCase):
    def _make_user(self, email, timezone_name='UTC'):
        user = User.objects.create_user(email=email, password='mostdope1')
        user.timezone = timezone_name
        user.confirmed_email = True
        user.is_subscribed = True
        user.save()
        return user

    @patch.object(User, 'local_time')
    def test_skips_users_before_8am(self, mock_local_time):
        self._make_user('early@example.com')
        Prompt.objects.create(question='Q', mail_day=timezone.now())
        mock_local_time.return_value = timezone.now().replace(hour=6)

        call_command('send_daily_mail')

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PromptSend.objects.count(), 0)

    @patch.object(User, 'local_time')
    def test_sends_at_or_after_8am(self, mock_local_time):
        user = self._make_user('due@example.com')
        Prompt.objects.create(question='Q', mail_day=timezone.now())
        mock_local_time.return_value = timezone.now().replace(hour=8)

        call_command('send_daily_mail')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(PromptSend.objects.filter(user=user).count(), 1)

    @patch.object(User, 'local_time')
    def test_skips_unconfirmed_and_unsubscribed(self, mock_local_time):
        mock_local_time.return_value = timezone.now().replace(hour=9)
        Prompt.objects.create(question='Q', mail_day=timezone.now())

        unconfirmed = User.objects.create_user(
            email='unconfirmed@example.com', password='mostdope1')
        unconfirmed.timezone = 'UTC'
        unconfirmed.is_subscribed = True
        unconfirmed.save()

        unsubscribed = User.objects.create_user(
            email='unsubscribed@example.com', password='mostdope1')
        unsubscribed.timezone = 'UTC'
        unsubscribed.confirmed_email = True
        unsubscribed.is_subscribed = False
        unsubscribed.save()

        call_command('send_daily_mail')

        self.assertEqual(len(mail.outbox), 0)

    @patch.object(User, 'local_time')
    def test_does_not_resend_when_already_sent(self, mock_local_time):
        user = self._make_user('once@example.com')
        Prompt.objects.create(question='Q', mail_day=timezone.now())
        mock_local_time.return_value = timezone.now().replace(hour=8)

        call_command('send_daily_mail')
        call_command('send_daily_mail')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(PromptSend.objects.filter(user=user).count(), 1)

    @patch.object(User, 'local_time')
    @patch('core.management.commands.send_daily_mail.send_prompt_to_user')
    def test_one_user_failure_does_not_abort_the_run(
            self, mock_send, mock_local_time):
        mock_local_time.return_value = timezone.now().replace(hour=9)
        self._make_user('a@example.com')
        self._make_user('b@example.com')
        mock_send.side_effect = [Exception('boom'), None]

        call_command('send_daily_mail')

        self.assertEqual(mock_send.call_count, 2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test core.tests.SendDailyMailCommandTests -v 2`
Expected: FAIL — the current command checks `hour == 5`, so `test_sends_at_or_after_8am` and others fail (no mail sent / `PromptSend` table not used).

- [ ] **Step 3: Rewrite the command**

Replace the entire contents of `core/management/commands/send_daily_mail.py` with:

```python
from django.core.management.base import BaseCommand

from authentication.models import User
from core.utils import send_prompt_to_user


class Command(BaseCommand):
    help = ("Send today's prompt to every confirmed, subscribed user "
            "whose local time is at or past 8am and who has not yet "
            "received it. Intended to run hourly.")

    def handle(self, *args, **options):
        for user in User.objects.filter(confirmed_email=True,
                                        is_subscribed=True):
            local_time = user.local_time()
            if local_time is None or local_time.hour < 8:
                continue
            try:
                send_prompt_to_user(user)
            except Exception as exc:
                self.stderr.write(
                    f"Failed to send prompt to {user.email}: {exc}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test core.tests.SendDailyMailCommandTests -v 2`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add core/management/commands/send_daily_mail.py core/tests.py
git commit -m "Rewrite send_daily_mail: hourly, 8am, dedup-guarded, fault-isolated"
```

---

## Task 4: Admin "Send today's prompt" button uses the dedup helper

**Files:**
- Modify: `authentication/admin.py`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `core/tests.py`:

```python
class AdminSendPromptButtonTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@example.com', password='mostdope1')
        self.target = User.objects.create_user(
            email='target@example.com', password='mostdope1')
        self.target.timezone = 'UTC'
        self.target.confirmed_email = True
        self.target.save()
        self.prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())
        self.client.force_login(self.admin)

    def _send_url(self):
        return reverse('admin:authentication_user_send_prompt',
                       kwargs={'pk': self.target.pk})

    def test_button_sends_and_records_a_promptsend(self):
        response = self.client.get(self._send_url())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            PromptSend.objects.filter(user=self.target).count(), 1)

    def test_button_force_resends_when_already_sent(self):
        PromptSend.objects.create(user=self.target, prompt=self.prompt)

        self.client.get(self._send_url())

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            PromptSend.objects.filter(user=self.target).count(), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test core.tests.AdminSendPromptButtonTests -v 2`
Expected: FAIL — `test_button_sends_and_records_a_promptsend` fails because the current `send_prompt_view` calls `mail_newsletter` directly and records no `PromptSend`.

- [ ] **Step 3: Update the admin view**

In `authentication/admin.py`, change the import line `from core.utils import mail_newsletter` to:

```python
from core.utils import send_prompt_to_user
```

Then replace the body of `send_prompt_view` so the `mail_newsletter(user)` call becomes `send_prompt_to_user(user, force=True)`. The full method becomes:

```python
    def send_prompt_view(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        try:
            prompt = send_prompt_to_user(user, force=True)
        except Exception as exc:
            messages.error(request, f"Failed to send: {exc}")
        else:
            if prompt is None:
                messages.warning(
                    request,
                    f"No prompt for today for {user.email} "
                    f"(or the user has no valid timezone) — nothing sent.")
            else:
                messages.success(
                    request, f"Sent today's prompt to {user.email}.")
        return redirect('admin:authentication_user_change', pk)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test core.tests.AdminSendPromptButtonTests -v 2`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full suite**

Run: `python manage.py test`
Expected: PASS — all tests, including the existing `MailNewsletterTests` (which still exercise `mail_newsletter` directly and are unaffected).

- [ ] **Step 6: Commit**

```bash
git add authentication/admin.py core/tests.py
git commit -m "Admin send-prompt button records delivery via send_prompt_to_user"
```

---

## Task 5: Hourly cron in the web container (`supercronic`)

This task wires the trigger. There is no unit test — `send_daily_mail` itself is
covered by Task 3. Verification is a local Docker build.

**Files:**
- Create: `crontab`
- Modify: `Dockerfile`
- Modify: `start.sh`

- [ ] **Step 1: Create the crontab file**

Create `crontab` at the repo root with exactly this content:

```
# Send the daily writing prompt. Runs hourly; the command decides who is
# due (local time at or past 8am, not yet sent today).
0 * * * * cd /app && python manage.py send_daily_mail
```

- [ ] **Step 2: Install supercronic in the Dockerfile**

In `Dockerfile`, add the following block immediately after the `WORKDIR /app`
line and before `COPY requirements.txt .`:

```dockerfile
# Install supercronic — a container-friendly cron runner. The web machine is
# always on (min_machines_running = 1) and holds the SQLite volume, so the
# hourly prompt job runs in-process here. Pinned; bump deliberately.
ADD https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64 /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic
```

- [ ] **Step 3: Launch supercronic from start.sh**

In `start.sh`, add the supercronic launch immediately before the final
`exec gunicorn` line. The end of the file becomes:

```sh
# Pass "dev" to run the Django development server (uses settings.local).
if [ "$1" = "dev" ]; then
    exec $PYTHON manage.py runserver 0.0.0.0:8000
fi

# Run the hourly prompt cron alongside the web server (production only — the
# dev branch above execs and never reaches here).
supercronic /app/crontab &

exec gunicorn dailyinquirer.wsgi --bind 0.0.0.0:8000
```

- [ ] **Step 4: Verify the image builds**

Run: `docker build -t dailyinquirer-cron-check .`
Expected: build succeeds; the `ADD` step downloads `supercronic-linux-amd64`
and the `chmod` step succeeds.

If `docker` is not available locally, skip this step — CI's deploy step
(`flyctl deploy --remote-only`) will surface a build failure.

- [ ] **Step 5: Commit**

```bash
git add crontab Dockerfile start.sh
git commit -m "Run send_daily_mail hourly via supercronic in the web container"
```

---

## Post-merge verification (manual, after deploy)

Not part of the automated plan — confirm once after the first deploy:

- [ ] `fly logs` shows a `supercronic` startup line and an hourly
  `send_daily_mail` invocation at `:00`.
- [ ] After a real 8am-in-some-timezone run, a `PromptSend` row exists for a
  test user and they received exactly one email.
- [ ] Re-running the hour (or the admin button without force) does not send a
  second email to that user.

---

## Self-Review Notes

- **Spec coverage:** trigger via supercronic (Task 5); `PromptSend` model with
  unique `(user, prompt)` (Task 1); `send_prompt_to_user` helper with `force`
  (Task 2); `send_daily_mail` hourly loop, `hour >= 8`, confirmed+subscribed
  filter, per-user fault isolation (Task 3); admin button via the helper
  (Task 4); tests for every component (Tasks 1–4). All spec sections covered.
- **No placeholders:** every code and command step is concrete.
- **Type consistency:** `send_prompt_to_user(user, force=False)`, `PromptSend`
  fields `user`/`prompt`/`sent_at`, and the `unique_together` constraint are
  named identically across all tasks.
- **Note on `freezegun`:** intentionally not used (not a dependency). Tests
  control the clock by patching `User.local_time`, which is the only place the
  command and helper read the current time.
