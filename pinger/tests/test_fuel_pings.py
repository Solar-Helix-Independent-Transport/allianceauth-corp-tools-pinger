import datetime
import json
import sys
from datetime import timedelta
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from corptools.models import CorporationAudit, Structure, StructureService
from corptools.tests import CorptoolsTestCase
from eve_sde.models import Constellation, Region, SolarSystem
from requests.exceptions import HTTPError

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.forms.models import inlineformset_factory
from django.test import RequestFactory, TestCase
from django.utils import timezone

from allianceauth.eveonline.evelinks import dotlan, eveimageserver
from allianceauth.groupmanagement.models import Group

from pinger import tasks
from pinger.admin import (
    FuelThresholdForm, FuelThresholdFormSet, FuelThresholdInline,
)
from pinger.models import (
    DiscordWebhook, FuelPingConfig, FuelPingRecord, FuelThreshold, Ping,
)
from pinger.tasks import corporation_fuel_check
from pinger.utils.discord import build_fuel_embed, role_id_for_group

STRUCTURE_TYPE_ID = 35832

DISCORD_MODELS = "allianceauth.services.modules.discord.models"

FUEL_THRESHOLD_CSS = "pinger/admin/fuel_thresholds.css"


class ShiftedDatetime(datetime.datetime):
    """`datetime` with a test controlled offset to mock a future date."""

    offset = timedelta()

    @classmethod
    def now(cls, tz=None):
        return datetime.datetime.now(tz) + cls.offset


# stands in for `pinger.tasks`'s `datetime` module global
SHIFTED_DATETIME_MODULE = SimpleNamespace(
    datetime=ShiftedDatetime, timedelta=datetime.timedelta, timezone=datetime.timezone
)


