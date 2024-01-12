# Generated by Django 4.2.6 on 2023-12-12 19:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0189_inbound_hop_nodes'),
    ]

    operations = [
        migrations.AddField(
            model_name='instance',
            name='receptor_installation_method',
            field=models.CharField(
                choices=[
                    ('release', 'Install from GitHub release'),
                    ('package', 'Install from RPM package'),
                    ('local', 'Install from local source'),
                    ('container', 'Install via container'),
                ],
                default='release',
                help_text='Select your preferred receptor installation method',
                max_length=16,
            ),
        ),
    ]