import datetime
import logging

from corptools import models as ctm
from django.utils.html import strip_tags

from .base import NotificationPing
from .helpers import filetime_to_dt

from allianceauth.eveonline.evelinks import dotlan, eveimageserver

logger = logging.getLogger(__name__)


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
        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"

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

        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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
        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"

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

        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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
        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"

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

        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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
        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"

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

        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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
