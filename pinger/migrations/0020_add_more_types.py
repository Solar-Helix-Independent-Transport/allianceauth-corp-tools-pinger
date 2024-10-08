# Generated by Aaron on 2022-01-03

from django.db import migrations


def add_ping_types(apps, schema_editor):
    PingType = apps.get_model('pinger', 'PingType')

    # StructureUnderAttack
    p = PingType.objects.get(name="Orbitals: Skyhook Attacked")
    p.class_tag = "SkyhookUnderAttack"
    p.save()

    PingType.objects.create(name="Structures: Structure Low Reagent",
                            class_tag="StructureLowReagentsAlert")

    PingType.objects.create(name="Structures: Structure No Reagent",
                            class_tag="StructureNoReagentsAlert")


class Migration(migrations.Migration):

    dependencies = [
        ('pinger', '0019_discordwebhook_gas_pings'),
    ]

    operations = [
        migrations.RunPython(add_ping_types)
    ]
