# Editorial theme for the dashboard & settings pages

**Date:** 2026-05-17
**Status:** Approved design — ready for implementation planning

## Goal

Bring the two logged-in pages — the dashboard (`index_logged_in.html`) and the
settings page (`settings.html`) — onto the "editorial / newspaper" theme
introduced by the home page redesign (commit `565e9b5`). Both pages currently
use plain Bootstrap markup and look visually disconnected from the rest of the
site.

Alongside the visual work, the dashboard gains real archive controls: search,
a collapsible filter panel (date range, category, sort), a result count, and
pagination.

## Current state

- `core/views.py :: index` lists **all** of a user's entries, newest first,
  with no pagination or filtering: `Entry.objects.filter(author=request.user).order_by("-pub_date")`.
- `core/views.py :: settings` renders the subscription/timezone form, password
  reset form, and logout form.
- Both templates extend `core/base.html` (which still loads Bootstrap) and use
  Bootstrap grid/form/alert classes plus a `typewriter` site-title header.
- The editorial theme lives in `tokens.css` (design tokens) and `home.css`
  (home-page components, all scoped under `#home`).

`core/base.html` stays as-is — it still loads Bootstrap, exactly as it does for
the already-redesigned home page. The account pages simply stop using Bootstrap
classes; the unused Bootstrap CSS being present is harmless and consistent.

## Design principles

- **All backgrounds are white (`#fff`).** Body, masthead, and cards are all
  white; separation comes from hairline borders (`--rule`) and the masthead's
  soft shadow. No outer page border — content sits in `base.html`'s `.container`,
  matching the home page.
- Reuse the home page's editorial vocabulary: the masthead card with a green
  "folder tab", `--accent` green (`#009302`), the `Special Elite` typewriter
  display font for headings, `Open Sans` for body, uppercase letter-spaced
  section labels.
- No JavaScript framework. All interaction is plain server-rendered HTML:
  GET-form filtering, and the native `<details>` element for the collapsible
  filter panel.

## Shared components

### Stylesheet — `dailyinquirer/static/css/account.css`

A new stylesheet, loaded by both pages via `{% block extra_head %}`, consuming
the variables in `tokens.css`. It follows the `home.css` pattern: every selector
is scoped under a page root so styles cannot leak. Both account pages carry a
shared root class `.app` plus a page id (`#dashboard`, `#settings`); shared
components are scoped under `.app`, page-specific rules under the id.

Components defined: masthead, section label (`ed-label`), card (`ed-card`),
primary pill button (`ed-btn`), ghost/outline pill button (`ed-btn-ghost`),
editorial form controls (text input, select, checkbox row), accented alert
banner, the dashboard filter bar, and pagination tiles. Class names mirror the
home page (`ed-masthead`, `ed-card`, `ed-label`, `ed-btn`) for a consistent
vocabulary; scoping keeps them independent of `#home`.

The stylesheet includes the responsive and `prefers-reduced-motion` handling
that `home.css` already establishes.

### Masthead partial — `core/templates/core/_masthead.html`

Both pages share an identical masthead, so it becomes an `{% include %}`
partial taking one variable, `tab` (the green folder-tab label):

- a green folder tab — `"Your writing"` on the dashboard, `"Account"` on settings
- `The Daily Inquirer` site name in `Special Elite`, linking to `/`
- the logged-in user's email, linking to `/settings/`

## Dashboard page (`index_logged_in.html` + `index` view)

### Entry display — bordered cards

Each saved entry renders as a white `ed-card` with a hairline border (the same
card used for prompt cards on the home page). Inside each card:

- the prompt **category** as a small uppercase green label (omitted if the
  prompt has no category)
- the prompt **question** as a `Special Elite` heading
- the **publication date** (`M d, Y`) in faint text
- the **entry content** (`linebreaks`-filtered, as today)

### Controls

A single `<form method="get">` wraps all controls so every parameter combines:

- **Search box — always visible.** A full-width text input plus a green
  "Search" pill button.
- **"Filters" — a collapsed `<details>` disclosure.** Hidden by default; when
  opened it reveals a bordered panel containing:
  - **From / To** date inputs (`<input type="date">`)
  - **Category** select — `All categories` plus the distinct categories found
    among this user's entries
  - **Sort** select — `Newest first` (default) / `Oldest first`
  - an "Apply" pill button and a "Clear" link (links to bare `/`)
  The panel renders **open** (`<details open>`) when any filter parameter is
  active, so it stays expanded after the user applies a filter.
- **Result count — conditional.** "Showing X–Y of Z entries" appears **only
  when** a search or filter is active (`q`, `from`, `to`, or `category`
  present). It is hidden on the default unfiltered view.

### View behavior (`core/views.py :: index`)

The authenticated branch reads these GET parameters:

| Param      | Effect |
|------------|--------|
| `q`        | Case-insensitive match against entry content **or** prompt question (`content__icontains` OR `prompt__question__icontains`) |
| `from`     | `pub_date__date__gte` (parsed `YYYY-MM-DD`; ignored if unparseable) |
| `to`       | `pub_date__date__lte` (parsed `YYYY-MM-DD`; ignored if unparseable) |
| `category` | Exact match on `prompt__category` |
| `sort`     | `oldest` → `pub_date`; anything else → `-pub_date` (default) |
| `page`     | Page number for the paginator |

After filtering, the queryset is paged with Django's `Paginator` at **25
entries per page**. An out-of-range or non-integer `page` falls back to a valid
page. Pagination links preserve all active query parameters except `page`.

The template context gains: the page object, the result count and range, the
list of available categories, the current filter values (to repopulate the
form), and a `filters_active` boolean.

### Empty states

- **No entries at all** — the existing "No entries yet!" message, restyled.
- **Filter/search matches nothing** — a distinct message ("No entries match
  your search.") with a "Clear" link back to the unfiltered dashboard.

## Settings page (`settings.html`)

Template-only changes; the `settings` view is unchanged.

- The shared **masthead** partial with the `"Account"` tab.
- A `"Settings"` section label.
- **Subscription & timezone** form in one `ed-card`: a `Special Elite` card
  heading, a styled checkbox row for "Subscribed", an editorial select for the
  timezone with a hint line ("Your daily prompt is sent in the morning, in this
  time zone."), and a green "Update settings" pill button.
- **Account** card: password-reset and logout forms presented as `ed-btn-ghost`
  outline pill buttons, with a hint line noting where the reset link is sent.
- Success / error messages become an **accented alert banner** — green
  left-border (`--accent`) for success, firebrick-red (`--danger`) for form
  errors — replacing the Bootstrap `alert` classes.

## Testing

Add Django `TestCase` tests in `core/tests.py`, matching the existing style
(`HomePageTests` is the model):

- Dashboard renders the editorial layout (`id="dashboard"`, `ed-card`, masthead)
  and loads `account.css`.
- `q` filters by content and by prompt question.
- `from` / `to` constrain the date range.
- `category` filters by prompt category.
- `sort=oldest` reverses order.
- Pagination caps a page at 25 entries and page 2 shows the next set.
- Pagination links preserve active filter parameters.
- Result count is absent on the unfiltered view and present when filtering.
- Filter `<details>` renders `open` when a filter is active.
- Empty-state messages: no entries vs. no matches.
- Settings page renders the editorial layout and loads `account.css`.

## Out of scope

- Changing `core/base.html` or removing Bootstrap from the project.
- Restyling other pages (auth pages already use the separate `auth.css`
  editorial system; privacy/terms unchanged).
- Any change to how entries are created, or to the `settings` view logic.
- Per-entry detail pages or editing entries.
