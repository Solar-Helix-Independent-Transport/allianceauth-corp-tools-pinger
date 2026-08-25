import json
import logging

import requests

from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html, format_html_join

from . import models
from .utils.discord import _discord_service_installed

logger = logging.getLogger(__name__)


class PingAdmin(admin.ModelAdmin):
    list_display = ("time", "ping_sent", "alerting", "notification_id", "hook")


admin.site.register(models.Ping, PingAdmin)


@admin.action(description="Send Test Ping")
def sendTestPing(DiscordWebhook, request, queryset):
    for w in queryset:
        types = w.ping_types.all().values_list("name", flat=True)
        corps = w.corporation_filter.all().values_list("corporation_name", flat=True)
        if len(corps) == 0:
            corps = ["None"]

        allis = w.alliance_filter.all().values_list("alliance_name", flat=True)
        if len(allis) == 0:
            allis = ["None"]

        regions = w.region_filter.all().values_list("name", flat=True)
        if len(regions) == 0:
            regions = ["None"]

        payload = {
            "embeds": [
                {
                    "title": "Ping Channel Test",
                    "description": "Configured Notifications:\n\n```{}```".format(
                        "\n".join(types)
                    ),
                    "color": 10181046,
                    "fields": [
                        {
                            "name": "Structure Levels",
                            "value": "Ping LO: {}\nPing Gas: {}".format(
                                w.lo_pings, w.gas_pings
                            ),
                        },
                        {
                            "name": "Corportaion Filter",
                            "value": "{}".format("\n".join(corps)),
                        },
                        {
                            "name": "Alliance Filter",
                            "value": "{}".format("\n".join(allis)),
                        },
                        {
                            "name": "Region Filter",
                            "value": "{}".format("\n".join(regions)),
                        },
                    ],
                }
            ]
        }
        payload = json.dumps(payload)
        url = w.discord_webhook
        custom_headers = {"Content-Type": "application/json"}
        response = requests.post(
            url, headers=custom_headers, data=payload, params={"wait": True}
        )

        if response.status_code in [200, 204]:
            msg = f"{w.nickname}: Test Ping Sent!"
            messages.success(request, msg)
            logger.debug(msg)
        elif response.status_code == 429:
            errors = json.loads(response.content.decode("utf-8"))
            wh_sleep = (int(errors["retry_after"]) / 1000) + 0.15
            msg = f"{w.nickname}: rate limited: try again in {wh_sleep} seconds..."
            messages.warning(request, msg)
            logger.warning(msg)
        else:
            msg = f"{w.nickname}: failed ({response.status_code})"
            messages.error(request, msg)
            logger.error(msg)


class DiscordWebhookAdmin(admin.ModelAdmin):
    filter_horizontal = (
        "ping_types",
        "corporation_filter",
        "region_filter",
        "alliance_filter",
    )
    actions = [sendTestPing]

    def _list_2_html_w_tooltips(self, my_items: list, max_items: int) -> str:
        """converts list of strings into HTML with cutoff and tooltip"""
        items_truncated_str = format_html("<br> ".join(my_items[:max_items]))
        if not my_items:
            result = None
        elif len(my_items) <= max_items:
            result = items_truncated_str
        else:
            items_truncated_str += format_html("<br> (...)")
            items_all_str = format_html("<br> ".join(my_items))
            result = format_html(
                '<span data-tooltip="{}" class="tooltip">{}</span>',
                items_all_str,
                items_truncated_str,
            )
        return result

    @admin.display(description="Type Filter")
    def _types(self, obj):
        my_types = [x.name for x in obj.ping_types.order_by("name")]

        return self._list_2_html_w_tooltips(my_types, 10)

    @admin.display(description="Region Filter")
    def _regions(self, obj):
        my_regions = [x.name for x in obj.region_filter.order_by("name")]

        return self._list_2_html_w_tooltips(my_regions, 10)

    @admin.display(description="Corporation Filter")
    def _corps(self, obj):
        my_corps = [
            x.corporation_name
            for x in obj.corporation_filter.order_by("corporation_name")
        ]

        return self._list_2_html_w_tooltips(my_corps, 10)

    @admin.display(description="Alliance Filter")
    def _allis(self, obj):
        my_allis = [
            x.alliance_name for x in obj.alliance_filter.order_by("alliance_name")
        ]

        return self._list_2_html_w_tooltips(my_allis, 10)

    list_display = [
        "nickname",
        "_types",
        "lo_pings",
        "gas_pings",
        "_regions",
        "_corps",
        "_allis",
    ]


admin.site.register(models.DiscordWebhook, DiscordWebhookAdmin)

admin.site.register(models.PingType)


