# Site Nav Component Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ad-hoc masthead `tab` parameter and the `ed-detail-back` link with one reusable breadcrumb-tabs nav component used across dashboard, settings, archived, entry detail, and about.

**Architecture:** A custom Django inclusion template tag (`{% sitenav %}`) holds the page→trail hierarchy in one Python function and renders a `_sitenav.html` partial — a row of connected folder-tabs (ancestors are links, current page is the green tab) sitting on the existing masthead brand card. Styles live in a new global `sitenav.css`.

**Tech Stack:** Django 5 templates + template tags, plain CSS, Django `TestCase`.

---

## File Structure

| File | Responsibility |
|---|---|
| `core/templatetags/sitenav.py` | New. `build_trail()` (hierarchy → crumb list) + `sitenav` inclusion tag. |
| `core/templates/core/_sitenav.html` | New. Renders the tab row + masthead brand card. |
| `dailyinquirer/static/css/sitenav.css` | New. Self-contained styles for the component. |
| `core/templates/core/base.html` | Modify. Load `sitenav.css` globally. |
| `core/templates/core/index_logged_in.html` | Modify. Use `{% sitenav 'dashboard' %}`. |
| `core/templates/core/settings.html` | Modify. Use `{% sitenav 'settings' %}`. |
| `core/templates/core/archived.html` | Modify. Use `{% sitenav 'archived' %}`; drop back link. |
| `core/templates/core/entry_detail.html` | Modify. Use `{% sitenav 'entry' entry=entry %}`; drop back link. |
| `core/templates/core/about.html` | Modify. Add `{% sitenav 'about' %}`. |
| `core/templates/core/_masthead.html` | Delete. |
| `dailyinquirer/static/css/account.css` | Modify. Remove dead masthead / back-link rules; drop `.app` top padding. |
| `core/tests.py` | Modify. Add `SiteNavTests`. |

Each page declares its own trail; the hierarchy is the single source of truth in `build_trail()`.

---

## Task 1: Create the `sitenav` template tag

**Files:**
- Create: `core/templatetags/sitenav.py`
- Test: `core/tests.py` (new `SiteNavTests` class)

- [ ] **Step 1: Write the failing tests**

Add to the end of `core/tests.py`:

```python
class SiteNavTests(TestCase):
    def test_dashboard_trail_is_single_current_crumb(self):
        from core.templatetags.sitenav import build_trail
        trail = build_trail('dashboard')
        self.assertEqual(trail, [{'label': 'Your writing', 'url': None}])

    def test_settings_trail_links_back_to_dashboard(self):
        from core.templatetags.sitenav import build_trail
        trail = build_trail('settings')
        self.assertEqual(len(trail), 2)
        self.assertEqual(trail[0]['label'], 'Your writing')
        self.assertEqual(trail[0]['url'], reverse('dash'))
        self.assertEqual(trail[1], {'label': 'Settings', 'url': None})

    def test_archived_trail_links_back_to_dashboard(self):
        from core.templatetags.sitenav import build_trail
        trail = build_trail('archived')
        self.assertEqual(len(trail), 2)
        self.assertEqual(trail[0]['url'], reverse('dash'))
        self.assertEqual(trail[1], {'label': 'Archived', 'url': None})

    def test_about_trail_is_single_standalone_crumb(self):
        from core.templatetags.sitenav import build_trail
        trail = build_trail('about')
        self.assertEqual(trail, [{'label': 'About', 'url': None}])

    def test_active_entry_trail_has_two_crumbs_with_date_label(self):
        from core.templatetags.sitenav import build_trail
        prompt = Prompt.objects.create(
            question='A prompt', category='Memory', mail_day=timezone.now())
        user = User.objects.create_user(
            email='e@example.com', password='mostdope1')
        entry = Entry.objects.create(
            content='words', author=user, prompt=prompt,
            pub_date=timezone.make_aware(datetime(2026, 5, 12, 12, 0)))
        trail = build_trail('entry', entry=entry)
        self.assertEqual(len(trail), 2)
        self.assertEqual(trail[0]['url'], reverse('dash'))
        self.assertEqual(trail[1], {'label': 'May 12, 2026', 'url': None})

    def test_archived_entry_trail_inserts_archived_crumb(self):
        from core.templatetags.sitenav import build_trail
        prompt = Prompt.objects.create(
            question='A prompt', category='Memory', mail_day=timezone.now())
        user = User.objects.create_user(
            email='e2@example.com', password='mostdope1')
        entry = Entry.objects.create(
            content='words', author=user, prompt=prompt,
            pub_date=timezone.make_aware(datetime(2026, 5, 12, 12, 0)),
            archived_at=timezone.now())
        trail = build_trail('entry', entry=entry)
        self.assertEqual([c['label'] for c in trail],
                         ['Your writing', 'Archived', 'May 12, 2026'])
        self.assertEqual(trail[1]['url'], reverse('archived_entries'))
        self.assertIsNone(trail[2]['url'])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test core.tests.SiteNavTests -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.templatetags.sitenav'`

