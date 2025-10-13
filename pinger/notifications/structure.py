import datetime
import logging
import time

from corptools import models as ctm
from corptools.task_helpers.update_tasks import fetch_location_name

from allianceauth.eveonline.evelinks import dotlan, eveimageserver, zkillboard

from ..exceptions import MutedException
from ..models import MutedStructure
from ..providers import cache_client
from .base import NotificationPing
from .helpers import (
    create_timer, format_timedelta, time_till_to_dt, time_till_to_string,
    timers_enabled,
)

logger = logging.getLogger(__name__)


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
        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"

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
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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
                from allianceauth.timerboard.models import Timer

                self.timer = create_timer(
                    structure_name,
                    structure_type.name,
                    system_db.name,
                    Timer.TimerType.ARMOR,
                    ref_date_time,
                    self._notification.character.character.corporation
                )
            except Exception as e:
                logger.exception(
                    f"PINGER: Failed to build timer StructureLostShields {e}")

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
        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"

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
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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
                from allianceauth.timerboard.models import Timer

                self.timer = create_timer(
                    structure_name,
                    structure_type.name,
                    system_db.name,
                    Timer.TimerType.HULL,
                    ref_date_time,
                    self._notification.character.character.corporation
                )
            except Exception as e:
                logger.exception(
                    f"PINGER: Failed to build timer StructureLostArmor {e}")

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

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

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
        # corp_name = "[%s](%s)" % \
        #     (self._notification.character.character.corporation_name,
        #      zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        attacking_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])

        attackerStr = "%s%s%s" % \
            (
                f"*[{attacking_char.name}]({zkillboard.character_url(attacking_char.eve_id)})*",
                f", [{attacking_char.corporation.name}]({zkillboard.corporation_url(attacking_char.corporation.eve_id)})" if attacking_char.corporation else "",
                f", **[{attacking_char.alliance.name}]({zkillboard.alliance_url(attacking_char.alliance.eve_id)})**" if attacking_char.alliance else "",
            )

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

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

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

        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

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
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

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
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

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
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

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
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

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
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
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


class StructureNoReagentsAlert(NotificationPing):
    category = "sturucture-admin"  # Structure Alerts

    """
    StructureNoReagentsAlert

    solarsystemID: 30004048
    structureID: &id001 1045920555257
    structureShowInfoData:
    - showinfo
    - 81826
    - *id001
    structureTypeID: 81826
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarsystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

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
        body = "Structure Out of Reagents!"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}
        fields = [
            {'name': 'Corporation', 'value': corp_name, 'inline': True},
            {'name': 'System', 'value': system_name, 'inline': True},
            {'name': 'Region', 'value': region_name, 'inline': True},
            {'name': 'Type', 'value': structure_type.name, 'inline': True}
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
        self.force_at_ping = True


class StructureLowReagentsAlert(NotificationPing):
    category = "sturucture-admin"  # Structure Alerts

    """
    StructureLowReagentsAlert

    solarsystemID: 30004048
    structureID: &id001 1045995578326
    structureShowInfoData:
    - showinfo
    - 81826
    - *id001
    structureTypeID: 81826
    """

    def build_ping(self):
        system_db = ctm.MapSystem.objects.get(
            system_id=self._data['solarsystemID'])

        system_name = system_db.name
        region_name = system_db.constellation.region.name

        system_name = f"[{system_name}]({dotlan.solar_system_url(system_name)})"
        region_name = f"[{region_name}]({dotlan.region_url(region_name)})"

        structure_type, _ = ctm.EveItemType.objects.get_or_create_from_esi(
            self._data['structureTypeID'])

        try:
            structure_name = fetch_location_name(
                self._data['structureID'],
                "solar_system",
                self._notification.character.character.character_id
            )
            if structure_name:
                structure_name = structure_name.location_name
            else:
                structure_name = "Unknown"

        except Exception as e:
            logger.error(f"PINGER: Error fetching structure name? {e}")
            structure_name = "Unknown"

        title = structure_name
        body = "Structure Low Reagents!"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}
        fields = [
            {'name': 'Corporation', 'value': corp_name, 'inline': True},
            {'name': 'System', 'value': system_name, 'inline': True},
            {'name': 'Region', 'value': region_name, 'inline': True},
            {'name': 'Type', 'value': structure_type.name, 'inline': True}
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
        self.force_at_ping = True
