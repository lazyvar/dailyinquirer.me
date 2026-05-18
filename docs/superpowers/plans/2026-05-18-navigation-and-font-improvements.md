# Navigation & Font Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/` always render the marketing page (with an auth-aware CTA), move the logged-in dashboard to its own `/dash/` URL, and enlarge body/UI text across the home, auth, and signed-in pages.

**Architecture:** Split the dual-purpose `index` view into a public `index` (landing only) and a `@login_required` `dashboard` view at `/dash/`. The existing `OnboardingRequiredMiddleware` continues to gate un-onboarded users with no change. Font sizes are raised per-CSS-selector (no global root change) so headers stay as-is.

**Tech Stack:** Django 5 (Python 3.14), Django templates, plain CSS. Tests: `python manage.py test`.

---

## Background for the implementer

- `core/views.py:index` currently branches on auth state: confirmed users get `_dashboard(request)` (renders `core/index_logged_in.html`); anonymous users get `core/index.html` (marketing).
- `_dashboard(request)` is a plain helper (not a view) that builds the filtered/paginated entry list and renders `core/index_logged_in.html`. It stays unchanged throughout this plan.
- `core/middleware.py:OnboardingRequiredMiddleware` redirects any confirmed-but-not-onboarded authenticated user to `/onboarding/` on every non-exempt path. No change needed — it already covers both `/` and `/dash/`.
- `core/views.py` already imports everything needed: `login_required`, `logout`, `redirect`, `render`.
- Run the full suite with `python manage.py test` from the repo root. The settings default is `dailyinquirer.settings.local`.

---

## Task 1: Add the `/dash/` route and `dashboard` view

**Files:**
- Modify: `core/views.py` (add `dashboard` view after the `_dashboard` helper)
- Modify: `core/urls.py:7` (add the `dash/` path)
- Test: `core/tests.py` (append a new `DashboardRouteTests` class at the **end** of the file)

This task is purely additive — `index` still renders the dashboard for logged-in users, and `/dash/` becomes a second way to reach it. The whole suite stays green.

- [ ] **Step 1: Write the failing tests**

Append this class to the very end of `core/tests.py`:

```python
class DashboardRouteTests(TestCase):
    """The dashboard lives at its own /dash/ URL, gated by auth."""

    def _make_user(self, confirmed=True, onboarded=True):
        user = User.objects.create_user(
            email='router@example.com', password='mostdope1')
        user.confirmed_email = confirmed
        user.onboarded = onboarded
        user.save()
        return user

    def test_anonymous_dash_redirects_to_login(self):
        response = self.client.get(reverse('dash'))
        self.assertRedirects(response, '/login/?next=/dash/')

    def test_confirmed_onboarded_user_sees_dashboard(self):
        self.client.force_login(self._make_user())
        response = self.client.get(reverse('dash'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="dashboard"')

    def test_unconfirmed_user_is_logged_out_and_redirected(self):
        self.client.force_login(self._make_user(confirmed=False))
        response = self.client.get(reverse('dash'))
        self.assertRedirects(response, reverse('unconfirmed_email'))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.DashboardRouteTests`
Expected: FAIL — `django.urls.exceptions.NoReverseMatch: Reverse for 'dash' not found`.

- [ ] **Step 3: Add the `dashboard` view**

In `core/views.py`, add this function immediately after the `_dashboard` helper (the function ends with `return render(request, 'core/index_logged_in.html', context)`):

```python
@login_required
def dashboard(request):
    if not request.user.confirmed_email:
        logout(request)
        return redirect('unconfirmed_email')
    return _dashboard(request)
```

- [ ] **Step 4: Register the URL**

In `core/urls.py`, add the `dash/` path directly below the `index` path. The `urlpatterns` list begins:

```python
urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
```

Change it to:

```python
urlpatterns = [
    path('', views.index, name='index'),
    path('dash/', views.dashboard, name='dash'),
    path('register/', views.register, name='register'),
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python manage.py test core.tests.DashboardRouteTests`
Expected: PASS (3 tests).

