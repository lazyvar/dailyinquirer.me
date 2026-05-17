# Daily Prompt Cron — Design

**Date:** 2026-05-17
**Status:** Approved, ready for implementation planning

## Problem

The `send_daily_mail` management command already builds and sends the daily
writing prompt, but nothing triggers it on a schedule. We need a recurring
trigger that delivers each day's prompt to users at 8am in their own timezone.

## Constraints

- The app runs on Fly.io as a **single machine** (`min_machines_running = 1`)
  with **SQLite on an attached volume**. A Fly volume attaches to only one
  machine at a time, so a separate scheduled machine cannot reach the database.
- Users span many timezones, so the trigger must fire **hourly**; the command
  decides who is due.
- Emails go only to users with `confirmed_email=True` and `is_subscribed=True`.
- The 8am hour is hardcoded for now. (`User.mail_time` exists but stays unused;
  per-user send times are out of scope.)

## Approach

In-process cron inside the web container. The web machine is always up and
already has the SQLite volume mounted, so the scheduler runs with direct
database access and needs no extra infrastructure, secrets, or network hop.

Rejected alternatives:
- **Fly scheduled machine** — cannot attach the SQLite volume held by the web
  machine; does not fit the storage model.
- **External scheduler (GitHub Actions / AWS EventBridge)** — adds secrets and
  an endpoint or SSH credentials; GitHub Actions cron is unreliable. Not worth
  the cost given a single always-on machine.

## Architecture

### Trigger: `supercronic` in the web container

- Add the `supercronic` static binary to the `Dockerfile`.
- Add a `crontab` file at the repo root with one entry:
  `0 * * * * cd /app && python manage.py send_daily_mail`
- `start.sh`: after `migrate`, launch `supercronic crontab &` in the
  background, then `exec gunicorn` as today. In `dev` mode, do not start
  supercronic.

### Data model: `PromptSend`

New model in `core/models.py` with a migration:

```python
class PromptSend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'prompt')
```

Each `Prompt` maps to one calendar day via `mail_day`, so `(user, prompt)`
means "this user received this day's prompt." The unique constraint is a
DB-level backstop against double-sends; the send helper also checks explicitly.

## Components

### `send_prompt_to_user(user, force=False)` — `core/utils.py`

One helper, used by both the cron and the admin button, so dedup logic lives
in one place:

1. Compute `local_time`; return if the timezone is invalid.
2. Find `todays_prompt` via `prompt_for_datetime`; return if none exists.
3. If `not force` and a `PromptSend` already exists for `(user,
   todays_prompt)` → skip.
4. Send the email (current `mail_newsletter` body).
5. `PromptSend.objects.update_or_create(user=user, prompt=todays_prompt,
   defaults={'sent_at': now})`.
6. Return a result the caller can report on (sent / skipped / no-prompt).

### `send_daily_mail` command

A thin loop over eligible users:

```python
for user in User.objects.filter(confirmed_email=True, is_subscribed=True):
    local_time = user.local_time()
    if local_time is None or local_time.hour < 8:
        continue
    send_prompt_to_user(user)  # dedup-guarded
```

The command sends when local hour is **`>= 8`**, not `== 8`. This makes it
self-healing: if a run is missed (machine restart during the user's 8am hour),
a later run the same day still catches them, and `PromptSend` guarantees
exactly-once delivery. A user only misses the day entirely if the machine is
down for every hour from 8am to midnight in their timezone.

### Admin "Send today's prompt" button

`send_prompt_view` in `authentication/admin.py` calls
`send_prompt_to_user(user, force=True)` instead of `mail_newsletter` directly.
`force=True` lets admins re-send for testing, and it still records the
`PromptSend` so the cron does not double up afterward.

## Error handling

Each user's send is wrapped in try/except inside the command loop, so one
failure (bad address, SES hiccup) does not abort the rest. Failures are logged
to stdout (Fly captures it). A failed send creates no `PromptSend` row, so the
next hourly run retries it automatically.

## Testing

Test-driven, in `core/tests.py`, using Django's `locmem` email backend and
mocked/`freezegun` time:

- `prompt_for_datetime` matches a prompt by local calendar date.
- `send_prompt_to_user` skips when a `PromptSend` exists, sends and records
  when not, and respects `force=True`.
- `send_daily_mail` skips users with local `hour < 8`, invalid timezone, and
  those who are unconfirmed or unsubscribed.
- A send failure for one user does not stop the loop and leaves no
  `PromptSend` row.

## Out of scope

- Per-user send times (`User.mail_time`).
- Moving off SQLite or to a multi-machine setup.
- External scheduling and observability dashboards.
