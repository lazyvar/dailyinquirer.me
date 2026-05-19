# Prompt Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a logged-in inbox-style prompt viewer at `/prompts/` (past prompts, month at a time, answered/not-answered pill) plus a prompt detail page at `/prompts/<id>/` that lists the user's entries for a prompt and lets them add new entries from the web.

**Architecture:** Two new Django function views in `core/views.py` (`prompts`, `prompt_detail`), two URL routes, two templates. Both pages render the shared header with the existing `{% sitenav %}` inclusion tag and inherit the standard footer from `base.html`. The detail page reuses the existing `_entry_card.html` partial and `EntryEditForm`. No model or migration changes — `Entry` already permits multiple entries per `(user, prompt)`.

**Tech Stack:** Django 5 / Python 3.14, SQLite in tests, Django template language, `django.test.TestCase`. Tests run with `python manage.py test` (exactly what CI runs).

---

## Reference: design spec

`docs/superpowers/specs/2026-05-19-prompt-viewer-design.md`

## File map

- **Modify** `core/urls.py` — add `prompts` and `prompt_detail` routes.
- **Modify** `core/views.py` — add `prompts` and `prompt_detail` views; add `Http404` and `date` imports.
- **Modify** `core/templatetags/sitenav.py` — add `prompts` and `prompt` breadcrumb cases.
- **Create** `core/templates/core/prompts.html` — the inbox page.
- **Create** `core/templates/core/prompt_detail.html` — the detail page.
- **Modify** `core/templates/core/index_logged_in.html` — add a "Browse all prompts" link.
- **Modify** `dailyinquirer/static/css/account.css` — append prompt-viewer styles.
- **Modify** `core/tests.py` — add test classes for each task.

## Conventions to follow

- Test classes are appended to the end of `core/tests.py`. Each test class's
  `setUp` calls `Prompt.objects.all().delete()` first — the `0007` seed
  migration leaves prompts in the test database (existing tests do this).
- Log a test client in with `self.client.force_login(user)`.
- Views guard confirmed email exactly like the existing `dashboard` view:
  unconfirmed users are logged out and redirected to `unconfirmed_email`.
- Run a single test class with:
  `python manage.py test core.tests.<ClassName> -v 2`

---

## Task 1: Routing & page skeletons

Creates both URL routes, minimal stub views, both templates, and the two new
`sitenav` breadcrumb cases. After this task both pages exist, require login,
and render the shared header — but show no prompt data yet.

**Files:**
- Modify: `core/urls.py`
- Modify: `core/views.py`
- Modify: `core/templatetags/sitenav.py`
- Create: `core/templates/core/prompts.html`
- Create: `core/templates/core/prompt_detail.html`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Append to the end of `core/tests.py`:

```python
class PromptViewerRoutingTests(TestCase):
    def setUp(self):
        Prompt.objects.all().delete()
        self.user = User.objects.create_user(
            email='reader@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.confirmed_email = True
        self.user.save()
        self.prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())

    def test_prompts_page_requires_login(self):
        response = self.client.get('/prompts/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_prompts_page_renders_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get('/prompts/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/prompts.html')

    def test_prompt_detail_requires_login(self):
        response = self.client.get(f'/prompts/{self.prompt.pk}/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_prompt_detail_renders_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/prompts/{self.prompt.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/prompt_detail.html')
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.PromptViewerRoutingTests -v 2`
Expected: FAIL — `/prompts/` is unrouted, so requests return 404 instead of 302/200.

- [ ] **Step 3: Add the URL routes**

In `core/urls.py`, add these two lines immediately after the `archived/` path
(the line with `name='archived_entries'`):

```python
    path('prompts/', views.prompts, name='prompts'),
    path('prompts/<int:pk>/', views.prompt_detail, name='prompt_detail'),
```

- [ ] **Step 4: Add the stub views**

In `core/views.py`, add these two functions immediately after the
`archived_entries` view function:

```python
@login_required
def prompts(request):
    if not request.user.confirmed_email:
        logout(request)
        return redirect('unconfirmed_email')
    return render(request, 'core/prompts.html', {})


@login_required
def prompt_detail(request, pk):
    if not request.user.confirmed_email:
        logout(request)
        return redirect('unconfirmed_email')
    prompt = get_object_or_404(Prompt, pk=pk)
    return render(request, 'core/prompt_detail.html', {'prompt': prompt})
```

- [ ] **Step 5: Add the `sitenav` breadcrumb cases**

Replace the entire body of `core/templatetags/sitenav.py` with:

```python
from django import template
from django.urls import reverse
from django.utils.formats import date_format

register = template.Library()


def build_trail(page, entry=None, prompt=None):
    """Return the breadcrumb trail for a page.

    Each crumb is a dict ``{'label': str, 'url': str | None}``. Ancestor
    crumbs carry a url; the final (current-page) crumb has ``url=None``.
    """
    writing = {'label': 'Your writing', 'url': reverse('dash')}
    archived = {'label': 'Archived', 'url': reverse('archived_entries')}
    prompts = {'label': 'Prompts', 'url': reverse('prompts')}

    if page == 'dashboard':
        return [{**writing, 'url': None}]
    if page == 'settings':
        return [writing, {'label': 'Settings', 'url': None}]
    if page == 'archived':
        return [writing, {'label': 'Archived', 'url': None}]
    if page == 'about':
        return [{'label': 'About', 'url': None}]
    if page == 'prompts':
        return [{**prompts, 'url': None}]
    if page == 'prompt':
        if prompt is None:
            raise ValueError("sitenav page 'prompt' requires a prompt argument")
        return [prompts, {
            'label': date_format(prompt.mail_day, 'M j, Y'),
            'url': None,
        }]
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
def sitenav(context, page, entry=None, prompt=None):
    return {
        'crumbs': build_trail(page, entry=entry, prompt=prompt),
        'user': context['user'],
    }
```

- [ ] **Step 6: Create the inbox template**

Create `core/templates/core/prompts.html`:

```html
{% extends "core/base.html" %}
{% load sitenav %}

{% block extra_head %}
<link href="/static/css/account.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="app" id="prompts">
  {% sitenav 'prompts' %}

  {% include "core/_messages.html" %}
</div>
{% endblock %}
```

- [ ] **Step 7: Create the detail template**

Create `core/templates/core/prompt_detail.html`:

```html
{% extends "core/base.html" %}
{% load sitenav %}

{% block extra_head %}
<link href="/static/css/account.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="app" id="prompt">
  {% sitenav 'prompt' prompt=prompt %}

  {% include "core/_messages.html" %}
</div>
{% endblock %}
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `python manage.py test core.tests.PromptViewerRoutingTests -v 2`
Expected: PASS — 4 tests OK.

- [ ] **Step 9: Commit**

```bash
git add core/urls.py core/views.py core/templatetags/sitenav.py \
        core/templates/core/prompts.html \
        core/templates/core/prompt_detail.html core/tests.py