- [ ] **Step 6: Run the full suite**

Run: `python manage.py test`
Expected: PASS — no regressions (`index` still serves the dashboard, so existing `DashboardTests` are unaffected).

- [ ] **Step 7: Commit**

```bash
git add core/views.py core/urls.py core/tests.py
git commit -m "Add /dash/ route and dashboard view"
```

---

## Task 2: Point the existing dashboard tests at `/dash/`

**Files:**
- Modify: `core/tests.py` (`DashboardTests` class and the `test_dashboard_renders_hard_wrapped_entry_without_inner_br` test)

`DashboardTests` and one test in `EntryContentUnwrapTests` currently fetch `reverse('index')` and expect dashboard markup. Move them onto `reverse('dash')` now, while both URLs still serve the dashboard, so the suite stays green when `index` is later converted to landing-only.

- [ ] **Step 1: Rewrite the `reverse('index')` calls in the dashboard test range**

`class DashboardTests` and the test `test_dashboard_renders_hard_wrapped_entry_without_inner_br` (inside `class EntryContentUnwrapTests`) both sit between the `class DashboardTests` line and the `class RepairMigrationHistoryTests` line. Every `reverse('index')` in that span refers to the dashboard. Replace them all:

Run: `sed -i '' "/^class DashboardTests/,/^class RepairMigrationHistoryTests/s/reverse('index')/reverse('dash')/g" core/tests.py`

(17 occurrences are replaced. No `reverse('index')` outside that span — `HomePageTests`, `FooterTests`, `OnboardingGateTests` — is touched.)

- [ ] **Step 2: Verify the replacement**

Run: `grep -n "reverse('index')\|reverse('dash')" core/tests.py`
Expected: every match between `class DashboardTests` and `class RepairMigrationHistoryTests` now reads `reverse('dash')`; matches in `HomePageTests`/`FooterTests`/`OnboardingGateTests` still read `reverse('index')`.

- [ ] **Step 3: Run the affected tests**

Run: `python manage.py test core.tests.DashboardTests core.tests.EntryContentUnwrapTests`
Expected: PASS — `/dash/` serves the dashboard for the confirmed, onboarded, logged-in user created in `DashboardTests.setUp`.

- [ ] **Step 4: Run the full suite**

Run: `python manage.py test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/tests.py
git commit -m "Move dashboard tests onto the /dash/ route"
```

---

## Task 3: Repoint redirects and internal links at `/dash/`

**Files:**
- Modify: `core/views.py` (`activate`, `onboarding`, `register`)
- Modify: `dailyinquirer/settings/base.py:105` (`LOGIN_REDIRECT_URL`)
- Modify: `core/templates/core/index_logged_in.html` (filter form action, clear links)
- Modify: `core/tests.py` (`OnboardingPageTests`, the `activate` comment, add a login-redirect test)

Every "go to your dashboard" path now points at the `dash` route. `index` still serves the dashboard for logged-in users at this point, so nothing breaks; the tests that assert these redirects are updated in the same commit.

> **Note (deviation from spec):** the design spec listed `activate`/`onboarding`/`register` but did not mention `LOGIN_REDIRECT_URL`. It currently points at `index`; leaving it would land users on the marketing page after login. Changing it to `dash` keeps the spec's intent ("all dashboard-bound paths point at `dash`"). This is included below.

- [ ] **Step 1: Write the failing login-redirect test**

Append this class to the end of `core/tests.py`:

```python
class LoginRedirectTests(TestCase):
    def test_login_sends_user_to_dashboard(self):
        user = User.objects.create_user(
            email='loginer@example.com', password='mostdope1')
        user.confirmed_email = True
        user.onboarded = True
        user.save()
        response = self.client.post(reverse('login'), {
            'username': 'loginer@example.com',
            'password': 'mostdope1',
        })
        self.assertRedirects(response, reverse('dash'))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test core.tests.LoginRedirectTests`
Expected: FAIL — the login redirects to `/` (index), not `/dash/`.