class FuelPingTestCase(CorptoolsTestCase):
    """
    Two independent map chains, so a config scoped anywhere in chain 1 misses a
    structure sitting in chain 2. Every structure belongs to corp2 (alliance alli1)
    unless a test says otherwise.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        FuelPingConfig.objects.all().delete()

        cls.region1 = Region.objects.create(id=19000001, name="Region One")
        cls.const1 = Constellation.objects.create(
            id=19100001, name="Constellation One", region=cls.region1
        )
        cls.system1 = SolarSystem.objects.create(
            id=19200001,
            name="System One",
            security_status=0.5,
            x=0,
            y=0,
            z=0,
            constellation=cls.const1,
        )
        cls.system1b = SolarSystem.objects.create(
            id=19200002,
            name="System One B",
            security_status=0.5,
            x=0,
            y=0,
            z=0,
            constellation=cls.const1,
        )

        cls.region2 = Region.objects.create(id=19000002, name="Region Two")
        cls.const2 = Constellation.objects.create(
            id=19100002, name="Constellation Two", region=cls.region2
        )
        cls.system2 = SolarSystem.objects.create(
            id=19200003,
            name="System Two",
            security_status=0.5,
            x=0,
            y=0,
            z=0,
            constellation=cls.const2,
        )

        cls.hook = DiscordWebhook.objects.create(
            nickname="Fuel Hook",
            discord_webhook="https://discord.com/api/webhooks/fuel",
        )

    def setUp(self):
        super().setUp()

        ShiftedDatetime.offset = timedelta()
        clock = patch("pinger.tasks.datetime", SHIFTED_DATETIME_MODULE)
        clock.start()
        self.addCleanup(clock.stop)

        self._next_structure_id = 90000

    # ------------------------------------------------------------------ helpers

    def _structure(
        self,
        days=None,
        system: SolarSystem = None,
        corp_audit: CorporationAudit = None,
        name=None,
    ):
        """A structure with `days` (and a bit) of fuel left. `days=None` means no fuel data."""
        self._next_structure_id += 1
        structure_id = self._next_structure_id

        struct = Structure.objects.create(
            corporation=corp_audit or self.cp2,
            profile_id=1,
            reinforce_hour=12,
            state="shield_vulnerable",
            structure_id=structure_id,
            system_id=system.id if system is not None else self.system1.id,
            system_name=system if system is not None else self.system1,
            type_id=STRUCTURE_TYPE_ID,
            name=name or f"Structure {structure_id}",
        )

        if days is not None:
            self._set_days(struct, days)
        return struct

    def _set_days(self, struct: Structure, days, skew_hours=12):
        """Refuel to `days` whole days (plus slack, so the task's `now` still floors to `days`)."""
        struct.fuel_expires = ShiftedDatetime.now(datetime.timezone.utc) + timedelta(
            days=days, hours=skew_hours
        )
        struct.save()
        return struct

    def _burn(self, days):
        """Advance the clock the task reads, leaving `fuel_expires` alone."""
        ShiftedDatetime.offset += timedelta(days=days)

    def _config(
        self,
        name,
        ladder,
        regions=(),
        constellations=(),
        systems=(),
        structures=(),
        webhooks=None,
        always_ping=False,
        blocks_broader=False,
    ):
        """`ladder` is a list of (days, message) or of kwargs dicts.

        `webhooks` defaults to the shared hook; pass `[]` for a config that names none.
        """
        cfg = FuelPingConfig.objects.create(
            name=name, always_ping=always_ping, blocks_broader=blocks_broader
        )
        cfg.regions.set(regions)
        cfg.constellations.set(constellations)
        cfg.systems.set(systems)
        cfg.structures.set(structures)
        cfg.webhooks.set([self.hook] if webhooks is None else webhooks)

        for entry in ladder:
            if isinstance(entry, dict):
                FuelThreshold.objects.create(config=cfg, **entry)
            else:
                days, message = entry
                FuelThreshold.objects.create(config=cfg, days=days, message=message)
        return cfg

    def _run(self, corp=None):
        corporation_fuel_check((corp or self.corp2).corporation_id)

    def _pings(self, struct, hook=None):
        qs = Ping.objects.filter(notification_id=-struct.structure_id)
        if hook is not None:
            qs = qs.filter(hook=hook)
        return qs

    def _messages(self, struct, hook=None):
        return sorted(
            json.loads(p.body).get("description", "") for p in self._pings(struct, hook)
        )

    def _records(self, struct):
        return FuelPingRecord.objects.filter(structure=struct)


@patch("pinger.models.Ping.send_ping", new=lambda self: None)
class FuelPingLadderTests(FuelPingTestCase):
    """Level 1: which pings a run produces."""

    LADDER = [(1, "T1"), (2, "T2"), (7, "T7"), (14, "T14")]

    def test_threshold_selection_at_every_boundary(self):
        self._config("Catch All", self.LADDER)

        expected = {
            0: ["T1"],
            1: ["T1"],
            2: ["T2"],
            3: ["T7"],
            7: ["T7"],
            8: ["T14"],
            14: ["T14"],
            15: [],
        }
        structures = {days: self._structure(days=days) for days in expected}

        self._run()

        for days, messages in expected.items():
            with self.subTest(days=days):
                self.assertEqual(self._messages(structures[days]), messages)

    def test_negative_days_left_is_silent(self):
        self._config("Catch All", self.LADDER)
        struct = self._structure()
        self._set_days(struct, -1, skew_hours=0)

        self._run()

        self.assertEqual(self._messages(struct), [])
        self.assertFalse(self._records(struct).exists())

    def test_structure_without_fuel_data_is_skipped(self):
        self._config("Catch All", self.LADDER)
        struct = self._structure()

        self._run()

        self.assertEqual(self._messages(struct), [])

    def test_system_config_suppresses_region_config(self):
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        self._config("System", [(7, "SYSTEM")], systems=[self.system1])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["SYSTEM"])

    def test_structure_config_suppresses_system_config(self):
        struct = self._structure(days=5)
        self._config("System", [(7, "SYSTEM")], systems=[self.system1])
        self._config("Structure", [(7, "STRUCTURE")], structures=[struct])

        self._run()

        self.assertEqual(self._messages(struct), ["STRUCTURE"])

    def test_structure_config_only_matches_the_named_structure(self):
        named = self._structure(days=5)
        other = self._structure(days=5)
        self._config("System", [(7, "SYSTEM")], systems=[self.system1])
        self._config("Structure", [(7, "STRUCTURE")], structures=[named])

        self._run()

        self.assertEqual(self._messages(named), ["STRUCTURE"])
        self.assertEqual(self._messages(other), ["SYSTEM"])

    def test_structures_only_config_is_not_a_catch_all(self):
        named = self._structure(days=5)
        other = self._structure(days=5)
        self._config("Structure", [(7, "STRUCTURE")], structures=[named])

        self._run()

        self.assertEqual(self._messages(named), ["STRUCTURE"])
        self.assertEqual(self._messages(other), [])

    def test_constellation_config_suppresses_region_config(self):
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        self._config("Const", [(7, "CONST")], constellations=[self.const1])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["CONST"])

    def test_two_configs_at_the_same_level_both_fire(self):
        self._config("System A", [(7, "A")], systems=[self.system1])
        self._config("System B", [(7, "B")], systems=[self.system1])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["A", "B"])

    def test_catch_all_applies_when_nothing_else_matches(self):
        self._config("Catch All", [(7, "CATCHALL")])
        self._config("Other Region", [(7, "OTHER")], regions=[self.region2])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["CATCHALL"])

    def test_catch_all_is_suppressed_by_a_matching_config(self):
        self._config("Catch All", [(7, "CATCHALL")])
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["REGION"])

    def test_structures_of_other_corps_are_untouched(self):
        self._config("Catch All", self.LADDER)
        mine = self._structure(days=5)
        theirs = self._structure(days=5, corp_audit=self.cp1)

        self._run()  # corp2 only

        self.assertEqual(self._messages(mine), ["T7"])
        self.assertEqual(self._messages(theirs), [])
        self.assertFalse(self._records(theirs).exists())

    def test_one_config_can_match_at_several_levels(self):
        self._config(
            "Multi", [(7, "MULTI")], regions=[self.region1], systems=[self.system2]
        )
        self._config("Region Two", [(7, "REGION2")], regions=[self.region2])

        by_region = self._structure(days=5)  # system1, region1 -> level 1
        by_system = self._structure(days=5, system=self.system2)  # level 3

        self._run()

        self.assertEqual(self._messages(by_region), ["MULTI"])
        # the level 3 match outranks REGION2's level 1 on the same structure
        self.assertEqual(self._messages(by_system), ["MULTI"])

    def test_null_constellation_matches_catch_all_and_skips_region_filters(self):
        """No constellation means no region, so a region filter cannot be applied."""
        self.hook.region_filter.add(self.region2)
        self._config("Catch All", [(7, "CATCHALL")])
        self._config("Region", [(7, "REGION")], regions=[self.region1])

        self.system1.constellation = None
        self.system1.save()
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["CATCHALL"])

    def test_null_system_matches_catch_all_only(self):
        # no system means no region either, so the region filter is skipped
        self.hook.region_filter.add(self.region2)
        self._config("Catch All", [(7, "CATCHALL")])
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        self._config("System", [(7, "SYSTEM")], systems=[self.system1])

        struct = self._structure(days=5)
        struct.system_name = None
        struct.save()

        self._run()

        self.assertEqual(self._messages(struct), ["CATCHALL"])
        # the embed still renders, falling back to the raw system id
        body = json.loads(self._pings(struct).first().body)
        system_field = [f for f in body["fields"] if f["name"] == "System"][0]
        self.assertEqual(system_field["value"], str(struct.system_id))

    def test_repeat_run_at_the_same_days_left_does_not_re_ping(self):
        self._config("Catch All", self.LADDER)
        struct = self._structure(days=5)

        self._run()
        self._run()

        self.assertEqual(self._pings(struct).count(), 1)

    def test_repeat_days_null_never_repeats_inside_a_band(self):
        self._config("Catch All", [(14, "BAND")])
        struct = self._structure(days=13)

        self._run()
        self._burn(4)
        self._run()

        self.assertEqual(self._pings(struct).count(), 1)

    def test_repeat_days_repeats_on_the_days_left_delta(self):
        self._config("Catch All", [{"days": 14, "message": "BAND", "repeat_days": 3}])
        struct = self._structure(days=13)

        self._run()
        self._burn(2)  # only 2 days burned, not due yet
        self._run()
        self.assertEqual(self._pings(struct).count(), 1)

        self._burn(1)  # 3 days burned since the last ping
        self._run()
        self.assertEqual(self._pings(struct).count(), 2)

    def test_crossing_into_a_tighter_band_pings_regardless_of_cadence(self):
        self._config(
            "Catch All",
            [
                {"days": 14, "message": "WARN", "repeat_days": 10},
                {"days": 2, "message": "CRIT", "repeat_days": 10},
            ],
        )
        struct = self._structure(days=13)

        self._run()
        self._burn(11)
        self._run()

        self.assertEqual(self._messages(struct), ["CRIT", "WARN"])

    def test_refuelling_resets_the_record(self):
        self._config("Catch All", [(14, "BAND")])
        struct = self._structure(days=13)

        self._run()
        self._set_days(struct, 13, skew_hours=20)  # a different fuel_expires
        self._run()

        self.assertEqual(self._pings(struct).count(), 2)

    def test_configs_keep_independent_repeat_clocks(self):
        """Regression: a fast config must not starve a slow one (they share no record)."""
        self._config(
            "Fast",
            [{"days": 14, "message": "FAST", "repeat_days": 1}],
            systems=[self.system1],
        )
        self._config(
            "Slow",
            [{"days": 14, "message": "SLOW", "repeat_days": 5}],
            systems=[self.system1],
        )
        struct = self._structure(days=14)

        self._run()
        for _ in range(6):  # 13 down to 8
            self._burn(1)
            self._run()

        # one per day, 14 down to 8
        self.assertEqual(self._pings(struct).filter(body__contains='"FAST"').count(), 7)
        # 14, then 9
        self.assertEqual(self._pings(struct).filter(body__contains='"SLOW"').count(), 2)

    def test_always_ping_fires_alongside_a_tighter_config(self):
        self._config(
            "Region Always", [(7, "REGION")], regions=[self.region1], always_ping=True
        )
        self._config("System", [(7, "SYSTEM")], systems=[self.system1])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["REGION", "SYSTEM"])

    def test_always_ping_still_raises_the_bar_for_everyone_else(self):
        self._config("Catch All", [(7, "CATCHALL")])
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        self._config(
            "System Always", [(7, "SYSTEM")], systems=[self.system1], always_ping=True
        )
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["SYSTEM"])

    def test_a_config_below_its_ladder_does_not_suppress(self):
        """A tighter config that would not ping leaves the broader one free to fire."""
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        self._config("System", [(1, "SYSTEM")], systems=[self.system1])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["REGION"])

    def test_blocks_broader_suppresses_without_pinging(self):
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        self._config(
            "System", [(1, "SYSTEM")], systems=[self.system1], blocks_broader=True
        )
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), [])

    def test_blocks_broader_changes_nothing_when_the_config_pings(self):
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        self._config(
            "System", [(7, "SYSTEM")], systems=[self.system1], blocks_broader=True
        )
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["SYSTEM"])

    def test_always_ping_survives_a_blocks_broader_blackout(self):
        self._config("Catch All", [(7, "CATCHALL")], always_ping=True)
        self._config(
            "System", [(1, "SYSTEM")], systems=[self.system1], blocks_broader=True
        )
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["CATCHALL"])

    def test_blocks_broader_at_structure_level(self):
        struct = self._structure(days=5)
        self._config("Catch All", [(7, "CATCHALL")], always_ping=True)
        self._config("System", [(7, "SYSTEM")], systems=[self.system1])
        self._config(
            "Structure",
            [(1, "STRUCTURE")],
            structures=[struct],
            blocks_broader=True,
        )

        self._run()

        self.assertEqual(self._messages(struct), ["CATCHALL"])

    def test_blocks_broader_only_bites_where_it_matches(self):
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        self._config(
            "Other Region",
            [(1, "OTHER")],
            regions=[self.region2],
            blocks_broader=True,
        )
        struct = self._structure(days=5)  # system1, region1

        self._run()

        self.assertEqual(self._messages(struct), ["REGION"])

    def test_the_bar_is_computed_per_structure(self):
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        self._config(
            "System", [(1, "SYSTEM")], systems=[self.system1], blocks_broader=True
        )
        blocked = self._structure(days=5)
        other = self._structure(days=5, system=self.system1b)

        self._run()

        self.assertEqual(self._messages(blocked), [])
        self.assertEqual(self._messages(other), ["REGION"])

    def test_all_flagged_match_set_all_fire(self):
        self._config("Catch All", [(7, "CATCHALL")], always_ping=True)
        self._config(
            "Region", [(7, "REGION")], regions=[self.region1], always_ping=True
        )
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["CATCHALL", "REGION"])

    def test_config_pings_only_its_own_webhooks(self):
        named = DiscordWebhook.objects.create(
            nickname="Named", discord_webhook="https://discord.com/api/webhooks/named"
        )
        self._config("Catch All", [(7, "MSG")], webhooks=[named])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct, hook=named), ["MSG"])
        self.assertEqual(self._messages(struct, hook=self.hook), [])

    def test_config_webhooks_still_honour_their_own_filters(self):
        self.hook.alliance_filter.add(self.alli2)  # corp2 is in alli1
        self._config("Catch All", [(7, "MSG")])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), [])

    def test_config_webhooks_honour_their_corporation_filter(self):
        self.hook.corporation_filter.add(self.corp3)  # the structure belongs to corp2
        in_corp = DiscordWebhook.objects.create(
            nickname="In Corp",
            discord_webhook="https://discord.com/api/webhooks/corp",
        )
        in_corp.corporation_filter.add(self.corp2)
        self._config("Catch All", [(7, "MSG")], webhooks=[self.hook, in_corp])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct, hook=self.hook), [])
        self.assertEqual(self._messages(struct, hook=in_corp), ["MSG"])

    def test_config_webhooks_honour_their_region_filter(self):
        self.hook.region_filter.add(self.region2)  # the structure is in region1
        in_region = DiscordWebhook.objects.create(
            nickname="In Region",
            discord_webhook="https://discord.com/api/webhooks/region",
        )
        in_region.region_filter.add(self.region1)
        self._config("Catch All", [(7, "MSG")], webhooks=[self.hook, in_region])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct, hook=self.hook), [])
        self.assertEqual(self._messages(struct, hook=in_region), ["MSG"])

    def test_config_without_webhooks_is_inert_and_does_not_suppress(self):
        self._config("Region", [(7, "REGION")], regions=[self.region1])
        self._config("System", [(7, "SYSTEM")], systems=[self.system1], webhooks=[])
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._messages(struct), ["REGION"])

    def test_message_substitution_and_colour(self):
        self._config(
            "Catch All",
            [
                {
                    "days": 7,
                    "message": "{structure} in {system} has {days} days",
                    "color": 123456,
                }
            ],
        )
        struct = self._structure(days=5, name="Fort Test")

        self._run()

        body = json.loads(self._pings(struct).first().body)
        self.assertEqual(body["description"], "Fort Test in System One has 5 days")
        self.assertEqual(body["color"], 123456)

    def test_message_substitution_with_a_null_system(self):
        self._config("Catch All", [{"days": 7, "message": "{system}"}])
        struct = self._structure(days=5)
        struct.system_name = None
        struct.save()

        self._run()

        self.assertEqual(self._messages(struct), ["Unknown"])

    def test_a_threshold_without_a_message_pings_without_a_description(self):
        self._config("Catch All", [{"days": 7}])
        struct = self._structure(days=5)

        self._run()

        body = json.loads(self._pings(struct).get().body)
        self.assertNotIn("description", body)
        self.assertEqual(self._records(struct).get().last_message, "")

    def test_nothing_matching_pings_nothing_and_sweeps_every_record(self):
        catch_all = self._config("Catch All", [(7, "CATCHALL")])
        struct = self._structure(days=5)

        self._run()
        self.assertEqual(self._records(struct).count(), 1)

        catch_all.regions.set([self.region2])  # only a region2 config is left
        self._run()

        self.assertEqual(self._pings(struct).count(), 1)
        self.assertFalse(self._records(struct).exists())

    def test_lowering_the_ladder_below_a_stored_ping_fires_once(self):
        """Decision 9b: `last_ping_time` is re-read against the *current* ladder.

        Dropping the top threshold under a stored `last_ping_time` makes
        `threshold_for(last)` fall off the ladder, which reads as a band change.
        """
        cfg = self._config("Catch All", [(14, "BAND")])
        struct = self._structure(days=13)

        self._run()
        self.assertEqual(self._pings(struct).count(), 1)  # last_ping_time = 13

        cfg.thresholds.update(days=10)  # 13 now sits above the whole ladder
        self._burn(3)
        self._run()

        self.assertEqual(self._pings(struct).count(), 2)


