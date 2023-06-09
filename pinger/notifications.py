from logging import exception
import struct
import sys
from allianceauth.eveonline.models import EveCharacter
from allianceauth.timerboard.models import Timer
from django.db import models
import yaml
import json
import datetime
import time

from corptools import models as ctm
from corptools.task_helpers.update_tasks import fetch_location_name

from .models import MutedStructure
from .providers import cache_client

from django.utils.html import strip_tags
from django.utils import timezone
import logging
from django.apps import apps

logger = logging.getLogger(__name__)


def timers_enabled():
    return apps.is_installed("allianceauth.timerboard")


if timers_enabled():  # NOQA
    from allianceauth.timerboard.models import TimerType, Timer


class MutedException(Exception):
    pass


def filetime_to_dt(ft):
    us = (ft - 116444736000000000) // 10
    return datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=us)


def convert_timedelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 60)
    return hours, minutes, seconds


def format_timedelta(td):
    hours, minutes, seconds = convert_timedelta(td)
    return ("%d Days, %d Hours, %d Min" % (td.days, round(hours), round(minutes)))


def time_till_to_td(ms):
    _secondsRemaining = ms / 10000000  # seconds
    return datetime.timedelta(seconds=_secondsRemaining)


def time_till_to_string(ms):
    _refTimeDelta = time_till_to_td(ms)
    return format_timedelta(_refTimeDelta)


def time_till_to_dt(ms, timestamp):
    _refTimeDelta = time_till_to_td(ms)
    return timestamp + _refTimeDelta


def create_timer(structure, structure_type, system, timer_type, date, corporation):
    # Pre process??? add anything new???
    return Timer(
        details=f"{structure} (Auto)",
        system=system,
        structure=structure_type,
        timer_type=timer_type,
        eve_time=date,
        eve_corp=corporation,
    )


def get_available_types():
    classes = NotificationPing.__subclasses__()

    output = {}

    for c in classes:
        output[c.__name__] = c

    return output


class NotificationPing:
    # Settings
    force_at_ping = False
    category = "None"
    timer = False

    # Data
    _notification = None
    _data = {}
    _ping = ""

    _corp = None
    _alli = None
    _region = None

    def __init__(self, notification):
        self._notification = notification
        self._data = self.parse_notification()
        self.build_ping()

    def parse_notification(self):
        return yaml.load(self._notification.notification_text, Loader=yaml.UnsafeLoader)

    def build_ping(self):
        raise NotImplementedError(
            "Create the Notifcaton Map class to process this ping!")

    def package_ping(self, title, body, timestamp, fields=None, footer=None, img_url=None, colour=16756480):
        custom_data = {'color': colour,
                       'title': title,
                       'description': body,
                       'timestamp': timestamp.replace(tzinfo=None).isoformat(),
                       }

        if fields:
            custom_data['fields'] = fields

        if img_url:
            custom_data['image'] = {'url': img_url}

        if footer:
            custom_data['footer'] = footer

        self._ping = json.dumps(custom_data)

    def get_filters(self):
        return (self._corp, self._alli, self._region)


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
        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['typeID'])
        moon_name, _ = ctm.MapSystemMoon.objects.get_or_create_from_esi(
            self._data['moonID'])

        owner, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['corpID'])

        alliance = "-" if owner.alliance is None else owner.alliance.name

        title = "Tower Anchoring!"

        body = (f"{structure_type.name}\n**{moon_name.name}**\n\n[{owner.name}]"
                f"(https://zkillboard.com/search/{owner.name.replace(' ', '%20')}/),"
                f" **[{alliance}](https://zkillboard.com/search/{alliance.replace(' ', '%20')}/)**")

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