- [ ] **Step 3: Create the template tag module**

Create `core/templatetags/sitenav.py`:

```python
from django import template
from django.urls import reverse
from django.utils.formats import date_format

register = template.Library()


def build_trail(page, entry=None):
    """Return the breadcrumb trail for a page.

    Each crumb is a dict ``{'label': str, 'url': str | None}``. Ancestor
    crumbs carry a url; the final (current-page) crumb has ``url=None``.
    """
    writing = {'label': 'Your writing', 'url': reverse('dash')}
    archived = {'label': 'Archived', 'url': reverse('archived_entries')}

    if page == 'dashboard':
        return [{'label': 'Your writing', 'url': None}]
    if page == 'settings':
        return [writing, {'label': 'Settings', 'url': None}]
    if page == 'archived':
        return [writing, {'label': 'Archived', 'url': None}]
    if page == 'about':
        return [{'label': 'About', 'url': None}]
    if page == 'entry':
        if entry is None:
            raise ValueError("sitenav page 'entry' requires an entry argument")
        crumbs = [writing]
        if entry.archived_at:
            crumbs.append(archived)
        crumbs.append({
            'label': date_format(entry.pub_date, 'M j, Y'),
            'url': None,
        })
        return crumbs
    raise ValueError(f"unknown sitenav page: {page!r}")


@register.inclusion_tag('core/_sitenav.html', takes_context=True)
def sitenav(context, page, entry=None):
    return {
        'crumbs': build_trail(page, entry=entry),
        'user': context['user'],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test core.tests.SiteNavTests -v 2`
Expected: PASS (6 tests). The inclusion tag references `core/_sitenav.html`, which does not exist yet — that is fine; `build_trail` is what these tests exercise.

- [ ] **Step 5: Commit**

```bash
git add core/templatetags/sitenav.py core/tests.py
git commit -m "$(cat <<'EOF'
Add sitenav template tag with breadcrumb trail builder

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Create the `_sitenav.html` partial

**Files:**
- Create: `core/templates/core/_sitenav.html`

- [ ] **Step 1: Create the partial**

Create `core/templates/core/_sitenav.html`:

```html
<header class="ed-sitenav">
  <nav class="ed-sitenav__tabs" aria-label="Breadcrumb">
    {% for crumb in crumbs %}
      {% if crumb.url %}
      <a class="ed-tab ed-tab--link" href="{{ crumb.url }}">{{ crumb.label }}</a>
      {% else %}
      <span class="ed-tab ed-tab--current" aria-current="page">{{ crumb.label }}</span>
      {% endif %}
    {% endfor %}
  </nav>
  <div class="ed-masthead">
    <h1 class="ed-masthead__name">
      <a href="{% if user.is_authenticated %}{% url 'dash' %}{% else %}/{% endif %}">The Daily Inquirer</a>
    </h1>
    {% if user.is_authenticated %}
    <p class="ed-masthead__email"><a href="{% url 'settings' %}">{{ user.email }}</a></p>
    {% endif %}
  </div>
</header>
```

- [ ] **Step 2: Run the sitenav tests to verify they still pass**

Run: `python manage.py test core.tests.SiteNavTests -v 2`
Expected: PASS (6 tests).

- [ ] **Step 3: Commit**

```bash
git add core/templates/core/_sitenav.html
git commit -m "$(cat <<'EOF'
Add _sitenav partial for breadcrumb tabs

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Create `sitenav.css` and wire it into `base.html`

**Files:**
- Create: `dailyinquirer/static/css/sitenav.css`
- Modify: `core/templates/core/base.html:16`

- [ ] **Step 1: Create the stylesheet**

Create `dailyinquirer/static/css/sitenav.css`:

