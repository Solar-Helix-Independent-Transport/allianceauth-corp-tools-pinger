from django.contrib import admin

from . import models

from .models import DiscordWebhook

from django.conf import settings
import requests
import json
from django.contrib import messages

from django.utils.html import format_html
import logging

logger = logging.getLogger(__name__)


class PingAdmin(admin.ModelAdmin):
    list_display = ('time',
                    'ping_sent',
                    'alerting',
                    'notification_id',
                    'hook')


admin.site.register(models.Ping, PingAdmin)


@admin.action(description='Send Test Ping')
def sendTestPing(DiscordWebhook, request, queryset):
    for w in queryset:
        types = w.ping_types.all().values_list('name', flat=True)
        corps = w.corporation_filter.all().values_list('corporation_name', flat=True)
        if len(corps) == 0:
            corps = ["None"]

        allis = w.alliance_filter.all().values_list('alliance_name', flat=True)
        if len(allis) == 0:
            allis = ["None"]

        regions = w.region_filter.all().values_list('name', flat=True)
        if len(regions) == 0:
            regions = ["None"]

        payload = {"embeds": [
            {
                "title": "Ping Channel Test",
                "description": "Configured Notifications:\n\n```{}```".format('\n'.join(types)),
                "color": 10181046,
                "fields": [
                    {
                        "name": "Fuel Levels",
                                "value": "Ping Fuel: {}\nPing LO: {}".format(w.fuel_pings, w.lo_pings)
                    },
                    {
                        "name": "Corportaion Filter",
                                "value": "{}".format('\n'.join(corps))
                    },
                    {
                        "name": "Alliance Filter",
                                "value": "{}".format('\n'.join(allis))
                    },
                    {
                        "name": "Region Filter",
                                "value": "{}".format('\n'.join(regions))
                    }
                ]
            }
        ]
        }
        payload = json.dumps(payload)
        url = w.discord_webhook
        custom_headers = {'Content-Type': 'application/json'}
        response = requests.post(url,
                                 headers=custom_headers,
                                 data=payload,
                                 params={'wait': True})

        if response.status_code in [200, 204]:
            msg = f"{w.nickname}: Test Ping Sent!"
            messages.success(request, msg)
            logger.debug(msg)
        elif response.status_code == 429:

            errors = json.loads(response.content.decode('utf-8'))
            wh_sleep = (int(errors['retry_after']) / 1000) + 0.15
            msg = f"{w.nickname}: rate limited: try again in {wh_sleep} seconds..."
            messages.warning(request, msg)
            logger.warning(msg)
        else:
            msg = f"{w.nickname}: failed ({response.status_code})"
            messages.error(request, msg)
            logger.error(msg)



@admin.action(description='Send Test Ping')
def sendTestPing(DiscordWebhook, request, queryset):
    for w in queryset:
        types = w.ping_types.all().values_list('name', flat=True)
        corps = w.corporation_filter.all().values_list('corporation_name', flat=True)
        if len(corps) == 0:
            corps = ["None"]

        allis = w.alliance_filter.all().values_list('alliance_name', flat=True)
        if len(allis) == 0:
            allis = ["None"]

        regions = w.region_filter.all().values_list('name', flat=True)
        if len(regions) == 0:
            regions = ["None"]

        payload = {"embeds": [
            {
                "title": "Ping Channel Test",
                "description": "Configured Notifications:\n\n```{}```".format('\n'.join(types)),
                "color": 10181046,
                "fields": [
                    {
                        "name": "Fuel Levels",
                                "value": "Ping Fuel: {}\nPing LO: {}".format(w.fuel_pings, w.lo_pings)
                    },
                    {
                        "name": "Corportaion Filter",
                                "value": "{}".format('\n'.join(corps))
                    },
                    {
                        "name": "Alliance Filter",
                                "value": "{}".format('\n'.join(allis))
                    },
                    {
                        "name": "Region Filter",
                                "value": "{}".format('\n'.join(regions))
                    }
                ]
            }
        ]
        }
        payload = json.dumps(payload)
        url = w.discord_webhook
        custom_headers = {'Content-Type': 'application/json'}
        response = requests.post(url,
                                 headers=custom_headers,
                                 data=payload,
                                 params={'wait': True})

        if response.status_code in [200, 204]:
            msg = f"{w.nickname}: Test Ping Sent!"
            messages.success(request, msg)
            logger.debug(msg)
        elif response.status_code == 429:

            errors = json.loads(response.content.decode('utf-8'))
            wh_sleep = (int(errors['retry_after']) / 1000) + 0.15
            msg = f"{w.nickname}: rate limited: try again in {wh_sleep} seconds..."
            messages.warning(request, msg)
            logger.warning(msg)
        else:
            msg = f"{w.nickname}: failed ({response.status_code})"
            messages.error(request, msg)
            logger.error(msg)


