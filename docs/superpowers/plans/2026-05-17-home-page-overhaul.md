# Home Page Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain Bootstrap logged-out home page with two complete, distinctive visual themes — Broadsheet and Editorial — switchable via a footer toggle.

**Architecture:** A single template (`core/templates/core/index.html`) renders both theme layouts into the DOM inside a wrapper element. The wrapper carries a `theme-broadsheet` / `theme-editorial` class; CSS shows only the active layout. A footer toggle swaps the class via JS and persists the choice in `localStorage`. No server, view, URL, or model changes.

**Tech Stack:** Django 5.2 templates, plain CSS, vanilla JS (no build step). Existing fonts: `TypoSlab Irregular Demo` (slab serif) and `Open Sans`. Accent color: firebrick (`#b22222`).

**Implementation note on styling tasks:** Tasks 5 and 7 are creative visual work. The implementer MUST invoke the `frontend-design` skill before writing the aesthetic CSS in those tasks. The brainstorming visual companion server may still be running (`.superpowers/brainstorm/`) and can be used to preview.

---

## Design tokens (used by all CSS tasks)

Add these as CSS custom properties at the top of `home.css` on `#home`:

```css
#home {
  --ink: #1a1a1a;
  --ink-soft: #555;
  --ink-faint: #8a8a8a;
  --rule: #d8d4cc;
  --accent: #b22222;        /* firebrick — existing brand */
  --accent-dark: #801919;   /* existing hover shade */
  --paper: #ffffff;
  --serif: 'TypoSlab Irregular Demo', Georgia, 'Times New Roman', serif;
  --body: 'Open Sans', system-ui, sans-serif;
}
```

## Shared page content (identical text in both themes)

- **Name:** The Daily Inquirer
- **Tagline:** a writing prompt email service
- **Primary CTA:** `Get started` → `/register/`
- **Secondary link:** `Already registered? Log in.` → `/login/`
- **How it works (4 steps):**
  1. Receive an email with a writing prompt. — `/static/img/inbox.png`
  2. Reply to the email with your response. — `/static/img/send.png`
  3. Your response is saved to your personal page. — `/static/img/blog.png`
  4. Repeat every day and improve your writing. — `/static/img/cal.png`