git commit -m "Add prompt viewer page skeletons and routing"
```

---

## Task 2: Inbox listing & answered pill

Fills in the `prompts` view to list the current month's past prompts with an
"Answered" / "No entry" pill, builds out the inbox template, and adds the CSS.

**Files:**
- Modify: `core/views.py:prompts`
- Modify: `core/templates/core/prompts.html`
- Modify: `dailyinquirer/static/css/account.css`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

First, update the datetime import at the top of `core/tests.py`. Change:

```python
from datetime import datetime
```

to:

```python
from datetime import datetime, timedelta
```

Then append to the end of `core/tests.py`:

```python
class PromptInboxTests(TestCase):
    def setUp(self):
        Prompt.objects.all().delete()
        self.user = User.objects.create_user(
            email='inbox@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.confirmed_email = True
        self.user.save()
        self.other = User.objects.create_user(
            email='someone@example.com', password='mostdope1')
        self.client.force_login(self.user)
        self.prompt = Prompt.objects.create(
            question='Question for today',
            mail_day=timezone.now())

    def test_lists_a_past_prompt_in_the_current_month(self):
        response = self.client.get('/prompts/')
        self.assertContains(response, 'Question for today')

    def test_excludes_a_future_dated_prompt(self):
        Prompt.objects.create(
            question='Future question',
            mail_day=timezone.now() + timedelta(days=1))
        response = self.client.get('/prompts/')
        self.assertNotContains(response, 'Future question')

    def test_excludes_a_prompt_from_another_month(self):
        Prompt.objects.create(
            question='Old month question',
            mail_day=timezone.now() - timedelta(days=60))
        response = self.client.get('/prompts/')
        self.assertNotContains(response, 'Old month question')

    def test_pill_reads_answered_when_user_has_an_entry(self):
        Entry.objects.create(
            content='My answer', author=self.user,
            prompt=self.prompt, pub_date=timezone.now())
        response = self.client.get('/prompts/')
        self.assertContains(response, 'Answered')

    def test_pill_reads_no_entry_without_an_entry(self):
        response = self.client.get('/prompts/')
        self.assertContains(response, 'No entry')

    def test_another_users_entry_does_not_flip_the_pill(self):
        Entry.objects.create(
            content='Their answer', author=self.other,
            prompt=self.prompt, pub_date=timezone.now())
        response = self.client.get('/prompts/')
        self.assertContains(response, 'No entry')

    def test_archived_entry_does_not_flip_the_pill(self):
        Entry.objects.create(
            content='Archived answer', author=self.user,
            prompt=self.prompt, pub_date=timezone.now(),
            archived_at=timezone.now())
        response = self.client.get('/prompts/')
        self.assertContains(response, 'No entry')

    def test_empty_month_shows_empty_state(self):
        self.prompt.delete()
        response = self.client.get('/prompts/')
        self.assertContains(response, 'No prompts this month')
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.PromptInboxTests -v 2`
Expected: FAIL — the stub view renders no prompt data, so the content/pill
assertions fail.

- [ ] **Step 3: Implement the inbox listing in the view**

In `core/views.py`, replace the entire `prompts` function with:

```python
@login_required
def prompts(request):
    if not request.user.confirmed_email:
        logout(request)
        return redirect('unconfirmed_email')

    local = request.user.local_time()
    today = local.date() if local is not None else timezone.localdate()

    month_prompts = Prompt.objects.filter(
        mail_day__year=today.year,
        mail_day__month=today.month,
        mail_day__date__lte=today,
    ).order_by('-mail_day')

    answered_ids = set(
        Entry.objects.filter(
            author=request.user,
            archived_at__isnull=True,
            prompt__in=month_prompts,
        ).values_list('prompt_id', flat=True)
    )

    rows = [
        {'prompt': p, 'answered': p.id in answered_ids}
        for p in month_prompts
    ]

    context = {
        'rows': rows,
        'month_label': today.strftime('%B %Y'),
    }
    return render(request, 'core/prompts.html', context)
```

- [ ] **Step 4: Build out the inbox template**

Replace the entire contents of `core/templates/core/prompts.html` with:

```html
{% extends "core/base.html" %}
{% load sitenav %}

{% block extra_head %}
<link href="/static/css/account.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="app" id="prompts">
  {% sitenav 'prompts' %}

  {% include "core/_messages.html" %}

  <div class="ed-promptnav">
    <h2 class="ed-promptnav__month">{{ month_label }}</h2>
    <span class="ed-promptnav__arrows">
      {% if prev_month %}
      <a class="ed-promptnav__arrow" href="?month={{ prev_month }}" aria-label="Previous month">&lsaquo;</a>
      {% else %}
      <span class="ed-promptnav__arrow is-disabled" aria-hidden="true">&lsaquo;</span>
      {% endif %}
      {% if next_month %}
      <a class="ed-promptnav__arrow" href="?month={{ next_month }}" aria-label="Next month">&rsaquo;</a>
      {% else %}
      <span class="ed-promptnav__arrow is-disabled" aria-hidden="true">&rsaquo;</span>
      {% endif %}
    </span>
  </div>

  {% if rows %}
  <ul class="ed-promptlist">
    {% for row in rows %}
    <li>
      <a class="ed-promptrow" href="{% url 'prompt_detail' row.prompt.pk %}">
        <span class="ed-promptrow__date">{{ row.prompt.mail_day|date:"M j" }}</span>
        <span class="ed-promptrow__q">{{ row.prompt.question }}</span>
        {% if row.answered %}
        <span class="ed-pill ed-pill--yes">Answered</span>
        {% else %}
        <span class="ed-pill ed-pill--no">No entry</span>
        {% endif %}
      </a>
    </li>
    {% endfor %}
  </ul>
  {% else %}
  <div class="ed-empty">
    <h2>No prompts this month.</h2>
  </div>
  {% endif %}
</div>
{% endblock %}
```

The month-navigation arrows are wired here but `prev_month` / `next_month` are
not supplied by the view until Task 3 — until then both arrows render disabled,
which is correct for a viewer that only shows the current month.

- [ ] **Step 5: Append the prompt-viewer CSS**

Append this block to the end of `dailyinquirer/static/css/account.css`:

```css
/* --- Prompt viewer ------------------------------------------ */
#prompts .ed-promptnav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 18px 0 4px;
}