class MoonminingExtractionFinished(NotificationPing):
    category = "moons-completed"  # Moon pings

    """
        MoonminingExtractionFinished Example

        autoTime: 132052212600000000
        moonID: 40291390
        oreVolumeByType:
            45490: 1588072.4935986102
            46677: 2029652.6969759
            46679: 3063178.818627033
            46682: 2839990.2933705184
        solarSystemID: 30004612
        structureID: 1029754067191
        structureLink: <a href="showinfo:35835//1029754067191">NY6-FH - ISF Three</a>
        structureName: NY6-FH - ISF Three
        structureTypeID: 35835

    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])

        system_name = system_db.name
        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        structure_name = self._data['structureName']
        if len(structure_name) < 1:
            structure_name = "Unknown"

        moon, _ = ctm.MapSystemMoon.objects.get_or_create_from_esi(
            self._data['moonID'])

        title = "Moon Extraction Complete!"
        body = "Ready to Fracture!"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker

        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        auto_time = filetime_to_dt(self._data['autoTime'])
        ores = {}
        totalm3 = 0
        for t, q in self._data['oreVolumeByType'].items():
            ore, _ = ctm.EveItemType.objects.get_or_create_from_esi(t)
            ores[t] = ore.name
            totalm3 += q
        ore_string = []
        for t, q in self._data['oreVolumeByType'].items():
            ore_string.append(
                "**{}**: {:2.1f}%".format(
                    ores[t],
                    q/totalm3*100
                )
            )
        fields = [{'name': 'Structure', 'value': structure_name, 'inline': True},
                  {'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Moon', 'value': moon.name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Auto Fire', 'value': auto_time.strftime(
                      "%Y-%m-%d %H:%M"), 'inline': False},
                  {'name': 'Ore', 'value': "\n".join(ore_string)},
                  ]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=3066993)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id


class MoonminingAutomaticFracture(NotificationPing):
    category = "moons-completed"  # Moon Pings

    """
        MoonminingAutomaticFracture Example

        moonID: 40291417
        oreVolumeByType:
            45492: 1524501.871099406
            46677: 2656351.8252801565
            46678: 1902385.1244004236
            46681: 2110988.956997792
        solarSystemID: 30004612
        structureID: 1030287515076
        structureLink: <a href="showinfo:35835//1030287515076">NY6-FH - ISF-5</a>
        structureName: NY6-FH - ISF-5
        structureTypeID: 35835

    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])

        system_name = system_db.name
        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        structure_name = self._data['structureName']
        if len(structure_name) < 1:
            structure_name = "Unknown"

        moon, _ = ctm.MapSystemMoon.objects.get_or_create_from_esi(
            self._data['moonID'])

        title = "Moon Auto-Fractured!"
        body = "Ready to Mine!"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker

        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        ores = {}
        totalm3 = 0
        for t, q in self._data['oreVolumeByType'].items():
            ore, _ = ctm.EveItemType.objects.get_or_create_from_esi(t)
            ores[t] = ore.name
            totalm3 += q
        ore_string = []
        for t, q in self._data['oreVolumeByType'].items():
            ore_string.append(
                "**{}**: {:2.1f}%".format(
                    ores[t],
                    q/totalm3*100
                )
            )
        fields = [{'name': 'Structure', 'value': structure_name, 'inline': True},
                  {'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Moon', 'value': moon.name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Ore', 'value': "\n".join(ore_string)},
                  ]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=15844367)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id


