# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-04-04 18:03
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0006_auto_20180207_1627'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganizationGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_string_representation', models.TextField(blank=True, help_text='The string representation of this object', null=True)),
                ('name', models.TextField(help_text='The description of the organization grouping')),
                ('_org_codes', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), default=list, size=None)),
                ('organizations', models.ManyToManyField(related_name='groups', to='organization.Organization')),
            ],
            options={
                'ordering': ['id'],
                'managed': True,
            },
        ),
    ]
