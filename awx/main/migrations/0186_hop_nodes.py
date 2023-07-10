# Generated by Django 4.2 on 2023-05-17 18:31

import django.core.validators
from django.db import migrations, models
from django.conf import settings


def automatically_peer_from_control_plane(apps, schema_editor):
    if settings.IS_K8S:
        Instance = apps.get_model('main', 'Instance')
        Instance.objects.filter(node_type='execution').update(peers_from_control_nodes=True)
        Instance.objects.filter(node_type='control').update(listener_port=None)


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0185_move_JSONBlob_to_JSONField'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='instancelink',
            options={'ordering': ('id',)},
        ),
        migrations.AddField(
            model_name='instance',
            name='peers_from_control_nodes',
            field=models.BooleanField(default=False, help_text='If True, control plane cluster nodes should automatically peer to it.'),
        ),
        migrations.AlterField(
            model_name='instancelink',
            name='link_state',
            field=models.CharField(
                choices=[('adding', 'Adding'), ('established', 'Established'), ('disconnected', 'Disconnected'), ('removing', 'Removing')],
                default='disconnected',
                help_text='Indicates the current life cycle stage of this peer link.',
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name='instancelink',
            constraint=models.CheckConstraint(check=models.Q(('source', models.F('target')), _negated=True), name='source_and_target_can_not_be_equal'),
        ),
        migrations.AlterField(
            model_name='instance',
            name='listener_port',
            field=models.PositiveIntegerField(
                blank=True,
                default=None,
                help_text='Port that Receptor will listen for incoming connections on.',
                null=True,
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)],
            ),
        ),
        migrations.RunPython(automatically_peer_from_control_plane),
    ]