class MoonminingLaserFired(NotificationPing):
    category = "moons-completed"  # Moons pings

    """
        MoonminingLaserFired Example

        firedBy: 824787891
        firedByLink: <a href="showinfo:1380//824787891">PoseDamen</a>
        moonID: 40291428
        oreVolumeByType:
            45493: 1983681.4476127427
            46679: 2845769.539271295
            46681: 2046606.19987059
            46688: 2115548.2348155645
        solarSystemID: 30004612
        structureID: 1029754054149
        structureLink: <a href="showinfo:35835//1029754054149">NY6-FH - ISF Two</a>
        structureName: NY6-FH - ISF Two
        structureTypeID: 35835

    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])

        system_name = system_db.name
        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        structure_name = self._data['structureName']
        if len(structure_name) < 1:
            structure_name = "Unknown"

        moon, _ = ctm.MapSystemMoon.objects.get_or_create_from_esi(
            self._data['moonID'])

        title = "Moon Laser Fired!"
        body = "Fired By [{0}](https://zkillboard.com/search/{1}/)".format(
            strip_tags(self._data['firedByLink']),
            strip_tags(self._data['firedByLink']).replace(" ", "%20"))

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker

        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        ores = {}
        totalm3 = 0
        for t, q in self._data['oreVolumeByType'].items():
            ore, _ = ctm.EveItemType.objects.get_or_create_from_esi(t)
            ores[t] = ore.name
            totalm3 += q
        ore_string = []
        for t, q in self._data['oreVolumeByType'].items():
            ore_string.append(
                "**{}**: {:2.1f}%".format(
                    ores[t],
                    q/totalm3*100
                )
            )
        fields = [{'name': 'Structure', 'value': structure_name, 'inline': True},
                  {'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Moon', 'value': moon.name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Ore', 'value': "\n".join(ore_string)},
                  ]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=1752220)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id


class MoonminingExtractionStarted(NotificationPing):
    category = "moons-started"  # Moons pings

    """
        MoonminingExtractionStarted Example

        autoTime: 132071260201940545
        moonID: 40291428
        oreVolumeByType:
            45493: 2742775.374017656
            46679: 3934758.0841854215
            46681: 2829779.495126257
            46688: 2925103.528079887
        readyTime: 132071130601940545
        solarSystemID: 30004612
        startedBy: 824787891
        startedByLink: <a href="showinfo:1380//824787891">PoseDamen</a>
        structureID: 1029754054149
        structureLink: <a href="showinfo:35835//1029754054149">NY6-FH - ISF Two</a>
        structureName: NY6-FH - ISF Two
        structureTypeID: 35835

    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])

        system_name = system_db.name
        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        structure_name = self._data['structureName']
        if len(structure_name) < 1:
            structure_name = "Unknown"

        moon, _ = ctm.MapSystemMoon.objects.get_or_create_from_esi(
            self._data['moonID'])

        title = "Moon Extraction Started!"
        body = "Fired By [{0}](https://zkillboard.com/search/{1}/)".format(
            strip_tags(self._data['startedByLink']),
            strip_tags(self._data['startedByLink']).replace(" ", "%20"))

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker

        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        auto_time = filetime_to_dt(self._data['autoTime'])
        ready_time = filetime_to_dt(self._data['readyTime'])

        ores = {}
        totalm3 = 0
        for t, q in self._data['oreVolumeByType'].items():
            ore, _ = ctm.EveItemType.objects.get_or_create_from_esi(t)
            ores[t] = ore.name
            totalm3 += q
        ore_string = []
        for t, q in self._data['oreVolumeByType'].items():
            ore_string.append(
                "**{}**: {:2.1f}%".format(
                    ores[t],
                    q/totalm3*100
                )
            )
        fields = [{'name': 'Structure', 'value': structure_name, 'inline': True},
                  {'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Moon', 'value': moon.name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Ready Time', 'value': ready_time.strftime(
                      "%Y-%m-%d %H:%M"), 'inline': False},
                  {'name': 'Auto Fire', 'value': auto_time.strftime(
                      "%Y-%m-%d %H:%M"), 'inline': False},
                  {'name': 'Ore', 'value': "\n".join(ore_string)},
                  ]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=1752220)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id


