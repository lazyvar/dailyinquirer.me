# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-18 22:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_auto_20171110_1556'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_subscribed',
            field=models.BooleanField(default=True),
        ),
    ]
