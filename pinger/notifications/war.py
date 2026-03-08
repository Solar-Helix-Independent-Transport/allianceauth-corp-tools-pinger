from django.utils.html import strip_tags

from pinger.notifications.helpers import (
    filter_from_notification, footer_from_notification, get_eve_name_by_id,
)

from .base import NotificationPing

# WAR stuffs


class WarDeclared(NotificationPing):
    category = "wars"  # Structure Alerts

    """
    WarDeclared

    againstID: 99011747
    cost: 100000000
    declaredByID: 1900696668
    delayHours: 24
    hostileState: false
    timeStarted: 133394547000000000
    warHQ: &lt;b&gt;Keba - The High Sec Initative.&lt;/b&gt;
    warHQ_IdType:
    - 1042059347183
    - 35833
    """

    def build_ping(self):
        footer = footer_from_notification(self._notification)

        title = "War Declared"
        declared_by_name = get_eve_name_by_id(self._data['declaredByID'])
        against_by_name, _ = get_eve_name_by_id(self._data['againstID'])

        body = f"War against `{against_by_name}` declared by `{declared_by_name}`\nWar HQ `{strip_tags(self._data['warHQ'])}`\nFighting can commence in {self._data['delayHours']} hours"

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            footer=footer,
            colour=15158332
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
        )
        self.force_at_ping = False
