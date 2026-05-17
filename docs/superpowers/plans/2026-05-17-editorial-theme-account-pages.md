# Editorial Theme for Account Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the logged-in dashboard and settings pages onto the home page's editorial theme, and give the dashboard search, filtering, and pagination.

**Architecture:** A new scoped stylesheet (`account.css`) and a shared masthead template partial provide the editorial look. The settings page is a template-only restyle. The dashboard's `index` view is refactored to delegate to a `_dashboard` helper that filters entries by GET parameters and paginates them with Django's `Paginator`. All interaction is plain server-rendered HTML — GET forms plus a native `<details>` element. No JavaScript.

**Tech Stack:** Django, Django templates, vanilla CSS (consuming the existing `tokens.css` custom properties).

**Spec:** `docs/superpowers/specs/2026-05-17-editorial-theme-account-pages-design.md`

---

## File Structure

- **Create** `dailyinquirer/static/css/account.css` — editorial stylesheet for both account pages, every selector scoped under `.app` / `#dashboard` / `#settings`.
- **Create** `core/templates/core/_masthead.html` — shared masthead partial, takes a `tab` variable.
- **Modify** `core/templates/core/settings.html` — replace Bootstrap markup with editorial markup.
- **Modify** `core/templates/core/index_logged_in.html` — replace Bootstrap markup with editorial markup; add the filter form, pagination, and result count.
- **Modify** `core/views.py` — refactor `index`, add the `_dashboard` helper.
- **Modify** `core/tests.py` — add `DashboardTests` and `SettingsPageTests`.

Run tests with: `python manage.py test core` (run from the repo root, `/Users/mack/Developer/di3`).

---

## Task 1: Create the `account.css` stylesheet

**Files:**
- Create: `dailyinquirer/static/css/account.css`

- [ ] **Step 1: Create the stylesheet**

Create `dailyinquirer/static/css/account.css` with exactly this content:

```css
/* ============================================================
   ACCOUNT PAGES — dashboard & settings
   Editorial theme. All selectors scoped under .app / #dashboard /
   #settings so styles cannot leak. Consumes tokens from tokens.css.
   ============================================================ */

.app {
  padding-top: 40px;
  padding-bottom: 24px;
}

/* --- Masthead ----------------------------------------------- */

.app .ed-masthead {
  position: relative;
  margin: 12px 0 8px;
  background: #fff;
  border: 1px solid var(--rule);
  border-bottom: 3px solid var(--accent);
  border-radius: 8px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
  padding: 26px 24px;
}

.app .ed-masthead__tab {
  position: absolute;
  bottom: 100%;
  left: 22px;
  margin-bottom: -1px;
  padding: 7px 16px;
  background: var(--accent);
  color: #fff;
  font-family: var(--body);
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  border-radius: 7px 7px 0 0;
}

.app .ed-masthead__name {
  font-family: var(--serif);
  font-size: clamp(1.7rem, 5.5vw, 2.4rem);
  font-weight: 400;
  line-height: 1.05;
  letter-spacing: -0.01em;
  margin: 0;
}

.app .ed-masthead__name a {
  color: var(--ink);
  text-decoration: none;
}

.app .ed-masthead__email {
  font-family: var(--body);
  font-size: 0.8rem;
  color: var(--ink-soft);
  margin: 8px 0 0;
}

.app .ed-masthead__email a {
  color: var(--accent);
  text-decoration: none;
}

.app .ed-masthead__email a:hover {
  text-decoration: underline;
}

/* --- Section label ------------------------------------------ */

.app .ed-label {
  font-family: var(--body);
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  color: var(--ink-faint);
  margin: 28px 0 14px;
}

/* --- Card --------------------------------------------------- */

.app .ed-card {
  background: #fff;
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 22px 20px;
  margin-bottom: 14px;
}

.app .ed-card:last-child {
  margin-bottom: 0;
}

.app .ed-card__head {
  font-family: var(--serif);
  font-size: 1.15rem;
  font-weight: 400;
  color: var(--ink);
  margin: 0 0 4px;
}

.app .ed-card__sub {
  font-family: var(--body);
  font-size: 0.82rem;
  line-height: 1.55;
  color: var(--ink-soft);
  margin: 0 0 18px;
}

/* --- Buttons ------------------------------------------------ */

.app .ed-btn {
  display: inline-block;
  padding: 11px 24px;
  background: var(--accent);
  color: #fff;
  font-family: var(--body);
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-decoration: none;
  border: 0;
  border-radius: 9999px;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}

.app .ed-btn:hover,
.app .ed-btn:focus {
  background: var(--accent-dark);
  color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(var(--accent-rgb), 0.28);
}

.app .ed-btn-ghost {
  display: inline-block;
  padding: 10px 22px;
  background: #fff;
  color: var(--ink);
  font-family: var(--body);
  font-size: 0.8rem;
  font-weight: 600;
  text-decoration: none;
  border: 1px solid var(--rule);
  border-radius: 9999px;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.app .ed-btn-ghost:hover,
.app .ed-btn-ghost:focus {
  border-color: var(--accent);
  color: var(--accent);
}

/* --- Form fields -------------------------------------------- */

.app .ed-field {
  margin-bottom: 18px;
}

.app .ed-field:last-child {
  margin-bottom: 0;
}

.app .ed-field__label {
  display: block;
  font-family: var(--body);
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.13em;
  color: var(--ink-faint);
  margin-bottom: 6px;
}

.app .ed-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 9px 11px;
  font-family: var(--body);
  font-size: 0.85rem;
  color: var(--ink);
  background: #fff;
}

.app .ed-input:focus {
  outline: none;
  border-color: var(--accent);
}

.app .ed-check {
  display: flex;
  gap: 9px;
  align-items: flex-start;
  font-family: var(--body);
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--ink);
}

.app .ed-check input {
  accent-color: var(--accent);
  width: 16px;
  height: 16px;
  margin-top: 1px;
  flex-shrink: 0;
}

.app .ed-hint {
  font-family: var(--body);
  font-size: 0.74rem;
  line-height: 1.5;
  color: var(--ink-faint);
  margin: 8px 0 0;
}

.app .ed-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.app .ed-actions form {
  margin: 0;
}

/* --- Alert -------------------------------------------------- */

.app .ed-alert {
  font-family: var(--body);
  font-size: 0.83rem;
  font-weight: 600;
  border-radius: 6px;
  padding: 11px 14px;
  margin-bottom: 14px;
}

.app .ed-alert--ok {
  background: rgba(var(--accent-rgb), 0.05);
  border: 1px solid var(--accent);
  border-left-width: 3px;
  color: var(--accent-dark);
}

.app .ed-alert--error {
  background: rgba(var(--danger-rgb), 0.05);
  border: 1px solid var(--danger);
  border-left-width: 3px;
  color: var(--danger);
}

/* --- Dashboard: filter bar ---------------------------------- */

#dashboard .ed-filters {
  margin-top: 18px;
}

#dashboard .ed-search-row {
  display: flex;
  gap: 8px;
}

#dashboard .ed-search {
  flex: 1;
  box-sizing: border-box;
  border: 1px solid var(--rule);
  border-radius: 6px;
  padding: 10px 12px;
  font-family: var(--body);
  font-size: 0.85rem;
  color: var(--ink);
  background: #fff;
}

#dashboard .ed-search:focus {
  outline: none;
  border-color: var(--accent);
}

#dashboard .ed-filter-disclosure {
  margin-top: 10px;
}

#dashboard .ed-filter-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  font-family: var(--body);
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent);
  list-style: none;
}

#dashboard .ed-filter-toggle::-webkit-details-marker {
  display: none;
}

#dashboard .ed-filter-toggle::after {
  content: "\25be";
  font-size: 0.7rem;
}

#dashboard .ed-filter-disclosure[open] .ed-filter-toggle::after {
  content: "\25b4";
}

#dashboard .ed-filter-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  margin-top: 12px;
  padding: 16px;
  border: 1px solid var(--rule);
  border-radius: 8px;
}

#dashboard .ed-filter-panel .ed-field {
  margin-bottom: 0;
}

#dashboard .ed-filter-panel .ed-input {
  width: auto;
}

#dashboard .ed-filter-clear {
  align-self: center;
  font-family: var(--body);
  font-size: 0.76rem;
  color: var(--ink-soft);
  text-decoration: underline;
}

#dashboard .ed-filter-clear:hover {
  color: var(--accent);
}

#dashboard .ed-count {
  font-family: var(--body);
  font-size: 0.74rem;
  color: var(--ink-faint);
  margin: 20px 0 0;
}

#dashboard .ed-count b {
  color: var(--ink);
  font-weight: 700;
}

/* --- Dashboard: entries ------------------------------------- */

#dashboard .ed-entry {
  margin: 14px 0 0;
}

#dashboard .ed-entry__cat {
  font-family: var(--body);
  font-size: 0.64rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent);
  margin: 0 0 6px;
}

#dashboard .ed-entry__q {
  font-family: var(--serif);
  font-size: 1.15rem;
  font-weight: 400;
  color: var(--ink);
  line-height: 1.25;
  margin: 0 0 4px;
}

#dashboard .ed-entry__date {
  font-family: var(--body);
  font-size: 0.72rem;
  color: var(--ink-faint);
  margin: 0 0 10px;
}

#dashboard .ed-entry__body {
  font-family: var(--body);
  font-size: 0.9rem;
  line-height: 1.7;
  color: var(--ink-soft);
}

#dashboard .ed-entry__body p {
  margin: 0 0 0.8em;
}

#dashboard .ed-entry__body p:last-child {
  margin-bottom: 0;
}

/* --- Dashboard: pagination ---------------------------------- */

#dashboard .ed-pagination {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--rule);
}

#dashboard .ed-page {
  min-width: 34px;
  text-align: center;
  padding: 7px 10px;
  font-family: var(--body);
  font-size: 0.78rem;
  color: var(--ink-soft);
  text-decoration: none;
  border: 1px solid var(--rule);
  border-radius: 6px;
}

#dashboard .ed-page:hover {
  border-color: var(--accent);
  color: var(--accent);
}

#dashboard .ed-page.is-current {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  font-weight: 700;
}

#dashboard .ed-page.is-disabled,
#dashboard .ed-page.is-disabled:hover {
  color: var(--ink-faint);
  border-color: var(--rule);
  border-style: dashed;
}

/* --- Empty state -------------------------------------------- */

.app .ed-empty {
  background: #fff;
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 40px 24px;
  text-align: center;
  margin-top: 14px;
}

.app .ed-empty h2 {
  font-family: var(--serif);
  font-size: 1.2rem;
  font-weight: 400;
  color: var(--ink);
  margin: 0 0 8px;
}

.app .ed-empty p {
  font-family: var(--body);
  font-size: 0.85rem;
  color: var(--ink-soft);
  margin: 0;
}

.app .ed-empty a {
  color: var(--accent);
}

/* --- Responsive --------------------------------------------- */

@media (max-width: 480px) {
  .app .ed-masthead {
    padding: 22px 18px;
  }

  #dashboard .ed-search-row {
    flex-direction: column;
  }

  #dashboard .ed-filter-panel .ed-field,
  #dashboard .ed-filter-panel .ed-input {
    width: 100%;
  }
}

/* --- Reduced motion ----------------------------------------- */

@media (prefers-reduced-motion: reduce) {
  .app .ed-btn,
  .app .ed-btn-ghost {
    transition: none;
  }

  .app .ed-btn:hover,
  .app .ed-btn:focus {
    transform: none;
  }
}
```

