from django.db import migrations


def onboard_existing_users(apps, schema_editor):
    User = apps.get_model('authentication', 'User')
    User.objects.update(onboarded=True, mail_time=480)


def noop(apps, schema_editor):
    """Intentionally irreversible: prior onboarded/mail_time values are
    not recorded, so reversing cannot restore them."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0006_onboarding_fields'),
    ]

    operations = [
        migrations.RunPython(onboard_existing_users, noop),
    ]
