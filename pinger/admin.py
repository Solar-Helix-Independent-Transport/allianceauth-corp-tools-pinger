from django.contrib import admin

from . import models
from django.conf import settings

from django.utils.html import format_html

admin.site.register(models.Ping)


class DiscordWebhookAdmin(admin.ModelAdmin):
    filter_horizontal = ('ping_types',
                         'corporation_filter',
                         'region_filter',
                         'alliance_filter')

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

    list_display = ['nickname', '_types', '_regions', '_corps', '_allis']


admin.site.register(models.DiscordWebhook, DiscordWebhookAdmin)

admin.site.register(models.PingType)


class SettingsAdmin(admin.ModelAdmin):
    filter_horizontal = ('AllianceLimiter',
                         'CorporationLimiter')


admin.site.register(models.PingerConfig, SettingsAdmin)