@patch("pinger.models.Ping.send_ping", new=lambda self: None)
class FuelPingMentionTests(FuelPingTestCase):
    """Level 1: the `content` line each ping carries."""

    def test_no_mentions_configured_leaves_content_empty(self):
        self._config("Catch All", [(7, "MSG")])
        struct = self._structure(days=5)

        self._run()

        ping = self._pings(struct).first()
        self.assertEqual(ping.content, "")
        self.assertFalse(ping.alerting)

    def test_ping_here(self):
        self._config("Catch All", [{"days": 7, "message": "MSG", "ping_here": True}])
        struct = self._structure(days=5)

        self._run()

        ping = self._pings(struct).first()
        self.assertEqual(ping.content, "@here")
        self.assertTrue(ping.alerting)

    def test_ping_everyone(self):
        self._config(
            "Catch All", [{"days": 7, "message": "MSG", "ping_everyone": True}]
        )
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._pings(struct).first().content, "@everyone")

    @patch("pinger.models.role_id_for_group", lambda group: f"role-{group.name}")
    def test_everyone_here_and_group_mentions_in_order(self):
        cfg = self._config(
            "Catch All",
            [{"days": 7, "message": "MSG", "ping_here": True, "ping_everyone": True}],
        )
        threshold = cfg.thresholds.get()
        threshold.ping_groups.add(Group.objects.create(name="alpha"))
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(
            self._pings(struct).first().content, "@everyone @here <@&role-alpha>"
        )

    @patch("pinger.models.role_id_for_group", lambda group: None)
    def test_unresolvable_group_is_skipped(self):
        cfg = self._config(
            "Catch All", [{"days": 7, "message": "MSG", "ping_here": True}]
        )
        cfg.thresholds.get().ping_groups.add(Group.objects.create(name="alpha"))
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._pings(struct).first().content, "@here")

    @patch("pinger.utils.discord._discord_service_installed", lambda: False)
    def test_group_mentions_are_dropped_without_the_discord_service(self):
        cfg = self._config("Catch All", [(7, "MSG")])
        cfg.thresholds.get().ping_groups.add(Group.objects.create(name="alpha"))
        struct = self._structure(days=5)

        self._run()

        self.assertEqual(self._pings(struct).first().content, "")