class StructureLostShields(NotificationPing):
    category = "sturucture-attack"  # Structure Alerts

    """
        StructureLostShields Example

        solarsystemID: 30004608
        structureID: &id001 1036096310753
        structureShowInfoData:
        - showinfo
        - 35835
        - *id001
        structureTypeID: 35835
        timeLeft: 958011150532
        timestamp: 132792333490000000
        vulnerableTime: 9000000000
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarsystemID'])

        system_name = system_db.name
        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        try:
            structure_name = fetch_location_name(
                self._data['structureID'], "solar_system", self._notification.character.character.character_id)
            if structure_name:
                structure_name = structure_name.location_name
            else:
                structure_name = "Unknown"

        except Exception as e:
            logger.error(f"PINGER: Error fetching structure name? {e}")
            structure_name = "Unknown"

        _secondsRemaining = self._data['timeLeft'] / 10000000  # seconds
        _refTimeDelta = datetime.timedelta(seconds=_secondsRemaining)
        tile_till = format_timedelta(_refTimeDelta)
        ref_date_time = self._notification.timestamp + _refTimeDelta

        title = structure_name
        body = "Structure has lost its Shields"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Owner', 'value': corp_name, 'inline': False},
                  {'name': 'Time Till Out', 'value': tile_till, 'inline': False},
                  {'name': 'Date Out', 'value': ref_date_time.strftime("%Y-%m-%d %H:%M"), 'inline': False}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=7419530)

        if timers_enabled():
            try:
                self.timer = create_timer(
                    structure_name,
                    structure_type.name,
                    system_db.name,
                    TimerType.ARMOR,
                    ref_date_time,
                    self._notification.character.character.corporation
                )
            except Exception as e:
                logger.exception(
                    "PINGER: Failed to build timer StructureLostShields")

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id


class StructureLostArmor(NotificationPing):
    category = "sturucture-attack"  # Structure Alerts

    """
        StructureLostArmor Example

        solarsystemID: 30004287
        structureID: &id001 1037256891589
        structureShowInfoData:
        - showinfo
        - 35835
        - *id001
        structureTypeID: 35835
        timeLeft: 2575911755713
        timestamp: 132776652750000000
        vulnerableTime: 18000000000
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarsystemID'])

        system_name = system_db.name
        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        try:
            structure_name = fetch_location_name(
                self._data['structureID'], "solar_system", self._notification.character.character.character_id)
            if structure_name:
                structure_name = structure_name.location_name
            else:
                structure_name = "Unknown"

        except Exception as e:
            logger.error(f"PINGER: Error fetching structure name? {e}")
            structure_name = "Unknown"

        _secondsRemaining = self._data['timeLeft'] / 10000000  # seconds
        _refTimeDelta = datetime.timedelta(seconds=_secondsRemaining)
        tile_till = format_timedelta(_refTimeDelta)
        ref_date_time = self._notification.timestamp + _refTimeDelta

        title = structure_name
        body = "Structure has lost its Armor"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Owner', 'value': corp_name, 'inline': False},
                  {'name': 'Time Till Out', 'value': tile_till, 'inline': False},
                  {'name': 'Date Out', 'value': ref_date_time.strftime("%Y-%m-%d %H:%M"), 'inline': False}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=7419530)

        if timers_enabled():
            try:
                self.timer = create_timer(
                    structure_name,
                    structure_type.name,
                    system_db.name,
                    TimerType.HULL,
                    ref_date_time,
                    self._notification.character.character.corporation
                )
            except Exception as e:
                logger.exception(
                    "PINGER: Failed to build timer StructureLostArmor")

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id