- [ ] **Step 3: Change `LOGIN_REDIRECT_URL`**

In `dailyinquirer/settings/base.py`, line 105 reads:

```python
LOGIN_REDIRECT_URL = 'index'
```

Change it to:

```python
LOGIN_REDIRECT_URL = 'dash'
```

- [ ] **Step 4: Repoint the view redirects**

In `core/views.py`, make these four edits.

`activate` — the success-path redirect:

old:
```python
        return redirect('index')
    else:
        return HttpResponse('Activation link is invalid!')
```
new:
```python
        return redirect('dash')
    else:
        return HttpResponse('Activation link is invalid!')
```

`register` — the already-authenticated guard:

old:
```python
    if request.user.is_authenticated:
        return redirect('index')
```
new:
```python
    if request.user.is_authenticated:
        return redirect('dash')
```

`onboarding` — the already-onboarded guard:

old:
```python
    if request.user.onboarded:
        return redirect('index')
```
new:
```python
    if request.user.onboarded:
        return redirect('dash')
```

`onboarding` — the post-save redirect:

old:
```python
            user.onboarded = True
            user.save()
            return redirect('index')
```
new:
```python
            user.onboarded = True
            user.save()
            return redirect('dash')
```

- [ ] **Step 5: Repoint the dashboard template's internal links**

In `core/templates/core/index_logged_in.html`, make these three edits.

Filter form action:

old: `  <form class="ed-filters" method="get" action="/">`
new: `  <form class="ed-filters" method="get" action="/dash/">`

Filter "Clear" link:

old: `        <a class="ed-filter-clear" href="/">Clear</a>`
new: `        <a class="ed-filter-clear" href="/dash/">Clear</a>`

Empty-state "Clear search and filters" link:

old: `      <p><a href="/">Clear search and filters</a></p>`
new: `      <p><a href="/dash/">Clear search and filters</a></p>`

- [ ] **Step 6: Update the onboarding tests**

In `core/tests.py`, `class OnboardingPageTests`, `test_post_completes_onboarding` — use this context block so the edit is unique (`reverse('index')` appears twice in this class):

old:
```python
        })
        self.assertRedirects(response, reverse('index'))
        self.user.refresh_from_db()
```
new:
```python
        })
        self.assertRedirects(response, reverse('dash'))
        self.user.refresh_from_db()
```

`test_already_onboarded_user_is_redirected_to_index` — rename it and fix the assertion:

old:
```python
    def test_already_onboarded_user_is_redirected_to_index(self):
        self.user.onboarded = True
        self.user.save()
        response = self.client.get(reverse('onboarding'))
        self.assertRedirects(response, reverse('index'))
```
new:
```python
    def test_already_onboarded_user_is_redirected_to_dashboard(self):
        self.user.onboarded = True
        self.user.save()
        response = self.client.get(reverse('onboarding'))
        self.assertRedirects(response, reverse('dash'))
```

- [ ] **Step 7: Update the stale comment in the activation test**

In `core/tests.py`, `EmailConfirmationTests.test_activation_link_confirms_email_and_logs_in`:

old:
```python
        # A freshly-confirmed user has not onboarded yet, so the index
        # redirect is itself gated onward to the onboarding page.
        self.assertRedirects(response, reverse('onboarding'))
```
new:
```python
        # A freshly-confirmed user has not onboarded yet, so the /dash/
        # redirect is itself gated onward to the onboarding page.
        self.assertRedirects(response, reverse('onboarding'))
```

- [ ] **Step 8: Run the affected tests**

Run: `python manage.py test core.tests.LoginRedirectTests core.tests.OnboardingPageTests core.tests.EmailConfirmationTests`
Expected: PASS.

- [ ] **Step 9: Run the full suite**