@patch("pinger.models.Ping.send_ping", new=lambda self: None)
class FuelPingRecordTests(FuelPingTestCase):
    """Level 2: the state a run leaves behind."""

    def test_one_record_per_structure_and_config(self):
        self._config("A", [(7, "A")])
        self._config("B", [(7, "B")])
        struct = self._structure(days=5)

        self._run()
        self._run()

        self.assertEqual(self._records(struct).count(), 2)

    def test_a_config_above_its_ladder_only_loses_its_own_record(self):
        short = self._config("Short", [(3, "SHORT")])
        tall = self._config("Tall", [(14, "TALL")])
        struct = self._structure(days=2)

        self._run()
        self.assertEqual(self._records(struct).count(), 2)

        self._set_days(struct, 10)
        self._run()

        self.assertFalse(self._records(struct).filter(config=short).exists())
        self.assertTrue(self._records(struct).filter(config=tall).exists())

    def test_a_config_suppressed_by_blocks_broader_loses_its_record(self):
        region = self._config("Region", [(7, "REGION")], regions=[self.region1])
        blocker = self._config(
            "System", [(1, "SYSTEM")], systems=[self.system1], blocks_broader=True
        )
        struct = self._structure(days=5)

        self._run()
        self.assertEqual(self._records(struct).count(), 0)

        blocker.systems.set([self.system2])  # no longer matches, region is free again
        self._run()
        self.assertEqual(
            list(self._records(struct).values_list("config_id", flat=True)), [region.id]
        )

        blocker.systems.set([self.system1])
        self._run()

        self.assertFalse(self._records(struct).exists())

    def test_a_config_that_stops_matching_is_swept(self):
        scoped = self._config("Scoped", [(7, "SCOPED")], systems=[self.system1])
        catch_all = self._config("Catch All", [(7, "CATCHALL")])
        struct = self._structure(days=5)

        self._run()
        self.assertEqual(
            list(self._records(struct).values_list("config_id", flat=True)), [scoped.id]
        )

        struct.system_name = self.system2
        struct.system_id = self.system2.id
        struct.save()
        self._run()

        self.assertEqual(
            list(self._records(struct).values_list("config_id", flat=True)),
            [catch_all.id],
        )

    def test_refuel_rewrites_the_record_in_place(self):
        self._config("Catch All", [(14, "BAND")])
        struct = self._structure(days=13)

        self._run()
        record_id = self._records(struct).get().id

        self._set_days(struct, 13, skew_hours=20)
        self._run()

        record = self._records(struct).get()
        self.assertEqual(record.id, record_id)
        struct.refresh_from_db()
        self.assertEqual(record.date_empty, struct.fuel_expires)

    def test_a_structure_without_fuel_data_keeps_its_records(self):
        self._config("Catch All", [(7, "MSG")])
        struct = self._structure(days=5)

        self._run()
        self.assertEqual(self._records(struct).count(), 1)

        struct.fuel_expires = None
        struct.save()
        self._run()

        self.assertEqual(self._records(struct).count(), 1)

    def test_last_ping_time_and_message_track_the_fired_threshold(self):
        self._config("Catch All", [(7, "SEVEN"), (2, "TWO")])
        struct = self._structure(days=5)

        self._run()

        record = self._records(struct).get()
        self.assertEqual(record.last_ping_time, 5)
        self.assertEqual(record.last_message, "SEVEN")

    def test_a_low_power_structure_keeps_its_records(self):
        """`days_left < 0` bails before the sweep, so nothing is touched."""
        self._config("Catch All", [(7, "MSG")])
        struct = self._structure(days=5)

        self._run()
        record = self._records(struct).get()

        self._set_days(struct, -1, skew_hours=0)
        self._run()

        self.assertEqual(self._pings(struct).count(), 1)
        untouched = self._records(struct).get()
        self.assertEqual(untouched.id, record.id)
        self.assertEqual(untouched.date_empty, record.date_empty)


