# Generated by Django 2.2.16 on 2021-01-21 16:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0130_auto_20210121_1017'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='projectexport',
            name='workflow_job_template_ids',
        ),
    ]