Run: `python manage.py test`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add core/views.py dailyinquirer/settings/base.py core/templates/core/index_logged_in.html core/tests.py
git commit -m "Point dashboard-bound redirects and links at /dash/"
```

---

## Task 4: Make `/` the landing page with an auth-aware CTA

**Files:**
- Modify: `core/views.py` (`index`)
- Modify: `core/templates/core/index.html` (CTA block)
- Modify: `core/tests.py` (`HomePageTests` — add a logged-in test, tighten an existing one)

Now `index` becomes landing-only. Because Tasks 2–3 already moved every dashboard-dependent test and redirect onto `/dash/`, this change breaks nothing.

- [ ] **Step 1: Write the failing test**

In `core/tests.py`, `class HomePageTests`, add this test (place it after `test_home_cta_links_are_correct`):

```python
    def test_logged_in_home_shows_dashboard_cta(self):
        user = User.objects.create_user(
            email='member@example.com', password='mostdope1')
        user.confirmed_email = True
        user.onboarded = True
        user.save()
        self.client.force_login(user)
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="home"')
        self.assertContains(response, 'Take me to dashboard')
        self.assertContains(response, 'href="/dash/"')
        self.assertNotContains(response, "Get started, it's free")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python manage.py test core.tests.HomePageTests.test_logged_in_home_shows_dashboard_cta`
Expected: FAIL — `index` still routes the logged-in user to the dashboard (`id="dashboard"`), so `id="home"` / "Take me to dashboard" are absent.

- [ ] **Step 3: Convert `index` to landing-only**

In `core/views.py`, replace the entire `index` function:

old:
```python
def index(request):
    if request.user.is_authenticated:
        if request.user.confirmed_email:
            return _dashboard(request)
        else:
            logout(request)
            return redirect('unconfirmed_email')
    else:
        return render(request, 'core/index.html')
```
new:
```python
def index(request):
    return render(request, 'core/index.html')
```

- [ ] **Step 4: Swap the CTA in the landing template**

In `core/templates/core/index.html`, the CTA block reads:

old:
```html
      <div class="ed-cta">
        <a class="ed-btn" href="/register/">Get started, it's free</a>
        <p class="ed-signin">Already registered? <a href="/login/">Log in.</a></p>
      </div>
```
new:
```html
      <div class="ed-cta">
        {% if user.is_authenticated %}
        <a class="ed-btn" href="/dash/">Take me to dashboard</a>
        {% else %}
        <a class="ed-btn" href="/register/">Get started, it's free</a>
        <p class="ed-signin">Already registered? <a href="/login/">Log in.</a></p>
        {% endif %}
      </div>
```

- [ ] **Step 5: Tighten the anonymous CTA test**

In `core/tests.py`, `class HomePageTests`, `test_home_cta_links_are_correct`:

old:
```python
    def test_home_cta_links_are_correct(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'href="/register/"')
        self.assertContains(response, 'href="/login/"')
```
new:
```python
    def test_home_cta_links_are_correct(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'href="/register/"')
        self.assertContains(response, 'href="/login/"')
        self.assertNotContains(response, 'Take me to dashboard')
```

- [ ] **Step 6: Run the home tests**

Run: `python manage.py test core.tests.HomePageTests`
Expected: PASS — anonymous visitors see the register/login CTA, logged-in visitors see "Take me to dashboard".

- [ ] **Step 7: Run the full suite**

Run: `python manage.py test`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add core/views.py core/templates/core/index.html core/tests.py
git commit -m "Make / the landing page with an auth-aware CTA"
```

---

## Task 5: Enlarge body and UI text

**Files:**
- Modify: `dailyinquirer/static/css/home.css`
- Modify: `dailyinquirer/static/css/account.css`
- Modify: `dailyinquirer/static/css/auth.css`

No global `:root` font-size change — that would scale headers. Each edit below raises one selector's `font-size`. Apply them with the `Edit` tool; the multi-line `old`/`new` blocks are chosen to be unique within each file. Headers and the small uppercase eyebrow labels are deliberately left alone.

Sizing rules applied: primary reading text → `1rem`; form inputs / selects / button labels → `0.95rem`; secondary & meta text → `0.875rem`.

- [ ] **Step 1: Edit `dailyinquirer/static/css/home.css`**

