# Generated by Django 2.1.7 on 2020-01-17 09:51

from django.db import migrations

import utils.models


class Migration(migrations.Migration):
    dependencies = [
        ('problem', '0005_auto_20191023_0958'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contestproblem',
            name='template',
            field=utils.models.MyJSONField(default=[], verbose_name='模板'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='template',
            field=utils.models.MyJSONField(default=[], verbose_name='模板'),
        ),
    ]
