import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

CATCH_ALL_LADDER = (
    (1, "Critical Fuel! :ambulance:", True),
    (2, "Critical Fuel! :ambulance: :eyes:", True),
    (7, "Low Fuel", False),
    (14, "Fuel Warning — {days} days remaining", False),
)


def seed_catch_all(apps, schema_editor):
    DiscordWebhook = apps.get_model("pinger", "DiscordWebhook")
    FuelPingConfig = apps.get_model("pinger", "FuelPingConfig")
    FuelThreshold = apps.get_model("pinger", "FuelThreshold")
    FuelPingRecord = apps.get_model("pinger", "FuelPingRecord")

    config = FuelPingConfig.objects.create(name="Default Fuel Pings", always_ping=False)

    config.webhooks.set(DiscordWebhook.objects.filter(fuel_pings=True))

    for days, message, ping_here in CATCH_ALL_LADDER:
        FuelThreshold.objects.create(
            config=config,
            days=days,
            repeat_days=None,
            message=message,
            color=15158332,
            ping_here=ping_here,
            ping_everyone=False,
        )

    FuelPingRecord.objects.filter(
        models.Q(structure_id__isnull=True) | models.Q(last_ping_time__isnull=True)
    ).delete()

    seen = set()
    stale = []
    for pk, structure_id in FuelPingRecord.objects.order_by(
        "structure_id", "-last_update", "-id"
    ).values_list("id", "structure_id"):
        if structure_id in seen:
            stale.append(pk)
        else:
            seen.add(structure_id)

    if stale:
        FuelPingRecord.objects.filter(id__in=stale).delete()

    FuelPingRecord.objects.update(config=config)


class Migration(migrations.Migration):
    dependencies = [
        ("groupmanagement", "0021_alter_authgroup_group_and_more"),
        ("eve_sde", "0012_alter_constellation_region"),
        ("corptools", "0059_invtypematerials_met_type"),
        ("pinger", "0026_add_more_types"),
    ]

    operations = [
        migrations.CreateModel(
            name="FuelPingConfig",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "always_ping",
                    models.BooleanField(
                        default=False,
                        help_text="Fire whenever this config matches a structure, even if a more specific config also matches.",
                    ),
                ),
                (
                    "blocks_broader",
                    models.BooleanField(
                        default=False,
                        help_text="Suppress more general configs whenever this config matches a structure, even at fuel levels where this config's own thresholds do not ping.",
                    ),
                ),
                (
                    "constellations",
                    models.ManyToManyField(
                        blank=True,
                        related_name="fuel_ping_configs",
                        to="eve_sde.constellation",
                    ),
                ),
                (
                    "regions",
                    models.ManyToManyField(
                        blank=True,
                        related_name="fuel_ping_configs",
                        to="eve_sde.region",
                    ),
                ),
                (
                    "structures",
                    models.ManyToManyField(
                        blank=True,
                        related_name="fuel_ping_configs",
                        to="corptools.structure",
                    ),
                ),
                (
                    "systems",
                    models.ManyToManyField(
                        blank=True,
                        related_name="fuel_ping_configs",
                        to="eve_sde.solarsystem",
                    ),
                ),
                (
                    "webhooks",
                    models.ManyToManyField(
                        help_text="Webhooks this config pings. At least one is required. Each webhook's own corporation / alliance / region filters still apply on top.",
                        related_name="fuel_ping_configs",
                        to="pinger.discordwebhook",
                    ),
                ),
            ],
            options={
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="FuelThreshold",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "days",
                    models.PositiveIntegerField(
                        help_text="Ping when the fuel left drops to this many days, or into the gap below the next threshold down.",
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                (
                    "repeat_days",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        default=None,
                        help_text="Ping every N days where N is the value specified. Leave empty to ping only once on entering the band.",
                        null=True,
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                (
                    "message",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Ping text. Supports {days}, {structure} and {system} for formatting.",
                    ),
                ),
                (
                    "color",
                    models.PositiveIntegerField(
                        default=15158332,
                        help_text="Embed color, as a decimal. Google 'discord color picker' to find the decimal value of the color you like.",
                    ),
                ),
                ("ping_here", models.BooleanField(default=False)),
                ("ping_everyone", models.BooleanField(default=False)),
                (
                    "config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="thresholds",
                        to="pinger.fuelpingconfig",
                    ),
                ),
                (
                    "ping_groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Ping the discord roles matching these groups.",
                        related_name="fuel_thresholds",
                        to="groupmanagement.group",
                    ),
                ),
            ],
            options={
                "default_permissions": (),
            },
        ),
        migrations.AddConstraint(
            model_name="fuelthreshold",
            constraint=models.UniqueConstraint(
                fields=("config", "days"), name="unique_threshold_per_config"
            ),
        ),
        migrations.AddField(
            model_name="ping",
            name="content",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RemoveField(
            model_name="fuelpingrecord",
            name="lo_level",
        ),
        migrations.RemoveField(
            model_name="fuelpingrecord",
            name="last_ping_lo_level",
        ),
        migrations.AddField(
            model_name="fuelpingrecord",
            name="config",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fuel_records",
                to="pinger.fuelpingconfig",
            ),
        ),
        migrations.RunPython(seed_catch_all, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="discordwebhook",
            name="fuel_pings",
        ),
        migrations.AlterField(
            model_name="fuelpingrecord",
            name="config",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="fuel_records",
                to="pinger.fuelpingconfig",
            ),
        ),
        migrations.AlterField(
            model_name="fuelpingrecord",
            name="structure",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="corptools.structure",
            ),
        ),
        migrations.AlterField(
            model_name="fuelpingrecord",
            name="last_ping_time",
            field=models.IntegerField(),
        ),
        migrations.AddConstraint(
            model_name="fuelpingrecord",
            constraint=models.UniqueConstraint(
                fields=("structure", "config"), name="unique_fuel_record_per_config"
            ),
        ),
    ]
