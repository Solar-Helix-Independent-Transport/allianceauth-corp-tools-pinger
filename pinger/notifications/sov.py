import datetime
import logging

from allianceauth.eveonline.evelinks import dotlan, eveimageserver, zkillboard
from corptools import models as ctm

from .base import NotificationPing
from .helpers import (create_timer, filetime_to_dt, format_timedelta,
                      timers_enabled)

logger = logging.getLogger(__name__)


class AllAnchoringMsg(NotificationPing):
    category = "secure-alert"  # SOV ADMIN ALERTS

    """
        AllAnchoringMsg Example

        allianceID: 499005583
        corpID: 1542255499
        moonID: 40290328
        solarSystemID: 30004594
        typeID: 27591
        corpsPresent:
        - allianceID: 1900696668
            corpID: 446274610
            towers:
            - moonID: 40290316
            typeID: 20060
        - allianceID: 1900696668
            corpID: 98549506
            towers:
            - moonID: 40290314
            typeID: 20063

    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])

        system_name = system_db.name
        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['typeID'])
        moon_name, _ = ctm.MapSystemMoon.objects.get_or_create_from_esi(
            self._data['moonID'])

        owner, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['corpID'])

        alliance = "-" if owner.alliance is None else owner.alliance.name
        alliance_id = "-" if owner.alliance is None else owner.alliance.eve_id

        title = "Tower Anchoring!"

        body = (f"{structure_type.name}\n**{moon_name.name}**\n\n[{owner.name}]"
                f"({zkillboard.corporation_url(owner.eve_id)}),"
                f" **[{alliance}]({zkillboard.alliance_url(alliance_id)})**")

        footer = {"icon_url": owner.get_image_url(),
                  "text": f"{owner.name}"}

        fields = []

        for m in self._data['corpsPresent']:
            moons = []
            for moon in m["towers"]:
                _moon_name, _ = ctm.MapSystemMoon.objects.get_or_create_from_esi(
                    moon['moonID'])
                moons.append(_moon_name.name)

            _owner, _ = ctm.EveName.objects.get_or_create_from_esi(m['corpID'])

            fields.append({'name': _owner.name, 'value': "\n".join(moons)})

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=15277667)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id
        self.force_at_ping = True


class SovStructureReinforced(NotificationPing):
    category = "sov-attack"  # Structure Alerts

    """
        SovStructureReinforced Example

        campaignEventType: 2
        decloakTime: 132790589950971525
        solarSystemID: 30004639
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

        title = "Entosis notification"
        body = "Sov Struct Reinforced in %s" % system_name
        sov_type = "Unknown"
        if self._data['campaignEventType'] == 1:
            body = "TCU Reinforced in %s" % system_name
            sov_type = "TCU"
        elif self._data['campaignEventType'] == 2:
            body = "IHub Reinforced in %s" % system_name
            sov_type = "I-HUB"

        ref_time_delta = filetime_to_dt(self._data['decloakTime'])

        tile_till = format_timedelta(
            ref_time_delta.replace(tzinfo=datetime.timezone.utc) - datetime.datetime.now(datetime.timezone.utc))
        alli_id = self._notification.character.character.alliance_id
        alli_ticker = self._notification.character.character.alliance_ticker

        footer = {"icon_url": eveimageserver.alliance_logo_url(alli_id, 64),
                  "text": "%s (%s)" % (self._notification.character.character.alliance_name, alli_ticker)}

        fields = [{'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Region', 'value': region_name, 'inline': True},
                  {'name': 'Time Till Decloaks',
                      'value': tile_till, 'inline': False},
                  {'name': 'Date Out', 'value': ref_time_delta.strftime("%Y-%m-%d %H:%M"), 'inline': False}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=7419530)
        if timers_enabled():
            try:
                from allianceauth.timerboard.models import TimerType

                self.timer = create_timer(
                    sov_type,
                    sov_type,
                    system_db.name,
                    TimerType.HULL,
                    ref_time_delta,
                    self._notification.character.character.corporation
                )
            except Exception as e:
                logger.exception(
                    f"PINGER: Failed to build timer SovStructureReinforced {e}")

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id


class EntosisCaptureStarted(NotificationPing):
    category = "sov-attack"  # Structure Alerts

    """
        EntosisCaptureStarted Example

        solarSystemID: 30004046
        structureTypeID: 32458
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        title = "Entosis Notification"

        body = "Entosis has started in %s on %s" % (
            system_name, structure_type.name)

        alli_id = self._notification.character.character.alliance_id
        alli_ticker = self._notification.character.character.alliance_ticker

        footer = {"icon_url": eveimageserver.alliance_logo_url(alli_id, 64),
                  "text": "%s (%s)" % (self._notification.character.character.alliance_name, alli_ticker)}

        fields = [{'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Region', 'value': region_name, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=15158332)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id
        self.force_at_ping = True


"""
SovStructureDestroyed

solarSystemID: 30001155
structureTypeID: 32458
"""