@patch("pinger.models.Ping.send_ping", new=lambda self: None)
class FuelEmbedTests(FuelPingTestCase):
    """Level 3: the embed body `build_fuel_embed` renders."""

    def _fields(self, embed):
        return {f["name"]: f["value"] for f in embed["fields"]}

    def test_full_embed_body(self):
        struct = self._structure(days=5, name="Fort Test")
        StructureService.objects.create(
            structure=struct, name="Clone Bay", state="online"
        )
        StructureService.objects.create(
            structure=struct, name="Offline Thing", state="offline"
        )

        embed = build_fuel_embed(struct, "MSG", 123456, 5)

        self.assertEqual(
            embed,
            {
                "color": 123456,
                "title": "Fort Test",
                "footer": {
                    "icon_url": eveimageserver.corporation_logo_url(
                        self.corp2.corporation_id, 64
                    ),
                    "text": f"{self.corp2.corporation_name} "
                    f"({self.corp2.corporation_ticker})",
                },
                "description": "MSG",
                "fields": [
                    {
                        "name": "System",
                        "value": "[System One]"
                        f"({dotlan.solar_system_url('System One')})",
                        "inline": False,
                    },
                    {
                        "name": "Fuel Expires",
                        "value": struct.fuel_expires.strftime("%Y-%m-%d %H:%M"),
                        "inline": True,
                    },
                    {"name": "Days Remaining", "value": "5", "inline": True},
                    {
                        "name": "Online Services",
                        "value": "Clone Bay",
                        "inline": False,
                    },
                ],
                "image": {"url": eveimageserver.type_icon_url(STRUCTURE_TYPE_ID, 64)},
            },
        )

    def test_a_blank_message_leaves_the_description_out(self):
        """Discord rejects a null description, and an empty one just wastes a line."""
        embed = build_fuel_embed(self._structure(days=5), "", 1, 5)

        self.assertNotIn("description", embed)

    def test_every_online_service_is_listed(self):
        struct = self._structure(days=5)
        for name in ("Clone Bay", "Market Hub"):
            StructureService.objects.create(structure=struct, name=name, state="online")

        embed = build_fuel_embed(struct, "MSG", 1, 5)

        self.assertEqual(
            sorted(self._fields(embed)["Online Services"].split(",")),
            ["Clone Bay", "Market Hub"],
        )

    def test_a_structure_without_services_reads_none(self):
        struct = self._structure(days=5)

        embed = build_fuel_embed(struct, "MSG", 1, 5)

        self.assertEqual(self._fields(embed)["Online Services"], "None")

    def test_without_fuel_data_only_the_system_field_renders(self):
        struct = self._structure()

        embed = build_fuel_embed(struct, "MSG", 1, 0)

        self.assertEqual(list(self._fields(embed)), ["System"])

    def test_days_remaining_follows_the_task_clock(self):
        """The task's `days_left` is the only source of truth for `{days}`."""
        self._config("Catch All", [(14, "BAND")])
        struct = self._structure(days=13)
        self._burn(5)  # 8 days left for the task; an unshifted clock still reads 13

        self._run()

        body = json.loads(self._pings(struct).first().body)
        self.assertEqual(self._fields(body)["Days Remaining"], "8")


