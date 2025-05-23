# Generated by Aaron on 2022-01-03

from django.db import migrations


def add_ping_types(apps, schema_editor):
    PingType = apps.get_model('pinger', 'PingType')

    PingType.objects.create(name="Projects: Project Created",
                            class_tag="CorporationGoalCreated")

    PingType.objects.create(name="Projects: Project Closed",
                            class_tag="CorporationGoalClosed")

    PingType.objects.create(name="Projects: Project Completed",
                            class_tag="CorporationGoalCompleted")

    PingType.objects.create(name="Projects: Project Expired",
                            class_tag="CorporationGoalExpired")

    PingType.objects.create(name="Projects: Project Limit Reached",
                            class_tag="CorporationGoalLimitReached")


class Migration(migrations.Migration):

    dependencies = [
        ('pinger', '0020_add_more_types'),
    ]

    operations = [
        migrations.RunPython(add_ping_types)
    ]