class StructureUnderAttack(NotificationPing):
    category = "sturucture-attack"  # Structure Alerts

    """
        StructureUnderAttack Example

        allianceID: 500010
        allianceLinkData:
        - showinfo
        - 30
        - 500010
        allianceName: Guristas Pirates
        armorPercentage: 100.0
        charID: 1000127
        corpLinkData:
        - showinfo
        - 2
        - 1000127
        corpName: Guristas
        hullPercentage: 100.0
        shieldPercentage: 94.88716147275748
        solarsystemID: 30004608
        structureID: &id001 1036096310753
        structureShowInfoData:
        - showinfo
        - 35835
        - *id001
        structureTypeID: 35835
    """

    def build_ping(self):
        try:
            muted = MutedStructure.objects.get(
                structure_id=self._data['structureID'])
            if muted.expired():
                muted.delete()
            else:
                raise MutedException()
        except MutedStructure.DoesNotExist:
            # no mutes move on
            pass

        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarsystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        try:
            structure_name = fetch_location_name(
                self._data['structureID'], "solar_system", self._notification.character.character.character_id)
            if structure_name:
                structure_name = structure_name.location_name
            else:
                structure_name = "Unknown"

        except Exception as e:
            logger.error(f"PINGER: Error fetching structure name? {e}")
            structure_name = "Unknown"

        title = structure_name
        shld = float(self._data['shieldPercentage'])
        armr = float(self._data['armorPercentage'])
        hull = float(self._data['hullPercentage'])
        body = "Structure under Attack!\n[ S: {0:.2f}% A: {1:.2f}% H: {2:.2f}% ]".format(
            shld, armr, hull)

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        attacking_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])

        attackerStr = "*[%s](https://zkillboard.com/search/%s/)*, [%s](https://zkillboard.com/search/%s/), **[%s](https://zkillboard.com/search/%s/)**" % \
            (attacking_char.name,
             attacking_char.name.replace(" ", "%20"),
             self._data.get('corpName', ""),
             self._data.get('corpName', "").replace(" ", "%20"),
             self._data.get('allianceName', "*-*"),
             self._data.get('allianceName', "").replace(" ", "%20"))

        fields = [{'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Region', 'value': region_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Attacker', 'value': attackerStr, 'inline': False}]

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

        if structure_name != "Unknown":
            epoch_time = int(time.time())
            cache_client.zadd("ctpingermute", {structure_name: epoch_time})
            rcount = cache_client.zcard("ctpingermute")
            if rcount > 5:
                cache_client.bzpopmin("ctpingermute")


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

        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

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

        footer = {"icon_url": "https://images.evetech.net/alliances/%s/logo" % (str(alli_id)),
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
                    "PINGER: Failed to build timer SovStructureReinforced")

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

        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        title = "Entosis Notification"

        body = "Entosis has started in %s on %s" % (
            system_name, structure_type.name)

        timestamp = self._notification.timestamp
        alli_id = self._notification.character.character.alliance_id
        alli_ticker = self._notification.character.character.alliance_ticker

        footer = {"icon_url": "https://images.evetech.net/alliances/%s/logo" % (str(alli_id)),
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


class OwnershipTransferred(NotificationPing):
    category = "alliance-admin"  # Structure Alerts

    """
        OwnershipTransferred Example

        charID: 972559932
        newOwnerCorpID: 98514543
        oldOwnerCorpID: 98465001
        solarSystemID: 30004626
        structureID: 1029829977992
        structureName: D4KU-5 - ducktales
        structureTypeID: 35835
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        structure_name = self._data['structureName']

        title = "Structure Transfered"

        originator, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])
        new_owner, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['newOwnerCorpID'])
        old_owner, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['oldOwnerCorpID'])

        body = "Structure Transfered from %s to %s" % (
            old_owner.name, new_owner.name)

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker

        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = []
        if len(structure_name) > 0:
            fields.append(
                {'name': 'Structure', 'value': structure_name, 'inline': True})

        fields += [
            {'name': 'System', 'value': system_name, 'inline': True},
            {'name': 'Region', 'value': region_name, 'inline': True},
            {'name': 'Type', 'value': structure_type.name, 'inline': True},
            {'name': 'Originator', 'value': originator.name, 'inline': True}
        ]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=10181046)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id


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

        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

        moon, _ = ctm.MapSystemMoon.objects.get_or_create_from_esi(
            self._data['moonID'])

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['typeID'])

        title = "Starbase Under Attack!"
        shld = float(self._data['shieldValue']*100)
        armr = float(self._data['armorValue']*100)
        hull = float(self._data['hullValue']*100)
        body = "Structure under Attack!\n[ S: {0:.2f}% A: {1:.2f}% H: {2:.2f}% ]".format(
            shld, armr, hull)

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        attackerStr = "Unknown"
        if self._data['aggressorID']:
            attacking_char, _ = ctm.EveName.objects.get_or_create_from_esi(
                self._data['aggressorID'])
            attacking_char_corp, _ = ctm.EveName.objects.get_or_create_from_esi(
                self._data['aggressorCorpID'])
            attacking_alliance_name = ""
            if self._data.get('aggressorAllianceID', False):
                attacking_char_alliance, _ = ctm.EveName.objects.get_or_create_from_esi(
                    self._data['aggressorAllianceID'])
                attacking_alliance_name = attacking_char_alliance.name

            attackerStr = "*[%s](https://zkillboard.com/search/%s/)*, [%s](https://zkillboard.com/search/%s/), **[%s](https://zkillboard.com/search/%s/)**" % \
                (attacking_char.name,
                 attacking_char.name.replace(" ", "%20"),
                 attacking_char_corp.name,
                 attacking_char_corp.name.replace(" ", "%20"),
                 attacking_alliance_name,
                 attacking_alliance_name.replace(" ", "%20"))

        fields = [{'name': 'Moon', 'value': moon.name, 'inline': True},
                  {'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Region', 'value': region_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Attacker', 'value': attackerStr, 'inline': False}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=15105570)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id
        self.force_at_ping = True

        if moon.name:
            epoch_time = int(time.time())
            cache_client.zadd("ctpingermute", {moon.name: epoch_time})
            rcount = cache_client.zcard("ctpingermute")
            if rcount > 5:
                cache_client.bzpopmin("ctpingermute")


class StructureAnchoring(NotificationPing):
    category = "sturucture-admin"  # Structure Alerts

    """
    StructureAnchoring

    ownerCorpLinkData:
    - showinfo
    - 2
    - 680022174
    ownerCorpName: DEFCON.
    solarsystemID: 30003795
    structureID: &id001 1030452747286
    structureShowInfoData:
    - showinfo
    - 35825
    - *id001
    structureTypeID: 35825
    timeLeft: 8999632416
    vulnerableTime: 9000000000
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarsystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        try:
            structure_name = fetch_location_name(
                self._data['structureID'], "solar_system", self._notification.character.character.character_id)
            if structure_name:
                structure_name = structure_name.location_name
            else:
                structure_name = "Unknown"

        except Exception as e:
            logger.error(f"PINGER: Error fetching structure name? {e}")
            structure_name = "Unknown"

        title = structure_name
        body = "Structure Anchoring!"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Region', 'value': region_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True}]
        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=1752220)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id
        self.force_at_ping = False


class StructureWentLowPower(NotificationPing):
    category = "sturucture-admin"  # Structure Alerts

    """
    StructureWentLowPower

    solarsystemID: 30000197
    structureID: &id001 1036261887208
    structureShowInfoData:
    - showinfo
    - 35832
    - *id001
    structureTypeID: 35832
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarsystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        try:
            structure_name = fetch_location_name(
                self._data['structureID'], "solar_system", self._notification.character.character.character_id)
            if structure_name:
                structure_name = structure_name.location_name
            else:
                structure_name = "Unknown"

        except Exception as e:
            logger.error(f"PINGER: Error fetching structure name? {e}")
            structure_name = "Unknown"

        title = structure_name
        body = "Structure Went Low Power!"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Region', 'value': region_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  ]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=15158332)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id
        self.force_at_ping = False


class StructureWentHighPower(NotificationPing):
    category = "sturucture-admin"  # Structure Alerts

    """
    StructureWentHighPower

    solarsystemID: 30004597
    structureID: &id001 1037513467358
    structureShowInfoData:
    - showinfo
    - 35841
    - *id001
    structureTypeID: 35841
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarsystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        try:
            structure_name = fetch_location_name(
                self._data['structureID'], "solar_system", self._notification.character.character.character_id)
            if structure_name:
                structure_name = structure_name.location_name
            else:
                structure_name = "Unknown"

        except Exception as e:
            logger.error(f"PINGER: Error fetching structure name? {e}")
            structure_name = "Unknown"

        title = structure_name
        body = "Structure Went High Power!"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Region', 'value': region_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  ]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=3066993)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id
        self.force_at_ping = False


class StructureUnanchoring(NotificationPing):
    category = "sturucture-admin"  # Structure Alerts

    """
    StructureUnanchoring

    ownerCorpLinkData:
    - showinfo
    - 2
    - 680022174
    ownerCorpName: DEFCON.
    solarsystemID: 30004665
    structureID: &id001 1034879252790
    structureShowInfoData:
    - showinfo
    - 37534
    - *id001
    structureTypeID: 37534
    timeLeft: 27000531441
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarsystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        try:
            structure_name = fetch_location_name(
                self._data['structureID'], "solar_system", self._notification.character.character.character_id)
            if structure_name:
                structure_name = structure_name.location_name
            else:
                structure_name = "Unknown"

        except Exception as e:
            logger.error(f"PINGER: Error fetching structure name? {e}")
            structure_name = "Unknown"

        title = structure_name
        body = "Structure Unanchoring!"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}
        date_out = time_till_to_dt(
            self._data['timeLeft'], self._notification.timestamp)
        time_till = time_till_to_string(self._data['timeLeft'])
        fields = [{'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Region', 'value': region_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Time Till Out', 'value': time_till, 'inline': False},
                  {'name': 'Date Out', 'value': date_out.strftime("%Y-%m-%d %H:%M"), 'inline': False}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=10181046)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id
        self.force_at_ping = False


class StructureDestroyed(NotificationPing):
    category = "sturucture-admin"  # Structure Alerts

    """
    StructureDestroyed

    isAbandoned: false
    ownerCorpLinkData:
    - showinfo
    - 2
    - 680022174
    ownerCorpName: DEFCON.
    solarsystemID: 30002354
    structureID: &id001 1036278739415
    structureShowInfoData:
    - showinfo
    - 35825
    - *id001
    structureTypeID: 35825
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarsystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        try:
            structure_name = fetch_location_name(
                self._data['structureID'], "solar_system", self._notification.character.character.character_id)
            if structure_name:
                structure_name = structure_name.location_name
            else:
                structure_name = "Unknown"

        except Exception as e:
            logger.error(f"PINGER: Error fetching structure name? {e}")
            structure_name = "Unknown"

        title = structure_name
        body = "Structure Destroyed!"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Region', 'value': region_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  ]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=15158332)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id
        self.force_at_ping = False


"""
StructureFuelAlert

listOfTypesAndQty:
- - 166
  - 4247
solarsystemID: 30000197
structureID: &id001 1036261887208
structureShowInfoData:
- showinfo
- 35832
- *id001
structureTypeID: 35832
"""


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


"""
OrbitalAttacked

aggressorAllianceID: 99005675
aggressorCorpID: 98081962
aggressorID: 437509777
planetID: 40066319
planetTypeID: 12
shieldLevel: 0.9897753365599623
solarSystemID: 30001039
typeID: 2233
"""


"""
StructureImpendingAbandonmentAssetsAtRisk

daysUntilAbandon: 2
isCorpOwned: true
solarsystemID: 30002119
structureID: &id001 1037228472779
structureLink: <a href="showinfo:35833//1037228472779">DY-P7Q - Guardtower</a>
structureShowInfoData:
- showinfo
- 35833
- *id001
structureTypeID: 35833
"""


"""
SovStructureDestroyed

solarSystemID: 30001155
structureTypeID: 32458
"""


"""
CharLeftCorpMsg

charID: 2112779955
corpID: 98577836
"""


class CorpAppAcceptMsg(NotificationPing):
    category = "hr-admin"  # Structure Alerts

    """
    CorpAppAcceptMsg

    applicationText: ''
    charID: 95954535
    corpID: 680022174
    """

    def build_ping(self):
        title = "Corp Application Accepted"
        app_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])
        try:
            eve_main = EveCharacter.objects.get(
                character_id=self._data['charID']).character_ownership.user.profile.main_character
            eve_main = f"[{eve_main.character_name}](https://evewho.com/character/{eve_main.character_id}/) [ [{eve_main.corporation_ticker}](https://evewho.com/corporation/{eve_main.corporation_id}) ]"
        except:
            eve_main = "Unknown"

        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Character', 'value': f"[{app_char}](https://evewho.com/character/{app_char.eve_id}/)", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'Main Character', 'value': eve_main, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=3066993)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self.force_at_ping = False