```css
/* ============================================================
   SITE NAV — breadcrumb tabs + masthead brand card.
   Shared across dashboard, settings, archived, entry detail and
   about. Self-contained; consumes tokens from tokens.css. Not
   scoped under .app, because the about page is not an .app page.
   ============================================================ */

.ed-sitenav {
  padding-top: 40px;
  margin-bottom: 8px;
}

/* --- Breadcrumb tabs ---------------------------------------- */

.ed-sitenav__tabs {
  display: flex;
  padding-left: 22px;
  overflow-x: auto;
  scrollbar-width: none;
}

.ed-sitenav__tabs::-webkit-scrollbar {
  display: none;
}

.ed-tab {
  font-family: var(--body);
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  padding: 7px 16px;
  margin-bottom: -1px;
  border-radius: 7px 7px 0 0;
  white-space: nowrap;
  text-decoration: none;
}

.ed-tab--current {
  position: relative;
  z-index: 2;
  background: var(--accent);
  color: #fff;
}

.ed-tab--link {
  background: #efece2;
  color: var(--ink-faint);
  border: 1px solid var(--rule);
  border-bottom: none;
  margin-right: 2px;
  transition: color 0.15s ease, background 0.15s ease;
}

.ed-tab--link:hover {
  color: var(--ink);
  background: #e7e3d6;
}

/* --- Masthead brand card ------------------------------------ */

.ed-sitenav .ed-masthead {
  position: relative;
  z-index: 1;
  background: var(--paper);
  border: 1px solid var(--rule);
  border-bottom: 3px solid var(--accent);
  border-radius: 8px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
  padding: 26px 24px;
}

.ed-sitenav .ed-masthead__name {
  font-family: var(--display);
  font-size: clamp(1.7rem, 5.5vw, 2.4rem);
  font-weight: 400;
  line-height: 1.05;
  letter-spacing: -0.01em;
  margin: 0;
}

.ed-sitenav .ed-masthead__name a {
  color: var(--ink);
  text-decoration: none;
}

.ed-sitenav .ed-masthead__email {
  font-family: var(--body);
  font-size: 0.875rem;
  color: var(--ink-soft);
  margin: 8px 0 0;
}

.ed-sitenav .ed-masthead__email a {
  color: var(--accent);
  text-decoration: none;
}

.ed-sitenav .ed-masthead__email a:hover {
  text-decoration: underline;
}

@media (max-width: 480px) {
  .ed-sitenav .ed-masthead {
    padding: 22px 18px;
  }
}
```

- [ ] **Step 2: Load the stylesheet in `base.html`**

In `core/templates/core/base.html`, the `<head>` currently ends with:

```html
    <link href="/static/css/footer.css" rel="stylesheet">
    {% block extra_head %}{% endblock %}
```

Change it to:

```html
    <link href="/static/css/footer.css" rel="stylesheet">
    <link href="/static/css/sitenav.css" rel="stylesheet">
    {% block extra_head %}{% endblock %}
```

- [ ] **Step 3: Run the full suite to verify nothing broke**

Run: `python manage.py test`
Expected: PASS — same count as before this task (no behavior change yet).

- [ ] **Step 4: Commit**

```bash
git add dailyinquirer/static/css/sitenav.css core/templates/core/base.html
git commit -m "$(cat <<'EOF'
Add sitenav.css and load it globally

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Wire the dashboard to `{% sitenav %}`

**Files:**
- Modify: `core/templates/core/index_logged_in.html:1-2,10`
- Test: `core/tests.py` (`SiteNavTests`)

- [ ] **Step 1: Write the failing test**

Add to `SiteNavTests` in `core/tests.py`:

```python
    def test_dashboard_renders_sitenav_current_tab(self):
        user = User.objects.create_user(
            email='dash@example.com', password='mostdope1')
        user.confirmed_email = True
        user.onboarded = True
        user.save()
        self.client.force_login(user)
        response = self.client.get(reverse('dash'))
        self.assertContains(response, 'ed-sitenav')
        self.assertContains(response, 'ed-tab--current')
        self.assertContains(response, 'Your writing')
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.SiteNavTests.test_dashboard_renders_sitenav_current_tab -v 2`
Expected: FAIL — response does not contain `ed-sitenav`.

- [ ] **Step 3: Update the dashboard template**

In `core/templates/core/index_logged_in.html`, the file starts:

```html
{% extends "core/base.html" %}
{% load entry_extras %}
```

Change it to:

```html
{% extends "core/base.html" %}
{% load entry_extras %}
{% load sitenav %}
```

Then replace this line:

```html
  {% include "core/_masthead.html" with tab="Your writing" %}
