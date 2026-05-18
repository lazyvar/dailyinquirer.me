# Footer redesign + About page — design

**Date:** 2026-05-18
**Branch:** footer

## Goal

Improve the site footer across every page: better style and spacing, a
copyright line, an About link (and the page it points to), and a Contact
link. Replace the two divergent footers with one shared, consistent footer.

## Current state

- `core/templates/core/base.html` — public/dashboard footer. A bare Bootstrap
  row with Terms/Privacy links; an About link sits commented out. Styled only
  by `.footer-link` in `styles.css` (4px side margins).
- `templates/registration/auth_base.html` — auth-page footer (`.auth-footer`),
  already polished: top rule, centered, faint links, accent hover.
- No About page exists; `core/urls.py` has only `terms/` and `privacy/`.
- Both base templates already load `tokens.css` (shared design tokens).

## Decisions

- **Layout:** compact one-line bar — wordmark · About · Terms · Privacy ·
  Contact · copyright. No tagline.
- **Scope:** unify — one footer partial and one CSS file shared by public,
  dashboard, and auth pages.
- **About:** create a real `/about/` page; footer links to it.
- **Contact:** `mailto:hello@dailyinquirer.me`.
- **About copy:** drafted from the CLAUDE.md description (see below).

## Design

### 1. Shared footer partial — `core/templates/core/_footer.html`

Renders, centered on one line:

```
The Daily Inquirer · About · Terms · Privacy · Contact · © 2026 The Daily Inquirer
```

- Wordmark "The Daily Inquirer" links to `/`, set in the Special Elite display
  font, ink color.
- Links: `About` → `/about/`, `Terms` → `/terms/`, `Privacy` → `/privacy/`,
  `Contact` → `mailto:hello@dailyinquirer.me`.
- Copyright year is dynamic: `© {% now "Y" %} The Daily Inquirer`. No
  hardcoded year.
- Dot separators (`·`) are presentational spans/pseudo-elements between
  groups, not links.
- Markup uses a `<footer class="site-footer">` element. Groups: a `.wordmark`
  span/anchor, a `.site-footer__links` group of anchors, a `.copyright` span.

### 2. Shared footer CSS — `dailyinquirer/static/css/footer.css`

New stylesheet, loaded by both `core/base.html` and
`registration/auth_base.html`. Uses existing tokens from `tokens.css`.

- `.site-footer`: centered flexbox row, `flex-wrap: wrap`, gap for spacing,
  `border-top: 1px solid var(--rule)`, generous vertical padding (~22px).
- Links: `var(--ink-faint)`, `text-decoration: none`, hover →
  `var(--accent)`, short color transition.
- Wordmark: `var(--display)` font, `var(--ink)` color, slightly larger than
  the links.
- Copyright: `var(--ink-faint)`, smallest size.
- Dot separators: `var(--rule)` color.
- Responsive (`@media (max-width: 480px)`): items stack centered, dot
  separators hidden, link group wraps.
- `prefers-reduced-motion`: drop the hover transition (matches the existing
  pattern in `auth.css`).

**Removals:** delete the `.footer-link` rule from `styles.css` and the
`.auth-footer` rules from `auth.css` — superseded by `.site-footer`. Remove
the now-unused `.auth-footer a` entry from the `prefers-reduced-motion` block
in `auth.css`.

### 3. Wiring

- `core/base.html`: remove the Bootstrap footer row and the commented-out
  markup. Add `{% include "core/_footer.html" %}` inside a `<footer>` placed
  **after** the `.container` div so the top rule spans the full page width.
  Add `<link href="/static/css/footer.css" rel="stylesheet">` to `<head>`.
- `registration/auth_base.html`: replace the existing `.auth-footer` block
  with `{% include "core/_footer.html" %}`. Add the `footer.css` `<link>`.
  (The auth page is a flex column; the footer keeps `flex-shrink: 0` behavior
  via the `.site-footer` rules or a small `.auth-page .site-footer` tweak if
  needed.)

The partial lives under `core/templates/core/` and is reachable from the
project-level `templates/` tree because Django's app-directories loader makes
`core/_footer.html` resolvable from any template.

### 4. About page

- `core/views.py`: add `about(request)` → `render(request, 'core/about.html')`,
  mirroring `terms` and `privacy`.
- `core/urls.py`: add `path('about/', views.about, name='about')`.
- `core/templates/core/about.html`: extends `core/base.html`, styled to match
  the site (reuse masthead/typography patterns; no new heavy CSS).

**Drafted copy** (editable later):

> **About The Daily Inquirer**
>
> The Daily Inquirer sends you one writing prompt every morning. Reply to the
> email with whatever it stirs up — a sentence, a paragraph, a page — and your
> reply is saved as a journal entry on your personal dashboard.
>
> No app to open, no blank page to face. The prompt comes to your inbox; your
> writing goes back the way it came. Over time your dashboard becomes a
> searchable record of what you thought about, one day at a time.
>
> The Daily Inquirer is a small, independent project. Questions or feedback?
> Email [hello@dailyinquirer.me](mailto:hello@dailyinquirer.me).

### Testing

- Add `test_about_page_renders` to `core/tests.py`: GET `/about/` returns 200.
- Optionally assert the footer markup appears on a rendered page (e.g. the
  index response contains the `site-footer` class).
- CI runs `python manage.py test`; run it locally before finishing.

## Out of scope / follow-up

- `hello@dailyinquirer.me` must be provisioned as a real mailbox or forwarding
  alias for the Contact link to work. This is a DNS/email-hosting step, not a
  code change, and is not handled by this work.
- No changes to the daily email template footer (`daily_email.html`) — that
  email has its own footer and was not part of this request.
