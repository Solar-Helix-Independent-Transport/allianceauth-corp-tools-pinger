from django.core.exceptions import ValidationError
from django.db import models
from allianceauth.eveonline.models import EveAllianceInfo, EveCorporationInfo
from corptools.models import MapRegion
from django.db.models.deletion import CASCADE
from django.utils import timezone
from datetime import timedelta


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


class PingerConfig(models.Model):

    AllianceLimiter = models.ManyToManyField(EveAllianceInfo, blank=True,
                                             help_text='Alliances to put into the queue')
    CorporationLimiter = models.ManyToManyField(EveCorporationInfo, blank=True,
                                                help_text='Corporations to put into the queue')

    min_time_between_updates = models.IntegerField(default=60,
                                                   help_text='Minimmum time between tasks for corp.')

    discord_mute_channels = models.TextField(
        default="", blank=True, help_text='Comma Separated list of channel_ids the mute command can be used in.')

    def save(self, *args, **kwargs):
        if not self.pk and PingerConfig.objects.exists():
            # Force a single object
            raise ValidationError(
                'Only one Settings Model can there be at a time! No Sith Lords there are here!')
        self.pk = self.id = 1  # If this happens to be deleted and recreated, force it to be 1
        return super().save(*args, **kwargs)


class MutedStructure(models.Model):
    structure_id = models.BigIntegerField()
    date_added = models.DateTimeField(auto_now=True)

    def expired(self):
        return timezone.now() > (self.date_added + timedelta(hours=48))