```

with:

```html
  {% sitenav 'dashboard' %}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python manage.py test core.tests.SiteNavTests.test_dashboard_renders_sitenav_current_tab core.tests.DashboardTests -v 2`
Expected: PASS — including the existing `DashboardTests` (they assert `ed-masthead`, which the partial still renders).

- [ ] **Step 5: Commit**

```bash
git add core/templates/core/index_logged_in.html core/tests.py
git commit -m "$(cat <<'EOF'
Use sitenav on the dashboard

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Wire settings to `{% sitenav %}`

**Files:**
- Modify: `core/templates/core/settings.html:1,9`
- Test: `core/tests.py` (`SiteNavTests`)

- [ ] **Step 1: Write the failing test**

Add to `SiteNavTests` in `core/tests.py`:

```python
    def test_settings_renders_sitenav_with_ancestor_link(self):
        user = User.objects.create_user(
            email='set@example.com', password='mostdope1')
        user.confirmed_email = True
        user.onboarded = True
        user.save()
        self.client.force_login(user)
        response = self.client.get(reverse('settings'))
        self.assertContains(response, 'ed-sitenav')
        self.assertContains(
            response,
            '<a class="ed-tab ed-tab--link" href="%s">Your writing</a>'
            % reverse('dash'), html=False)
        self.assertContains(response, '>Settings</span>')
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.SiteNavTests.test_settings_renders_sitenav_with_ancestor_link -v 2`
Expected: FAIL — response does not contain `ed-sitenav`.

- [ ] **Step 3: Update the settings template**

In `core/templates/core/settings.html`, the file starts:

```html
{% extends "core/base.html" %}

{% block extra_head %}
```

Change it to:

```html
{% extends "core/base.html" %}
{% load sitenav %}

{% block extra_head %}
```

Then replace this line:

```html
  {% include "core/_masthead.html" with tab="Account" %}
```

with:

```html
  {% sitenav 'settings' %}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python manage.py test core.tests.SiteNavTests.test_settings_renders_sitenav_with_ancestor_link core.tests.SettingsPageTests -v 2`
Expected: PASS — including the existing `SettingsPageTests`.

- [ ] **Step 5: Commit**

```bash
git add core/templates/core/settings.html core/tests.py
git commit -m "$(cat <<'EOF'
Use sitenav on the settings page

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Wire archived to `{% sitenav %}` and remove its back link

**Files:**
- Modify: `core/templates/core/archived.html:1,9,13-16`
- Test: `core/tests.py` (`SiteNavTests`)

- [ ] **Step 1: Write the failing test**

Add to `SiteNavTests` in `core/tests.py`:

```python
    def test_archived_renders_sitenav_and_drops_back_link(self):
        user = User.objects.create_user(
            email='arc@example.com', password='mostdope1')
        user.confirmed_email = True
        user.onboarded = True
        user.save()
        self.client.force_login(user)
        response = self.client.get(reverse('archived_entries'))
        self.assertContains(response, 'ed-sitenav')
        self.assertContains(response, '>Archived</span>')
        self.assertNotContains(response, 'ed-detail-back')
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.SiteNavTests.test_archived_renders_sitenav_and_drops_back_link -v 2`
Expected: FAIL — response does not contain `ed-sitenav` and still contains `ed-detail-back`.

- [ ] **Step 3: Update the archived template**

In `core/templates/core/archived.html`, the file starts:

```html
{% extends "core/base.html" %}

{% block extra_head %}
```

Change it to:

```html
{% extends "core/base.html" %}
{% load sitenav %}

{% block extra_head %}
```

Replace this line:

```html
  {% include "core/_masthead.html" with tab="Archived" %}
```

with:

```html
  {% sitenav 'archived' %}
```

Then delete this block entirely:

```html
  <a class="ed-detail-back" href="{% url 'dash' %}">
    <svg class="ed-icon" aria-hidden="true"><use href="/static/img/icons.svg#chevron-left"></use></svg>
    Your writing
  </a>

