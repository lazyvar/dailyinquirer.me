"""Data migration: seed 30 days of writing prompts (2026-05-18 .. 2026-06-16).

Each prompt's category follows the weekly schedule published in the
"A week of prompts" section of core/templates/core/index.html. Dates that
already have a Prompt are skipped, so the migration is safe to re-apply.
"""
from datetime import datetime, timedelta, timezone

from django.db import migrations

# Weekday (date.weekday(): Monday=0 .. Sunday=6) -> home-page category.
WEEKDAY_CATEGORY = {
    0: 'Expository',
    1: 'Descriptive',
    2: 'Persuasive',
    3: 'Narrative',
    4: 'Free Write',
    5: 'Creative',
    6: 'Reflective',
}

START_DATE = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)

# 30 prompts in date order; each must match the category of its weekday.
QUESTIONS = [
    'Explain how a habit forms, and why it is so hard to break one.',
    'Describe the room you spend the most time in, down to its smallest details.',
    'Should handwriting still be taught in schools? Argue your case.',
    'Write a story that begins with a knock at the door no one expected.',
    'Happy Friday! Write about whatever is on your mind today.',
    'Write a six-word story about a long journey.',
    'What is a piece of advice you ignored, and what happened?',
    'Explain how the internet delivers a web page to your screen.',
    'Describe a meal so vividly that the reader can taste it.',
    'Is it ever acceptable to break a promise? Make your argument.',
    'Write a story in which a character finds a letter addressed to them from ten years ago.',
    "It's Friday. Write freely — no topic, no rules.",
    'Write a haiku about the changing of the seasons.',
    'Describe a moment when you changed your mind about something important.',
    'Explain how compound interest works to someone who has never heard of it.',
    'Describe a storm using only what your five senses notice.',
    'Should remote work be the default for jobs that allow it? Argue your position.',
    'Write a story about the last day of summer.',
    'Happy Friday! Put down whatever words want to come out.',
    'Invent a new holiday and write the speech announcing it.',
    'What is something you were certain about as a child that you now see differently?',
    'Explain how to do something you are good at, step by step.',
    'Describe a stranger you saw recently so clearly a reader could pick them out of a crowd.',
    'Are zoos good or bad for animals? Defend your view.',
    'Write a story where the main character tells a lie that grows out of control.',
    'Friday again — write about anything at all.',
    'Write a short poem from the point of view of an old pair of shoes.',
    'Reflect on a friendship that shaped who you are.',
    'Explain why the sky changes color at sunrise and sunset.',
    'Describe your favorite place at your favorite time of day.',
]


def seed_prompts(apps, schema_editor):
    Prompt = apps.get_model('core', 'Prompt')
    for offset, question in enumerate(QUESTIONS):
        mail_day = START_DATE + timedelta(days=offset)

        already_exists = Prompt.objects.filter(
            mail_day__year=mail_day.year,
            mail_day__month=mail_day.month,
            mail_day__day=mail_day.day,
        ).exists()
        if already_exists:
            continue

        Prompt.objects.create(
            question=question,
            mail_day=mail_day,
            category=WEEKDAY_CATEGORY[mail_day.weekday()],
        )


def unseed_prompts(apps, schema_editor):
    """No-op: reversing must not delete prompts (they may have entries)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_merge_20260517_2159'),
    ]

    operations = [
        migrations.RunPython(seed_prompts, unseed_prompts),
    ]
