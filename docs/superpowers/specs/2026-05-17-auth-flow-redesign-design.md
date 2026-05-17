# Auth Flow Redesign — Design

**Date:** 2026-05-17
**Status:** Approved

## Summary

A focused visual redesign of the authentication pages: center the form in a card,
pin the footer to the bottom of the viewport, and clean up a few rough edges.
No behavior, view, form, or backend changes. References: the RevenueCat and
LinkedIn login pages — clean, centered, footer at the bottom.

## Goals

- Form content centered horizontally and vertically in a card.
- Footer pinned to the bottom of the viewport on every auth page.
- A consistent, clean look across all 9 auth pages.

## Non-Goals (Out of Scope)

- Social login (Google/Apple).
- Password-visibility toggle.
- Any change to views, forms, URLs, or backend logic.
- Any change to `core/base.html` or non-auth pages (homepage, settings, terms, privacy).
- Changes to `confirm_email.html` (it is a plain-text email body, not a page).

## Layout

### New template: `templates/registration/auth_base.html`

A dedicated, standalone base template — its own complete HTML document. It does
**not** extend `core/base.html`, because the centered/pinned layout is
auth-specific and `core/base.html` wraps content in a Bootstrap `.container`
used by non-auth pages.

Structure (full-viewport flex column, `min-height: 100vh`):

1. **Wordmark** — "The Daily Inquirer" in the typewriter font, a link to `/`,
   positioned above the card on the page background (LinkedIn/RevenueCat
   convention).
2. **Centered card** — a white card (~400px max width, rounded corners, 1px
   border, subtle shadow) containing a `{% block card %}`. The card area grows
   to fill available space so the card is vertically centered.
3. **Footer** — full width, pinned to the bottom, light top border. Contains the
   same Terms · Privacy links as today's `core/base.html` footer.

Page background: light gray (`#f4f4f6`). Card: white. Brand color: firebrick
(unchanged). Loads the same CSS as the rest of the site
(`bootstrap.css`, `fonts.css`, `styles.css`).

## Pages

All 9 page templates in `templates/registration/` are rewritten to extend
`auth_base.html` and fill the `card` block. Two categories:

### Form pages

`login.html`, `register.html`, `password_reset_form.html`,
`password_reset_confirm.html`, `resend_confirmation.html`

- Card heading + subtitle text.
- Fields each get a `<label>` above the input.
- Full-width firebrick primary submit button.
- Error-alert blocks preserved exactly as today (`form.errors`,
  `form.non_field_errors` iteration).
- All field names, `name`/`id` attributes, hidden inputs (e.g. login's
  `next`), and form `action`s preserved unchanged.

### Message pages

`activation_email_sent.html`, `password_reset_done.html`,
`password_reset_complete.html`, `user_unconfirmed.html`

- Card heading + message text + the relevant link(s), preserved from today's
  content.

### Untouched

`confirm_email.html` — plain-text email body, not rendered as a page.

## Cleanups (baked into the redesign)

- Field `<label>`s added above inputs on all form pages.
- "Forgot password?" on the login page: demoted from a heavy gray
  `btn-light btn-block` to a plain inline link.
- Login page gains a "No account? Sign up" link (to the register page).
- Register page gains an "Already have an account? Log in" link.

## CSS

A small set of scoped `.auth-*` classes is added to the shared
`dailyinquirer/static/css/styles.css`:

- A page wrapper class (flex column, full viewport height, gray background).
- A card class (white, max-width, border, radius, shadow, padding).
- A wordmark class (typewriter font, spacing above the card).
- A pinned-footer class (margin-top auto / flex push, light top border).

No existing CSS class is modified, so non-auth pages are visually unaffected.

## Verification

- Each of the 9 auth pages renders with the centered card and a footer pinned
  to the bottom of the viewport (including on short content where the footer
  would otherwise float up).
- Login, register, password reset request, password reset confirm, and resend
  confirmation forms submit successfully and display validation errors as
  before.
- Homepage, settings, terms, and privacy pages are visually unchanged.
