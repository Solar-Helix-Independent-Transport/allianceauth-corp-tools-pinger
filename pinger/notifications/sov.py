import datetime
import logging

from corptools import models as ctm

from allianceauth.eveonline.evelinks import dotlan, eveimageserver, zkillboard

from .base import NotificationPing
from .helpers import (
    alliance_footer_from_notification, create_timer, filetime_to_dt,
    filter_from_notification, footer_from_notification, format_timedelta,
    get_eve_name_by_id, get_item_name_from_id, get_moon_name_from_id,
    get_planet_name_from_id, get_region_url_from_system_id, get_system_from_id,
    get_system_url_from_id, timers_enabled,
)

logger = logging.getLogger(__name__)


class AllAnchoringMsg(NotificationPing): # NOQA
    """ This no longer works """
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
        system = get_system_from_id(self._data['solarSystemID'])
        moon_name = get_moon_name_from_id(self._data['moonID'])
        structure_type = get_item_name_from_id(self._data['typeID'])
        footer = footer_from_notification(self._notification)
        owner = get_eve_name_by_id(self._data['corpID'])

        alliance = "-" if owner.alliance is None else owner.alliance.name
        alliance_id = "-" if owner.alliance is None else owner.alliance.eve_id

        title = "Tower Anchoring!"

        body = (
            f"{structure_type}\n**{moon_name}**\n\n[{owner}]"
            f"({zkillboard.corporation_url(self._data['corpID'])}),"
            f" **[{alliance}]({zkillboard.alliance_url(alliance_id)})**"
        )

        fields = []

        for m in self._data['corpsPresent']:
            moons = []
            for moon in m["towers"]:
                _moon_name = get_moon_name_from_id(moon['moonID'])
                moons.append(_moon_name)

            _owner = get_eve_name_by_id(m['corpID'])

            fields.append({'name': _owner, 'value': "\n".join(moons)})

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=15277667
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
            system=system
        )
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
        system = get_system_from_id(self._data['solarSystemID'])
        system_name = get_system_url_from_id(self._data['solarSystemID'])
        region_name = get_region_url_from_system_id(self._data['solarSystemID'])
        footer = footer_from_notification(self._notification)

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

        fields = [
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
                'name': 'Time Till Decloaks',
                'value': tile_till,
                'inline': False
            },
            {
                'name': 'Date Out',
                'value': ref_time_delta.strftime("%Y-%m-%d %H:%M"),
                'inline': False
            }
        ]

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=7419530
        )

        if timers_enabled():
            try:
                from allianceauth.timerboard.models import Timer

                self.timer = create_timer(
                    sov_type,
                    sov_type,
                    system.name,
                    Timer.TimerType.HULL,
                    ref_time_delta,
                    self._notification.character.character.corporation
                )
            except Exception as e:
                logger.exception(
                    f"PINGER: Failed to build timer SovStructureReinforced {e}")

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
            system=system
        )


class EntosisCaptureStarted(NotificationPing):
    category = "sov-attack"  # Structure Alerts

    """
        EntosisCaptureStarted Example

        solarSystemID: 30004046
        structureTypeID: 32458
    """

    def build_ping(self):
        system = get_system_from_id(self._data['solarSystemID'])
        system_name = get_system_url_from_id(self._data['solarSystemID'])
        region_name = get_region_url_from_system_id(self._data['solarSystemID'])
        structure_type = get_item_name_from_id(self._data['structureTypeID'])
        footer = alliance_footer_from_notification(self._notification)

        title = "Entosis Notification"

        body = "Entosis has started in %s on %s" % (
            system_name, structure_type)

        fields = [
            {
                'name': 'System',
                'value': system_name,
                'inline': True
            },
            {
                'name': 'Region',
                'value': region_name,
                'inline': True
            }
        ]

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=15158332
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
            system=system
        )
        self.force_at_ping = True


"""
SovStructureDestroyed

solarSystemID: 30001155
structureTypeID: 32458
"""