#prompts .ed-promptnav__month {
  font-family: var(--display);
  font-size: 1.1rem;
  font-weight: 400;
  margin: 0;
}

#prompts .ed-promptnav__arrows {
  display: flex;
  gap: 6px;
}

#prompts .ed-promptnav__arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--paper);
  color: var(--ink-soft);
  font-size: 1rem;
  text-decoration: none;
}

#prompts .ed-promptnav__arrow:hover,
#prompts .ed-promptnav__arrow:focus {
  border-color: var(--ink-soft);
  color: var(--ink);
}

#prompts .ed-promptnav__arrow.is-disabled {
  color: var(--ink-faint);
  opacity: 0.4;
  pointer-events: none;
}

#prompts .ed-promptlist {
  list-style: none;
  margin: 0;
  padding: 0;
}

#prompts .ed-promptrow {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 11px 4px;
  border-bottom: 1px solid var(--rule);
  text-decoration: none;
  color: var(--ink);
}

#prompts .ed-promptrow:hover {
  background: rgba(0, 0, 0, 0.02);
}

#prompts .ed-promptrow__date {
  flex: none;
  width: 52px;
  font-family: var(--body);
  font-size: 0.8rem;
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
}

#prompts .ed-promptrow__q {
  flex: 1;
  font-family: var(--body);
  font-size: 1rem;
  line-height: 1.3;
}

.app .ed-pill {
  flex: none;
  font-family: var(--body);
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 3px 9px;
  border-radius: 999px;
  white-space: nowrap;
}

.app .ed-pill--yes {
  background: rgba(var(--accent-rgb), 0.13);
  color: var(--accent-dark);
}

