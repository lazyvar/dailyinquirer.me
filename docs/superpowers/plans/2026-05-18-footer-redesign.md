# Footer Redesign + About Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two divergent site footers with one shared, polished footer (wordmark · About · Terms · Privacy · Contact · copyright) and add the `/about/` page it links to.

**Architecture:** A single `<footer class="site-footer">` partial (`core/templates/core/_footer.html`) is `{% include %}`-d by both base templates. A new shared stylesheet `footer.css` styles it using existing `tokens.css` variables. The old `.footer-link` (styles.css) and `.auth-footer` (auth.css) rules are deleted. A new Django view/url/template renders `/about/`.

**Tech Stack:** Django 5 templates, plain CSS, Django `TestCase`.

---

## File Structure

- **Create** `core/templates/core/_footer.html` — the shared footer partial (a self-contained `<footer>` element).
- **Create** `dailyinquirer/static/css/footer.css` — styles for `.site-footer`, loaded by both base templates.
- **Create** `core/templates/core/about.html` — the About page, extends `core/base.html`.
- **Modify** `core/views.py` — add `about` view.
- **Modify** `core/urls.py` — add `about/` route.
- **Modify** `core/templates/core/base.html` — load `footer.css`; replace the Bootstrap footer row with the include.
- **Modify** `templates/registration/auth_base.html` — load `footer.css`; replace `.auth-footer` block with the include.
- **Modify** `dailyinquirer/static/css/styles.css` — delete `.footer-link`; add a small `.about-page` rule.
- **Modify** `dailyinquirer/static/css/auth.css` — delete `.auth-footer` rules; add `.auth-page .site-footer` shrink rule.
- **Modify** `core/tests.py` — add About page and footer tests.

---

## Task 1: About page (view + url + template)

**Files:**
- Modify: `core/tests.py` (add `AboutPageTests` class after `HomePageTests`, ends line 83)
- Modify: `core/urls.py:10` (after the `privacy/` route)
- Modify: `core/views.py:268-269` (after the `terms` view)
- Create: `core/templates/core/about.html`
- Modify: `dailyinquirer/static/css/styles.css:71` (after the `.footer-link` block — that block is still present at this point)

- [ ] **Step 1: Write the failing test**

Add this class to `core/tests.py` immediately after the `HomePageTests` class (after line 83):

```python
class AboutPageTests(TestCase):
    def test_about_page_renders(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'About The Daily Inquirer')

    def test_about_page_extends_base_layout(self):
        response = self.client.get(reverse('about'))
        self.assertContains(response, 'bootstrap.css')
        self.assertNotContains(response, 'home.css')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test core.tests.AboutPageTests`
Expected: FAIL — `NoReverseMatch: Reverse for 'about' not found`.

- [ ] **Step 3: Add the URL route**

In `core/urls.py`, add this line directly after the `privacy/` path (line 10):

```python
    path('about/', views.about, name='about'),
```

- [ ] **Step 4: Add the view**

In `core/views.py`, add this function directly after the `terms` view (after line 269):

```python
def about(request):
    return render(request, 'core/about.html')
```

- [ ] **Step 5: Create the About template**

Create `core/templates/core/about.html`:

```html
{% extends "core/base.html" %}

{% block content %}
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

- [ ] **Step 6: Add the `.about-page` style**

In `dailyinquirer/static/css/styles.css`, add this block directly after the existing `.footer-link` block (after line 71):

```css
.about-page {
    max-width: 640px;
    margin: 48px auto;
}

.about-page h1 {
    margin-bottom: 24px;
}

