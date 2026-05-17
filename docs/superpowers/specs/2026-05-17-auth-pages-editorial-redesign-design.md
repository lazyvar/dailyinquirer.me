# Auth Pages — Editorial Redesign

**Date:** 2026-05-17
**Status:** Approved
**Branch:** home-page-improvements (PR #15)

## Goal

Restyle the authentication pages to match the editorial design language
established by the home page overhaul: Special Elite headings, Open Sans body,
the shared accent color, pill buttons, clean form inputs, and understated
section labels.

## Scope

In scope — the 9 auth **web** pages, all of which extend
`templates/registration/auth_base.html`:

- `login.html`
- `register.html` (served at `/register/`)
- `password_reset_form.html`
- `password_reset_done.html`
- `password_reset_confirm.html`
- `password_reset_complete.html`
- `resend_confirmation.html`
- `user_unconfirmed.html`
- `activation_email_sent.html`

Out of scope — the two email templates, which are not web pages and keep their
current form:

- `confirm_email.html`
- `password_reset_email.html`

No changes to views, URLs, models, or forms. This is templates + static assets
only. Work lands on `home-page-improvements` / PR #15.

## CSS Architecture

### `tokens.css` (new)

The design tokens currently defined inside `home.css` on the `#home` selector
are promoted to `:root` in a new shared file, so the home page and the auth
pages read one source of truth (preventing palette drift):

```css
:root {
  --ink: #1a1a1a;
  --ink-soft: #555;
  --ink-faint: #8a8a8a;
  --rule: #d8d4cc;
  --accent: #009302;
  --accent-rgb: 0, 147, 2;
  --danger: #b22222;
  --danger-rgb: 178, 34, 34;
  --paper: #ffffff;
  --serif: 'Special Elite', Georgia, 'Times New Roman', serif;
  --body: 'Open Sans', system-ui, sans-serif;
}
```

`--danger` / `--danger-rgb` are new: the accent is now green, so error alerts
must use a dedicated red rather than the accent.

`tokens.css` is loaded in the `<head>` of both `core/base.html` and
`templates/registration/auth_base.html`.

### `home.css` (modify)

Delete the `#home { --… }` token-declaration block (lines 1–11). All
`var(--…)` references continue to resolve, now inheriting from `:root`. No
other home-page rule changes.

### `auth.css` (new)

All editorial styling for the auth pages. Every selector scoped under the
existing `.auth-page` body class so the styles cannot leak. Covers: page
background and layout, wordmark, card, headings, subtitle, form fields and
labels, primary button, error alerts, secondary links, footer, responsive
behavior, and a `prefers-reduced-motion` block.

### `auth_base.html` (modify)

The `<head>` loads: `fonts.css` (for the Special Elite `@font-face`), the
Google Open Sans link, `tokens.css`, and `auth.css`. It no longer loads
`bootstrap.css` or `styles.css`. The body keeps its `wordmark → card → footer`
structure.

### `styles.css` (modify)

Remove the now-dead `.auth-*` rules. The auth pages no longer load
`styles.css`; no other page uses those selectors.

## Visual Treatment

Mirrors the editorial home page:

- **Page:** light background, single centered column. The "The Daily Inquirer"
  wordmark sits above the card in Special Elite, small, linking to `/`.
- **Card:** white (`--paper`), 1px `--rule` border, ~8px radius, generous
  padding, max-width ~400px. Comfortable down to 320px.
- **Heading:** the card's `<h1>` (`Log in`, `Reset password`, …) in
  `--serif`, sized like a scaled-down home headline.
- **Subtitle:** `--body`, `--ink-soft`.
- **Inputs:** full-width, 1px `--rule` border, ~6px radius, padded; label
  above each in small medium-weight `--body`. Focus state raises the border to
  `--accent`. The timezone `<select>` on the register page gets matching
  treatment.
- **Primary button:** full-width pill — dark `--ink` background, white text,
  hover → `--accent` with a subtle lift — matching the home page `.ed-btn`.
  Styled to render identically whether the element is a `<button>`, an
  `<input type="submit">`, or an `<a>` (the reset-done / complete / invalid-link
  pages use anchors).
- **Error alerts:** a distinct red-tinted block using `--danger` /
  `--danger-rgb` (tinted background, red left border, small `--body` text).
- **Secondary links** ("Forgot password?", "No account? Sign up", footer
  Terms/Privacy): understated, underlined or quiet, `--accent` on hover.
- **Motion:** hover transitions ~150ms; a `prefers-reduced-motion: reduce`
  block disables transforms.

## Markup Changes

Each of the 9 card templates has its `{% block card %}` markup updated to the
new editorial classes; Bootstrap classes (`form-group`, `form-control`,
`btn`, `btn-primary`, `btn-block`, `alert`, `mt-*`) are removed. Content
wording is preserved.

### Form-errors include (new)

The repeated error block —

```django
{% if form.errors %}{% for field in form %}{% for error in field.errors %}
<div class="alert alert-danger">…</div>
{% endfor %}{% endfor %}{% for error in form.non_field_errors %}…{% endfor %}{% endif %}
```

— currently duplicated in `login`, `register`, `password_reset_form`,
`password_reset_confirm`, and `resend_confirmation` is extracted to one
`templates/registration/_form_errors.html` partial, included with
`{% include "registration/_form_errors.html" %}`. The partial renders the
editorial error alert.

## Testing

A new `AuthPagesTests` test class (in `core/tests.py`, alongside the existing
`HomePageTests` and `EmailConfirmationTests`):

- Each directly GET-able auth page returns HTTP 200, contains `auth.css`, and
  does **not** contain `bootstrap.css`: `login`, `register`, `password_reset`
  (form), `password_reset_done`, `password_reset_complete`,
  `resend_confirmation`, `unconfirmed_email`. A GET to `password_reset_confirm`
  with a dummy `uidb64`/`token` renders the invalid-link branch (HTTP 200) and
  is asserted the same way.
- `activation_email_sent.html` is rendered only as the response to a `POST`
  (register or resend); the test POSTs valid registration data and asserts the
  response contains `auth.css` and not `bootstrap.css`.
- A page with a form (`login`) is asserted to render the editorial form markup
  rather than Bootstrap classes.
- The pre-existing `EmailConfirmationTests` continue to pass.

## Out of Scope / Non-Goals

- No redesign of the logged-in pages (`settings`, logged-in home), `terms`,
  or `privacy` — those keep `styles.css`.
- No changes to authentication logic, validation, or flows.
- The email templates are untouched.
