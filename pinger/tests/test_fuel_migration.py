import importlib
from datetime import timedelta
from unittest.mock import patch

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from pinger.tests.test_fuel_pings import FuelPingTestCase

# the module name starts with a digit, so it cannot be imported with `from ... import`
MIGRATION = importlib.import_module("pinger.migrations.0027_fuel_ping_configs")


@patch("pinger.models.Ping.send_ping", new=lambda self: None)
class CatchAllLadderTests(FuelPingTestCase):
    """The seeded ladder has to reproduce master's hardcoded 15/8/3/2 bands, or every
    structure already inside a band re-pings the first time the new task runs."""

    def test_the_seeded_ladder_reproduces_the_hardcoded_bands(self):
        self._config(
            "Default Fuel Pings",
            [
                {
                    "days": days,
                    "message": message,
                    "repeat_days": None,
                    "ping_here": ping_here,
                }
                for days, message, ping_here in MIGRATION.CATCH_ALL_LADDER
            ],
        )

        expected = {
            # days_left: (message, master's `alerting = days_left < 3`)
            0: ("Critical Fuel! :ambulance:", True),
            1: ("Critical Fuel! :ambulance:", True),
            2: ("Critical Fuel! :ambulance: :eyes:", True),
            3: ("Low Fuel", False),
            7: ("Low Fuel", False),
            8: ("Fuel Warning — 8 days remaining", False),
            14: ("Fuel Warning — 14 days remaining", False),
            15: (None, False),  # master's `daysLeft < 15`
        }
        structures = {days: self._structure(days=days) for days in expected}

        self._run()

        for days, (message, alerting) in expected.items():
            with self.subTest(days=days):
                self.assertEqual(
                    self._messages(structures[days]), [message] if message else []
                )
                if message:
                    ping = self._pings(structures[days]).get()
                    self.assertEqual(ping.alerting, alerting)
                    self.assertEqual(ping.content, "@here" if alerting else "")


class SeedCatchAllMigrationTests(TransactionTestCase):
    """`seed_catch_all` is the entire upgrade path off the hardcoded ladder: it purges
    unusable rows, dedupes to one row per structure, and adopts them into the catch-all."""

    migrate_from = [("pinger", "0026_add_more_types")]
    migrate_to = [("pinger", "0027_fuel_ping_configs")]

    def setUp(self):
        self.addCleanup(self._migrate_to_latest)
        self.old_apps = self._migrate(self.migrate_from)

    def _migrate(self, targets):
        """Move `targets`' apps to those migrations and return the matching models."""
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        executor.loader.build_graph()

        # A state built from `targets` alone would carry every other app at whatever
        # migration pinger happens to depend on, which no longer matches their tables.
        pinned = {app for app, _ in targets}
        nodes = [n for n in executor.loader.graph.leaf_nodes() if n[0] not in pinned]
        return executor.loader.project_state(nodes + list(targets)).apps

    def _migrate_to_latest(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        self._migrate(executor.loader.graph.leaf_nodes("pinger"))

    def _corp_audit(self):
        corp = self.old_apps.get_model("eveonline", "EveCorporationInfo").objects.create(
            corporation_id=98000001,
            corporation_name="corporation.migrated",
            corporation_ticker="MIGR",
            member_count=1,
            ceo_id=1,
        )
        return self.old_apps.get_model(
            "corptools", "CorporationAudit"
        ).objects.create(corporation=corp)

    def _webhook(self, i, fuel_pings):
        return self.old_apps.get_model("pinger", "DiscordWebhook").objects.create(
            nickname=f"Hook {i}",
            discord_webhook=f"https://example.com/hook/{i}",
            fuel_pings=fuel_pings,
        )

    def _structure(self, audit, structure_id, name):
        return self.old_apps.get_model("corptools", "Structure").objects.create(
            corporation=audit,
            profile_id=1,
            reinforce_hour=12,
            state="shield_vulnerable",
            structure_id=structure_id,
            system_id=30000001,
            type_id=35832,
            name=name,
        )

    def test_seed_catch_all_upgrades_the_legacy_records(self):
        audit = self._corp_audit()
        keeper = self._structure(audit, 99000001, "Keeper")
        duped = self._structure(audit, 99000002, "Duped")
        no_ping_time = self._structure(audit, 99000003, "Never Pinged")

        fuel_hook = self._webhook(0, fuel_pings=True)
        self._webhook(1, fuel_pings=False)

        Record = self.old_apps.get_model("pinger", "FuelPingRecord")
        empty_at = timezone.now() + timedelta(days=7)
        Record.objects.create(
            structure=keeper, last_ping_time=7, last_message="Low Fuel",
            date_empty=empty_at,
        )
        Record.objects.create(structure=None, last_ping_time=7)  # no structure
        Record.objects.create(structure=no_ping_time, last_ping_time=None)  # never fired

        Record.objects.create(structure=duped, last_ping_time=2, last_message="newest")
        stale = Record.objects.create(
            structure=duped, last_ping_time=9, last_message="stale"
        )
        # `last_update` is auto_now, so it can only be backdated after the fact
        Record.objects.filter(id=stale.id).update(
            last_update=timezone.now() - timedelta(days=1)
        )

        new_apps = self._migrate(self.migrate_to)

        config = new_apps.get_model("pinger", "FuelPingConfig").objects.get()
        self.assertEqual(config.name, "Default Fuel Pings")
        self.assertFalse(config.always_ping)
        self.assertFalse(config.blocks_broader)
        self.assertEqual(
            sorted(config.thresholds.values_list("days", "message", "ping_here")),
            sorted(MIGRATION.CATCH_ALL_LADDER),
        )
        self.assertEqual(
            list(config.thresholds.values_list("repeat_days", flat=True)),
            [None] * len(MIGRATION.CATCH_ALL_LADDER),
        )
        # only the webhooks that opted in under the dropped `fuel_pings` flag
        self.assertEqual(
            set(config.webhooks.values_list("id", flat=True)), {fuel_hook.id}
        )

        records = new_apps.get_model("pinger", "FuelPingRecord").objects
        self.assertEqual(
            sorted(
                records.values_list("structure_id", "last_ping_time", "last_message")
            ),
            [(keeper.pk, 7, "Low Fuel"), (duped.pk, 2, "newest")],
        )
        self.assertEqual(
            set(records.values_list("config_id", flat=True)), {config.id}
        )
        self.assertEqual(records.get(structure_id=keeper.pk).date_empty, empty_at)

    def test_seed_catch_all_without_opted_in_webhooks_is_inert(self):
        """No webhook had the flag, so the config adopts none and `usable()` drops it —
        fuel stays as silent as it was — but the records still need it to adopt them."""
        audit = self._corp_audit()
        structure = self._structure(audit, 99000001, "Keeper")
        self._webhook(0, fuel_pings=False)

        Record = self.old_apps.get_model("pinger", "FuelPingRecord")
        Record.objects.create(structure=structure, last_ping_time=7)

        new_apps = self._migrate(self.migrate_to)

        config = new_apps.get_model("pinger", "FuelPingConfig").objects.get()
        self.assertEqual(config.webhooks.count(), 0)
        self.assertEqual(config.thresholds.count(), len(MIGRATION.CATCH_ALL_LADDER))
        self.assertEqual(
            new_apps.get_model("pinger", "FuelPingRecord").objects.get().config_id,
            config.id,
        )