class DiscordWebhookAdmin(admin.ModelAdmin):
    filter_horizontal = ('ping_types',
                         'corporation_filter',
                         'region_filter',
                         'alliance_filter')
    actions = [sendTestPing]

    def _list_2_html_w_tooltips(self, my_items: list, max_items: int) -> str:
        """converts list of strings into HTML with cutoff and tooltip"""
        items_truncated_str = format_html('<br> '.join(my_items[:max_items]))
        if not my_items:
            result = None
        elif len(my_items) <= max_items:
            result = items_truncated_str
        else:
            items_truncated_str += format_html('<br> (...)')
            items_all_str = format_html('<br> '.join(my_items))
            result = format_html(
                '<span data-tooltip="{}" class="tooltip">{}</span>',
                items_all_str,
                items_truncated_str
            )
        return result

    def _types(self, obj):
        my_types = [x.name for x in obj.ping_types.order_by('name')]

        return self._list_2_html_w_tooltips(
            my_types,
            10
        )
    _types.short_description = 'Type Filter'

    def _regions(self, obj):
        my_regions = [x.name for x in obj.region_filter.order_by('name')]

        return self._list_2_html_w_tooltips(
            my_regions,
            10
        )
    _regions.short_description = 'Region Filter'

    def _corps(self, obj):
        my_corps = [x.corporation_name for x in obj.corporation_filter.order_by(
            'corporation_name')]

        return self._list_2_html_w_tooltips(
            my_corps,
            10
        )
    _corps.short_description = 'Corporation Filter'

    def _allis(self, obj):
        my_allis = [
            x.alliance_name for x in obj.alliance_filter.order_by('alliance_name')]

        return self._list_2_html_w_tooltips(
            my_allis,
            10
        )
    _allis.short_description = 'Alliance Filter'

    list_display = ['nickname', '_types', 'fuel_pings',
                    'lo_pings', '_regions', '_corps', '_allis']


admin.site.register(models.DiscordWebhook, DiscordWebhookAdmin)

admin.site.register(models.PingType)
admin.site.register(models.FuelPingRecord)


class MuteAdmin(admin.ModelAdmin):
    list_display = ('structure_id',
                    'date_added'
                    )


admin.site.register(models.MutedStructure, MuteAdmin)


class SettingsAdmin(admin.ModelAdmin):
    filter_horizontal = ('AllianceLimiter',
                         'CorporationLimiter')

    def _list_2_html_w_tooltips(self, my_items: list, max_items: int) -> str:
        """converts list of strings into HTML with cutoff and tooltip"""
        items_truncated_str = format_html('<br> '.join(my_items[:max_items]))
        if not my_items:
            result = None
        elif len(my_items) <= max_items:
            result = items_truncated_str
        else:
            items_truncated_str += format_html('<br> (...)')
            items_all_str = format_html('<br> '.join(my_items))
            result = format_html(
                '<span data-tooltip="{}" class="tooltip">{}</span>',
                items_all_str,
                items_truncated_str
            )
        return result

    def _corps(self, obj):
        my_corps = [x.corporation_name for x in obj.CorporationLimiter.order_by(
            'corporation_name')]

        return self._list_2_html_w_tooltips(
            my_corps,
            10
        )
    _corps.short_description = 'Corporation Limiter'

    def _allis(self, obj):
        my_allis = [
            x.alliance_name for x in obj.AllianceLimiter.order_by('alliance_name')]

        return self._list_2_html_w_tooltips(
            my_allis,
            10
        )
    _allis.short_description = 'Alliance Limiter'

    list_display = ['__str__', '_corps', '_allis',
                    "min_time_between_updates", "discord_mute_channels"]


admin.site.register(models.PingerConfig, SettingsAdmin)