```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python manage.py test core.tests.SiteNavTests.test_archived_renders_sitenav_and_drops_back_link -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/templates/core/archived.html core/tests.py
git commit -m "$(cat <<'EOF'
Use sitenav on the archived page; remove its back link

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Wire entry detail to `{% sitenav %}` and remove its back link

**Files:**
- Modify: `core/templates/core/entry_detail.html:1-2,10-13`
- Test: `core/tests.py` (`SiteNavTests`)

- [ ] **Step 1: Write the failing tests**

Add to `SiteNavTests` in `core/tests.py`:

```python
    def _make_entry(self, email, archived=False):
        user = User.objects.create_user(email=email, password='mostdope1')
        user.confirmed_email = True
        user.onboarded = True
        user.save()
        prompt = Prompt.objects.create(
            question='A prompt', category='Memory', mail_day=timezone.now())
        return user, Entry.objects.create(
            content='words', author=user, prompt=prompt,
            pub_date=timezone.make_aware(datetime(2026, 5, 12, 12, 0)),
            archived_at=timezone.now() if archived else None)

    def test_active_entry_renders_two_crumb_sitenav(self):
        user, entry = self._make_entry('ent@example.com')
        self.client.force_login(user)
        response = self.client.get(
            reverse('entry_detail', args=[entry.pk]))
        self.assertContains(response, 'ed-sitenav')
        self.assertContains(response, '>May 12, 2026</span>')
        self.assertNotContains(response, 'ed-detail-back')

    def test_archived_entry_renders_three_crumb_sitenav(self):
        user, entry = self._make_entry('ent2@example.com', archived=True)
        self.client.force_login(user)
        response = self.client.get(
            reverse('entry_detail', args=[entry.pk]))
        self.assertContains(response, 'ed-sitenav')
        self.assertContains(response, '>Archived</a>')
        self.assertContains(response, '>May 12, 2026</span>')
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.SiteNavTests.test_active_entry_renders_two_crumb_sitenav core.tests.SiteNavTests.test_archived_entry_renders_three_crumb_sitenav -v 2`
Expected: FAIL — response does not contain `ed-sitenav`.

- [ ] **Step 3: Update the entry detail template**

In `core/templates/core/entry_detail.html`, the file starts:

```html
{% extends "core/base.html" %}
{% load entry_extras %}
```

Change it to:

```html
{% extends "core/base.html" %}
{% load entry_extras %}
{% load sitenav %}
```

Then replace this block:

```html
  <a class="ed-detail-back" href="{% url 'dash' %}">
    <svg class="ed-icon" aria-hidden="true"><use href="/static/img/icons.svg#chevron-left"></use></svg>
    Your writing
  </a>
```

with:

```html
  {% sitenav 'entry' entry=entry %}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python manage.py test core.tests.SiteNavTests -v 2`
Expected: PASS (all sitenav tests).

- [ ] **Step 5: Commit**

```bash
git add core/templates/core/entry_detail.html core/tests.py
git commit -m "$(cat <<'EOF'
Use sitenav on entry detail; remove its back link

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Wire the about page to `{% sitenav %}`

**Files:**
- Modify: `core/templates/core/about.html`
- Modify: `dailyinquirer/static/css/styles.css:77-79`
- Test: `core/tests.py` (`SiteNavTests`)

- [ ] **Step 1: Write the failing tests**

Add to `SiteNavTests` in `core/tests.py`:

```python
    def test_about_renders_standalone_sitenav_anonymous(self):
        response = self.client.get(reverse('about'))
        self.assertContains(response, 'ed-sitenav')
        self.assertContains(response, '>About</span>')
        # Anonymous: no email line in the masthead.
        self.assertNotContains(response, 'ed-masthead__email')

    def test_about_renders_sitenav_with_email_when_logged_in(self):
        user = User.objects.create_user(
            email='abt@example.com', password='mostdope1')
        user.confirmed_email = True
        user.onboarded = True
        user.save()
        self.client.force_login(user)
        response = self.client.get(reverse('about'))
        self.assertContains(response, 'ed-sitenav')
        self.assertContains(response, 'ed-masthead__email')
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.SiteNavTests.test_about_renders_standalone_sitenav_anonymous core.tests.SiteNavTests.test_about_renders_sitenav_with_email_when_logged_in -v 2`
Expected: FAIL — response does not contain `ed-sitenav`.

- [ ] **Step 3: Update the about template**

Replace the entire contents of `core/templates/core/about.html` with:

```html
{% extends "core/base.html" %}
{% load sitenav %}

{% block content %}
{% sitenav 'about' %}
<div class="about-page">
  <h1 class="typewriter">About The Daily Inquirer</h1>

  <p>The Daily Inquirer sends you one writing prompt every morning. Reply to
  the email with whatever it stirs up &mdash; a sentence, a paragraph, a page
  &mdash; and your reply is saved as a journal entry on your personal
  dashboard.</p>

  <p>No app to open, no blank page to face. The prompt comes to your inbox;
  your writing goes back the way it came. Over time your dashboard becomes a
  searchable record of what you thought about, one day at a time.</p>

  <p>The Daily Inquirer is a small, independent project. Questions or
  feedback? Email <a href="mailto:hello@dailyinquirer.me">hello@dailyinquirer.me</a>.</p>
</div>
{% endblock %}
```

