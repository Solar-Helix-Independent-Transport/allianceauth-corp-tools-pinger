import datetime
import json
import logging
from datetime import timedelta
from string import Formatter
from typing import TYPE_CHECKING, ClassVar

from corptools.models import Structure
from corptools.models.audits import CharacterAudit
from eve_sde.models import Constellation, Region, SolarSystem

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from allianceauth.groupmanagement.models import Group

from .utils.discord import build_fuel_embed, role_id_for_group

logger = logging.getLogger(__name__)

DEFAULT_FUEL_PING_COLOR = 15158332

# The `str.format` keys `FuelThreshold.message` may use.
MESSAGE_FORMAT_KEYS = frozenset(["days", "structure", "system"])


class FuelPingConfigQuerySet(models.QuerySet["FuelPingConfig"]):
    def usable(self):
        """Configs that name at least one webhook."""
        return self.filter(webhooks__isnull=False).distinct()

    def matching(
        self, structure: Structure, days_left: int
    ) -> list[tuple["FuelPingConfig", "FuelThreshold"]]:
        """The configs that should ping for `structure`, each with its triggered threshold.

        A config raises the specificity bar only when it would actually ping, or when it
        is flagged `blocks_broader`. Every config that pings at the resulting bar fires,
        plus every `always_ping` config that pings at all.
        """
        hits = [
            (config, level, config.threshold_for(days_left))
            for config in self
            if (level := config.level_for(structure)) is not None
        ]

        bar = max(
            (
                level
                for config, level, threshold in hits
                if threshold is not None or config.blocks_broader
            ),
            default=None,
        )
        if bar is None:
            return []

        return [
            (config, threshold)
            for config, level, threshold in hits
            if threshold is not None and (level == bar or config.always_ping)
        ]


class FuelPingConfigManager(models.Manager["FuelPingConfig"]):
    def get_queryset(self) -> FuelPingConfigQuerySet:
        return FuelPingConfigQuerySet(self.model, using=self._db)

    def usable(self) -> FuelPingConfigQuerySet:
        return self.get_queryset().usable()

    def matching(
        self, structure, days_left: int
    ) -> list[tuple["FuelPingConfig", "FuelThreshold"]]:
        return self.get_queryset().matching(structure, days_left)


def _webhook_passes_filters(hook, corp_id=None, alli_id=None, region_id=None):
    corporations = hook.corporation_filter.all().values_list("corporation_id", flat=True) if corp_id is not None else []
    alliances = hook.alliance_filter.all().values_list("alliance_id", flat=True) if alli_id is not None else []

    if len(corporations) > 0 or len(alliances) > 0:
        corp_match = len(corporations) > 0 and corp_id in corporations
        alli_match = len(alliances) > 0 and alli_id in alliances
        if not corp_match and not alli_match:
            return False
    if region_id is not None:
        regions = hook.region_filter.all().values_list("id", flat=True)
        if len(regions) > 0 and region_id not in regions:
            return False
    return True


class PingType(models.Model):
    name = models.CharField(max_length=100)
    class_tag = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class DiscordWebhook(models.Model):
    nickname = models.TextField(default="Discord Webhook")
    discord_webhook = models.TextField()

    corporation_filter = models.ManyToManyField(EveCorporationInfo,
                                                related_name="corp_filters",
                                                blank=True)

    alliance_filter = models.ManyToManyField(EveAllianceInfo,
                                             related_name="alli_filters",
                                             blank=True)

    region_filter = models.ManyToManyField(Region,
                                           related_name="region_filters",
                                           blank=True)

    ping_types = models.ManyToManyField(PingType,
                                        blank=True)

    lo_pings = models.BooleanField(default=False)
    gas_pings = models.BooleanField(default=False)

    no_at_pings = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nickname} - {self.discord_webhook[-10:]}"


class Ping(models.Model):
    notification_id = models.BigIntegerField()
    hook = models.ForeignKey(DiscordWebhook, on_delete=models.CASCADE)
    body = models.TextField()
    time = models.DateTimeField()
    ping_sent = models.BooleanField(default=False)
    alerting = models.BooleanField(default=False)
    content = models.TextField(default="", blank=True)

    def __str__(self):
        return "%s, %s" % (self.notification_id, str(self.time.strftime("%Y %m %d %H:%M:%S")))

    class Meta:
        indexes = (
            models.Index(fields=['notification_id']),
            models.Index(fields=['time']),
        )

    def send_ping(self):
        from . import tasks
        tasks.send_ping.apply_async(
            priority=2,
            args=[
                self.id
            ]
        )