class FuelThresholdForm(forms.ModelForm):
    class Meta:
        model = models.FuelThreshold
        fields = "__all__"

    def clean_ping_groups(self):
        groups = self.cleaned_data["ping_groups"]
        if groups and not _discord_service_installed():
            raise forms.ValidationError(
                "Group mentions require the Alliance Auth Discord service to be installed."
            )
        return groups


class FuelThresholdFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        live = [
            f
            for f in self.forms
            if f.cleaned_data and not f.cleaned_data.get("DELETE", False)
        ]
        if not live:
            raise forms.ValidationError(
                "A fuel ping config needs at least one threshold."
            )


class FuelThresholdInline(admin.StackedInline):
    model = models.FuelThreshold
    form = FuelThresholdForm
    formset = FuelThresholdFormSet
    filter_horizontal = ["ping_groups"]
    ordering = ["-days"]
    extra = 1
    classes = ["fuel-threshold-inline"]

    class Media:
        css = {"all": ("pinger/admin/fuel_thresholds.css",)}

    def get_exclude(self, request, obj=None):
        exclude = list(super().get_exclude(request, obj) or [])
        if not _discord_service_installed():
            exclude.append("ping_groups")
        return exclude


class FuelPingConfigAdmin(admin.ModelAdmin):
    # NOTE: eve_sde models declare `default_permissions = ()`, so the autocomplete
    # endpoints only pass their view-permission check for superusers. The location
    # fields are therefore superuser-editable only.
    autocomplete_fields = ["regions", "constellations", "systems"]
    filter_horizontal = ["webhooks", "structures"]
    inlines = [FuelThresholdInline]
    list_display = [
        "name",
        "always_ping",
        "blocks_broader",
        "_ladder",
        "_locations",
        "_webhooks",
    ]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        formfield = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name == "structures":
            formfield.queryset = formfield.queryset.select_related(
                "system_name"
            ).order_by("name")
            formfield.label_from_instance = lambda obj: (
                f"{obj.name} — {obj.system_name or obj.system_id}"
            )
        return formfield

    @admin.display(description="Thresholds (days)")
    def _ladder(self, obj):
        return ", ".join(str(t.days) for t in obj.thresholds.order_by("-days"))

    @admin.display(description="Locations")
    def _locations(self, obj):
        counts = {
            "regions": obj.regions.count(),
            "constellations": obj.constellations.count(),
            "systems": obj.systems.count(),
            "structures": obj.structures.count(),
        }
        if not any(counts.values()):
            return "Everywhere"
        return ", ".join(f"{n} {label}" for label, n in counts.items() if n)

    @admin.display(description="Webhooks")
    def _webhooks(self, obj):
        hooks = [str(h) for h in obj.webhooks.all()]
        if not hooks:
            return "⚠ none — this config is inert"
        return format_html_join("", "{}<br>", ((h,) for h in hooks))


admin.site.register(models.FuelPingConfig, FuelPingConfigAdmin)


class FuelPingRecordAdmin(admin.ModelAdmin):
    list_display = (
        "structure",
        "config",
        "last_ping_time",
        "date_empty",
        "last_message",
        "last_update",
    )
    list_filter = ("config",)
    search_fields = ("structure__name",)
    ordering = ("structure__name", "config__name")
    list_select_related = ("structure", "config")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(models.FuelPingRecord, FuelPingRecordAdmin)


class MuteAdmin(admin.ModelAdmin):
    list_display = ("structure_id", "date_added")


admin.site.register(models.MutedStructure, MuteAdmin)


class SettingsAdmin(admin.ModelAdmin):
    filter_horizontal = ("AllianceLimiter", "CorporationLimiter")

    def _list_2_html_w_tooltips(self, my_items: list, max_items: int) -> str:
        """converts list of strings into HTML with cutoff and tooltip"""
        items_truncated_str = format_html("<br> ".join(my_items[:max_items]))
        if not my_items:
            result = None
        elif len(my_items) <= max_items:
            result = items_truncated_str
        else:
            items_truncated_str += format_html("<br> (...)")
            items_all_str = format_html("<br> ".join(my_items))
            result = format_html(
                '<span data-tooltip="{}" class="tooltip">{}</span>',
                items_all_str,
                items_truncated_str,
            )
        return result

    @admin.display(description="Corporation Limiter")
    def _corps(self, obj):
        my_corps = [
            x.corporation_name
            for x in obj.CorporationLimiter.order_by("corporation_name")
        ]

        return self._list_2_html_w_tooltips(my_corps, 10)

    @admin.display(description="Alliance Limiter")
    def _allis(self, obj):
        my_allis = [
            x.alliance_name for x in obj.AllianceLimiter.order_by("alliance_name")
        ]

        return self._list_2_html_w_tooltips(my_allis, 10)

    list_display = [
        "__str__",
        "_corps",
        "_allis",
        "min_time_between_updates",
        "discord_mute_channels",
    ]


admin.site.register(models.PingerConfig, SettingsAdmin)