@patch("pinger.tasks._get_wh_cooloff", lambda wh_id: False)
class SendPingPayloadTests(FuelPingTestCase):
    """Level 3: what actually goes over the wire."""

    def _post_body(self, mock_post):
        self.assertTrue(mock_post.called)
        return json.loads(mock_post.call_args.kwargs["data"])

    def _fuel_ping(self, **threshold_kwargs):
        with patch("pinger.models.Ping.send_ping", new=lambda self: None):
            self._config(
                "Catch All", [dict({"days": 7, "message": "MSG"}, **threshold_kwargs)]
            )
            self._structure(days=5)
            self._run()
        return Ping.objects.get()

    def _legacy_ping(self, **kwargs):
        """A notification ping: a positive `notification_id` and no `content`."""
        return Ping.objects.create(
            notification_id=12345,
            hook=self.hook,
            body=json.dumps({"description": "NOTIFICATION"}),
            time=timezone.now(),
            **kwargs,
        )

    @patch("pinger.tasks.requests.post")
    def test_custom_content_is_sent(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)
        ping = self._fuel_ping(ping_here=True)

        tasks.send_ping(ping.id)

        body = self._post_body(mock_post)
        self.assertEqual(body["content"], "@here")
        self.assertEqual(body["allowed_mentions"], {"parse": ["everyone"], "roles": []})
        self.assertEqual(body["embeds"][0]["description"], "MSG")

    @patch("pinger.tasks.requests.post")
    def test_no_at_pings_suppresses_content_including_roles(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)
        self.hook.no_at_pings = True
        self.hook.save()

        ping = self._fuel_ping(ping_here=True)
        ping.content = "@here <@&4242>"
        ping.save()

        tasks.send_ping(ping.id)

        body = self._post_body(mock_post)
        self.assertNotIn("content", body)
        self.assertNotIn("allowed_mentions", body)

    @patch("pinger.tasks.requests.post")
    def test_allowed_mentions_carries_the_role_ids(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)
        ping = self._fuel_ping(ping_here=True)
        ping.content = "@here <@&4242> <@&9001>"
        ping.save()

        tasks.send_ping(ping.id)

        body = self._post_body(mock_post)
        self.assertEqual(body["allowed_mentions"]["roles"], ["4242", "9001"])

    @patch("pinger.tasks.cache_client")
    @patch("pinger.tasks.requests.post")
    def test_legacy_alerting_still_sends_at_here(self, mock_post, mock_cache):
        mock_post.return_value = MagicMock(status_code=204)
        mock_cache.sadd.return_value = 1

        tasks.send_ping(self._legacy_ping(alerting=True).id)

        body = self._post_body(mock_post)
        self.assertEqual(body["content"], "@here")
        self.assertEqual(body["embeds"][0]["description"], "NOTIFICATION")

    @patch("pinger.tasks.cache_client")
    @patch("pinger.tasks.requests.post")
    def test_legacy_non_alerting_ping_carries_embeds_only(self, mock_post, mock_cache):
        mock_post.return_value = MagicMock(status_code=204)
        mock_cache.sadd.return_value = 1

        tasks.send_ping(self._legacy_ping(alerting=False).id)

        body = self._post_body(mock_post)
        self.assertEqual(list(body), ["embeds"])
        self.assertEqual(body["embeds"][0]["description"], "NOTIFICATION")

    @patch("pinger.tasks.cache_client")
    @patch("pinger.tasks.requests.post")
    def test_legacy_alerting_ping_honours_no_at_pings(self, mock_post, mock_cache):
        mock_post.return_value = MagicMock(status_code=204)
        mock_cache.sadd.return_value = 1
        self.hook.no_at_pings = True
        self.hook.save()

        tasks.send_ping(self._legacy_ping(alerting=True).id)

        body = self._post_body(mock_post)
        self.assertNotIn("content", body)
        self.assertNotIn("allowed_mentions", body)

    @patch("pinger.tasks.requests.post")
    def test_fuel_ping_without_mentions_carries_embeds_only(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)

        tasks.send_ping(self._fuel_ping().id)

        body = self._post_body(mock_post)
        self.assertEqual(list(body), ["embeds"])

    @patch("pinger.tasks.cache_client")
    @patch("pinger.tasks.requests.post")
    def test_fuel_pings_bypass_the_duplicate_lock(self, mock_post, mock_cache):
        """`notification_id` is negative on purpose: two configs may ping one structure."""
        mock_post.return_value = MagicMock(status_code=204)
        ping = self._fuel_ping()
        self.assertLess(ping.notification_id, 0)

        tasks.send_ping(ping.id)

        mock_cache.sadd.assert_not_called()


