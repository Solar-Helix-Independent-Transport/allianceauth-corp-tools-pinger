
import time

from corptools import models as ctm

from allianceauth.eveonline.evelinks import dotlan, eveimageserver, zkillboard

from pinger.notifications.helpers import (
    filter_from_notification, footer_from_notification, get_attacker_string,
    get_item_name_from_id, get_moon_name_from_id,
    get_region_url_from_system_id, get_system_from_id, get_system_url_from_id,
)

from ..exceptions import MutedException
from ..models import MutedStructure
from ..providers import cache_client
from .base import NotificationPing


class TowerAlertMsg(NotificationPing):
    category = "starbase-attack"  # starbase Alerts

    """
    TowerAlertMsg Example

    aggressorAllianceID: 933731581
    aggressorCorpID: 98656901
    aggressorID: 109390934
    armorValue: 0.35075108372869623
    hullValue: 1.0
    moonID: 40255844
    shieldValue: 6.249723757441368e-10
    solarSystemID: 30004040
    typeID: 27786
    """

    def build_ping(self):
        try:
            muted = MutedStructure.objects.get(
                structure_id=self._data['moonID'])
            if muted.expired():
                muted.delete()
            else:
                raise MutedException()
        except MutedStructure.DoesNotExist:
            # no mutes move on
            pass

        system = get_system_from_id(self._data['solarSystemID'])
        system_name = get_system_url_from_id(self._data['solarSystemID'])
        moon = get_moon_name_from_id(self._data['moonID'])
        region_name = get_region_url_from_system_id(self._data['solarSystemID'])
        structure_type = get_item_name_from_id(self._data['typeID'])
        footer = footer_from_notification(self._notification)

        title = "Starbase Under Attack!"
        shld = float(self._data['shieldValue']*100)
        armr = float(self._data['armorValue']*100)
        hull = float(self._data['hullValue']*100)
        body = "Structure under Attack!\n[ S: {0:.2f}% A: {1:.2f}% H: {2:.2f}% ]".format(
            shld, armr, hull)

        attackerStr = get_attacker_string(
            self._data['aggressorID'],
            self._data['aggressorCorpID'],
            self._data.get('aggressorAllianceID', False)
        )

        fields = [
            {
                'name': 'Moon',
                'value': moon,
                'inline': True
            },
            {
                'name': 'System',
                'value': system_name,
                'inline': True
            },
            {
                'name': 'Region',
                'value': region_name,
                'inline': True
            },
            {
                'name': 'Type',
                'value': structure_type,
                'inline': True
            },
            {
                'name': 'Attacker',
                'value': attackerStr,
                'inline': False
            }
        ]

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=15105570
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
            system=system
        )

        if moon:
            epoch_time = int(time.time())
            cache_client.zadd("ctpingermute", {moon: epoch_time})
            rcount = cache_client.zcard("ctpingermute")
            if rcount > 5:
                cache_client.bzpopmin("ctpingermute")


"""
TowerResourceAlertMsg

allianceID: 1900696668
corpID: 680022174
moonID: 40066395
solarSystemID: 30001041
typeID: 16214
wants:
- quantity: 780
  typeID: 4246
"""