class CorpAppInvitedMsg(NotificationPing):
    category = "hr-admin"  # Structure Alerts

    """
    CorpAppInvitedMsg

    applicationText: ''
    charID: 95954535
    corpID: 680022174
    invokingCharID: 95946886
    """

    def build_ping(self):
        title = "Corp Invite Sent"
        app_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])
        invoked_by, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['invokingCharID'])
        try:
            eve_main = EveCharacter.objects.get(
                character_id=self._data['charID']).character_ownership.user.profile.main_character
            eve_main = f"[{eve_main.character_name}](https://evewho.com/character/{eve_main.character_id}/) [ [{eve_main.corporation_ticker}](https://evewho.com/corporation/{eve_main.corporation_id}) ]"
        except:
            eve_main = "Unknown"

        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Character', 'value': f"[{app_char}](https://evewho.com/character/{app_char.eve_id}/)", 'inline': True},
                  {'name': 'Invoking Character',
                      'value': invoked_by.name, 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'Main Character', 'value': eve_main, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=3066993)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self.force_at_ping = False


class CorpAppNewMsg(NotificationPing):
    category = "hr-admin"  # Structure Alerts

    """
    CorpAppNewMsg

    applicationText: ''
    charID: 95954535
    corpID: 680022174
    """

    def build_ping(self):
        title = "New Corp Application"
        app_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])
        try:
            eve_main = EveCharacter.objects.get(
                character_id=self._data['charID']).character_ownership.user.profile.main_character
            eve_main = f"[{eve_main.character_name}](https://evewho.com/character/{eve_main.character_id}/) [ [{eve_main.corporation_ticker}](https://evewho.com/corporation/{eve_main.corporation_id}) ]"
        except:
            eve_main = "Unknown"

        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Character', 'value': f"[{app_char}](https://evewho.com/character/{app_char.eve_id}/)", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'Main Character', 'value': eve_main, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=1752220)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self.force_at_ping = False