.about-page p {
    line-height: 1.6;
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python manage.py test core.tests.AboutPageTests`
Expected: PASS (2 tests).

- [ ] **Step 8: Commit**

```bash
git add core/urls.py core/views.py core/templates/core/about.html dailyinquirer/static/css/styles.css core/tests.py
git commit -m "Add an About page"
```

---

## Task 2: Shared footer partial and stylesheet

This task creates the footer assets. They are not wired into any page yet (Tasks 3 and 4 do that), so there is no test here — it is a pure asset-creation step.

**Files:**
- Create: `core/templates/core/_footer.html`
- Create: `dailyinquirer/static/css/footer.css`

- [ ] **Step 1: Create the footer partial**

Create `core/templates/core/_footer.html`:

```html
<footer class="site-footer">
  <a class="site-footer__wordmark" href="/">The Daily Inquirer</a>
  <span class="site-footer__sep" aria-hidden="true">&middot;</span>
  <span class="site-footer__links">
    <a href="/about/">About</a>
    <a href="/terms/">Terms</a>
    <a href="/privacy/">Privacy</a>
    <a href="mailto:hello@dailyinquirer.me">Contact</a>
  </span>
  <span class="site-footer__sep" aria-hidden="true">&middot;</span>
  <span class="site-footer__copyright">&copy; {% now "Y" %} The Daily Inquirer</span>
</footer>
```

- [ ] **Step 2: Create the footer stylesheet**

Create `dailyinquirer/static/css/footer.css`:

```css
/* Shared site footer. Loaded by core/base.html and registration/auth_base.html. */
.site-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
    gap: 8px 16px;
    padding: 22px 24px;
    border-top: 1px solid var(--rule);
    font-family: var(--body);
    font-size: 0.78rem;
}

.site-footer a {
    color: var(--ink-faint);
    text-decoration: none;
    transition: color 0.12s ease;
}

.site-footer a:hover {
    color: var(--accent);
}

.site-footer a.site-footer__wordmark {
    font-family: var(--display);
    font-size: 0.92rem;
    letter-spacing: 0.01em;
    color: var(--ink);
}

.site-footer a.site-footer__wordmark:hover {
    color: var(--accent);
}

.site-footer__links {
    display: flex;
    gap: 16px;
}

.site-footer__sep {
    color: var(--rule);
}

.site-footer__copyright {
    color: var(--ink-faint);
    font-size: 0.73rem;
}

@media (max-width: 480px) {
    .site-footer {
        flex-direction: column;
        gap: 10px;
    }

    .site-footer__sep {
        display: none;
    }
}

