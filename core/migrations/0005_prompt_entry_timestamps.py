import django.utils.timezone
from django.db import migrations, models
from django.db.models import F, OuterRef, Subquery


def backfill_timestamps(apps, schema_editor):
    """Replace today's-date placeholders with real dates.

    The AddField operations above seed every existing row with today's
    date. Here we improve on that using the prompt's mail_day -- the
    date it was scheduled to go out:

    * Prompts use their own mail_day.
    * Entries use the mail_day of the prompt they answer.
    """
    Prompt = apps.get_model('core', 'Prompt')
    Entry = apps.get_model('core', 'Entry')

    Prompt.objects.update(created_at=F('mail_day'), updated_at=F('mail_day'))

    mail_day = Prompt.objects.filter(
        pk=OuterRef('prompt_id')).values('mail_day')[:1]
    Entry.objects.update(
        created_at=Subquery(mail_day), updated_at=Subquery(mail_day))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20171118_2207'),
    ]

    operations = [
        migrations.AddField(
            model_name='prompt',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='prompt',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='entry',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='entry',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(
            backfill_timestamps, migrations.RunPython.noop),
    ]