class FuelPingRecord(models.Model):
    structure = models.ForeignKey(Structure, on_delete=models.CASCADE)

    config = models.ForeignKey(
        "FuelPingConfig", on_delete=models.CASCADE, related_name="fuel_records"
    )

    last_message = models.TextField(default="", blank=True)  # admin readability only
    date_empty = models.DateTimeField(
        null=True, default=None, blank=True
    )  # the fuel_expires this row is about
    last_ping_time = models.IntegerField()  # days remaining @last ping

    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["structure", "config"], name="unique_fuel_record_per_config"
            )
        ]

    def __str__(self):
        return "Fuel Ping for: %s" % self.structure.name


class FuelPingConfig(models.Model):
    name = models.CharField(max_length=100)

    regions = models.ManyToManyField(
        Region, related_name="fuel_ping_configs", blank=True
    )

    constellations = models.ManyToManyField(
        Constellation, related_name="fuel_ping_configs", blank=True
    )

    systems = models.ManyToManyField(
        SolarSystem, related_name="fuel_ping_configs", blank=True
    )

    structures = models.ManyToManyField(
        Structure, related_name="fuel_ping_configs", blank=True
    )

    webhooks = models.ManyToManyField(
        DiscordWebhook,
        related_name="fuel_ping_configs",
        help_text="Webhooks this config pings. At least one is required. "
        "Each webhook's own corporation / alliance / region "
        "filters still apply on top.",
    )

    always_ping = models.BooleanField(
        default=False,
        help_text="Fire whenever this config matches a structure, even if a more specific config also "
        "matches.",
    )

    blocks_broader = models.BooleanField(
        default=False,
        help_text="Suppress more general configs whenever this config matches a structure, "
        "even at fuel levels where this config's own thresholds do not ping.",
    )

    objects: ClassVar[FuelPingConfigManager] = FuelPingConfigManager()

    if TYPE_CHECKING:
        thresholds: models.manager.RelatedManager["FuelThreshold"]

    class Meta:
        default_permissions = ()

    def __str__(self):
        return self.name

    def level_for(self, structure: Structure):
        """4 = structure, 3 = system, 2 = constellation, 1 = region, 0 = catch-all, None = no match."""
        structure_ids = {s.id for s in self.structures.all()}
        if structure.pk in structure_ids:
            return 4

        region_ids = {r.pk for r in self.regions.all()}
        constellation_ids = {c.pk for c in self.constellations.all()}
        system_ids = {s.pk for s in self.systems.all()}
        system = structure.system_name
        if system is not None:
            if system.pk in system_ids:
                return 3
            constellation = system.constellation
            if constellation is not None:
                if constellation.pk in constellation_ids:
                    return 2
                if constellation.region_id in region_ids:
                    return 1

        if not (structure_ids or system_ids or constellation_ids or region_ids):
            return 0  # no locations configured, this is a catch-all

        return None

    def threshold_for(self, days: int) -> "FuelThreshold | None":
        """The threshold with the smallest `days` >= `days`; None if above all thresholds."""
        return min(
            (t for t in self.thresholds.all() if t.days >= days),
            key=lambda t: t.days,
            default=None,
        )

    def send_fuel_ping(self, structure: "Structure", threshold: "FuelThreshold", days_left: int):
        system = structure.system_name
        message = threshold.message.format(
            days=days_left,
            structure=structure.name,
            system=system.name if system is not None else "Unknown",
        )

        embed = build_fuel_embed(structure, message, threshold.color, days_left)

        corp = structure.corporation.corporation
        alli = corp.alliance
        region_id = None
        if system is not None and system.constellation is not None:
            region_id = system.constellation.region_id

        webhooks = [
            hook
            for hook in self.webhooks.all()
            if _webhook_passes_filters(
                hook, corp.corporation_id, alli.alliance_id if alli else None, region_id
            )
        ]
        logger.info(
            f"PINGER: FUEL Sending Pings for {structure.name} to {len(webhooks)} webhooks"
        )

        content = threshold.build_mention_content()
        body = json.dumps(embed)

        for hook in webhooks:
            p = Ping.objects.create(
                notification_id=-1 * structure.structure_id,
                hook=hook,
                body=body,
                time=timezone.now(),
                alerting=bool(content),
                content=content,
            )
            p.send_ping()