@media (prefers-reduced-motion: reduce) {
    .site-footer a {
        transition: none;
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add core/templates/core/_footer.html dailyinquirer/static/css/footer.css
git commit -m "Add shared site-footer partial and stylesheet"
```

---

## Task 3: Wire the footer into the public/dashboard layout

**Files:**
- Modify: `core/tests.py` (add `FooterTests` class after `AboutPageTests`)
- Modify: `core/templates/core/base.html:15` and `:20-31`
- Modify: `dailyinquirer/static/css/styles.css:68-71` (delete `.footer-link`)

- [ ] **Step 1: Write the failing test**

Add this class to `core/tests.py` immediately after the `AboutPageTests` class:

```python
class FooterTests(TestCase):
    def test_public_pages_render_shared_footer(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'footer.css')
        self.assertContains(response, 'site-footer')
        self.assertContains(response, 'href="/about/"')
        self.assertContains(response, 'mailto:hello@dailyinquirer.me')

    def test_old_footer_link_class_is_gone(self):
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, 'footer-link')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test core.tests.FooterTests.test_public_pages_render_shared_footer`
Expected: FAIL — response does not contain `footer.css`.

- [ ] **Step 3: Load footer.css in base.html**

In `core/templates/core/base.html`, add this line directly after the `tokens.css` link (line 15):

```html
    <link href="/static/css/footer.css" rel="stylesheet">
```

- [ ] **Step 4: Replace the footer markup in base.html**

In `core/templates/core/base.html`, replace the entire block from line 20 (`<div class="container">`) through line 31 (`</div>`):

```html
    <div class="container">
        {% block content %} {% endblock %}
        <div class="row justify-content-between">
            <div class="col">
                <p><!--<a href="/about/" class="footer-link">About</a>--><a href="/terms/" class="footer-link">Terms</a><a href="/privacy/" class="footer-link">Privacy</a></p>
            </div>
<!--        <div class="col text-right">
                <p><a href="#">mack.cloud</a></p>
            </div>
-->
        </div>
    </div>
```

with:

```html
    <div class="container">
        {% block content %} {% endblock %}
    </div>
    {% include "core/_footer.html" %}
```

- [ ] **Step 5: Delete the `.footer-link` rule**

In `dailyinquirer/static/css/styles.css`, delete this block (lines 68-71). Leave the `.about-page` block added in Task 1 in place.

```css
.footer-link {
    margin-left: 4px;
    margin-right: 4px;
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python manage.py test core.tests.FooterTests core.tests.HomePageTests`
Expected: PASS (all tests). `HomePageTests` is included to confirm the home page still renders after the footer change.

- [ ] **Step 7: Commit**

```bash
git add core/templates/core/base.html dailyinquirer/static/css/styles.css core/tests.py
git commit -m "Use the shared footer on public and dashboard pages"
```

---

## Task 4: Wire the footer into the auth layout and verify the suite

**Files:**
- Modify: `core/tests.py` (extend the `FooterTests` class)
- Modify: `templates/registration/auth_base.html:14` and `:24-26`
- Modify: `dailyinquirer/static/css/auth.css:293-319` (delete `.auth-footer` rules) and `:356` (remove one selector)

- [ ] **Step 1: Write the failing test**

Add this method to the `FooterTests` class in `core/tests.py`:

```python
    def test_auth_pages_render_shared_footer(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'footer.css')
        self.assertContains(response, 'site-footer')
        self.assertContains(response, 'href="/about/"')
        self.assertNotContains(response, 'auth-footer')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test core.tests.FooterTests.test_auth_pages_render_shared_footer`
Expected: FAIL — response does not contain `footer.css` (and still contains `auth-footer`).

- [ ] **Step 3: Load footer.css in auth_base.html**

In `templates/registration/auth_base.html`, add this line directly after the `auth.css` link (line 14):

```html
    <link href="/static/css/footer.css" rel="stylesheet">
```

- [ ] **Step 4: Replace the footer markup in auth_base.html**

In `templates/registration/auth_base.html`, replace this block (lines 24-26):

```html
    <footer class="auth-footer">
        <p><a href="/terms/">Terms</a><a href="/privacy/">Privacy</a></p>
    </footer>
```

with:

```html
    {% include "core/_footer.html" %}
```

- [ ] **Step 5: Delete the `.auth-footer` rules from auth.css**

In `dailyinquirer/static/css/auth.css`, delete this entire block (lines 293-319):

```css
.auth-page .auth-footer {
  flex-shrink: 0;
  border-top: 1px solid var(--rule);
  text-align: center;
  padding: 16px 20px;
}

.auth-page .auth-footer p {
  font-family: var(--body);
  font-size: 0.72rem;
  color: var(--ink-faint);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
}

.auth-page .auth-footer a {
  color: var(--ink-faint);
  text-decoration: none;
  transition: color 0.12s ease;
}

.auth-page .auth-footer a:hover {
  color: var(--accent);
}
```

- [ ] **Step 6: Add an auth-scoped shrink rule and fix the reduced-motion block**

In `dailyinquirer/static/css/auth.css`, in the spot the deleted block occupied (between the comment `/* --- Responsive ... */` and the rule above it), add:

```css
/* Shared footer sits at the bottom of the auth flex column. */
.auth-page .site-footer {
  flex-shrink: 0;
}
```

Then, in the `@media (prefers-reduced-motion: reduce)` block, remove the line `  .auth-page .auth-footer a,` so the selector list reads:

```css
@media (prefers-reduced-motion: reduce) {
  .auth-page .auth-btn,
  .auth-page .auth-input,
  .auth-page .auth-wordmark a,
  .auth-page .auth-link {
    transition: none;
  }
```

- [ ] **Step 7: Run the focused tests to verify they pass**

Run: `python manage.py test core.tests.FooterTests core.tests.AuthPagesTests`
Expected: PASS (all tests).

- [ ] **Step 8: Run the full suite**

Run: `python manage.py test`
Expected: PASS — entire suite green (this is exactly what CI runs).

- [ ] **Step 9: Commit**

```bash
git add templates/registration/auth_base.html dailyinquirer/static/css/auth.css core/tests.py
git commit -m "Use the shared footer on auth pages"
```

---

## Manual verification (after Task 4)

Run `python manage.py runserver` and check in a browser:
- `/` (home), `/settings/` (log in first), `/login/`, `/about/` — all show the same one-line footer with a top rule.
- The footer reads: **The Daily Inquirer · About · Terms · Privacy · Contact · © <current year> The Daily Inquirer**.
- Narrow the window below 480px — footer items stack centered and the `·` separators disappear.
- The `Contact` link opens a mail composer to `hello@dailyinquirer.me`.

## Notes

- `hello@dailyinquirer.me` must be provisioned as a real mailbox or forwarding alias for the Contact link to deliver mail. That is a DNS/email-hosting step, outside this plan.
- The daily email footer (`core/templates/core/daily_email.html`) is intentionally untouched — it has its own footer and was not part of this request.