class FuelThresholdValidationTests(FuelPingTestCase):
    """`FuelThreshold.clean()` is all that stands between an admin typo and a
    `KeyError` that kills a whole corp's run mid-way through."""

    def _threshold(self, **kwargs):
        config = kwargs.pop("config", None) or self._config("Catch All", [])
        return FuelThreshold(config=config, **{"days": 7, "message": "MSG", **kwargs})

    def test_an_unknown_substitution_is_rejected(self):
        with self.assertRaises(ValidationError) as caught:
            self._threshold(message="{corp} is low").full_clean()

        error = caught.exception.message_dict["message"][0]
        self.assertIn("{corp}", error)
        for allowed in ("{days}", "{structure}", "{system}"):
            self.assertIn(allowed, error)

    def test_a_malformed_substitution_is_rejected(self):
        with self.assertRaises(ValidationError) as caught:
            self._threshold(message="{").full_clean()

        self.assertIn(
            "Malformed substitution", caught.exception.message_dict["message"][0]
        )

    def test_a_blank_message_validates(self):
        self._threshold(message="").full_clean()

    def test_every_supported_substitution_validates(self):
        self._threshold(message="{structure} in {system} has {days} days").full_clean()

    def test_repeat_days_zero_is_rejected(self):
        """Zero would make `(last - days_left) >= 0` true on every single run."""
        with self.assertRaises(ValidationError) as caught:
            self._threshold(repeat_days=0).full_clean()

        self.assertIn("repeat_days", caught.exception.message_dict)

    def test_repeat_days_null_and_positive_validate(self):
        self._threshold(repeat_days=None).full_clean()
        self._threshold(repeat_days=1).full_clean()

    def test_one_threshold_per_config_and_days(self):
        config = self._config("Catch All", [(7, "MSG")])

        with self.assertRaises(IntegrityError), transaction.atomic():
            FuelThreshold.objects.create(config=config, days=7, message="OTHER")

    def test_one_record_per_structure_and_config(self):
        """`update_or_create` in the task leans on this constraint."""
        config = self._config("Catch All", [(7, "MSG")])
        struct = self._structure(days=5)
        FuelPingRecord.objects.create(structure=struct, config=config, last_ping_time=5)

        with self.assertRaises(IntegrityError), transaction.atomic():
            FuelPingRecord.objects.create(
                structure=struct, config=config, last_ping_time=4
            )


