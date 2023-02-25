# Generated by Django 3.2.16 on 2023-02-17 02:45

import awx.main.fields
from django.db import migrations
import django.db.models.deletion

from awx.main.migrations import _rbac as rbac
from awx.main.migrations import _migration_utils as migration_utils
from awx.main.migrations import _OrgAdmin_to_use_ig as oamigrate


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0174_ensure_org_ee_admin_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='instancegroup',
            name='admin_role',
            field=awx.main.fields.ImplicitRoleField(
                editable=False,
                null='True',
                on_delete=django.db.models.deletion.CASCADE,
                parent_role=['singleton:system_administrator'],
                related_name='+',
                to='main.role',
            ),
            preserve_default='True',
        ),
        migrations.AddField(
            model_name='instancegroup',
            name='read_role',
            field=awx.main.fields.ImplicitRoleField(
                editable=False,
                null='True',
                on_delete=django.db.models.deletion.CASCADE,
                parent_role=['singleton:system_auditor', 'use_role', 'admin_role'],
                related_name='+',
                to='main.role',
            ),
            preserve_default='True',
        ),
        migrations.AddField(
            model_name='instancegroup',
            name='use_role',
            field=awx.main.fields.ImplicitRoleField(
                editable=False, null='True', on_delete=django.db.models.deletion.CASCADE, parent_role=['admin_role'], related_name='+', to='main.role'
            ),
            preserve_default='True',
        ),
        migrations.RunPython(migration_utils.set_current_apps_for_migrations),
        migrations.RunPython(rbac.create_roles),
        migrations.RunPython(oamigrate.migrate_org_admin_to_use),
    ]
