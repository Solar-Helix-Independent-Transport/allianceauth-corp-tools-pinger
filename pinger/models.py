import json
import logging
from datetime import timedelta

from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from allianceauth.eveonline.evelinks import dotlan, eveimageserver
from corptools.models import MapRegion, Structure
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.deletion import CASCADE
from django.utils import timezone

logger = logging.getLogger(__name__)


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

    region_filter = models.ManyToManyField(MapRegion,
                                           related_name="region_filters",
                                           blank=True)

    ping_types = models.ManyToManyField(PingType,
                                        blank=True)

    fuel_pings = models.BooleanField(default=False)
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
    lo_level = models.IntegerField(
        null=True, default=None, blank=True)  # ozone level
    last_ping_lo_level = models.IntegerField(
        null=True, default=None, blank=True)  # ozone remaining @last ping
    last_message = models.TextField(default="", blank=True)
    date_empty = models.DateTimeField(
        null=True, default=None, blank=True)  # expiry
    last_ping_time = models.IntegerField(
        null=True, default=None, blank=True)  # hours remaining @last ping

    structure = models.ForeignKey(
        Structure, on_delete=models.CASCADE, null=True, default=None)

    last_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Fuel Ping for: %s" % self.structure.name

    def build_ping_ob(self, message):
        _title = f"{self.structure.name}"

        _system_name = f"[{self.structure.system_name.name}]({dotlan.solar_system_url(self.structure.system_name.name)})"

        _url = eveimageserver.type_icon_url(self.structure.type_id, 64)

        _services = ",".join(self.structure.structureservice_set.filter(
            state='online').values_list('name', flat=True))
        if len(_services) == 0:
            _services = "None"

        corp_ticker = self.structure.corporation.corporation.corporation_ticker
        corp_name = self.structure.corporation.corporation.corporation_name
        corp_id = self.structure.corporation.corporation.corporation_id
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
                  "text": f"{corp_name} ({corp_ticker})"}

        custom_data = {'color': 15158332,
                       'title': _title,
                       'footer': footer,
                       'description': message,
                       'fields': [{'name': 'System',
                                   'value': _system_name,
                                   'inline': False},
                                  ]}

        if self.structure.fuel_expires:
            daysLeft = (self.structure.fuel_expires - timezone.now()).days

            custom_data['fields'].append({'name': 'Fuel Expires',
                                          'value': self.structure.fuel_expires.strftime("%Y-%m-%d %H:%M"),
                                          'inline': True})
            custom_data['fields'].append({'name': 'Days Remaining',
                                          'value': str(daysLeft),
                                          'inline': True})
            custom_data['fields'].append({'name': 'Online Services',
                                          'value': _services,
                                          'inline': False})

        custom_data['image'] = {'url': _url}

        return custom_data

    def ping_task_ob(self, message):
        embed = self.build_ping_ob(message)
        logger.info(
            f"PINGER: FUEL Sending Pings for {self.structure.name}")

        webhooks = DiscordWebhook.objects.filter(fuel_pings=True)\
            .prefetch_related("alliance_filter", "corporation_filter", "region_filter")
        logger.info(
            f"PINGER: FUEL Webhooks {webhooks.count()}")

        for hook in webhooks:
            regions = hook.region_filter.all().values_list("region_id", flat=True)
            alliances = hook.alliance_filter.all().values_list("alliance_id", flat=True)
            corporations = hook.corporation_filter.all(
            ).values_list("corporation_id", flat=True)

            corp_filter = self.structure.corporation.corporation.corporation_id
            alli_filter = self.structure.corporation.corporation.alliance
            if alli_filter:
                alli_filter = alli_filter.alliance_id
            region_filter = self.structure.system_name.constellation.region.region_id

            if corp_filter is not None and len(corporations) > 0:
                if corp_filter not in corporations:
                    logger.info(
                        f"PINGER: FUEL  Skipped {self.structure.name} Corp {corp_filter} not in {corporations}")
                    continue

            if alli_filter is not None and len(alliances) > 0:
                if alli_filter not in alliances:
                    logger.info(
                        f"PINGER: FUEL  Skipped {self.structure.name} Alliance {alli_filter} not in {alli_filter}")
                    continue

            if region_filter is not None and len(regions) > 0:
                if region_filter not in regions:
                    logger.info(
                        f"PINGER: FUEL  Skipped {self.structure.name} Region {region_filter} not in {regions}")
                    continue

            alert = False
            if (self.structure.fuel_expires - timezone.now()).days < 3:
                alert = True
            p = Ping.objects.create(notification_id=-1*self.structure.structure_id,
                                    hook=hook,
                                    body=json.dumps(embed),
                                    time=timezone.now(),
                                    alerting=alert
                                    )
            p.send_ping()


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
        return f"Pinger Configuration"


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
