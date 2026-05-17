# Seed 30 days of writing prompts — design

**Date:** 2026-05-17
**Status:** Approved

## Goal

Create `Prompt` rows for 30 consecutive days so the daily email service
(`send_daily_mail` / `mail_newsletter`) and reply intake (`on_incoming_message`)
have content to serve. Each prompt's category follows the weekly schedule
already published on the home page.

## Category schedule

Taken from the "A week of prompts" section of `core/templates/core/index.html`:

| Weekday | Category |
|---|---|
| Monday | Expository |
| Tuesday | Descriptive |
| Wednesday | Persuasive |
| Thursday | Narrative |
| Friday | Free Write |
| Saturday | Creative |
| Sunday | Reflective |

## Date range

30 consecutive days, **2026-05-18 through 2026-06-16** (the day after this
spec was written). 2026-05-18 is a Monday, so the run starts at the top of the
weekly schedule. Weekday distribution over the 30 days: Expository ×5,
Descriptive ×5, Persuasive/Narrative/Free Write/Creative/Reflective ×4 each.

## Approach

A single Django **data migration** in `core/migrations/`, depending on
`0006_entry_core_entry_author__d99711_idx`. A management command was
considered but the user asked for a migration, and a one-shot seed fits the
migration model.

## Behaviour

1. For each of the 30 dates, derive the weekday and map it to a category via
   the table above.
2. `mail_day` is set to **12:00 UTC** on each date. The matching code
   (`prompt_for_datetime`, `on_incoming_message`) compares only day/month/year;
   noon UTC avoids any date shift under `USE_TZ`.
3. **Idempotent:** skip any date that already has a `Prompt` (matched by
   `mail_day` day/month/year), so the migration is safe to apply against a
   database that already holds prompts for some of those days.
4. `override_html` is left at its model default (blank/null).
5. `created_at` / `updated_at` (from `TimestampedModel`) are populated by
   `auto_now_add` / `auto_now` as normal.
6. `reverse_code` is a no-op — reversing the migration does not delete data
   (safest default; avoids removing prompts that may have collected entries).

## The 30 prompts

Day order, with the category each date resolves to:

| # | Date | Category | Question |
|---|---|---|---|
| 1 | 2026-05-18 Mon | Expository | Explain how a habit forms, and why it is so hard to break one. |
| 2 | 2026-05-19 Tue | Descriptive | Describe the room you spend the most time in, down to its smallest details. |
| 3 | 2026-05-20 Wed | Persuasive | Should handwriting still be taught in schools? Argue your case. |
| 4 | 2026-05-21 Thu | Narrative | Write a story that begins with a knock at the door no one expected. |
| 5 | 2026-05-22 Fri | Free Write | Happy Friday! Write about whatever is on your mind today. |
| 6 | 2026-05-23 Sat | Creative | Write a six-word story about a long journey. |
| 7 | 2026-05-24 Sun | Reflective | What is a piece of advice you ignored, and what happened? |
| 8 | 2026-05-25 Mon | Expository | Explain how the internet delivers a web page to your screen. |
| 9 | 2026-05-26 Tue | Descriptive | Describe a meal so vividly that the reader can taste it. |
| 10 | 2026-05-27 Wed | Persuasive | Is it ever acceptable to break a promise? Make your argument. |
| 11 | 2026-05-28 Thu | Narrative | Write a story in which a character finds a letter addressed to them from ten years ago. |
| 12 | 2026-05-29 Fri | Free Write | It's Friday. Write freely — no topic, no rules. |
| 13 | 2026-05-30 Sat | Creative | Write a haiku about the changing of the seasons. |
| 14 | 2026-05-31 Sun | Reflective | Describe a moment when you changed your mind about something important. |
| 15 | 2026-06-01 Mon | Expository | Explain how compound interest works to someone who has never heard of it. |
| 16 | 2026-06-02 Tue | Descriptive | Describe a storm using only what your five senses notice. |
| 17 | 2026-06-03 Wed | Persuasive | Should remote work be the default for jobs that allow it? Argue your position. |
| 18 | 2026-06-04 Thu | Narrative | Write a story about the last day of summer. |
| 19 | 2026-06-05 Fri | Free Write | Happy Friday! Put down whatever words want to come out. |
| 20 | 2026-06-06 Sat | Creative | Invent a new holiday and write the speech announcing it. |
| 21 | 2026-06-07 Sun | Reflective | What is something you were certain about as a child that you now see differently? |
| 22 | 2026-06-08 Mon | Expository | Explain how to do something you are good at, step by step. |
| 23 | 2026-06-09 Tue | Descriptive | Describe a stranger you saw recently so clearly a reader could pick them out of a crowd. |
| 24 | 2026-06-10 Wed | Persuasive | Are zoos good or bad for animals? Defend your view. |
| 25 | 2026-06-11 Thu | Narrative | Write a story where the main character tells a lie that grows out of control. |
| 26 | 2026-06-12 Fri | Free Write | Friday again — write about anything at all. |
| 27 | 2026-06-13 Sat | Creative | Write a short poem from the point of view of an old pair of shoes. |
| 28 | 2026-06-14 Sun | Reflective | Reflect on a friendship that shaped who you are. |
| 29 | 2026-06-15 Mon | Expository | Explain why the sky changes color at sunrise and sunset. |
| 30 | 2026-06-16 Tue | Descriptive | Describe your favorite place at your favorite time of day. |

## Verification

- `python manage.py migrate` applies cleanly against local SQLite.
- After applying, `Prompt.objects.count()` reflects 30 new rows (or fewer if
  some dates were already populated and skipped).
- Spot-check that each prompt's `category` matches its `mail_day` weekday.
- `python manage.py test` still passes.