class FuelThreshold(models.Model):
    config = models.ForeignKey(
        FuelPingConfig, on_delete=models.CASCADE, related_name="thresholds"
    )

    days = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Ping when the fuel left drops to this many days, or into the gap "
        "below the next threshold down.",
    )

    repeat_days = models.PositiveSmallIntegerField(
        null=True,
        default=None,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Ping every N days where N is the value specified. Leave empty to ping only once on entering the band.",
    )

    message = models.TextField(
        blank=True,
        default="",
        help_text="Ping text. Supports {days}, {structure} and {system} for formatting.",
    )

    color = models.PositiveIntegerField(
        default=DEFAULT_FUEL_PING_COLOR, help_text="Embed color, as a decimal. Google 'discord color picker' to find the decimal value of the color you like."
    )

    ping_groups = models.ManyToManyField(
        Group,
        related_name="fuel_thresholds",
        blank=True,
        help_text="Ping the discord roles matching these groups."
    )

    ping_here = models.BooleanField(default=False)
    ping_everyone = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["config", "days"], name="unique_threshold_per_config"
            )
        ]

    def __str__(self):
        return f"{self.days} days"

    def clean(self):
        super().clean()

        try:
            keys = {
                field
                for _, field, _, _ in Formatter().parse(self.message or "")
                if field is not None
            }
        except ValueError as e:
            raise ValidationError({"message": f"Malformed substitution: {e}"})

        unknown = keys - MESSAGE_FORMAT_KEYS
        if unknown:
            raise ValidationError(
                {
                    "message": "Unknown substitution(s) {}. Allowed: {}.".format(
                        ", ".join(f"{{{k}}}" for k in sorted(unknown)),
                        ", ".join(f"{{{k}}}" for k in sorted(MESSAGE_FORMAT_KEYS)),
                    )
                }
            )

    def build_mention_content(self) -> str:
        """The `content` line of a fuel ping: @everyone, then @here, then one mention per group."""
        mentions = []

        if self.ping_everyone:
            mentions.append("@everyone")
        if self.ping_here:
            mentions.append("@here")

        for group in self.ping_groups.all():
            role_id = role_id_for_group(group)
            if role_id:
                mentions.append(f"<@&{role_id}>")

        return " ".join(mentions)


class PingerConfig(models.Model):

    AllianceLimiter = models.ManyToManyField(EveAllianceInfo, blank=True,
                                             help_text='Alliances to put into the queue')
    CorporationLimiter = models.ManyToManyField(EveCorporationInfo, blank=True,
                                                help_text='Corporations to put into the queue')

    min_time_between_updates = models.IntegerField(default=60,
                                                   help_text='Minimmum time between tasks for corp.')

    discord_mute_channels = models.TextField(
        default="",
        blank=True,
        help_text='Comma Separated list of channel_ids the mute command can be used in.'
    )

    attack_command_output_id = models.BigIntegerField(
        default=0,
        blank=True,
        help_text='discord channel_id that the /attack command outputs too.'
    )

    def save(self, *args, **kwargs):
        if not self.pk and PingerConfig.objects.exists():
            # Force a single object
            raise ValidationError(
                'Only one Settings Model can there be at a time! No Sith Lords there are here!')
        self.pk = self.id = 1  # If this happens to be deleted and recreated, force it to be 1
        return super().save(*args, **kwargs)

    def __str__(self):
        return "Pinger Configuration"


class MutedStructure(models.Model):
    structure_id = models.BigIntegerField()
    date_added = models.DateTimeField(auto_now=True)

    def expired(self):
        return timezone.now() > (self.date_added + timedelta(hours=48))

    def __str__(self):
        return f"{self.structure_id}"


class StructureLoThreshold(models.Model):
    structure = models.OneToOneField(
        Structure, related_name="lo_th", on_delete=models.CASCADE)
    low = models.IntegerField(default=1500000)
    critical = models.IntegerField(default=250000)

    def __str__(self):
        return f"{self.structure.name}"


class Notification:
    character: CharacterAudit
    notification_id: int
    timestamp: datetime.datetime
    notification_type: str
    notification_text: str

    def __init__(self, character: CharacterAudit, notification_id: int, timestamp: datetime.datetime, notification_type: str, notification_text: str):
        self.character = character
        self.notification_id = notification_id
        self.timestamp = timestamp
        self.notification_type = notification_type
        self.notification_text = notification_text