class CorpAppRejectMsg(NotificationPing):
    category = "hr-admin"  # Structure Alerts

    """
    CorpAppRejectMsg

    applicationText: ''
    charID: 95954535
    corpID: 680022174
    """

    def build_ping(self):
        title = "Corp Application Rejected"
        app_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])
        try:
            eve_main = EveCharacter.objects.get(
                character_id=self._data['charID']).character_ownership.user.profile.main_character
            eve_main = f"[{eve_main.character_name}](https://evewho.com/character/{eve_main.character_id}/) [ [{eve_main.corporation_ticker}](https://evewho.com/corporation/{eve_main.corporation_id}) ]"
        except:
            eve_main = "Unknown"
        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Character', 'value': f"[{app_char}](https://evewho.com/character/{app_char.eve_id}/)", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'Main Character', 'value': eve_main, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=15158332)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self.force_at_ping = False


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
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])
        planet_db, _ = ctm.MapSystemPlanet.objects.get_or_create_from_esi(
            planet_id=self._data['planetID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name
        planet_name = planet_db.name

        system_name = f"[{planet_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        region_name = f"[{region_name}](http://evemaps.dotlan.net/region/{region_name.replace(' ', '_')})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['typeID'])

        title = "Poco Under Attack"
        shld = float(self._data['shieldLevel'])*100
        body = "{} under Attack!\nShield Level: {:.2f}%".format(
            structure_type.name, shld)

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        attacking_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['aggressorID'])
        attacking_corp, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['aggressorCorpID'])

        attacking_alli = None
        if self._data['aggressorAllianceID']:
            attacking_alli, _ = ctm.EveName.objects.get_or_create_from_esi(
                self._data['aggressorAllianceID'])

        attackerStr = "*[%s](https://zkillboard.com/search/%s/)*, [%s](https://zkillboard.com/search/%s/), **[%s](https://zkillboard.com/search/%s/)**" % \
            (attacking_char.name,
             attacking_char.name.replace(" ", "%20"),
             attacking_corp.name,
             attacking_corp.name.replace(" ", "%20"),
             attacking_alli.name if attacking_alli else "*-*",
             attacking_alli.name.replace(" ", "%20") if attacking_alli else "")

        fields = [{'name': 'System/Planet', 'value': system_name, 'inline': True},
                  {'name': 'Region', 'value': region_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Attacker', 'value': attackerStr, 'inline': False}]

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
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarSystemID'])
        planet_db, _ = ctm.MapSystemPlanet.objects.get_or_create_from_esi(
            planet_id=self._data['planetID'])

        system_name = system_db.name
        planet_name = planet_db.name
        system_name = f"[{planet_name}](http://evemaps.dotlan.net/system/{system_name.replace(' ', '_')})"
        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['typeID'])

        _timeTill = filetime_to_dt(self._data['reinforceExitTime']).replace(
            tzinfo=datetime.timezone.utc)
        _refTimeDelta = _timeTill - timezone.now()
        tile_till = format_timedelta(_refTimeDelta)

        title = "Poco Reinforced"
        body = f"{structure_type.name} has lost its Shields"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](https://zkillboard.com/search/%s/)" % \
            (self._notification.character.character.corporation_name,
             self._notification.character.character.corporation_name.replace(" ", "%20"))
        footer = {"icon_url": "https://imageserver.eveonline.com/Corporation/%s_64.png" % (str(corp_id)),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'System', 'value': system_name, 'inline': True},
                  {'name': 'Type', 'value': structure_type.name, 'inline': True},
                  {'name': 'Owner', 'value': corp_name, 'inline': False},
                  {'name': 'Time Till Out', 'value': tile_till, 'inline': False},
                  {'name': 'Date Out', 'value': _timeTill.strftime("%Y-%m-%d %H:%M"), 'inline': False}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=7419530)

        if timers_enabled():
            try:
                self.timer = create_timer(
                    f"{planet_name} POCO",
                    structure_type.name,
                    system_db.name,
                    TimerType.ARMOR,
                    _timeTill,
                    self._notification.character.character.corporation
                )
            except Exception as e:
                logger.exception(
                    "PINGER: Failed to build timer OrbitalReinforced")

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self._region = system_db.constellation.region.region_id
