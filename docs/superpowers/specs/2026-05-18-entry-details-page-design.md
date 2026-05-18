# Entry detail page — design

## Summary

Add a per-entry detail page. A subscriber clicks one of their entries on the
dashboard and lands on a page showing the prompt, their full reply, and when the
entry was added and last updated. From the page they can edit the reply, archive
the entry, or permanently delete it.

Today entries are created only by inbound email reply (`core.views.on_incoming_message`),
have no individual page, no way to edit, and no archive concept. This feature
adds all of that.

## Goals

- A detail page for a single `Entry`, reachable by clicking an entry card.
- Edit the entry's reply text.
- Archive an entry (soft delete) and restore it later.
- Permanently delete an entry, behind a confirmation step.
- Show "added" (`pub_date`) and "last updated" (`updated_at`) timestamps.
- Success and error feedback for save, archive, restore, and delete.

## Non-goals

- Editing the prompt question or category — prompts are shared across all
  recipients, so they are not user-editable.
- Editing `pub_date`.
- Creating entries from the web — entries still originate from email replies.
- Bulk actions on multiple entries.

## Approach: server-rendered, no JavaScript

The site has effectively no JavaScript (`static/js/hack.js` is cosmetic only),
and the settings page already implements inline editing with pure-CSS
`<details>`/`<summary>` (`.ed-email-edit`). The detail page follows the same
style:

- The "⋯" overflow menu is a `<details>` dropdown — no JS.
- Edit mode and the delete-confirmation panel are reached by re-rendering the
  same page with a query-string flag.

This keeps the feature consistent with the existing codebase and avoids
introducing a JS toolchain.

## Layout

Single-column "article" layout (selected from mockups). Top to bottom:

1. Back link — "‹ Your writing" → dashboard.
2. A card containing:
   - "⋯" overflow menu in the top-right corner (`<details>` dropdown).
   - Category eyebrow (only when `prompt.category` is set).
   - Prompt question as the headline.
   - Meta line: "Added May 12, 2026 · Last updated May 14, 2026".
   - Horizontal rule.
   - The reply body, rendered with the existing `unwrap`/`linebreaks` filters.

The overflow menu items depend on entry state:

- Active entry: **Edit entry**, **Archive**, **Delete**.
- Archived entry: **Edit entry**, **Restore**, **Delete**.

**Edit mode** (`?edit=1`): the reply body is replaced in place by a labeled
`<textarea>` pre-filled with `entry.content`, plus **Save changes** and
**Cancel** buttons. The prompt question and meta line stay visible and
read-only.

**Delete confirmation** (`?confirm_delete=1`): the reply body is replaced in
place by a red `.ed-alert--error`-style panel — "Delete this entry? This
permanently removes your reply. This can't be undone — if you only want it out
of the way, archive it instead." — with **Delete permanently** and **Cancel**
buttons.

## Data model

Add one field to `core.models.Entry`:

```python
archived_at = models.DateTimeField(null=True, blank=True, default=None)
```

`null` means the entry is active; a timestamp means it is archived. Storing a
timestamp rather than a boolean records *when* the entry was archived at no
extra cost, letting the archived list sort by most-recently-archived.

One migration adds the column. The existing `(author, -pub_date)` index still
serves the dashboard query. Archived lists are small, so no new index is added.

## URLs and views

| URL | Name | Purpose |
|---|---|---|
| `/entry/<int:pk>/` | `entry_detail` | GET: view / edit / confirm-delete modes. POST: action dispatch. |
| `/archived/` | `archived_entries` | GET: list of the user's archived entries. |

### `entry_detail(request, pk)` — `@login_required`

Loads the entry with
`get_object_or_404(Entry.objects.select_related('prompt'), pk=pk, author=request.user)`.
Scoping the lookup to `author=request.user` means a non-owner or a missing
entry both get a plain 404 — the page never reveals that an entry exists.

**GET** renders `core/entry_detail.html`. The render mode comes from the query
string:

- `?edit=1` → edit form.
- `?confirm_delete=1` → delete-confirmation panel.
- otherwise → read view.

**POST** dispatches on an `action` form field (same pattern as
`manage_email_change`):

