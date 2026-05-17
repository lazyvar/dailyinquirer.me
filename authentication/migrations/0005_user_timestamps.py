import django.utils.timezone
from django.db import migrations, models


def backfill_user_timestamps(apps, schema_editor):
    """Date each user from the earliest prompt they have an entry for.

    The AddField operations above seed every user with today's date.
    A user who has written at least one entry is re-dated to the
    mail_day of the earliest prompt they answered; a user with no
    entries keeps today's date.
    """
    User = apps.get_model('authentication', 'User')
    Entry = apps.get_model('core', 'Entry')

    for user in User.objects.all():
        earliest = (Entry.objects.filter(author=user)
                    .order_by('prompt__mail_day')
                    .values_list('prompt__mail_day', flat=True)
                    .first())
        if earliest is not None:
            User.objects.filter(pk=user.pk).update(
                created_at=earliest, updated_at=earliest)


class Migration(migrations.Migration):
    """Add created_at/updated_at to User.

    The User model has never stored a creation date, so existing rows
    are backfilled from their earliest entry (or today, if they have
    none).
    """

    dependencies = [
        ('authentication', '0004_user_is_subscribed'),
        ('core', '0005_prompt_entry_timestamps'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='user',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(
            backfill_user_timestamps, migrations.RunPython.noop),
    ]