- [ ] **Step 4: Tighten the about page top margin**

In `dailyinquirer/static/css/styles.css`, the `.about-page` rule is:

```css
.about-page {
    max-width: 640px;
    margin: 48px auto;
}
```

Change it to (the sitenav now provides the top spacing):

```css
.about-page {
    max-width: 640px;
    margin: 24px auto 48px;
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python manage.py test core.tests.SiteNavTests core.tests.AboutPageTests -v 2`
Expected: PASS — including the existing `AboutPageTests` (`About The Daily Inquirer` text and `bootstrap.css` are still present; `home.css` still absent).

- [ ] **Step 6: Commit**

```bash
git add core/templates/core/about.html dailyinquirer/static/css/styles.css core/tests.py
git commit -m "$(cat <<'EOF'
Use sitenav on the about page

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Delete `_masthead.html` and remove dead CSS

**Files:**
- Delete: `core/templates/core/_masthead.html`
- Modify: `dailyinquirer/static/css/account.css`

- [ ] **Step 1: Confirm `_masthead.html` is no longer referenced**

Run: `grep -rn "_masthead" core/templates`
Expected: no output (all includes were replaced in Tasks 4–8).

- [ ] **Step 2: Delete the partial**

Run: `git rm core/templates/core/_masthead.html`

- [ ] **Step 3: Remove the `.app` top padding**

In `dailyinquirer/static/css/account.css`, the `.app` rule is:

```css
.app {
  padding-top: 40px;
  padding-bottom: 24px;
}
```

Change it to (sitenav.css now owns the top spacing via `.ed-sitenav`):

```css
.app {
  padding-bottom: 24px;
}
```

- [ ] **Step 4: Remove the dead masthead block**

In `dailyinquirer/static/css/account.css`, delete this entire block:

```css
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
  font-family: var(--display);
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
  font-size: 0.875rem;
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
```

- [ ] **Step 5: Remove the dead back-link block**

In `dailyinquirer/static/css/account.css`, delete this entire block:

```css
/* --- Back link ---------------------------------------------- */

.app .ed-detail-back {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--body);
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent);
  text-decoration: none;
  margin: 6px 0 4px;
}

.app .ed-detail-back:hover {
  color: var(--accent-dark);
}
```

- [ ] **Step 6: Remove the dead masthead media-query rule**

In `dailyinquirer/static/css/account.css`, inside the `@media (max-width: 480px)` block, delete just this rule (leave the rest of the media query intact):

```css
  .app .ed-masthead {
    padding: 22px 18px;
  }
```

- [ ] **Step 7: Verify no dangling references remain**

Run: `grep -nE "\.app .ed-masthead|ed-detail-back" dailyinquirer/static/css/account.css`
Expected: no output — the removed selectors are gone from `account.css`.

Note: `ed-masthead` legitimately survives in `core/templates/core/_sitenav.html` (the brand card), in `core/templates/core/index.html` / `home.css` (`#home .ed-masthead*`, the separate landing-page hero), and in `sitenav.css`. Those are intentional and must remain.

- [ ] **Step 8: Run the full test suite**

Run: `python manage.py test`
Expected: PASS — all tests, including `SiteNavTests`, `DashboardTests`, `SettingsPageTests`, `AboutPageTests`.

- [ ] **Step 9: Commit**

```bash
git add core/templates/core/_masthead.html dailyinquirer/static/css/account.css
git commit -m "$(cat <<'EOF'
Delete _masthead partial and dead masthead/back-link CSS

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Manual verification (after Task 9)

Run `python manage.py runserver` and confirm in a browser:

- Dashboard `/dash/` — single green "Your writing" tab; masthead unchanged.
- Settings `/settings/` — `Your writing` (grey link) + `Settings` (green); clicking the grey tab returns to the dashboard.
- Archived `/archived/` — `Your writing` + `Archived`; no back link above the list.
- An entry `/entry/<id>/` — `Your writing` + the entry date; archived entries also show an `Archived` crumb between them.
- About `/about/` — single green `About` tab, logged in and logged out; logged out shows no email line.
- Narrow the viewport to ~360px: the entry/archived trail scrolls horizontally instead of wrapping.