class FuelAdminFormTests(FuelPingTestCase):
    """A config with no thresholds still matches structures and still raises the
    specificity bar, so admin is the only place it can be stopped."""

    FormSet = inlineformset_factory(
        FuelPingConfig,
        FuelThreshold,
        form=FuelThresholdForm,
        formset=FuelThresholdFormSet,
        extra=1,
    )

    NO_THRESHOLDS = "A fuel ping config needs at least one threshold."

    def _data(self, total, initial=0, **fields):
        return {
            "thresholds-TOTAL_FORMS": str(total),
            "thresholds-INITIAL_FORMS": str(initial),
            "thresholds-MIN_NUM_FORMS": "0",
            "thresholds-MAX_NUM_FORMS": "1000",
            **fields,
        }

    def test_a_config_with_no_forms_is_rejected(self):
        formset = self.FormSet(self._data(0), instance=self._config("Empty", []))

        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.non_form_errors(), [self.NO_THRESHOLDS])

    def test_an_untouched_extra_form_does_not_count(self):
        formset = self.FormSet(
            self._data(1, **{"thresholds-0-color": "15158332"}),  # admin's default
            instance=self._config("Empty", []),
        )

        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.non_form_errors(), [self.NO_THRESHOLDS])

    def test_deleting_the_last_threshold_is_rejected(self):
        config = self._config("Catch All", [(7, "MSG")])
        threshold = config.thresholds.get()

        formset = self.FormSet(
            self._data(
                1,
                initial=1,
                **{
                    "thresholds-0-id": str(threshold.id),
                    "thresholds-0-days": "7",
                    "thresholds-0-message": "MSG",
                    "thresholds-0-color": "15158332",
                    "thresholds-0-DELETE": "on",
                },
            ),
            instance=config,
        )

        self.assertFalse(formset.is_valid())
        self.assertEqual(formset.non_form_errors(), [self.NO_THRESHOLDS])

    def test_one_live_threshold_is_enough(self):
        formset = self.FormSet(
            self._data(
                1,
                **{
                    "thresholds-0-days": "7",
                    "thresholds-0-message": "MSG",
                    "thresholds-0-color": "15158332",
                },
            ),
            instance=self._config("Empty", []),
        )

        self.assertTrue(formset.is_valid(), formset.errors)

    def test_group_mentions_need_the_discord_service(self):
        config = self._config("Empty", [])
        group = Group.objects.create(name="alpha")

        with patch("pinger.admin._discord_service_installed", lambda: False):
            form = FuelThresholdForm(
                {
                    "config": str(config.id),
                    "days": "7",
                    "message": "MSG",
                    "color": "15158332",
                    "ping_groups": [str(group.id)],
                }
            )

            self.assertFalse(form.is_valid())

        self.assertIn("ping_groups", form.errors)

    def _inline_formset(self, config=None):
        """The formset the admin actually builds, as opposed to `self.FormSet`."""
        request = RequestFactory().get("/")
        request.user = User.objects.create_superuser(f"admin{User.objects.count()}")
        inline = FuelThresholdInline(FuelPingConfig, admin.site)
        return inline.get_formset(request, config)

    def test_group_mentions_are_hidden_without_the_discord_service(self):
        with patch("pinger.admin._discord_service_installed", lambda: False):
            formset = self._inline_formset()

        self.assertNotIn("ping_groups", formset.form.base_fields)

    def test_group_mentions_are_shown_with_the_discord_service(self):
        with patch("pinger.admin._discord_service_installed", lambda: True):
            formset = self._inline_formset()

        self.assertIn("ping_groups", formset.form.base_fields)

    def test_saving_without_the_discord_service_keeps_existing_groups(self):
        """Hiding the field must not quietly drop groups configured while discord was
        still installed — nothing renders them, so nothing can put them back."""
        config = self._config("Catch All", [(7, "MSG")])
        threshold = config.thresholds.get()
        group = Group.objects.create(name="alpha")
        threshold.ping_groups.add(group)

        with patch("pinger.admin._discord_service_installed", lambda: False):
            FormSet = self._inline_formset(config)
            formset = FormSet(
                self._data(
                    1,
                    initial=1,
                    **{
                        "thresholds-0-id": str(threshold.id),
                        "thresholds-0-days": "7",
                        "thresholds-0-message": "CHANGED",
                        "thresholds-0-color": "15158332",
                    },
                ),
                instance=config,
            )

            self.assertTrue(formset.is_valid(), formset.errors)
            formset.save()

        threshold.refresh_from_db()
        self.assertEqual(threshold.message, "CHANGED")
        self.assertEqual(list(threshold.ping_groups.all()), [group])

    def test_the_threshold_cards_are_styled(self):
        """The stylesheet draws each threshold as its own card; without the class to
        scope it and the media to load it, the ladder renders as one wall of fields."""
        inline = FuelThresholdInline(FuelPingConfig, admin.site)

        self.assertIn("fuel-threshold-inline", inline.classes)
        self.assertIn(FUEL_THRESHOLD_CSS, str(inline.media))

    def test_the_stylesheet_resolves(self):
        self.assertIsNotNone(finders.find(FUEL_THRESHOLD_CSS))


@patch("pinger.utils.discord._discord_service_installed", lambda: True)
class RoleResolutionTests(TestCase):
    """`role_id_for_group` against the `DiscordUser.objects.group_to_role` contract:
    the role as a dict, or `{}` when nothing matches."""

    def setUp(self):
        self.group = Group.objects.create(name="alpha")

    def _discord_models(self, group_to_role):
        """Stand in for the discord service's models module, which is not installed."""
        module = ModuleType(DISCORD_MODELS)
        module.DiscordUser = SimpleNamespace(
            objects=SimpleNamespace(group_to_role=group_to_role)
        )
        return patch.dict(sys.modules, {DISCORD_MODELS: module})

    def test_a_matching_role_resolves_to_its_id(self):
        with self._discord_models(lambda group: {"id": 4242, "name": group.name}):
            self.assertEqual(role_id_for_group(self.group), 4242)

    def test_no_matching_role_warns_and_resolves_to_none(self):
        with self._discord_models(lambda group: {}):
            with self.assertLogs("pinger.utils.discord", "WARNING") as logs:
                self.assertIsNone(role_id_for_group(self.group))

        self.assertIn("no discord role matches", logs.output[0])

    def test_an_http_error_warns_and_resolves_to_none(self):
        def boom(group):
            raise HTTPError("502 Bad Gateway")

        with self._discord_models(boom):
            with self.assertLogs("pinger.utils.discord", "WARNING") as logs:
                self.assertIsNone(role_id_for_group(self.group))

        self.assertIn("failed to fetch the discord role", logs.output[0])

    def test_without_the_discord_service_nothing_is_imported(self):
        # `None` in sys.modules makes the import raise, so a clean None proves the
        # import never ran
        with patch("pinger.utils.discord._discord_service_installed", lambda: False):
            with patch.dict(sys.modules, {DISCORD_MODELS: None}):
                self.assertIsNone(role_id_for_group(self.group))
