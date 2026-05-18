# Change Account Email — Design

**Date:** 2026-05-18
**Branch:** change-email

## Goal

Let a logged-in user change the email address on their account from the
settings page. The settings page lists the current email with a pencil
affordance; editing it checks whether the requested address is already taken
and, if not, puts the change into a "pending" state that completes only after
the new address is verified.

## Background

`email` is the `USERNAME_FIELD` on the custom `authentication.User` model — it
is the login identity. A change must therefore prove the new address is real
and reachable before it takes effect, or a typo would lock the user out.

The account-activation flow already establishes the pattern this design
reuses: a `PasswordResetTokenGenerator` subclass in `authentication/tokens.py`
whose `_make_hash_value` includes a mutable field, making the link single-use
once that field changes. Auth-related views (`register`, `activate`,
`send_activation_email`) currently live in `core/views.py`; the new views
follow that placement for consistency.

## Approach

Pending-email with new-address verification:

1. The requested address is stored on the user as `pending_email`.
2. A confirmation link is emailed to the **new** address.
3. A heads-up notice is emailed to the **old** address (security signal).
4. The `email` field is swapped only when the confirmation link is clicked.

## Data model

Add to `authentication.User`:

```python
pending_email = models.EmailField(max_length=255, null=True, blank=True)
```

Migration: `authentication/migrations/0006_user_pending_email.py`.

No change to `confirmed_email` — the user remains confirmed throughout; the new
address is proven by the link click rather than by toggling that flag.

## Token

New generator in `authentication/tokens.py`:

```python
class EmailChangeTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.email}{user.pending_email}"

email_change_token = EmailChangeTokenGenerator()
```

Because the hash includes both `email` and `pending_email`, the link becomes
invalid as soon as the swap completes (email changed, `pending_email` cleared)
or the change is cancelled (`pending_email` cleared). This makes the link
single-use without any extra state.

## Flow

1. `/settings/` Account card shows the current email with a pencil toggle. The
   toggle is a native `<details>`/`<summary>` element — no JavaScript —
   revealing an inline "new email" field and a "Send confirmation" button.
2. Submitting POSTs to the new `manage_email_change` view with
   `action=request`. The view normalizes the address
   (`User.objects.normalize_email`) and checks uniqueness server-side
   (`User.objects.filter(email__iexact=new).exclude(pk=user.pk)`).
   - If taken, or equal to the user's current email → inline error; the
     `<details>` editor is re-rendered open so the user can correct it.
   - If available → set `user.pending_email`, save, send the two emails, and
     render the settings page with a "Change to X is pending" banner.
3. The pending banner offers **Resend** (`action=resend` — re-send the
   confirmation to the existing `pending_email`) and **Cancel**
   (`action=cancel` — clear `pending_email`). Both POST to
   `manage_email_change`.
4. The confirmation email links to `confirm_email_change` at
   `settings/email/confirm/<uidb64>/<token>/`. That view decodes the uid,
   loads the user, and validates the token. On success it re-checks
   uniqueness (the address could have been registered in the interim):
   - Still available → set `user.email = user.pending_email`, clear
     `pending_email`, save; render `change_email_confirmed.html`.
   - Taken now → clear `pending_email`, save; render the confirmed template
     in an error state explaining the address was claimed.
   - Invalid/expired token, or no `pending_email` → plain failure response,
     matching the existing `activate` view's behaviour.

Changing `email` does not log the user out: `AbstractBaseUser`'s session auth
hash is derived from the password, not the email.

## Views & URLs

New views in `core/views.py`:

- `manage_email_change(request)` — POST only, `@login_required`. Dispatches on
  the `action` POST field (`request`, `resend`, `cancel`). Renders
  `core/settings.html` with the appropriate context.
- `confirm_email_change(request, uidb64, token)` — performs the swap.

New URLs in `core/urls.py`:

```python
path('settings/email/', views.manage_email_change, name='manage_email_change'),
path('settings/email/confirm/<uidb64>/<token>/',
     views.confirm_email_change, name='confirm_email_change'),
```

## Form

New form in `core/forms.py`:

```python
class ChangeEmailForm(forms.Form):
    email = forms.EmailField(max_length=255)
```

Uniqueness and "same as current" checks live in the view, since they need
`request.user`.

## Templates

- `core/templates/core/settings.html` — edit the Account card:
  - When no change is pending: show the email with the pencil `<details>`
    editor.
  - When `user.pending_email` is set: show the pending banner with Resend and
    Cancel forms.
  - Surface email-change success/error via context flags
    (`email_change_error`, `email_change_requested`, `email_change_canceled`)
    using the existing `ed-alert` markup. When `email_change_error` is set,
    render the `<details>` editor `open`.
- `templates/registration/change_email_confirm.html` — confirmation link, sent
  to the new address.
- `templates/registration/change_email_notice.html` — heads-up, sent to the
  old address.
- `templates/registration/change_email_confirmed.html` — result page shown
  after the confirmation link is clicked (success and address-taken states).

## Emails

Both built with `EmailMessage`, mirroring `send_activation_email`, from
`"Beep Boop <beep-boop@dailyinquirer.me>"`:

- To the new address — subject "Confirm your new Daily Inquirer email";
  body links to `confirm_email_change`.
- To the old address — subject "Your Daily Inquirer email is being changed";
  body states which address was requested and that no action is needed if it
  was them.

## Edge cases

- Case-insensitive duplicate check (`email__iexact`) at both request time and
  confirmation time.
- New address equal to the current address → rejected with an inline error.
- Requesting a change while one is already pending → overwrites the prior
  `pending_email`.
- A stale link (change already confirmed, or cancelled) → token validation
  fails and the view returns the failure response.
- Confirmation clicked on a device where the user is not logged in → still
  works; the uid in the link identifies the user, the token authorises it.

## Testing

Add to `core/tests.py`:

- Request with an available address → `pending_email` set; two emails sent
  (new address + old address).
- Request with an address already taken by another user → inline error; no
  `pending_email` set.
- Request with the user's own current address → inline error.
- Valid confirmation link → `email` swapped, `pending_email` cleared.
- Re-using a confirmation link after the swap → rejected.
- Cancel → `pending_email` cleared.
- Resend → confirmation re-sent to the unchanged `pending_email`.
