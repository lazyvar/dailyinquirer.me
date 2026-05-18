# Site nav component — design

**Date:** 2026-05-18
**Status:** Approved

## Problem

The top-of-page navigation is inconsistent across the logged-in app:

- `_masthead.html` (brand card with a single green "tab" label) appears on the
  dashboard, settings, and archived pages, but **not** on entry detail or about.
- Entry detail and archived use a separate `ed-detail-back` link that always
  points at the dashboard.
- The about page has no masthead at all — a plain `about-page` layout.

There is no single component expressing "where am I, and how do I get back up".

## Solution

One reusable nav component: a **breadcrumb rendered as connected folder-tabs**,
sitting on top of the existing masthead brand card.

- The trail is the path from the root to the current page.
- Ancestor crumbs are muted, clickable pills that link upward.
- The current page is the green connected tab (the existing single-tab look).
- There is **no back button** — the ancestor pills are the way up.
- The masthead card below the tabs (brand title + email subtitle) is unchanged.

This replaces both the ad-hoc `tab` parameter on `_masthead.html` and the
`ed-detail-back` link.

## Hierarchy

Each page declares a trail. The last crumb is the current page (green,
not a link); all earlier crumbs are muted links.

| Page          | Trail                                              |
|---------------|----------------------------------------------------|
| Dashboard     | `Your writing`                                     |
| Settings      | `Your writing` › `Settings`                        |
| Archived list | `Your writing` › `Archived`                        |
| Entry (active)| `Your writing` › `<date>`                          |
| Entry (archived)| `Your writing` › `Archived` › `<date>`           |
| About         | `About` (standalone — single crumb)                |

- The entry crumb label is `entry.pub_date` formatted `M j, Y`
  (e.g. `May 12, 2026`).
- The `Archived` crumb is inserted into an entry's trail only when
  `entry.archived_at` is set.
- About is always a single standalone crumb, identical logged in or out.

URL names used for ancestor links: `dash`, `archived_entries`. The `Your writing`
crumb links to `dash`; `Archived` links to `archived_entries`.

## Components

### 1. Trail builder + template tag

`core/templatetags/sitenav.py` — a custom **inclusion tag**:

```
{% sitenav 'dashboard' %}
{% sitenav 'settings' %}
{% sitenav 'archived' %}
{% sitenav 'entry' entry=entry %}
{% sitenav 'about' %}
```

The tag holds the page → trail hierarchy in **one** Python function (single
source of truth). It builds a list of crumbs — each `{label, url, current}` —
and renders the partial. No view needs to assemble breadcrumb data.

- For `'entry'`, the tag inspects `entry.archived_at` to decide whether to
  insert the `Archived` crumb, and formats `entry.pub_date` for the label.
- The current (last) crumb has no `url`.

### 2. Partial

`core/templates/core/_sitenav.html` — renders:

- the tab row: ancestor crumbs as `<a>` muted pills, the current crumb as a
  `<span>` green tab;
- the masthead brand card below (brand title linking to `/dash/` when
  authenticated else `/`, plus the email subtitle when a user is present).

This partial absorbs the markup currently in `_masthead.html`. The old
`tab` parameter is removed. `_masthead.html` is deleted (its includes are
replaced by `{% sitenav %}`).

### 3. Styles

`dailyinquirer/static/css/sitenav.css` — new, self-contained, loaded globally
in `base.html`. **Not** scoped under `.app`, because the about page is not an
`.app` page. Masthead/tab rules currently in `account.css` (`.ed-masthead*`)
and the back-link rules (`.ed-detail-back`) move here or are removed.

The `.ed-masthead*` rules and the `.ed-detail-back` rules are removed from
`account.css`; their replacements live in `sitenav.css`. The landing page
(`/`, `index.html`, `#home`) keeps its own hero masthead in `home.css` — its
`#home .ed-masthead*` rules are a separate, out-of-scope set and are untouched.

## Affected templates

Add `{% sitenav %}` (load the tag library at top of each template):

- `core/templates/core/index_logged_in.html` — replace masthead include.
- `core/templates/core/settings.html` — replace masthead include.
- `core/templates/core/archived.html` — replace masthead include; remove the
  `ed-detail-back` link.
- `core/templates/core/entry_detail.html` — add the nav (currently has none);
  remove the `ed-detail-back` link.
- `core/templates/core/about.html` — add the nav; the page keeps its body
  content but gains the masthead + tab.

## Edge & responsive behavior

- The tab row never wraps. On a narrow screen a deep trail scrolls
  horizontally, preserving the connected-tab appearance.
- Logged-out about page: the masthead shows no email line; the brand title
  links to `/`.
- A single-crumb trail (dashboard, about) renders exactly like today's
  single-tab masthead — no visual regression.

## Testing

- Template tag unit tests (`core/tests`): trail contents for each page type;
  archived vs. active entry; entry label formatting.
- Render checks: each affected page renders with the expected current crumb
  and ancestor links; about renders both authenticated and anonymous.
- `python manage.py test` is the CI gate and must pass.

## Out of scope

- The landing page hero (`/`).
- `terms`, `privacy`, `onboarding`, registration/auth pages — not part of the
  in-app hierarchy.
- Any change to the masthead brand card content beyond what is described.