.app .ed-pill--no {
  background: #efece4;
  color: var(--ink-faint);
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python manage.py test core.tests.PromptInboxTests -v 2`
Expected: PASS — 8 tests OK.

- [ ] **Step 7: Commit**

```bash
git add core/views.py core/templates/core/prompts.html \
        dailyinquirer/static/css/account.css core/tests.py
git commit -m "List current-month prompts with answered pill"
```

---

## Task 3: Month navigation

Adds `?month=YYYY-MM` support and the previous/next month arrows. A future
month is never shown; the previous arrow is offered only when an older prompt
exists.

**Files:**
- Modify: `core/views.py` (imports and `prompts`)
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Append to the end of `core/tests.py`:

```python
class PromptInboxNavigationTests(TestCase):
    def setUp(self):
        Prompt.objects.all().delete()
        self.user = User.objects.create_user(
            email='nav@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.confirmed_email = True
        self.user.save()
        self.client.force_login(self.user)
        self.today_prompt = Prompt.objects.create(
            question='Today question', mail_day=timezone.now())
        self.old_prompt = Prompt.objects.create(
            question='Old question',
            mail_day=timezone.now() - timedelta(days=70))

    def test_current_month_disables_the_next_arrow(self):
        response = self.client.get('/prompts/')
        self.assertContains(response, 'is-disabled')

    def test_current_month_offers_a_previous_arrow_link(self):
        # An older prompt exists 70 days back, so previous is a real link.
        response = self.client.get('/prompts/')
        self.assertContains(response, 'aria-label="Previous month"')
        self.assertContains(response, '?month=')

    def test_month_param_shows_that_months_prompts(self):
        old_month = (timezone.now() - timedelta(days=70)).strftime('%Y-%m')
        response = self.client.get(f'/prompts/?month={old_month}')
        self.assertContains(response, 'Old question')
        self.assertNotContains(response, 'Today question')

    def test_future_month_param_falls_back_to_current_month(self):
        future_month = (timezone.now() + timedelta(days=400)).strftime('%Y-%m')
        response = self.client.get(f'/prompts/?month={future_month}')
        self.assertContains(response, 'Today question')

    def test_invalid_month_param_falls_back_to_current_month(self):
        response = self.client.get('/prompts/?month=not-a-month')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Today question')
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.PromptInboxNavigationTests -v 2`
Expected: FAIL — `test_month_param_shows_that_months_prompts` fails because the
view ignores `?month=` and always shows the current month.

- [ ] **Step 3: Add the `date` import**

In `core/views.py`, change:

```python
from datetime import datetime
```

to:

```python
from datetime import date, datetime
```

- [ ] **Step 4: Implement month resolution and navigation**

In `core/views.py`, replace the entire `prompts` function with:

```python
@login_required
def prompts(request):
    if not request.user.confirmed_email:
        logout(request)
        return redirect('unconfirmed_email')

    local = request.user.local_time()
    today = local.date() if local is not None else timezone.localdate()

    year, month = today.year, today.month
    raw_month = request.GET.get('month', '')
    try:
        parsed = datetime.strptime(raw_month, '%Y-%m')
        year, month = parsed.year, parsed.month
    except (ValueError, TypeError):
        year, month = today.year, today.month

    # Never show a month in the future.
    if (year, month) > (today.year, today.month):
        year, month = today.year, today.month

    month_prompts = Prompt.objects.filter(
        mail_day__year=year,
        mail_day__month=month,
        mail_day__date__lte=today,
    ).order_by('-mail_day')

    answered_ids = set(
        Entry.objects.filter(
            author=request.user,
            archived_at__isnull=True,
            prompt__in=month_prompts,
        ).values_list('prompt_id', flat=True)
    )

    rows = [
        {'prompt': p, 'answered': p.id in answered_ids}
        for p in month_prompts
    ]

    first_of_month = date(year, month, 1)
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    has_older = Prompt.objects.filter(
        mail_day__date__lt=first_of_month).exists()
    has_newer = (year, month) < (today.year, today.month)

    context = {
        'rows': rows,
        'month_label': first_of_month.strftime('%B %Y'),
        'prev_month': (f'{prev_year:04d}-{prev_month:02d}'
                       if has_older else None),
        'next_month': (f'{next_year:04d}-{next_month:02d}'
                       if has_newer else None),
    }
    return render(request, 'core/prompts.html', context)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python manage.py test core.tests.PromptInboxNavigationTests -v 2`
Expected: PASS — 5 tests OK.

- [ ] **Step 6: Run the earlier inbox tests to confirm no regression**

Run: `python manage.py test core.tests.PromptInboxTests -v 2`
Expected: PASS — 8 tests OK.

- [ ] **Step 7: Commit**

```bash
git add core/views.py core/tests.py
git commit -m "Add month-at-a-time navigation to prompt viewer"
```

---

## Task 4: Dashboard link

Adds a "Browse all prompts" link to the logged-in dashboard so the viewer is
discoverable.

**Files:**
- Modify: `core/templates/core/index_logged_in.html`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing test**

Append to the end of `core/tests.py`:

```python
class DashboardPromptsLinkTests(TestCase):
    def setUp(self):
        Prompt.objects.all().delete()
        self.user = User.objects.create_user(
            email='dashlink@example.com', password='mostdope1')
        self.user.confirmed_email = True
        self.user.save()
        self.client.force_login(self.user)

    def test_dashboard_links_to_the_prompt_viewer(self):
        response = self.client.get('/dash/')
        self.assertContains(response, reverse('prompts'))
        self.assertContains(response, 'Browse all prompts')
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python manage.py test core.tests.DashboardPromptsLinkTests -v 2`
Expected: FAIL — the dashboard has no "Browse all prompts" link yet.

- [ ] **Step 3: Add the link to the dashboard template**

In `core/templates/core/index_logged_in.html`, find this block:

```html
  {% if archived_count %}
  <p class="ed-archived-link"><a href="{% url 'archived_entries' %}">View archived ({{ archived_count }})</a></p>
  {% endif %}
```

Add a new line immediately after it (after the `{% endif %}`):

```html
  <p class="ed-archived-link"><a href="{% url 'prompts' %}">Browse all prompts</a></p>
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python manage.py test core.tests.DashboardPromptsLinkTests -v 2`
Expected: PASS — 1 test OK.

- [ ] **Step 5: Commit**

```bash
git add core/templates/core/index_logged_in.html core/tests.py
git commit -m "Link to prompt viewer from the dashboard"
```

---

## Task 5: Prompt detail page

Fills in the `prompt_detail` view to show the prompt and list the user's own
active entries for it, and builds out the detail template. A future-dated
prompt returns 404.

**Files:**
- Modify: `core/views.py` (imports and `prompt_detail`)
- Modify: `core/templates/core/prompt_detail.html`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Append to the end of `core/tests.py`:

```python
class PromptDetailTests(TestCase):
    def setUp(self):
        Prompt.objects.all().delete()
        self.user = User.objects.create_user(
            email='detail@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.confirmed_email = True
        self.user.save()
        self.other = User.objects.create_user(
            email='stranger@example.com', password='mostdope1')
        self.client.force_login(self.user)
        self.prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())

    def test_detail_shows_the_prompt_question(self):
        response = self.client.get(f'/prompts/{self.prompt.pk}/')
        self.assertContains(response, 'What did you learn today?')

    def test_detail_lists_only_the_users_own_entries(self):
        Entry.objects.create(
            content='My reflection', author=self.user,
            prompt=self.prompt, pub_date=timezone.now())
        Entry.objects.create(
            content='Their reflection', author=self.other,
            prompt=self.prompt, pub_date=timezone.now())
        response = self.client.get(f'/prompts/{self.prompt.pk}/')
        self.assertContains(response, 'My reflection')
        self.assertNotContains(response, 'Their reflection')

    def test_detail_excludes_archived_entries(self):
        Entry.objects.create(
            content='Archived note', author=self.user,
            prompt=self.prompt, pub_date=timezone.now(),
            archived_at=timezone.now())
        response = self.client.get(f'/prompts/{self.prompt.pk}/')
        self.assertNotContains(response, 'Archived note')

    def test_detail_shows_empty_state_with_no_entries(self):
        response = self.client.get(f'/prompts/{self.prompt.pk}/')
        self.assertContains(response, 'No entry for this prompt yet')

    def test_future_prompt_returns_404(self):
        future = Prompt.objects.create(
            question='Future question',
            mail_day=timezone.now() + timedelta(days=10))
        response = self.client.get(f'/prompts/{future.pk}/')
        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.PromptDetailTests -v 2`
Expected: FAIL — the stub view renders no entries and does not 404 on a future
prompt.

- [ ] **Step 3: Add the `Http404` import**

In `core/views.py`, change:

```python
from django.http import (HttpResponse, HttpResponseBadRequest,
                          HttpResponseForbidden, HttpResponseNotAllowed)
```

to:

```python
from django.http import (Http404, HttpResponse, HttpResponseBadRequest,
                          HttpResponseForbidden, HttpResponseNotAllowed)
```

- [ ] **Step 4: Implement the detail view**

In `core/views.py`, replace the entire `prompt_detail` function with:

```python
@login_required
def prompt_detail(request, pk):
    if not request.user.confirmed_email:
        logout(request)
        return redirect('unconfirmed_email')

    prompt = get_object_or_404(Prompt, pk=pk)

    local = request.user.local_time()
    today = local.date() if local is not None else timezone.localdate()
    if prompt.mail_day.date() > today:
        raise Http404('prompt is not yet available')

    entries = Entry.objects.filter(
        author=request.user,
        prompt=prompt,
        archived_at__isnull=True,
    ).select_related('prompt').order_by('-pub_date')

    return render(request, 'core/prompt_detail.html', {
        'prompt': prompt,
        'entries': entries,
    })
```

- [ ] **Step 5: Build out the detail template**

Replace the entire contents of `core/templates/core/prompt_detail.html` with:

```html
{% extends "core/base.html" %}
{% load sitenav %}

{% block extra_head %}
<link href="/static/css/account.css" rel="stylesheet">
{% endblock %}

{% block content %}
<div class="app" id="prompt">
  {% sitenav 'prompt' prompt=prompt %}

  {% include "core/_messages.html" %}

  <article class="ed-card">
    {% if prompt.category %}<p class="ed-entry__cat">{{ prompt.category }}</p>{% endif %}
    <h1 class="ed-detail__q">{{ prompt.question }}</h1>
    <p class="ed-entry__date">{{ prompt.mail_day|date:"M d, Y" }}</p>
  </article>

  {% if entries %}
    {% for entry in entries %}
      {% include "core/_entry_card.html" with entry=entry %}
    {% endfor %}
  {% else %}
  <div class="ed-empty">
    <h2>No entry for this prompt yet.</h2>
    <p>You haven&rsquo;t written anything for this prompt.</p>
  </div>
  {% endif %}
</div>
{% endblock %}
```

This template reuses existing styled classes (`ed-card`, `ed-entry__cat`,
`ed-detail__q`, `ed-entry__date`, `ed-empty`) and the `_entry_card.html`
partial, so no new CSS is needed for this task.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python manage.py test core.tests.PromptDetailTests -v 2`
Expected: PASS — 5 tests OK.

- [ ] **Step 7: Commit**

```bash
git add core/views.py core/templates/core/prompt_detail.html core/tests.py
git commit -m "Show prompt detail page with the user's entries"
```

---

## Task 6: Add entry from the prompt detail page

Adds a POST handler and an inline "Add entry" form so a user can write a new
entry for a prompt directly on the web.

**Files:**
- Modify: `core/views.py:prompt_detail`
- Modify: `core/templates/core/prompt_detail.html`
- Modify: `dailyinquirer/static/css/account.css`
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Append to the end of `core/tests.py`:

```python
class PromptAddEntryTests(TestCase):
    def setUp(self):
        Prompt.objects.all().delete()
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.confirmed_email = True
        self.user.save()
        self.client.force_login(self.user)
        self.prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())

    def test_detail_page_shows_the_add_entry_control(self):
        response = self.client.get(f'/prompts/{self.prompt.pk}/')
        self.assertContains(response, 'Add entry')

    def test_post_creates_an_entry_for_the_prompt(self):
        response = self.client.post(
            f'/prompts/{self.prompt.pk}/',
            {'action': 'add', 'content': 'A brand new reflection.'})
        self.assertRedirects(response, f'/prompts/{self.prompt.pk}/')
        entry = Entry.objects.get(prompt=self.prompt, author=self.user)
        self.assertEqual(entry.content, 'A brand new reflection.')

    def test_added_entry_appears_on_the_detail_page(self):
        self.client.post(
            f'/prompts/{self.prompt.pk}/',
            {'action': 'add', 'content': 'Visible reflection.'})
        response = self.client.get(f'/prompts/{self.prompt.pk}/')
        self.assertContains(response, 'Visible reflection.')

    def test_blank_entry_is_rejected(self):
        response = self.client.post(
            f'/prompts/{self.prompt.pk}/',
            {'action': 'add', 'content': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Entry.objects.filter(prompt=self.prompt).count(), 0)

    def test_add_entry_requires_login(self):
        self.client.logout()
        response = self.client.post(
            f'/prompts/{self.prompt.pk}/',
            {'action': 'add', 'content': 'Should not be saved.'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Entry.objects.count(), 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.PromptAddEntryTests -v 2`
Expected: FAIL — there is no add-entry control and POST does not create an
`Entry`.

- [ ] **Step 3: Add POST handling to the detail view**

In `core/views.py`, replace the entire `prompt_detail` function with:

```python
@login_required
def prompt_detail(request, pk):
    if not request.user.confirmed_email:
        logout(request)
        return redirect('unconfirmed_email')

    prompt = get_object_or_404(Prompt, pk=pk)

    local = request.user.local_time()
    today = local.date() if local is not None else timezone.localdate()
    if prompt.mail_day.date() > today:
        raise Http404('prompt is not yet available')

    form = None
    if request.method == 'POST':
        if request.POST.get('action') != 'add':
            return HttpResponseBadRequest('unknown action')
        form = EntryEditForm(request.POST)
        if form.is_valid():
            Entry.objects.create(
                content=form.cleaned_data['content'],
                author=request.user,
                prompt=prompt,
                pub_date=timezone.now(),
            )
            messages.success(request, 'Your entry was added.')
            return redirect('prompt_detail', pk=prompt.pk)

    entries = Entry.objects.filter(
        author=request.user,
        prompt=prompt,
        archived_at__isnull=True,
    ).select_related('prompt').order_by('-pub_date')

    return render(request, 'core/prompt_detail.html', {
        'prompt': prompt,
        'entries': entries,
        'form': form,
        'show_form': form is not None,
    })
```

`EntryEditForm` is already imported in `core/views.py`. `show_form` is true
only after a failed POST, so the form re-opens with its errors shown.

- [ ] **Step 4: Add the add-entry form to the detail template**

In `core/templates/core/prompt_detail.html`, add this block immediately before
the final `</div>` (the one that closes `<div class="app" id="prompt">`):

```html
  <details class="ed-add"{% if show_form %} open{% endif %}>
    <summary class="ed-btn ed-add__toggle">Add entry</summary>
    <form class="ed-add__form" method="post">
      {% csrf_token %}
      <input type="hidden" name="action" value="add">
      <label class="ed-field__label" for="id_content">Your entry</label>
      {% if form.content.errors %}
      <div class="ed-alert ed-alert--error">{{ form.content.errors|join:" " }}</div>
      {% endif %}
      <textarea class="ed-detail__textarea" id="id_content" name="content">{{ form.content.value|default_if_none:"" }}</textarea>
      <div class="ed-actions">
        <button class="ed-btn" type="submit">Save entry</button>
      </div>
    </form>
  </details>
```

- [ ] **Step 5: Append the add-entry CSS**

Append this block to the end of `dailyinquirer/static/css/account.css`:

```css
/* --- Prompt detail: add entry ------------------------------- */
#prompt .ed-add {
  margin-top: 18px;
}

#prompt .ed-add__toggle {
  display: inline-block;
  cursor: pointer;
  list-style: none;
}

#prompt .ed-add__toggle::-webkit-details-marker {
  display: none;
}

#prompt .ed-add[open] .ed-add__toggle {
  margin-bottom: 12px;
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python manage.py test core.tests.PromptAddEntryTests -v 2`
Expected: PASS — 5 tests OK.

- [ ] **Step 7: Run the full test suite**

Run: `python manage.py test`
Expected: PASS — the entire suite, including all prompt-viewer tests, OK.

- [ ] **Step 8: Commit**

```bash
git add core/views.py core/templates/core/prompt_detail.html \
        dailyinquirer/static/css/account.css core/tests.py
git commit -m "Allow adding entries from the prompt detail page"
```

---

## Done

After Task 6 the feature is complete: `/prompts/` lists past prompts a month at
a time with answered status, `/prompts/<id>/` shows a prompt with the user's
entries and an add-entry form, and the dashboard links to it. The full suite
passes with `python manage.py test`.