- `save` — validated by a new `EntryEditForm` (single required `content`
  field). Valid: update `entry.content`, save (`updated_at` auto-bumps via
  `TimestampedModel`), `messages.success("Your entry was updated.")`, redirect
  to the detail page. Invalid (empty/whitespace content): re-render edit mode
  with an inline `.ed-alert--error`.
- `archive` — set `archived_at = timezone.now()`, save,
  `messages.success("Entry archived.")`, redirect to the dashboard.
- `restore` — set `archived_at = None`, save,
  `messages.success("Entry restored.")`, redirect to the detail page.
- `delete` — `entry.delete()`, `messages.success("Entry deleted.")`, redirect
  to the dashboard. `Entry`'s outgoing foreign keys use `on_delete=PROTECT`,
  but no protected relations point *at* `Entry`, so a hard delete succeeds.
- unknown/missing action → `HttpResponseBadRequest`.

A POST to `entry_detail` with a method other than GET/POST → `HttpResponseNotAllowed`.

### `archived_entries(request)` — `@login_required`

Lists entries where `author=request.user` and `archived_at__isnull=False`,
ordered by `-archived_at` (most recently archived first). Renders
`core/archived.html`.

## Dashboard integration

`core.views._dashboard`:

- The base queryset gains `.filter(archived_at__isnull=True)` so archived
  entries drop off the dashboard.
- A small "Archived (N)" link to `/archived/` is added near the entry count,
  where N is the user's archived-entry count. The link is shown only when
  N > 0.

## Templates

- **`core/entry_detail.html`** (new) — the article layout described above, with
  read / edit / confirm-delete modes.
- **`core/archived.html`** (new) — the archived ("Trash") list: entry cards each
  with Restore and Delete actions, plus a link back to the dashboard. Shows an
  empty state when the user has no archived entries.
- **`core/_entry_card.html`** (new partial) — the entry card markup, extracted
  from `core/index_logged_in.html` so the dashboard and the archived list share
  one definition. Each card links to `/entry/<pk>/`.
- **`core/index_logged_in.html`** — updated to use the `_entry_card.html`
  partial and to render flash messages.
- Flash messages are rendered with the existing `.ed-alert--ok` /
  `.ed-alert--error` classes on the dashboard, detail, and archived templates.

## Icons

Create `static/img/icons.svg` as a one-time Feather-icons SVG sprite containing
`<symbol>` definitions for the icons used: `more-vertical`, `edit-2`, `archive`,
`trash-2`, `chevron-left`, `rotate-ccw`. Templates reference symbols with
`<use href="/static/img/icons.svg#archive">`. Self-hosted, one cacheable file,
no CDN request — consistent with the project's self-hosted-fonts preference.

## CSS

A new `#entry`-scoped section is appended to
`dailyinquirer/static/css/account.css`, which already scopes `#dashboard`,
`#settings`, and `#onboarding`. It reuses existing tokens and the `.ed-card`,
`.ed-btn`, `.ed-btn-ghost`, `.ed-alert` components, and adds styling for the
overflow menu, the meta line, the edit textarea, the delete-confirm panel, and
icon sizing.

## Error handling

- Non-owner or missing entry → 404 (does not leak existence).
- Anonymous user → redirected to login by `@login_required`.
- Empty/whitespace-only content on save → form invalid, edit mode re-rendered
  with an inline error alert; the entry is not changed.
- Unknown or missing `action` on POST → `HttpResponseBadRequest`.
- Disallowed HTTP method → `HttpResponseNotAllowed`.
- Archive of an already-archived entry / restore of an active entry → harmless;
  the field is simply set to the same effective value.
- Permanent delete is reachable only through the `?confirm_delete=1` step.

## Testing

Test-driven. A new test class in `core/tests.py` covers:

- Detail page renders for the entry's author.
- 404 for a non-owner; login redirect for an anonymous visitor.
- Edit saves new content and bumps `updated_at`.
- Empty/whitespace content is rejected and leaves the entry unchanged.
- Archive sets `archived_at` and removes the entry from the dashboard.
- The archived entry appears in `/archived/`.
- Restore clears `archived_at` and the entry returns to the dashboard.
- Delete removes the row from the database.
- Delete requires the confirmation step.
- Success flash messages appear after save, archive, restore, and delete.
- Unknown POST action → 400.
