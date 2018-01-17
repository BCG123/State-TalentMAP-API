# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-28 18:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_string_representation', models.TextField(blank=True, help_text='The string representation of this object', null=True)),
                ('code', models.TextField(db_index=True, help_text='The unique country code', unique=True)),
                ('short_code', models.TextField(db_index=True, help_text='The 2-character country code')),
                ('location_prefix', models.TextField(db_index=True, help_text='The 2-character location prefix')),
                ('name', models.TextField(help_text='The name of the country')),
                ('short_name', models.TextField(help_text='The short name of the country', null=True)),
            ],
            options={
                'ordering': ['code'],
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_string_representation', models.TextField(blank=True, help_text='The string representation of this object', null=True)),
                ('code', models.TextField(db_index=True, help_text='The unique location code', unique=True)),
                ('city', models.TextField(blank=True, default='')),
                ('state', models.TextField(blank=True, default='')),
                ('_country', models.TextField(null=True)),
            ],
            options={
                'ordering': ['code'],
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_string_representation', models.TextField(blank=True, help_text='The string representation of this object', null=True)),
                ('code', models.TextField(db_index=True, help_text='The organization code', unique=True)),
                ('long_description', models.TextField(help_text='Long-format description of the organization')),
                ('short_description', models.TextField(help_text='Short-format description of the organization')),
                ('is_bureau', models.BooleanField(default=False, help_text='Boolean indicator if this organization is a bureau')),
                ('is_regional', models.BooleanField(default=False, help_text='Boolean indicator if this organization is regional')),
                ('_parent_organization_code', models.TextField(help_text='Organization Code of the parent Organization', null=True)),
                ('_parent_bureau_code', models.TextField(help_text='Bureau Code of the parent parent Bureau', null=True)),
                ('_location_code', models.TextField(help_text='The location code for this organization', null=True)),
                ('bureau_organization', models.ForeignKey(help_text='The parent Bureau for this organization', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bureau_children', to='organization.Organization')),
            ],
            options={
                'ordering': ['code'],
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_string_representation', models.TextField(blank=True, help_text='The string representation of this object', null=True)),
                ('cost_of_living_adjustment', models.IntegerField(default=0, help_text='Cost of living adjustment number')),
                ('differential_rate', models.IntegerField(default=0, help_text='Differential rate number')),
                ('danger_pay', models.IntegerField(default=0, help_text='Danger pay number')),
                ('rest_relaxation_point', models.TextField(blank=True, help_text='Rest and relaxation point')),
                ('has_consumable_allowance', models.BooleanField(default=False)),
                ('has_service_needs_differential', models.BooleanField(default=False)),
                ('_tod_code', models.TextField(null=True)),
                ('_location_code', models.TextField(null=True)),
                ('location', models.ForeignKey(help_text='The location of the post', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='organization.Location')),
            ],
            options={
                'ordering': ['_location_code'],
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='TourOfDuty',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_string_representation', models.TextField(blank=True, help_text='The string representation of this object', null=True)),
                ('code', models.TextField(db_index=True, help_text='The tour of duty code', unique=True)),
                ('long_description', models.TextField(help_text='Long-format description of the tour of duty')),
                ('short_description', models.TextField(help_text='Short-format description of the tour of duty')),
                ('months', models.IntegerField(default=0, help_text='The number of months for this tour of duty')),
            ],
            options={
                'ordering': ['code'],
                'managed': True,
            },
        ),
        migrations.AddField(
            model_name='post',
            name='tour_of_duty',
            field=models.ForeignKey(help_text='The tour of duty', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='posts', to='organization.TourOfDuty'),
        ),
    ]
