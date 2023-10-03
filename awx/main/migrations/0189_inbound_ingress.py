# Generated by Django 4.2.5 on 2023-10-03 18:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0188_add_bitbucket_dc_webhook'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReceptorAddress',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(max_length=255)),
                ('port', models.IntegerField(null=True)),
                ('protocol', models.CharField(max_length=10)),
                ('websocket_path', models.CharField(blank=True, default='', max_length=255)),
                ('is_internal', models.BooleanField(default=False)),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receptor_addresses', to='main.instance')),
            ],
        ),
    ]
