# Generated by Django 4.2.13 on 2024-08-11 01:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pinger', '0018_add_more_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='discordwebhook',
            name='gas_pings',
            field=models.BooleanField(default=False),
        ),
    ]