Edit A — `.ed-btn` button label:
old:
```
  font-size: 0.88rem;
  font-weight: 600;
```
new:
```
  font-size: 0.95rem;
  font-weight: 600;
```

Edit B — `.ed-signin` secondary line:
old:
```
  font-size: 0.78rem;
  color: var(--ink-faint);
```
new:
```
  font-size: 0.875rem;
  color: var(--ink-faint);
```

Edit C — `.ed-step p` step description:
old:
```
  font-size: 0.78rem;
  line-height: 1.5;
```
new:
```
  font-size: 1rem;
  line-height: 1.5;
```

Edit D — `.ed-text` prompt-card body:
old:
```
  font-size: 0.8rem;
  line-height: 1.5;
```
new:
```
  font-size: 1rem;
  line-height: 1.5;
```

Edit E — `.ed-about__text p` "why it exists" copy:
old:
```
  font-size: 0.9rem;
  line-height: 1.72;
```
new:
```
  font-size: 1rem;
  line-height: 1.72;
```

- [ ] **Step 2: Edit `dailyinquirer/static/css/account.css`**

Edit A — `.ed-masthead__email`:
old:
```
  font-size: 0.8rem;
  color: var(--ink-soft);
  margin: 8px 0 0;
```
new:
```
  font-size: 0.875rem;
  color: var(--ink-soft);
  margin: 8px 0 0;
```

Edit B — `.ed-card__sub`:
old:
```
  font-size: 0.82rem;
  line-height: 1.55;
```
new:
```
  font-size: 1rem;
  line-height: 1.55;
```

Edit C — `.ed-btn` button label:
old:
```
  font-size: 0.82rem;
  font-weight: 600;
```
new:
```
  font-size: 0.95rem;
  font-weight: 600;
```

Edit D — `.ed-btn-ghost` button label:
old:
```
  font-size: 0.8rem;
  font-weight: 600;
```
new:
```
  font-size: 0.95rem;
  font-weight: 600;
```

Edit E — `.ed-input` form field:
old:
```
  padding: 9px 11px;
  font-family: var(--body);
  font-size: 0.85rem;
```
new:
```
  padding: 9px 11px;
  font-family: var(--body);
  font-size: 0.95rem;
```

Edit F — `.ed-check` checkbox label:
old:
```
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--ink);
```
new:
```
  font-size: 1rem;
  line-height: 1.4;
  color: var(--ink);
```

Edit G — `.ed-hint`:
old:
```
  font-size: 0.74rem;
  line-height: 1.5;
  color: var(--ink-faint);
```
new:
```
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--ink-faint);
```

Edit H — `.ed-alert`:
old:
```
  font-size: 0.83rem;
  font-weight: 600;
```
new:
```
  font-size: 0.875rem;
  font-weight: 600;
```

Edit I — `#onboarding .ed-timeopt__time`:
old:
```
  font-size: 0.7rem;
  color: var(--ink-faint);
```
new:
```
  font-size: 0.875rem;
  color: var(--ink-faint);
```

Edit J — `#dashboard .ed-search` form field:
old:
```
  padding: 10px 12px;
  font-family: var(--body);
  font-size: 0.85rem;
```
new:
```
  padding: 10px 12px;
  font-family: var(--body);
  font-size: 0.95rem;
```

Edit K — `#dashboard .ed-filter-clear`:
old:
```
  font-size: 0.76rem;
  color: var(--ink-soft);
```
new:
```
  font-size: 0.875rem;
  color: var(--ink-soft);
```

Edit L — `#dashboard .ed-count`:
old:
```
  font-size: 0.74rem;
  color: var(--ink-faint);
  margin: 20px 0 0;
```
new:
```
  font-size: 0.875rem;
  color: var(--ink-faint);
  margin: 20px 0 0;
```

Edit M — `#dashboard .ed-entry__date`:
old:
```
  font-size: 0.72rem;
  color: var(--ink-faint);
  margin: 0 0 10px;
```
new:
```
  font-size: 0.875rem;
  color: var(--ink-faint);
  margin: 0 0 10px;
```

