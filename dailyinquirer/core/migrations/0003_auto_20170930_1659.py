# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-09-30 16:59
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20170930_1659'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='prompt',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.Prompt'),
        ),
    ]
