# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-10-19 17:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0016_auto_20171013_1406'),
    ]

    operations = [
        migrations.AlterField(
            model_name='country',
            name='location_prefix',
            field=models.TextField(db_index=True, help_text='The 2-character location prefix'),
        ),
        migrations.AlterField(
            model_name='country',
            name='name',
            field=models.TextField(help_text='The name of the country'),
        ),
        migrations.AlterField(
            model_name='country',
            name='short_name',
            field=models.TextField(help_text='The short name of the country', null=True),
        ),
    ]
