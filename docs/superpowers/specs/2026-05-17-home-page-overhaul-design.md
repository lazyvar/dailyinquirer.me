# Home Page Overhaul — Design

**Date:** 2026-05-17
**Status:** Approved
**Branch:** home-page-improvements

## Goal

Replace the plain Bootstrap logged-out home page with a distinctive, redesigned
page that keeps the existing vibe ("The Daily Inquirer," slab-serif headline,
firebrick accent, writing-prompt service). Ship **two complete visual themes**
the user can switch between with a footer toggle.

## Themes

Two themes, both presenting the same content with radically different styling:

### Broadsheet (A) — default

A newspaper front page.

- Double-rule masthead: "The Daily Inquirer" in a heavy serif headline.
- Dateline above the masthead showing today's date via Django's `{% now %}`
  tag, plus the tagline "A Writing Prompt, Delivered Daily."
- Drop caps on the About section's opening paragraph.
- About text laid out in newspaper-style multiple columns.
- The 7-day prompt sample arranged as a front-page grid with day-of-week
  headers and genre labels.
- Firebrick remains the accent color on links and the "Get started" CTA.

### Editorial (C)

A crisp, modern product landing page.

- Small uppercase firebrick kicker above the headline.
- Large editorial headline with exactly one italic firebrick phrase.
- Pill-shaped "Get started" CTA.
- The 4 how-it-works steps as clean bordered cards.
- The 7-day prompt sample as a row/grid of cards; today's card is highlighted.
- Generous whitespace and subtle hover motion.

### Content present in both themes

- Site name and tagline.
- "Get started" CTA linking to `/register/`.
- "Already registered? Log in." link to `/login/`.
- The 4-step how-it-works section (reuses `inbox.png`, `send.png`,
  `blog.png`, `cal.png`).
- The About blurb (reuses `typing_monkey.png`).
- The 7-day writing-prompt sample (Monday–Sunday, with genre + prompt text).

## Architecture

**Single template, both layouts in the DOM.** A wrapper element carries a
class — `theme-broadsheet` or `theme-editorial`. Both theme layouts are
rendered in the HTML; CSS displays only the active one. Switching themes is
purely client-side: swap the class, persist to `localStorage`. No server
round-trip.

### Files

| File | Change |
|------|--------|
| `core/templates/core/index.html` | Rewritten: both theme layouts + footer toggle |
| `core/templates/core/base.html` | Add `{% block extra_head %}{% endblock %}` in `<head>` |
| `dailyinquirer/static/css/home.css` | **New** — all theme styles, every rule scoped under `.theme-broadsheet` / `.theme-editorial` so styles cannot leak to other pages |
| `dailyinquirer/static/js/home-theme.js` | **New** — read `localStorage`, apply theme class, wire the toggle |

`home.css` is loaded only on the home page via the new `extra_head` block.

## The toggle

A discreet control rendered at the bottom of the home page content, directly
above the existing Terms/Privacy footer from `base.html`:

> View as: **Broadsheet** · **Editorial**

- **Preview-only** — intended for the maintainer to compare A vs C, not a
  promoted public feature. It is not hidden, but it is understated.
- First visit defaults to **Broadsheet**.
- The selected theme persists in `localStorage` across visits.
- The toggle markup lives inside `index.html`, so no other page is affected
  and it is trivial to remove or gate later.

### Theme application timing

`home-theme.js` applies the stored theme class as early as possible to avoid a
flash of the default theme. The wrapper ships with `theme-broadsheet` already
set in the HTML (matching the default), so a first visit or a Broadsheet user
sees no flash; only an Editorial-preferring returning visitor may see a brief
correction, which is acceptable for a preview tool.

## Out of scope

- The logged-in home page (`index_logged_in.html`).
- All other pages (settings, terms, privacy, auth templates).
- The daily email template.
- Any change to views, URLs, models, or forms — this is template + static
  assets only.

## Testing

- Manual: load `/`, confirm Broadsheet renders by default; click the toggle,
  confirm Editorial renders; reload, confirm the choice persisted.
- Confirm other pages (`/terms/`, `/privacy/`, `/login/`) are visually
  unchanged — no style leakage from `home.css`.
- Confirm both CTAs link correctly (`/register/`, `/login/`).
