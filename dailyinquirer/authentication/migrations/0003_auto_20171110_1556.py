# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-10 15:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_user_timezone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='timezone',
            field=models.CharField(max_length=64),
        ),
    ]