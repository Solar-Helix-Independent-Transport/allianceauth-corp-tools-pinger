
import datetime
import logging

from corptools import models as ctm

from django.utils import timezone

from allianceauth.eveonline.evelinks import dotlan, eveimageserver, zkillboard

from .base import NotificationPing
from .helpers import (
    create_timer, filetime_to_dt, filter_from_notification,
    footer_from_notification, format_timedelta, get_attacker_string,
    get_eve_name_by_id, get_item_name_from_id, get_planet_name_from_id,
    get_region_url_from_system_id, get_system_from_id, get_system_url_from_id,
    time_till_out, time_till_to_td, timers_enabled,
)

logger = logging.getLogger(__name__)


class OrbitalAttacked(NotificationPing):
    category = "orbital-attack"  # Structure Alerts

    """
    aggressorAllianceID: null
    aggressorCorpID: 98729563
    aggressorID: 90308296
    planetID: 40066681
    planetTypeID: 2016
    shieldLevel: 0.0
    solarSystemID: 30001046
    typeID: 2233
    """

    def build_ping(self):
        system = get_system_from_id(self._data['solarSystemID'])
        planet_name = get_planet_name_from_id(self._data['planetID'])
        system_name = get_system_url_from_id(self._data['solarSystemID'])
        region_name = get_region_url_from_system_id(self._data['solarSystemID'])
        structure_type = get_item_name_from_id(self._data['typeID'])
        footer = footer_from_notification(self._notification)

        title = "Poco Under Attack"

        shld = float(self._data['shieldLevel'])*100

        body = "{} under Attack!\nShield Level: {:.2f}%".format(
            structure_type, shld)

        attackerStr = get_attacker_string(
            self._data['aggressorID'],
            self._data['aggressorCorpID'],
            self._data['aggressorAllianceID']
        )

        fields = [
            {
                'name': 'System/Planet',
                'value': f"{system_name} - {planet_name}",
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
            colour=15158332
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
            system=system
        )
        self.force_at_ping = True


class OrbitalReinforced(NotificationPing):
    category = "orbital-attack"  # orbital-attack

    """
    aggressorAllianceID: null
    aggressorCorpID: 98183625
    aggressorID: 94416120
    planetID: 40066687
    planetTypeID: 2016
    reinforceExitTime: 133307777010000000
    solarSystemID: 30001046
    typeID: 2233
    """

    def build_ping(self):
        system = get_system_from_id(self._data['solarSystemID'])
        planet_name = get_planet_name_from_id(self._data['planetID'])
        system_name = get_system_url_from_id(self._data['solarSystemID'])
        region_name = get_region_url_from_system_id(self._data['solarSystemID'])
        structure_type = get_item_name_from_id(self._data['typeID'])
        footer = footer_from_notification(self._notification)

        _timeTill = filetime_to_dt(self._data['reinforceExitTime']).replace(
            tzinfo=datetime.timezone.utc)
        _refTimeDelta = _timeTill - timezone.now()
        tile_till = format_timedelta(_refTimeDelta)

        title = "Skyhook Reinforced"
        body = f"{structure_type} has lost its Shields"

        fields = [
            {
                'name': 'System/Planet',
                'value': f"{system_name} - {planet_name}",
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
                'name': 'Owner',
                'value': self._notification.character.character.corporation_name,
                'inline': False
            },
            {
                'name': 'Time Till Out',
                'value': tile_till,
                'inline': False
            },
            {
                'name': 'Date Out',
                'value': _timeTill.strftime("%Y-%m-%d %H:%M"),
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
                    f"{planet_name} POCO",
                    structure_type,
                    system.name,
                    Timer.TimerType.ARMOR,
                    _timeTill,
                    self._notification.character.character.corporation
                )
            except Exception as e:
                logger.exception(
                    f"PINGER: Failed to build timer OrbitalReinforced {e}")

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
            system=system
        )


class SkyhookUnderAttack(NotificationPing):
    category = "orbital-attack"  # orbital-attack

    """
        allianceID: 1900696668
        allianceLinkData:
        - showinfo
        - 16159
        - 1900696668
        allianceName: The Initiative.
        armorPercentage: 100.0
        charID: 90406623
        corpLinkData:
        - showinfo
        - 2
        - 98434316
        corpName: Tactically Challenged
        hullPercentage: 100.0
        isActive: true
        itemID: &id001 1045736027496
        planetID: 40290676
        planetShowInfoData:
        - showinfo
        - 2015
        - 40290676
        shieldPercentage: 94.98293275026545
        skyhookShowInfoData:
        - showinfo
        - 81080
        - *id001
        solarsystemID: 30004600
        typeID: 81080
    """

    def build_ping(self):
        system = get_system_from_id(self._data['solarsystemID'])
        planet_name = get_planet_name_from_id(self._data['planetID'])
        system_name = get_system_url_from_id(self._data['solarsystemID'])
        region_name = get_region_url_from_system_id(self._data['solarsystemID'])
        structure_type = get_item_name_from_id(self._data['typeID'])
        footer = footer_from_notification(self._notification)

        attackerStr = get_attacker_string(
            self._data['charID'],
            self._data['corpLinkData'][2],
            self._data['allianceID']
        )


        title = "Skyhook Under Attack"

        body = "{} - {} under Attack!\nS: {:.2f}%, A: {:.2f}%, H: {:.2f}%".format(
            structure_type,
            f"{system_name} - {planet_name}",
            float(self._data['shieldPercentage']),
            float(self._data['armorPercentage']),
            float(self._data['hullPercentage']))

        fields = [
            {
                'name': 'System/Planet',
                'value': f"{system_name} - {planet_name}",
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
            colour=15158332
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
            system=system
        )
        self.force_at_ping = True


class SkyhookLostShields(NotificationPing):
    category = "orbital-attack"  # orbital-attack

    """
    itemID: &id001 1046042982766
    planetID: 40288591
    planetShowInfoData:
    - showinfo
    - 2017
    - 40288591
    skyhookShowInfoData:
    - showinfo
    - 81080
    - *id001
    solarsystemID: 30004563
    timeLeft: 1859680938756               # figure out what this is
    timestamp: 133690999080000000         # figure out what this is
    typeID: 81080
    vulnerableTime: 9000000000            # figure out what this is
    """

    def build_ping(self):
        system = get_system_from_id(self._data['solarsystemID'])
        planet_name = get_planet_name_from_id(self._data['planetID'])
        system_name = get_system_url_from_id(self._data['solarsystemID'])
        region_name = get_region_url_from_system_id(self._data['solarsystemID'])
        structure_type = get_item_name_from_id(self._data['typeID'])
        footer = footer_from_notification(self._notification)

        _timeTill = filetime_to_dt(self._data['timestamp']).replace(
            tzinfo=datetime.timezone.utc)
        _refTimeDelta = _timeTill - timezone.now()
        tile_till = format_timedelta(_refTimeDelta)

        title = "Skyhook Reinforced"
        body = f"{structure_type} has lost its Shields"

        fields = [
            {
                'name': 'System/Planet',
                'value': f"{system_name} - {planet_name}",
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
                'name': 'Owner',
                'value': self._notification.character.character.corporation_name,
                'inline': False
            },
            {
                'name': 'Time Till Out',
                'value': tile_till,
                'inline': False
            },
            {
                'name': 'Date Out',
                'value': _timeTill.strftime("%Y-%m-%d %H:%M"),
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
                    f"{planet_name} Skyhook",
                    structure_type,
                    system_name,
                    Timer.TimerType.ARMOR,
                    _timeTill,
                    self._notification.character.character.corporation
                )
            except Exception as e:
                logger.exception(
                    f"PINGER: Failed to build timer SkyhookLostShields {e}")

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
            system=system
        )


class SkyhookOnline(NotificationPing):
    category = "orbital-attack"  # orbital-attack

    """
        itemID: &id002 1046336471456
        planetID: &id001 40288233
        planetShowInfoData:
        - showinfo
        - 13
        - *id001
        skyhookShowInfoData:
        - showinfo
        - 81080
        - *id002
        solarsystemID: 30004557
        typeID: 81080
    """

    def build_ping(self):
        system = get_system_from_id(self._data['solarsystemID'])
        planet_name = get_planet_name_from_id(self._data['planetID'])
        system_name = get_system_url_from_id(self._data['solarsystemID'])
        region_name = get_region_url_from_system_id(self._data['solarsystemID'])
        structure_type = get_item_name_from_id(self._data['typeID'])
        footer = footer_from_notification(self._notification)

        title = "Skyhook Online"
        body = "{} - {} - {} Online".format(
            system_name,
            region_name,
            planet_name
        )

        fields = [
            {
                'name': 'System/Planet',
                'value': f"{system_name} - {planet_name}",
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


class SkyhookDeployed(NotificationPing):
    category = "orbital-attack"  # orbital-attack

    """
        itemID: &id002 1046336471456
        ownerCorpLinkData:
        - showinfo
        - 2
        - 98609787
        ownerCorpName: Initiative Trust
        planetID: &id001 40288233
        planetShowInfoData:
        - showinfo
        - 13
        - *id001
        skyhookShowInfoData:
        - showinfo
        - 81080
        - *id002
        solarsystemID: 30004557
        timeLeft: 18000000000
        typeID: 81080
    """

    def build_ping(self):
        system = get_system_from_id(self._data['solarsystemID'])
        planet_name = get_planet_name_from_id(self._data['planetID'])
        system_name = get_system_url_from_id(self._data['solarsystemID'])
        region_name = get_region_url_from_system_id(self._data['solarsystemID'])
        structure_type = get_item_name_from_id(self._data['typeID'])
        footer = footer_from_notification(self._notification)
        tile_till, out_date_time = time_till_out(self._data['timeLeft'], self._notification)

        title = "Skyhook Deployed"
        body = "{} - {} - {} Deployed".format(
            system_name,
            region_name,
            planet_name
        )

        fields = [
            {
                'name': 'System/Planet',
                'value': f"{system_name} - {planet_name}",
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
                'name': 'Time Till Out',
                'value': tile_till,
                'inline': False
            },
            {
                'name': 'Date Out',
                'value': out_date_time.strftime("%Y-%m-%d %H:%M"),
                'inline': False
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


class MercenaryDenAttacked(NotificationPing):
    """
    unknown notification type (287)
    Guestimated to be MercenaryDenAttacked
    """
    category = "orbital-attack"  # i guess this is kinda an orbital :-D

    """
    aggressorAllianceName: Unknown
    aggressorCharacterID: 800103040
    aggressorCorporationName: <a href=\"showinfo:2//1715234301\">Isk sellers</a>
    armorPercentage: 100.0
    hullPercentage: 100.0
    itemID: &id001 1047336167535
    mercenaryDenShowInfoData:
    - showinfo
    - 85230
    - *id001
    planetID: 40249672
    planetShowInfoData:
    - showinfo
    - 11
    - 40249672
    shieldPercentage: 94.93757889836118
    solarsystemID: 30003945
    typeID: 85230
    """

    def build_ping(self):
        system = get_system_from_id(self._data['solarsystemID'])
        planet_name = get_planet_name_from_id(self._data['planetID'])
        system_name = get_system_url_from_id(self._data['solarsystemID'])
        region_name = get_region_url_from_system_id(self._data['solarsystemID'])
        structure_type = get_item_name_from_id(self._data['typeID'])
        footer = footer_from_notification(self._notification)

        title = "Merc Den Under Attack"
        shld = float(self._data['shieldPercentage'])
        armr = float(self._data['armorPercentage'])
        hull = float(self._data['hullPercentage'])
        body = "{} under Attack!\n[ S: {:.2f}% A: {:.2f}% H: {:.2f}% ]".format(
            structure_type, shld, armr, hull
        )

        attacking_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['aggressorCharacterID'])

        attackerStr = "[%s](%s)" % \
            (
                attacking_char.name,
                zkillboard.character_url(attacking_char.eve_id)
            )

        fields = [
            {
                'name': 'System/Planet',
                'value': f"{system_name} - {planet_name}",
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
                'name': 'Owner',
                'value': self._notification.character.character.corporation_name,
                'inline': False
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
            colour=15158332
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
            system=system
        )
        self.force_at_ping = True


class MercenaryDenReinforced(NotificationPing):
    category = "orbital-attack"  # i guess this is kinda an orbital :-D

    """
    aggressorAllianceName: &lt;a href="showinfo:16159//99013809"&gt;HYPE-TRAIN&lt;/a&gt;
    aggressorCharacterID: 708182017
    aggressorCorporationName: &lt;a href="showinfo:2//98793267"&gt;BRAWLS DEEP&lt;/a&gt;
    itemID: &amp;id001 1047848379927
    mercenaryDenShowInfoData:
    - showinfo
    - 85230
    - *id001
    planetID: 40255737
    planetShowInfoData:
    - showinfo
    - 11
    - 40255737
    solarsystemID: 30004038
    timestampEntered: 133829589044450230
    timestampExited: 133830637854450230
    typeID: 85230
    """

    def build_ping(self):
        system = get_system_from_id(self._data['solarsystemID'])
        planet_name = get_planet_name_from_id(self._data['planetID'])
        system_name = get_system_url_from_id(self._data['solarsystemID'])
        region_name = get_region_url_from_system_id(self._data['solarsystemID'])
        structure_type = get_item_name_from_id(self._data['typeID'])
        footer = footer_from_notification(self._notification)

        _timeTill = filetime_to_dt(self._data['timestampExited']).replace(
            tzinfo=datetime.timezone.utc)
        _refTimeDelta = _timeTill - timezone.now()
        tile_till = format_timedelta(_refTimeDelta)

        title = "Merc Den Reinforced"
        body = f"{structure_type} has lost its Shields"

        fields = [
            {
                'name': 'System/Planet',
                'value': f"{system_name} - {planet_name}",
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
                'name': 'Owner',
                'value': self._notification.character.character.corporation_name,
                'inline': False
            },
            {
                'name': 'Time Till Out',
                'value': tile_till,
                'inline': False
            },
            {
                'name': 'Date Out',
                'value': _timeTill.strftime("%Y-%m-%d %H:%M"),
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
                    f"{planet_name} Merc Den",
                    structure_type,
                    system_name,
                    Timer.TimerType.ARMOR,
                    _timeTill,
                    self._notification.character.character.corporation
                )
            except Exception as e:
                logger.exception(
                    f"PINGER: Failed to build timer Merc Den Reinforced {e}")

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
            system=system
        )
