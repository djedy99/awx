# Generated by Django 2.2.16 on 2021-01-21 07:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0127_auto_20210114_1209'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectexport',
            name='commit_message',
            field=models.CharField(default='', editable=False, help_text='The commit message for this project export.', max_length=1024, verbose_name='Commit Message'),
        ),
    ]
