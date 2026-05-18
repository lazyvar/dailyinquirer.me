# Onboarding step + per-user send time — design

## Summary

Add a one-page onboarding step that new users must complete after confirming
their email. The page collects three things: opt-in to the daily email
(`is_subscribed`), the user's timezone (JS-autodetected), and the hour of day
the prompt is sent. Onboarding completion is tracked by a new `onboarded`
boolean on the `User` model; until it is `True`, every authenticated request is
redirected to the onboarding page.

A new feature ships alongside it: users choose the hour their prompt arrives
(default 8am local). This repurposes the existing-but-unused `mail_time` field.
Signup is also simplified to email + password only — timezone moves to
onboarding.

## Data model — `authentication.User`

- **Add** `onboarded = models.BooleanField(default=False)`.
- **`mail_time`** (existing unused `IntegerField`, minutes-from-midnight):
  change default from `360` to `480` (8:00am). Add a property:
  ```python
  @property
  def mail_hour(self):
      return self.mail_time // 60
  ```
- **`timezone`**: change to `models.CharField(max_length=64, blank=True, default='')`
  so a user can be created without one (set later during onboarding).
- **`REQUIRED_FIELDS`**: remove `'timezone'` (now optional;
  `createsuperuser` no longer prompts for it).

### Migrations

1. Schema migration: add `onboarded`; alter `mail_time` default; alter
   `timezone` to `blank=True, default=''`.
2. Data migration: for every existing `User`, set `onboarded=True` and
   `mail_time=480`. This makes current users skip the onboarding page and keeps
   their delivery at 8am (rather than the stale 6am implied by the old `360`
   default). Reverse operation is a no-op.

## Onboarding gate — middleware

New `core.middleware.OnboardingRequiredMiddleware`, registered in
`dailyinquirer/settings/base.py` `MIDDLEWARE` immediately after
`AuthenticationMiddleware`.

Behaviour: if `request.user` is authenticated, has `confirmed_email=True`, and
`onboarded=False`, redirect to `/onboarding/`.

Exempt path prefixes (no redirect): `/onboarding/`, `/logout/`, `/admin/`,
`/messages/`, and `STATIC_URL`. The exemption check uses `request.path`.

Rationale for middleware over per-view decorators: the redirect must apply
uniformly to every page; a decorator would need to be added to each view and is
easy to forget on new views.

## Onboarding page — `/onboarding/`

New URL `path('onboarding/', views.onboarding, name='onboarding')` in
`core/urls.py`.

New view `core.views.onboarding` (decorated `@login_required`):

- **GET**: render `core/onboarding.html` with an unbound `OnboardingForm` (or a
  bound one prefilled from the user) plus `timezones` context.
- **POST**: bind `OnboardingForm`. On valid:
  - `user.is_subscribed = form.cleaned_data['subscribed']`
  - `user.timezone = form.cleaned_data['timezone']`
  - `user.mail_time = int(form.cleaned_data['mail_hour']) * 60`
    (`ChoiceField` cleans to a string)
  - `user.onboarded = True`
  - `user.save()`, then `redirect('index')`.
  - On invalid: re-render `core/onboarding.html` with form errors.

If an already-onboarded user reaches `/onboarding/`, redirect to `index`
(the middleware will not have redirected them here, but a direct visit should
not let them re-run it).

### Template — `core/templates/core/onboarding.html`

Single page styled with the existing `ed-card` / `ed-field` classes (same
visual language as `settings.html`). One `<form method="post">` with:

- **Opt-in checkbox** — "Receive a writing prompt by email every day."
  Unchecked by default.
- **Timezone `<select>`** — populated from `timezones`, prefilled with
  `user.timezone` if set.
- **Send-time `<select>`** — hours `0`–`23`, labelled as "8:00 AM" etc.,
  default `8`.
- Submit button completing onboarding.

A small inline `<script>` runs on load:
`Intl.DateTimeFormat().resolvedOptions().timeZone`; if that value matches an
`<option>`, select it. Falls back silently to the server-rendered selection.

## Settings page — send-time control

- `SettingsForm` gains `mail_hour = forms.ChoiceField` with choices `0`–`23`.
- `core.views.settings`: on valid POST, additionally set
  `user.mail_time = int(form.cleaned_data['mail_hour']) * 60`.
- `settings.html`: add the hour `<select>` inside the existing
  "Subscription & timezone" card, prefilled from `user.mail_hour`.

## Signup simplification

- `UserCreationForm.Meta.fields` (`authentication/admin.py`): change
  `('email', 'timezone')` to `('email',)`. Admin's `add_fieldsets` already only
  uses `email`/`password1`/`password2`, so the admin add flow is unaffected.
- `templates/registration/register.html`: remove the timezone `<select>`
  block; the form is email + password + confirm only.
- `core.views.register`: no longer needs to pass `timezones` in context.

Newly registered users therefore have `timezone=''` and `onboarded=False`. They
cannot receive mail (`local_time()` returns `None` for an empty timezone) and
are gated into onboarding on first login after email confirmation.

## Daily send logic

`core/management/commands/send_daily_mail.py`: change the per-user check from
`local_time.hour < 8` to `local_time.hour < user.mail_hour`.

No crontab change — the job still runs hourly and now sends each user their
prompt once their local clock reaches their chosen hour. `send_prompt_to_user`
and the `PromptSend` dedup are unchanged.

## Forms

- **New** `OnboardingForm(forms.Form)`:
  - `subscribed = forms.BooleanField(required=False, initial=False)`
  - `timezone = forms.CharField(max_length=64)`
  - `mail_hour = forms.ChoiceField(choices=[(h, h) for h in range(24)])`
- **`SettingsForm`** gains the same `mail_hour` `ChoiceField`.

## Testing

- **Model/migration**: `onboarded` defaults `False` for new users; data
  migration leaves existing users `onboarded=True` with `mail_time=480`;
  `mail_hour` property returns the expected hour.
- **Middleware**: a confirmed, not-onboarded user is redirected to
  `/onboarding/` from an arbitrary page; an onboarded user is not; exempt paths
  (`/logout/`, `/admin/...`, `/onboarding/`) are not redirected; anonymous users
  are not redirected.
- **Onboarding view**: GET renders the page; valid POST sets `is_subscribed`,
  `timezone`, `mail_time`, and `onboarded=True`, then redirects to `index`;
  invalid POST re-renders with errors; an already-onboarded user GETting
  `/onboarding/` is redirected to `index`.
- **Settings**: POST saves `mail_time` from `mail_hour` alongside existing
  fields.
- **`send_daily_mail`**: a user whose local hour equals/exceeds `mail_hour`
  receives the prompt; a user below their `mail_hour` does not.
- **Signup**: registering with email + password only succeeds and produces a
  user with `timezone=''` and `onboarded=False`.

## Out of scope

- JS timezone autodetect on the signup and settings pages (onboarding only).
- Sub-hourly send precision (would require a more frequent cron).