- [ ] **Step 2: Verify the project still starts**

Run: `python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Commit**

```bash
git add dailyinquirer/static/css/account.css
git commit -m "Add account.css editorial stylesheet for logged-in pages

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Create the shared masthead partial

**Files:**
- Create: `core/templates/core/_masthead.html`

- [ ] **Step 1: Create the partial**

Create `core/templates/core/_masthead.html` with exactly this content:

```html
<header class="ed-masthead">
  <span class="ed-masthead__tab">{{ tab }}</span>
  <h1 class="ed-masthead__name"><a href="/">The Daily Inquirer</a></h1>
  <p class="ed-masthead__email"><a href="/settings/">{{ user.email }}</a></p>
</header>
```

- [ ] **Step 2: Commit**

```bash
git add core/templates/core/_masthead.html
git commit -m "Add shared editorial masthead partial

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Restyle the settings page

**Files:**
- Modify: `core/tests.py`
- Modify: `core/templates/core/settings.html`

- [ ] **Step 1: Write the failing tests**

Add this class to the end of `core/tests.py`:

```python
class SettingsPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.save()
        self.client.force_login(self.user)

    def test_settings_renders_editorial_layout(self):
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="settings"')
        self.assertContains(response, 'ed-masthead')
        self.assertContains(response, 'ed-card')

    def test_settings_loads_account_css(self):
        response = self.client.get(reverse('settings'))
        self.assertContains(response, 'account.css')

    def test_settings_update_shows_success_alert(self):
        response = self.client.post(reverse('settings'), {
            'subscribed': 'on', 'timezone': 'America/New_York'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ed-alert--ok')
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.SettingsPageTests -v 2`
Expected: FAIL — the page still uses Bootstrap markup, so `id="settings"`, `ed-masthead`, `ed-card`, `account.css`, and `ed-alert--ok` are all absent.

- [ ] **Step 3: Replace the settings template**

Replace the entire contents of `core/templates/core/settings.html` with:

```html
{% extends "core/base.html" %}

{% block extra_head %}
<link href="/static/css/account.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="app" id="settings">
  {% include "core/_masthead.html" with tab="Account" %}

  <p class="ed-label">Settings</p>

  {% if success %}
  <div class="ed-alert ed-alert--ok">Your settings have been updated.</div>
  {% endif %}
  {% if form.errors %}
    {% for field in form %}{% for error in field.errors %}
    <div class="ed-alert ed-alert--error">{{ error|escape }}</div>
    {% endfor %}{% endfor %}
    {% for error in form.non_field_errors %}
    <div class="ed-alert ed-alert--error">{{ error|escape }}</div>
    {% endfor %}
  {% endif %}

  <section class="ed-card">
    <h2 class="ed-card__head">Subscription &amp; timezone</h2>
    <p class="ed-card__sub">Control whether you get a daily prompt and when it arrives.</p>
    <form method="post" action="">
      {% csrf_token %}
      <div class="ed-field">
        <label class="ed-check">
          <input type="checkbox" name="subscribed"{% if user.is_subscribed %} checked{% endif %}>
          <span>Subscribed &mdash; receive a writing prompt by email every day.</span>
        </label>
      </div>
      <div class="ed-field">
        <label class="ed-field__label" for="id_timezone">Time zone</label>
        {% load tz %}
        {% with user.timezone as user_tz %}
        <select class="ed-input" name="timezone" id="id_timezone">
          {% for tz in timezones %}
          <option value="{{ tz }}"{% if tz == user_tz %} selected{% endif %}>{{ tz }}</option>
          {% endfor %}
        </select>
        {% endwith %}
        <p class="ed-hint">Your daily prompt is sent in the morning, in this time zone.</p>
      </div>
      <button class="ed-btn" type="submit">Update settings</button>
    </form>
  </section>

  <section class="ed-card">
    <h2 class="ed-card__head">Account</h2>
    <p class="ed-card__sub">Manage access to your account.</p>
    <div class="ed-actions">
      <form action="/password_reset/" method="post">
        {% csrf_token %}
        <input type="hidden" name="email" value="{{ user.email }}">
        <button class="ed-btn-ghost" type="submit">Reset password</button>
      </form>
      <form action="/logout/" method="post">
        {% csrf_token %}
        <button class="ed-btn-ghost" type="submit">Log out</button>
      </form>
    </div>
    <p class="ed-hint">Reset password sends a link to {{ user.email }}.</p>
  </section>
</div>
{% endblock %}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python manage.py test core.tests.SettingsPageTests -v 2`
Expected: PASS — 3 tests OK.

- [ ] **Step 5: Commit**

```bash
git add core/tests.py core/templates/core/settings.html
git commit -m "Restyle settings page with the editorial theme

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Dashboard — editorial layout with search, filters, and pagination

**Files:**
- Modify: `core/tests.py`
- Modify: `core/views.py`
- Modify: `core/templates/core/index_logged_in.html`

- [ ] **Step 1: Write the failing tests**

In `core/tests.py`, add `datetime` to the imports. The file currently starts with `import json`; change the import block so it also has:

```python
from datetime import datetime
```

Then add this class to the end of `core/tests.py`:

```python
class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.save()
        self.client.force_login(self.user)

    def _entry(self, question='A prompt', category='Reflective',
               content='Some words', day=15):
        prompt = Prompt.objects.create(
            question=question, category=category, mail_day=timezone.now())
        return Entry.objects.create(
            content=content, author=self.user, prompt=prompt,
            pub_date=timezone.make_aware(datetime(2026, 1, day, 12, 0)))

    def test_dashboard_renders_editorial_layout(self):
        self._entry()
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="dashboard"')
        self.assertContains(response, 'ed-masthead')
        self.assertContains(response, 'ed-card')

    def test_dashboard_loads_account_css(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'account.css')

    def test_search_matches_entry_content(self):
        self._entry(content='a story about lighthouses')
        self._entry(content='a note about mountains')
        response = self.client.get(reverse('index'), {'q': 'lighthouse'})
        self.assertContains(response, 'lighthouses')
        self.assertNotContains(response, 'mountains')

    def test_search_matches_prompt_question(self):
        self._entry(question='Describe your first car', content='aaa')
        self._entry(question='Write a haiku', content='bbb')
        response = self.client.get(reverse('index'), {'q': 'haiku'})
        self.assertContains(response, 'bbb')
        self.assertNotContains(response, 'aaa')

    def test_date_range_filters_entries(self):
        self._entry(content='january fifth', day=5)
        self._entry(content='january twentyfifth', day=25)
        response = self.client.get(
            reverse('index'), {'from': '2026-01-10', 'to': '2026-01-31'})
        self.assertContains(response, 'twentyfifth')
        self.assertNotContains(response, 'fifth')

    def test_category_filter(self):
        self._entry(category='Narrative', content='narrative entry')
        self._entry(category='Expository', content='expository entry')
        response = self.client.get(reverse('index'), {'category': 'Narrative'})
        self.assertContains(response, 'narrative entry')
        self.assertNotContains(response, 'expository entry')

    def test_sort_oldest_first(self):
        self._entry(content='older one', day=1)
        self._entry(content='newer one', day=28)
        response = self.client.get(reverse('index'), {'sort': 'oldest'})
        body = response.content.decode()
        self.assertLess(body.index('older one'), body.index('newer one'))

    def test_pagination_caps_page_at_25(self):
        for i in range(26):
            self._entry(content='entry number %d' % i)
        response = self.client.get(reverse('index'))
        self.assertEqual(len(response.context['page_obj'].object_list), 25)

    def test_pagination_second_page(self):
        for i in range(26):
            self._entry(content='entry number %d' % i)
        response = self.client.get(reverse('index'), {'page': 2})
        self.assertEqual(len(response.context['page_obj'].object_list), 1)

    def test_pagination_links_preserve_filters(self):
        for i in range(26):
            self._entry(category='Narrative', content='narrative %d' % i)
        response = self.client.get(reverse('index'), {'category': 'Narrative'})
        self.assertContains(response, 'category=Narrative')
        self.assertContains(response, 'page=2')

    def test_result_count_hidden_without_filters(self):
        self._entry()
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'ed-count')

    def test_result_count_shown_when_searching(self):
        self._entry(content='findable text')
        response = self.client.get(reverse('index'), {'q': 'findable'})
        self.assertContains(response, 'ed-count')

    def test_filter_panel_open_when_filtering(self):
        self._entry()
        response = self.client.get(reverse('index'), {'category': 'Reflective'})
        self.assertContains(response, '<details class="ed-filter-disclosure" open>')

    def test_filter_panel_closed_by_default(self):
        self._entry()
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'ed-filter-disclosure" open')

    def test_empty_state_no_entries(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'No entries yet')

    def test_empty_state_no_matches(self):
        self._entry(content='something')
        response = self.client.get(reverse('index'), {'q': 'zzzznomatch'})
        self.assertContains(response, 'No entries match')
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.DashboardTests -v 2`
Expected: FAIL — the current dashboard has no `id="dashboard"`, no filtering, and no `page_obj` in its context.

- [ ] **Step 3: Refactor the view**

In `core/views.py`, add these imports near the other Django imports at the top of the file:

```python
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.dateparse import parse_date
```

Replace the existing `index` function:

```python
def index(request):
    if request.user.is_authenticated:
        if request.user.confirmed_email:
            entries = Entry.objects.filter(author=request.user).\
                order_by("-pub_date")
            return render(request, 'core/index_logged_in.html',
                          {'entries': entries})
        else:
            logout(request)
            return redirect('unconfirmed_email')
    else:
        return render(request, 'core/index.html')
```

with this — the `index` function plus a new `_dashboard` helper and an `ENTRIES_PER_PAGE` constant directly above `index`:

```python
ENTRIES_PER_PAGE = 25


def index(request):
    if request.user.is_authenticated:
        if request.user.confirmed_email:
            return _dashboard(request)
        else:
            logout(request)
            return redirect('unconfirmed_email')
    else:
        return render(request, 'core/index.html')


def _dashboard(request):
    entries = Entry.objects.filter(author=request.user).select_related('prompt')

    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('from', '').strip()
    date_to = request.GET.get('to', '').strip()
    category = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'newest').strip()

    if q:
        entries = entries.filter(
            Q(content__icontains=q) | Q(prompt__question__icontains=q))

    parsed_from = parse_date(date_from) if date_from else None
    if parsed_from:
        entries = entries.filter(pub_date__date__gte=parsed_from)

    parsed_to = parse_date(date_to) if date_to else None
    if parsed_to:
        entries = entries.filter(pub_date__date__lte=parsed_to)

    if category:
        entries = entries.filter(prompt__category=category)

    if sort == 'oldest':
        entries = entries.order_by('pub_date')
    else:
        sort = 'newest'
        entries = entries.order_by('-pub_date')

    paginator = Paginator(entries, ENTRIES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    categories = Entry.objects.filter(author=request.user) \
        .exclude(prompt__category__isnull=True) \
        .exclude(prompt__category='') \
        .values_list('prompt__category', flat=True) \
        .distinct().order_by('prompt__category')

    params = request.GET.copy()
    params.pop('page', None)
    for key in list(params.keys()):
        if not params.get(key):
            del params[key]
    querystring = params.urlencode()

    context = {
        'entries': page_obj.object_list,
        'page_obj': page_obj,
        'total_count': paginator.count,
        'categories': categories,
        'filters_active': bool(q or parsed_from or parsed_to or category),
        'querystring': querystring,
        'q': q,
        'date_from': date_from,
        'date_to': date_to,
        'category': category,
        'sort': sort,
    }
    return render(request, 'core/index_logged_in.html', context)
```

- [ ] **Step 4: Replace the dashboard template**

Replace the entire contents of `core/templates/core/index_logged_in.html` with:

```html
{% extends "core/base.html" %}

{% block extra_head %}
<link href="/static/css/account.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="app" id="dashboard">
  {% include "core/_masthead.html" with tab="Your writing" %}

  <form class="ed-filters" method="get" action="/">
    <div class="ed-search-row">
      <input class="ed-search" type="text" name="q" value="{{ q }}"
             placeholder="Search your entries and prompts&hellip;">
      <button class="ed-btn" type="submit">Search</button>
    </div>
    <details class="ed-filter-disclosure"{% if filters_active %} open{% endif %}>
      <summary class="ed-filter-toggle">Filters</summary>
      <div class="ed-filter-panel">
        <div class="ed-field">
          <label class="ed-field__label" for="id_from">From</label>
          <input class="ed-input" type="date" name="from" id="id_from" value="{{ date_from }}">
        </div>
        <div class="ed-field">
          <label class="ed-field__label" for="id_to">To</label>
          <input class="ed-input" type="date" name="to" id="id_to" value="{{ date_to }}">
        </div>
        <div class="ed-field">
          <label class="ed-field__label" for="id_category">Category</label>
          <select class="ed-input" name="category" id="id_category">
            <option value="">All categories</option>
            {% for cat in categories %}
            <option value="{{ cat }}"{% if cat == category %} selected{% endif %}>{{ cat }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="ed-field">
          <label class="ed-field__label" for="id_sort">Sort</label>
          <select class="ed-input" name="sort" id="id_sort">
            <option value="newest"{% if sort != 'oldest' %} selected{% endif %}>Newest first</option>
            <option value="oldest"{% if sort == 'oldest' %} selected{% endif %}>Oldest first</option>
          </select>
        </div>
        <button class="ed-btn" type="submit">Apply</button>
        <a class="ed-filter-clear" href="/">Clear</a>
      </div>
    </details>
  </form>

  {% if filters_active %}
  <p class="ed-count">Showing <b>{{ page_obj.start_index }}&ndash;{{ page_obj.end_index }}</b> of <b>{{ total_count }}</b> entries</p>
  {% endif %}

  {% if entries %}
    {% for entry in entries %}
    <article class="ed-card ed-entry">
      {% if entry.prompt.category %}<p class="ed-entry__cat">{{ entry.prompt.category }}</p>{% endif %}
      <h2 class="ed-entry__q">{{ entry.prompt.question }}</h2>
      <p class="ed-entry__date">{{ entry.pub_date|date:"M d, Y" }}</p>
      <div class="ed-entry__body">{{ entry.content|linebreaks }}</div>
    </article>
    {% endfor %}

    {% if page_obj.paginator.num_pages > 1 %}
    <nav class="ed-pagination">
      {% if page_obj.has_previous %}
      <a class="ed-page" href="?page={{ page_obj.previous_page_number }}{% if querystring %}&{{ querystring }}{% endif %}">&lsaquo; Prev</a>
      {% else %}
      <span class="ed-page is-disabled">&lsaquo; Prev</span>
      {% endif %}
      {% for num in page_obj.paginator.page_range %}
        {% if num == page_obj.number %}
        <span class="ed-page is-current">{{ num }}</span>
        {% else %}
        <a class="ed-page" href="?page={{ num }}{% if querystring %}&{{ querystring }}{% endif %}">{{ num }}</a>
        {% endif %}
      {% endfor %}
      {% if page_obj.has_next %}
      <a class="ed-page" href="?page={{ page_obj.next_page_number }}{% if querystring %}&{{ querystring }}{% endif %}">Next &rsaquo;</a>
      {% else %}
      <span class="ed-page is-disabled">Next &rsaquo;</span>
      {% endif %}
    </nav>
    {% endif %}

  {% elif filters_active %}
    <div class="ed-empty">
      <h2>No entries match your search.</h2>
      <p><a href="/">Clear search and filters</a></p>
    </div>
  {% else %}
    <div class="ed-empty">
      <h2>No entries yet!</h2>
      <p>When you reply to an email, your responses will appear here.</p>
    </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python manage.py test core.tests.DashboardTests -v 2`
Expected: PASS — 17 tests OK.

- [ ] **Step 6: Commit**

```bash
git add core/tests.py core/views.py core/templates/core/index_logged_in.html
git commit -m "Redesign dashboard: editorial theme, search, filters, pagination

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Final verification

**Files:** none

- [ ] **Step 1: Run the full test suite**

Run: `python manage.py test core -v 2`
Expected: PASS — all tests OK, including the pre-existing `HomePageTests` and `EmailConfirmationTests` (confirming the home page and auth flows are unaffected).

- [ ] **Step 2: Visual smoke check**

Run: `python manage.py runserver`
In a browser, log in as a confirmed user and check both pages:
- `/` (dashboard): masthead with green "Your writing" tab; search box always visible; "Filters" collapsed by default and expanding on click; entries shown as bordered cards; pagination tiles appear once there are more than 25 entries; the "Showing X–Y of Z" line appears only after searching/filtering.
- `/settings/`: masthead with "Account" tab; subscription/timezone form in a card; ghost buttons for password reset and logout; submitting the form shows a green success banner.

Stop the server with Ctrl+C when done.

- [ ] **Step 3: Confirm nothing else is uncommitted**

Run: `git status`
Expected: working tree clean (the `.superpowers/` brainstorm directory is already gitignored).