Edit N — `#dashboard .ed-entry__body`:
old:
```
  font-size: 0.9rem;
  line-height: 1.7;
```
new:
```
  font-size: 1rem;
  line-height: 1.7;
```

Edit O — `#dashboard .ed-page` pagination control:
old:
```
  font-size: 0.78rem;
  color: var(--ink-soft);
```
new:
```
  font-size: 0.875rem;
  color: var(--ink-soft);
```

Edit P — `.ed-empty p` empty-state copy:
old:
```
  font-size: 0.85rem;
  color: var(--ink-soft);
  margin: 0;
```
new:
```
  font-size: 1rem;
  color: var(--ink-soft);
  margin: 0;
```

Edit Q — `.ed-email-edit__action`:
old:
```
  font-size: 0.85rem;
  color: var(--ink-soft);
  text-decoration: underline;
```
new:
```
  font-size: 0.875rem;
  color: var(--ink-soft);
  text-decoration: underline;
```

- [ ] **Step 3: Edit `dailyinquirer/static/css/auth.css`**

Edit A — `.auth-subtitle`:
old:
```
  font-size: 0.85rem;
  line-height: 1.6;
```
new:
```
  font-size: 1rem;
  line-height: 1.6;
```

Edit B — `.auth-fineprint`:
old:
```
  font-size: 0.72rem;
  line-height: 1.55;
```
new:
```
  font-size: 0.875rem;
  line-height: 1.55;
```

Edit C — `.auth-input` form field:
old:
```
  font-size: 0.9rem;
  color: var(--ink);
  background: var(--paper);
```
new:
```
  font-size: 0.95rem;
  color: var(--ink);
  background: var(--paper);
```

Edit D — `.auth-btn` button label:
old:
```
  font-size: 0.88rem;
  font-weight: 600;
```
new:
```
  font-size: 0.95rem;
  font-weight: 600;
```

Edit E — `.auth-forgot`:
old:
```
  font-size: 0.78rem;
  color: var(--accent);
```
new:
```
  font-size: 0.875rem;
  color: var(--accent);
```

Edit F — `.auth-alt`:
old:
```
  font-size: 0.82rem;
  color: var(--ink-soft);
```
new:
```
  font-size: 0.875rem;
  color: var(--ink-soft);
```

Edit G — `.auth-error p`:
old:
```
  font-size: 0.8rem;
  color: var(--danger);
```
new:
```
  font-size: 0.875rem;
  color: var(--danger);
```

- [ ] **Step 4: Run the full suite (regression check)**

Run: `python manage.py test`
Expected: PASS — these are CSS-only changes; no test asserts a `font-size`.

- [ ] **Step 5: Eyeball the pages**

Start the server (`python manage.py runserver`) and visually confirm body text is noticeably larger while headers are unchanged on: `/` (logged out and logged in), `/login/`, `/register/`, `/dash/`, `/settings/`, `/onboarding/`.

- [ ] **Step 6: Commit**

```bash
git add dailyinquirer/static/css/home.css dailyinquirer/static/css/account.css dailyinquirer/static/css/auth.css
git commit -m "Increase body and UI font sizes across home, auth, and account pages"
```

---

## Self-review notes

- **Spec coverage:** routing split (Tasks 1, 3, 4), auth-aware CTA (Task 4), `/dash/` URL (Task 1), redirect updates incl. `LOGIN_REDIRECT_URL` (Task 3 — flagged as a spec gap), unconfirmed-at-`/dash/` guard (Task 1), font rules for primary/control/secondary text (Task 5), test migration + new tests (Tasks 1–4). All spec sections map to a task.
- **`_masthead.html` / `_footer.html`:** unchanged, as the spec specifies — their site-name links stay pointing at `/`.
- **Middleware:** unchanged, as the spec specifies.
- **`styles.css`:** untouched. Its global `p { font-size: 0.85em }` is overridden by the higher-specificity scoped selectors on the home/dashboard pages and is not loaded at all by `auth_base.html`, so it does not affect the in-scope pages.