- **About (two paragraphs):**
  > This service was created out of a need for [one human](https://mack.cloud) to improve his writing. The best way to improve something is to practice, practice, practice. Free writing has its benefits, but it is easier to write when prompted about something.
  >
  > Use this service to practice your writing, start a personal journal, or find inspiration. If you choose to reply to the email, your response will be saved to this website. Your entries are private — only you can see them.
- **Sample prompt week** (genre — prompt):
  - Monday — Expository — "Explain what pollution is."
  - Tuesday — Descriptive — "Describe your first car."
  - Wednesday — Persuasive — "Can anything be funny, or are some things off limits?"
  - Thursday — Narrative — "Write a story about a family who has a tree with dollar bills for leaves in their backyard."
  - Friday — Free Write — "Happy Friday! Write about whatever you want."
  - Saturday — Creative — "Write a haiku about the mailman."
  - Sunday — Reflective — "Have you ever made a New Year's resolution that you kept?"

---

## Task 1: Add an `extra_head` block to base.html

**Files:**
- Modify: `core/templates/core/base.html`

- [ ] **Step 1: Add the block inside `<head>`**

In `core/templates/core/base.html`, add a block as the last line before `</head>` (after the existing `styles.css` link):

```html
    <link href="/static/css/styles.css" rel="stylesheet">
    {% block extra_head %}{% endblock %}
</head>
```

- [ ] **Step 2: Verify other pages are unaffected**

Run: `python manage.py test core authentication`
Expected: PASS (same result as before — the empty block changes nothing).

- [ ] **Step 3: Commit**

```bash
git add core/templates/core/base.html
git commit -m "Add extra_head block to base template"
```

---

## Task 2: Home page skeleton — wrapper, empty layouts, toggle, asset links

**Files:**
- Modify: `core/templates/core/index.html` (full rewrite)
- Test: `core/tests.py`

- [ ] **Step 1: Write the failing tests**

Append to `core/tests.py`:

```python
from django.urls import reverse


class HomePageTests(TestCase):
    def test_home_renders_both_theme_layouts(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="home"')
        self.assertContains(response, 'broadsheet-layout')
        self.assertContains(response, 'editorial-layout')

    def test_home_loads_theme_assets(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'home.css')
        self.assertContains(response, 'home-theme.js')

    def test_home_has_theme_toggle(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'data-theme="broadsheet"')
        self.assertContains(response, 'data-theme="editorial"')

    def test_other_pages_do_not_load_home_css(self):
        response = self.client.get(reverse('terms'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'home.css')
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python manage.py test core.tests.HomePageTests`
Expected: FAIL — current `index.html` has none of these markers.

- [ ] **Step 3: Rewrite `core/templates/core/index.html`**

Replace the entire file with the skeleton below. The two `*-layout` divs are intentionally near-empty here; Tasks 4 and 6 fill them.

```html
{% extends "core/base.html" %}

{% block extra_head %}
<link href="/static/css/home.css" rel="stylesheet">
<script defer src="/static/js/home-theme.js"></script>
{% endblock %}

{% block content %}
<div id="home" class="theme-broadsheet">

  <div class="broadsheet-layout">
    {# Task 4 fills this in #}
  </div>

  <div class="editorial-layout">
    {# Task 6 fills this in #}
  </div>

  <div class="theme-switch">
    <span class="theme-switch__label">View as</span>
    <button type="button" class="theme-switch__btn" data-theme="broadsheet">Broadsheet</button>
    <span class="theme-switch__sep">·</span>
    <button type="button" class="theme-switch__btn" data-theme="editorial">Editorial</button>
  </div>

</div>
{% endblock %}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python manage.py test core.tests.HomePageTests`
Expected: PASS — all four tests green. (`home.css` and `home-theme.js` files do not exist yet; that is fine, the tests only assert the references are present in the HTML.)

- [ ] **Step 5: Commit**

```bash
git add core/templates/core/index.html core/tests.py
git commit -m "Add home page skeleton with theme wrapper and toggle"
```

---

## Task 3: Theme switching — JS plus functional CSS

This task makes the toggle actually work (show/hide layouts, persist choice). Visual styling comes later; here the layouts just need to appear/disappear.

**Files:**
- Create: `dailyinquirer/static/js/home-theme.js`
- Create: `dailyinquirer/static/css/home.css`

- [ ] **Step 1: Create `dailyinquirer/static/js/home-theme.js`**

```js
(function () {
  'use strict';
  var KEY = 'di-home-theme';
  var THEMES = ['broadsheet', 'editorial'];
  var root = document.getElementById('home');
  if (!root) { return; }

  function apply(theme) {
    if (THEMES.indexOf(theme) === -1) { theme = 'broadsheet'; }
    root.className = 'theme-' + theme;
    var buttons = document.querySelectorAll('[data-theme]');
    for (var i = 0; i < buttons.length; i++) {
      var match = buttons[i].getAttribute('data-theme') === theme;
      buttons[i].classList.toggle('is-active', match);
    }
  }

  var stored = null;
  try { stored = localStorage.getItem(KEY); } catch (e) {}
  apply(stored || 'broadsheet');

  var buttons = document.querySelectorAll('[data-theme]');
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener('click', function () {
      var theme = this.getAttribute('data-theme');
      apply(theme);
      try { localStorage.setItem(KEY, theme); } catch (e) {}
    });
  }
})();
```

- [ ] **Step 2: Create `dailyinquirer/static/css/home.css` with tokens and switching rules**

```css
#home {
  --ink: #1a1a1a;
  --ink-soft: #555;
  --ink-faint: #8a8a8a;
  --rule: #d8d4cc;
  --accent: #b22222;
  --accent-dark: #801919;
  --paper: #ffffff;
  --serif: 'TypoSlab Irregular Demo', Georgia, 'Times New Roman', serif;
  --body: 'Open Sans', system-ui, sans-serif;
}

/* Theme switching: only the active layout is shown. */
#home .broadsheet-layout,
#home .editorial-layout { display: none; }
#home.theme-broadsheet .broadsheet-layout { display: block; }
#home.theme-editorial .editorial-layout { display: block; }

/* Footer theme switch — understated, sits above Terms/Privacy. */
.theme-switch {
  margin: 28px 0 4px;
  text-align: center;
  font-family: var(--body);
  font-size: 0.72rem;
  color: var(--ink-faint);
}
.theme-switch__label {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-right: 8px;
}
.theme-switch__btn {
  background: none;
  border: none;
  padding: 2px 4px;
  font: inherit;
  color: var(--ink-soft);
  cursor: pointer;
  border-bottom: 1px solid transparent;
}
.theme-switch__btn:hover { color: var(--accent); }
.theme-switch__btn.is-active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
.theme-switch__sep { margin: 0 4px; color: var(--rule); }
```

- [ ] **Step 3: Verify switching works in a browser**

Run: `python manage.py runserver`
Open `http://localhost:8000/`. The page is currently near-empty, but:
- The "View as Broadsheet · Editorial" control appears near the bottom; "Broadsheet" is highlighted.
- Click "Editorial" — highlight moves to Editorial.
- Reload the page — Editorial stays highlighted (persisted).
- Click "Broadsheet" — highlight returns; reload confirms persistence.

Expected: toggle highlight and persistence both work.

- [ ] **Step 4: Run the test suite**

Run: `python manage.py test core.tests.HomePageTests`
Expected: PASS (all four still green).

- [ ] **Step 5: Commit**

```bash
git add dailyinquirer/static/js/home-theme.js dailyinquirer/static/css/home.css
git commit -m "Add theme toggle script and switching styles"
```

---

## Task 4: Broadsheet layout markup

Fill the `broadsheet-layout` div with the full newspaper-style structure and content. This task is markup + content only — visual styling is Task 5. Use semantic, clearly-named classes prefixed `bs-`.

**Files:**
- Modify: `core/templates/core/index.html` (the `broadsheet-layout` div)

- [ ] **Step 1: Replace the `broadsheet-layout` div contents**

```html
  <div class="broadsheet-layout">

    <header class="bs-masthead">
      <div class="bs-dateline">
        <span>Vol. I</span>
        <span>{% now "l, F j, Y" %}</span>
        <span>Price: Free</span>
      </div>
      <h1 class="bs-title">The Daily Inquirer</h1>
      <p class="bs-motto">A Writing Prompt, Delivered to Your Inbox Each Morning</p>
    </header>

    <section class="bs-lede">
      <p class="bs-lede__text">
        A fresh writing prompt arrives every day. Reply from your inbox,
        and your words are saved to a private page that is yours alone.
      </p>
      <div class="bs-lede__cta">
        <a class="bs-btn" href="/register/">Get started</a>
        <p class="bs-signin">Already registered? <a href="/login/">Log in.</a></p>
      </div>
    </section>

    <section class="bs-section">
      <h2 class="bs-kicker">How It Works</h2>
      <ol class="bs-steps">
        <li class="bs-step">
          <img src="/static/img/inbox.png" alt="">
          <p><span class="bs-step__num">1.</span> Receive an email with a writing prompt.</p>
        </li>
        <li class="bs-step">
          <img src="/static/img/send.png" alt="">
          <p><span class="bs-step__num">2.</span> Reply to the email with your response.</p>
        </li>
        <li class="bs-step">
          <img src="/static/img/blog.png" alt="">
          <p><span class="bs-step__num">3.</span> Your response is saved to your personal page.</p>
        </li>
        <li class="bs-step">
          <img src="/static/img/cal.png" alt="">
          <p><span class="bs-step__num">4.</span> Repeat every day and improve your writing.</p>
        </li>
      </ol>
    </section>

    <section class="bs-section bs-about">
      <h2 class="bs-kicker">About the Inquirer</h2>
      <div class="bs-about__body">
        <p>This service was created out of a need for
          <a href="https://mack.cloud">one human</a> to improve his writing.
          The best way to improve something is to practice, practice, practice.
          Free writing has its benefits, but it is easier to write when
          prompted about something.</p>
        <p>Use this service to practice your writing, start a personal journal,
          or find inspiration. If you choose to reply to the email, your
          response will be saved to this website. Your entries are private —
          only you can see them.</p>
      </div>
      <figure class="bs-about__figure">
        <img src="/static/img/typing_monkey.png" alt="An illustration of a monkey at a typewriter">
        <figcaption>Practice makes prose.</figcaption>
      </figure>
    </section>

    <section class="bs-section">
      <h2 class="bs-kicker">This Week's Dispatches</h2>
      <div class="bs-prompts">
        <article class="bs-prompt"><h3>Monday</h3><p class="bs-genre">Expository</p><p>Explain what pollution is.</p></article>
        <article class="bs-prompt"><h3>Tuesday</h3><p class="bs-genre">Descriptive</p><p>Describe your first car.</p></article>
        <article class="bs-prompt"><h3>Wednesday</h3><p class="bs-genre">Persuasive</p><p>Can anything be funny, or are some things off limits?</p></article>
        <article class="bs-prompt"><h3>Thursday</h3><p class="bs-genre">Narrative</p><p>Write a story about a family who has a tree with dollar bills for leaves in their backyard.</p></article>
        <article class="bs-prompt"><h3>Friday</h3><p class="bs-genre">Free Write</p><p>Happy Friday! Write about whatever you want.</p></article>
        <article class="bs-prompt"><h3>Saturday</h3><p class="bs-genre">Creative</p><p>Write a haiku about the mailman.</p></article>
        <article class="bs-prompt"><h3>Sunday</h3><p class="bs-genre">Reflective</p><p>Have you ever made a New Year's resolution that you kept?</p></article>
      </div>
    </section>

  </div>
```

- [ ] **Step 2: Verify it renders**

Run: `python manage.py runserver`, open `http://localhost:8000/` with Broadsheet selected.
Expected: all content is visible (unstyled / Bootstrap-default look is fine at this stage). The dateline shows today's date.

- [ ] **Step 3: Run the test suite**

Run: `python manage.py test core.tests.HomePageTests`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/templates/core/index.html
git commit -m "Add Broadsheet layout markup to home page"
```

---

## Task 5: Broadsheet visual styling

**Before starting this task, invoke the `frontend-design` skill.** This is the creative styling of the newspaper theme. Append all rules to `dailyinquirer/static/css/home.css`, every selector prefixed `#home .bs-` so styles cannot leak.

**Files:**
- Modify: `dailyinquirer/static/css/home.css` (append)

- [ ] **Step 1: Style the Broadsheet theme**

Implement CSS that achieves this visual intent (the implementer chooses exact values, guided by frontend-design):

- **Masthead:** `.bs-title` in `var(--serif)`, very large, heavy, centered, tight letter-spacing. Enclose the masthead between a thick double horizontal rule top and bottom (`border-top`/`border-bottom: 3px double var(--ink)`). `.bs-dateline` is a thin row of small uppercase letter-spaced text, justified left/center/right via flexbox, sitting just inside the top rule. `.bs-motto` is small italic serif, centered.
- **Lede:** `.bs-lede__text` set in serif, slightly larger than body, with a drop cap on its first letter (`::first-letter` — large, firebrick, floated). CTA `.bs-btn` is a solid `var(--accent)` block button, white serif text, square corners; hover → `var(--accent-dark)`. `.bs-signin` small and centered.
- **Sections:** `.bs-kicker` is a centered section header in serif with a hairline rule running through or under it. Each `.bs-section` separated by a `1px solid var(--rule)`.
- **Steps:** `.bs-steps` is a 4-column flex/grid row (stack to 2 then 1 column on narrow screens). Images ~64px. `.bs-step__num` is bold firebrick.
- **About:** `.bs-about__body` rendered in two newspaper columns (`column-count: 2; column-gap: 24px`) on wider screens, one column when narrow; first paragraph gets no separate drop cap (the lede already has one) — keep it justified text. `.bs-about__figure` floated or placed beside, image max ~180px, `figcaption` small italic centered.
- **Prompts:** `.bs-prompts` is a multi-column grid (3 across on wide, 2 on medium, 1 on narrow) with thin column rules between, evoking newspaper columns. `.bs-prompt h3` in serif; `.bs-genre` small uppercase italic, firebrick.
- **Responsive:** must look correct from 320px up to the container's 720px max-width.

Use `@media` breakpoints consistent with the existing files (576px, 768px).

- [ ] **Step 2: Visual review in the browser**

Run: `python manage.py runserver`, open `/` in Broadsheet. Optionally use the brainstorm visual companion for a side-by-side check. Resize the window from narrow to wide and confirm the layout holds.
Expected: a cohesive newspaper front page; firebrick accent present; no horizontal scroll at any width.

- [ ] **Step 3: Confirm no leakage**

Open `/terms/` and `/privacy/`.
Expected: unchanged from before — `home.css` is not loaded there, and even if it were, all rules are `#home`-scoped.

- [ ] **Step 4: Commit**

```bash
git add dailyinquirer/static/css/home.css
git commit -m "Style the Broadsheet home page theme"
```

---

## Task 6: Editorial layout markup

Fill the `editorial-layout` div. Markup + content only; styling is Task 7. Classes prefixed `ed-`. Today's prompt card is marked server-side with `{% now "l" %}`.

**Files:**
- Modify: `core/templates/core/index.html` (the `editorial-layout` div)

- [ ] **Step 1: Replace the `editorial-layout` div contents**

```html
  <div class="editorial-layout">
    {% now "l" as today %}

    <header class="ed-hero">
      <p class="ed-kicker">The Daily Inquirer</p>
      <h1 class="ed-headline">Write something <em>worth keeping.</em></h1>
      <p class="ed-sub">One thoughtful writing prompt in your inbox every
        morning. Reply, and your words are saved to a private page that's
        yours alone.</p>
      <div class="ed-cta">
        <a class="ed-btn" href="/register/">Get started — it's free</a>
        <p class="ed-signin">Already registered? <a href="/login/">Log in.</a></p>
      </div>
    </header>

    <section class="ed-section">
      <p class="ed-label">How it works</p>
      <div class="ed-steps">
        <div class="ed-card ed-step">
          <img src="/static/img/inbox.png" alt="">
          <h3>Get a prompt</h3>
          <p>Receive an email with a writing prompt each morning.</p>
        </div>
        <div class="ed-card ed-step">
          <img src="/static/img/send.png" alt="">
          <h3>Write back</h3>
          <p>Reply to the email with your response — no app required.</p>
        </div>
        <div class="ed-card ed-step">
          <img src="/static/img/blog.png" alt="">
          <h3>It's saved</h3>
          <p>Your response is saved to your private personal page.</p>
        </div>
        <div class="ed-card ed-step">
          <img src="/static/img/cal.png" alt="">
          <h3>Keep going</h3>
          <p>Repeat every day and watch your writing improve.</p>
        </div>
      </div>
    </section>

    <section class="ed-section ed-about">
      <p class="ed-label">Why it exists</p>
      <div class="ed-about__grid">
        <div class="ed-about__text">
          <p>This service was created out of a need for
            <a href="https://mack.cloud">one human</a> to improve his writing.
            The best way to improve something is to practice, practice,
            practice. Free writing has its benefits, but it is easier to write
            when prompted about something.</p>
          <p>Use it to practice your writing, start a personal journal, or
            find inspiration. Your entries are private — only you can see them.</p>
        </div>
        <img class="ed-about__img" src="/static/img/typing_monkey.png" alt="An illustration of a monkey at a typewriter">
      </div>
    </section>

    <section class="ed-section">
      <p class="ed-label">A week of prompts</p>
      <div class="ed-prompts">
        <article class="ed-prompt-card{% if today == 'Monday' %} is-today{% endif %}"><p class="ed-day">Monday</p><p class="ed-genre">Expository</p><p class="ed-text">Explain what pollution is.</p></article>
        <article class="ed-prompt-card{% if today == 'Tuesday' %} is-today{% endif %}"><p class="ed-day">Tuesday</p><p class="ed-genre">Descriptive</p><p class="ed-text">Describe your first car.</p></article>
        <article class="ed-prompt-card{% if today == 'Wednesday' %} is-today{% endif %}"><p class="ed-day">Wednesday</p><p class="ed-genre">Persuasive</p><p class="ed-text">Can anything be funny, or are some things off limits?</p></article>
        <article class="ed-prompt-card{% if today == 'Thursday' %} is-today{% endif %}"><p class="ed-day">Thursday</p><p class="ed-genre">Narrative</p><p class="ed-text">Write a story about a family who has a tree with dollar bills for leaves in their backyard.</p></article>
        <article class="ed-prompt-card{% if today == 'Friday' %} is-today{% endif %}"><p class="ed-day">Friday</p><p class="ed-genre">Free Write</p><p class="ed-text">Happy Friday! Write about whatever you want.</p></article>
        <article class="ed-prompt-card{% if today == 'Saturday' %} is-today{% endif %}"><p class="ed-day">Saturday</p><p class="ed-genre">Creative</p><p class="ed-text">Write a haiku about the mailman.</p></article>
        <article class="ed-prompt-card{% if today == 'Sunday' %} is-today{% endif %}"><p class="ed-day">Sunday</p><p class="ed-genre">Reflective</p><p class="ed-text">Have you ever made a New Year's resolution that you kept?</p></article>
      </div>
    </section>

    <section class="ed-final">
      <h2 class="ed-final__title">Your next page is one prompt away.</h2>
      <a class="ed-btn" href="/register/">Get started — it's free</a>
    </section>

  </div>
```

- [ ] **Step 2: Verify it renders**

Run: `python manage.py runserver`, open `/`, switch to Editorial.
Expected: all content visible (unstyled is fine). Exactly one prompt card has the `is-today` class — inspect the DOM and confirm it matches today's weekday.

- [ ] **Step 3: Run the test suite**

Run: `python manage.py test core.tests.HomePageTests`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add core/templates/core/index.html
git commit -m "Add Editorial layout markup to home page"
```

---

## Task 7: Editorial visual styling

**Before starting this task, invoke the `frontend-design` skill.** Append all rules to `dailyinquirer/static/css/home.css`, every selector prefixed `#home .ed-`.

**Files:**
- Modify: `dailyinquirer/static/css/home.css` (append)

- [ ] **Step 1: Style the Editorial theme**

Implement CSS achieving this visual intent (exact values chosen by the implementer via frontend-design):

- **Hero:** `.ed-kicker` small uppercase letter-spaced firebrick text. `.ed-headline` large editorial type (serif via `var(--serif)` or a clean heavy weight), tight line-height; the `<em>` inside is italic and `var(--accent)` — the one colored phrase. `.ed-sub` is `var(--body)`, `var(--ink-soft)`, comfortable measure. Generous vertical whitespace around the hero.
- **CTA:** `.ed-btn` is a pill (fully rounded), solid dark (`var(--ink)`) background, white text, `var(--body)`, with a subtle hover lift (`transform: translateY(-1px)` + shadow). `.ed-signin` small, muted, centered.
- **Labels:** `.ed-label` small uppercase letter-spaced `var(--ink-faint)` — section eyebrow.
- **Cards:** `.ed-card` white, `1px solid` light border, ~8px radius, padding; hover raises border to `var(--accent)` with a thicker bottom edge and a slight lift. `.ed-steps` is a responsive grid: 4 across wide → 2 → 1. Step images ~48px.
- **About:** `.ed-about__grid` two columns (text + image) on wide screens, stacked on narrow. `.ed-about__img` max ~200px, rounded.
- **Prompt cards:** `.ed-prompts` responsive grid (3/2/1). `.ed-prompt-card` like `.ed-card`. `.ed-day` bold, `.ed-genre` small uppercase firebrick, `.ed-text` body. `.ed-prompt-card.is-today` is visually highlighted — firebrick border, subtle tinted background, and a small "Today" marker (add it via CSS, e.g. `.is-today .ed-day::after { content: " · Today"; color: var(--accent); }`).
- **Final CTA:** `.ed-final` centered block with `.ed-final__title` in serif and the pill button repeated.
- **Motion:** keep it subtle — hover transitions ~150ms; respect `@media (prefers-reduced-motion: reduce)` by disabling transforms.
- **Responsive:** correct from 320px to the 720px container max-width; breakpoints at 576px / 768px.

- [ ] **Step 2: Visual review in the browser**

Run: `python manage.py runserver`, open `/`, switch to Editorial. Resize narrow→wide. Confirm today's prompt card is highlighted and shows the "Today" marker.
Expected: a polished modern landing page; firebrick accent present; no horizontal scroll.

- [ ] **Step 3: Commit**

```bash
git add dailyinquirer/static/css/home.css
git commit -m "Style the Editorial home page theme"
```

---

## Task 8: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `python manage.py test`
Expected: PASS — all tests, including `HomePageTests` and the pre-existing `EmailConfirmationTests`.

- [ ] **Step 2: Full manual walkthrough**

Run: `python manage.py runserver`.
- `/` loads in **Broadsheet** by default on a fresh browser profile (clear `localStorage` first, or use a private window).
- Toggle to **Editorial** — layout swaps instantly, no reload.
- Reload — Editorial persists.
- Toggle back to **Broadsheet**, reload — Broadsheet persists.
- Both CTAs reach `/register/`; both "Log in" links reach `/login/`.
- `/terms/`, `/privacy/`, `/login/`, `/register/` are visually unchanged from before this work.
- Check both themes at ~375px (mobile) and ~1200px (desktop) widths — no horizontal scroll, content readable.

- [ ] **Step 3: Confirm clean tree and stop the brainstorm server**

Run: `git status` — expected: clean (everything committed).
If the brainstorm companion server is still running, stop it:
`scripts/stop-server.sh` is in the brainstorming skill directory; or simply leave it — it auto-exits after 30 minutes of inactivity. `.superpowers/` is already gitignored.

---

## Self-review notes

- **Spec coverage:** Broadsheet theme → Tasks 4–5. Editorial theme → Tasks 6–7. Both layouts in one template / wrapper class → Task 2. Footer toggle, preview-only, default Broadsheet, localStorage persistence → Tasks 2–3. `extra_head` block → Task 1. `home.css` / `home-theme.js` new files, `#home`-scoped → Tasks 3, 5, 7. Today's prompt highlighted (Editorial) → Task 6. No view/URL/model change → confirmed; only templates + static. Out-of-scope pages untouched → verified in Tasks 5 and 8.
- **Placeholder scan:** the `{# Task N fills this in #}` comments in Task 2 are deliberate scaffolding, replaced wholesale in Tasks 4 and 6 — not residual placeholders.
- **Type/name consistency:** wrapper id `home`; classes `theme-broadsheet`/`theme-editorial`, `broadsheet-layout`/`editorial-layout`, `data-theme`, `is-active`; localStorage key `di-home-theme`. These names are used identically across the template, JS, and CSS tasks.
