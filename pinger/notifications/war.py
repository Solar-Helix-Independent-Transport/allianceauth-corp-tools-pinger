from allianceauth.eveonline.evelinks import eveimageserver
from corptools import models as ctm
from django.utils.html import strip_tags

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
        title = "War Declared"
        declared_by_name, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['declaredByID'])
        against_by_name, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['againstID'])
        body = f"War against `{against_by_name}` declared by `{declared_by_name}`\nWar HQ `{strip_tags(self._data['warHQ'])}`\nFighting can commence in {self._data['delayHours']} hours"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          footer=footer,
                          colour=15158332)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self.force_at_ping = False
