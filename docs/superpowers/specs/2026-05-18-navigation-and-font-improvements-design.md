# Navigation & Font Improvements — Design

Date: 2026-05-18
Branch: navigation-improvements

## Goals

Two independent improvements to the public/logged-in pages:

1. **Larger body text.** Body and UI text currently sits at ~13–14px and reads
   too small. Bump it to a comfortable size without touching headers.
2. **Stable root page.** `/` currently renders different content depending on
   auth state (marketing page vs. dashboard). Make `/` always render the
   marketing page, move the dashboard to its own URL `/dash/`, and adapt the
   marketing call-to-action for logged-in visitors.

## Part 1 — Routing split

### Current behaviour

- `core/urls.py`: `path('', views.index, name='index')` is the only entry point.
- `core/views.py:index` branches on auth state:
  - authenticated + `confirmed_email` → `_dashboard(request)` (renders
    `core/index_logged_in.html`).
  - authenticated + not confirmed → `logout()` + redirect to
    `unconfirmed_email`.
  - anonymous → renders `core/index.html` (marketing).
- `core/middleware.py:OnboardingRequiredMiddleware` already redirects every
  confirmed-but-not-onboarded user to `/onboarding/` on all non-exempt paths.

### Target behaviour

- **`index` view** becomes purely the public landing page: it always renders
  `core/index.html`, with no auth branching. URL stays `path('', views.index,
  name='index')`.
- **New `dashboard` view** at `path('dash/', views.dashboard, name='dash')`:
  - decorated `@login_required`;
  - keeps the confirmed-email guard — if `not request.user.confirmed_email`,
    call `logout(request)` and redirect to `unconfirmed_email`;
  - otherwise delegates to the existing `_dashboard(request)` helper (unchanged).
- **`core/index.html` CTA** swaps on `{% if user.is_authenticated %}`:
  - logged-in → a single button labelled **"Take me to dashboard"** linking to
    `/dash/`; the "Already registered? Log in." line is hidden.
  - anonymous → unchanged: "Get started, it's free" button (`/register/`) plus
    the "Already registered? Log in." line (`/login/`).
- **`core/index_logged_in.html`** internal links change `/` → `/dash/`:
  - the filter `<form ... action="/">` → `action="/dash/"`;
  - the `ed-filter-clear` "Clear" link;
  - the empty-state "Clear search and filters" link.
  - Pagination links already use relative `?page=…` URLs, so they remain on
    `/dash/` with no change.
- **View redirects** that previously meant "go to the home/dashboard" now point
  at the `dash` route:
  - `activate` — after `login()`, redirect to `dash` instead of `index`;
  - `onboarding` — the post-finish redirect and the already-onboarded guard
    redirect to `dash` instead of `index`;
  - `register` — the already-authenticated guard redirects to `dash` instead of
    `index`.
  - The `OnboardingRequiredMiddleware` still intercepts un-onboarded users, so
    the activation flow correctly chains: activate → `/dash/` → `/onboarding/`.
- **No change** to `_masthead.html` (site-name link → `/`) or `_footer.html`
  (wordmark → `/`). The landing page is an acceptable "home" for a logged-in
  user, who gets a one-click "Take me to dashboard" button there.
- **No change** to `OnboardingRequiredMiddleware` or `LogoutView` (`next_page`
  stays `/`, which is the landing page).

### Edge cases

- Anonymous visitor to `/dash/` → `@login_required` redirects to the login page.
- Authenticated-but-unconfirmed visitor to `/dash/` → the view's confirmed-email
  guard logs them out and redirects to `unconfirmed_email` (preserves the old
  `index` behaviour, just relocated).
- Authenticated-but-unconfirmed visitor to `/` → simply sees the landing page
  (the old forced logout at `/` is dropped; it is handled at `/dash/` instead).
- Confirmed-but-not-onboarded visitor to `/` or `/dash/` → middleware redirects
  to `/onboarding/`, unchanged.

## Part 2 — Font sizes

No global `:root` font-size change — that would scale headers too, and headers
are already the right size. Instead, raise the per-element `rem` values in
`home.css`, `account.css`, and `auth.css` according to these rules:

- **Primary reading text → `1rem` (16px):** paragraphs, entry bodies, the
  "about" text, prompt-card body text, "how it works" step descriptions, card
  subtitles, empty-state body text.
- **Form inputs, selects & button labels → ~`0.95rem`:** keeps controls
  proportionate to the larger surrounding text.
- **Secondary / meta text → ~`0.875rem` (14px):** dates, hints, fineprint, the
  entry count line, the "Already registered? Log in." line, alert text.
- **Left untouched:**
  - all headers — masthead names, `auth-title`, `ed-card__head`,
    `ed-entry__q`, `ed-step h3`, `ed-empty h2`, `ed-final__title`,
    `ed-welcome`;
  - the small uppercase letter-spaced eyebrow labels — `ed-label`, `ed-genre`,
    `ed-entry__cat`, `ed-masthead__tab`, `ed-field__label`, `auth-label`,
    `ed-filter-toggle` — these are intentional small caps, not body text.

The exact selector-by-selector mapping is left to the implementation plan; the
rules above are the contract.

## Tests

`core/tests.py`:

- `DashboardTests` currently call `reverse('index')` and assert dashboard
  markup (`id="dashboard"`, filtering, pagination, etc.). Switch every such
  call to `reverse('dash')`.
- Any test asserting that a logged-in user at `reverse('index')` sees the
  dashboard must move to `reverse('dash')`.
- `HomePageTests` (anonymous `reverse('index')`) stay valid — anonymous users
  still see the marketing page with register/login CTAs.
- New tests:
  - anonymous GET `/dash/` → redirects to the login page;
  - logged-in (confirmed, onboarded) GET `/` → 200, renders the marketing page
    and contains the "Take me to dashboard" link to `/dash/`;
  - anonymous GET `/` → still contains `href="/register/"` and `href="/login/"`.

Lambda tests (`infra/inbound-email/lambda`) are unaffected.

## Out of scope

- No redesign of the dashboard or marketing layouts beyond the CTA swap.
- No global typography token system; font changes are per-selector edits.
- No changes to email templates (`daily_email.html`).
