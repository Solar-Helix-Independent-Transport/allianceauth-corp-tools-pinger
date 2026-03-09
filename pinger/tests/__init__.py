import datetime
import json

from corptools.models import EveName
from corptools.task_helpers import sanitize_notification_type
from corptools.tests import CorptoolsTestCase
from eve_sde.models import Constellation, ItemType, Planet, Region, SolarSystem

from django.utils import timezone

from pinger.notifications.base import get_available_types
from pinger.notifications.helpers import filetime_to_dt
from pinger.tasks import Notification


class PingerTests(CorptoolsTestCase):

    def setUp(cls):
        super().setUp()
        cls.eveName3 = EveName.objects.create(
            eve_id=3,
            name="Alli 3",
            category="alliance"
        )
        cls.eveName2 = EveName.objects.create(
            eve_id=2,
            name="Corp 2",
            alliance=cls.eveName3,
            category="corporation"
        )
        cls.eveName1 = EveName.objects.create(
            eve_id=1,
            name="Char 1",
            corporation=cls.eveName2,
            alliance=cls.eveName3,
            category="character"
        )
        cls.eveName1link = "[%s](https://zkillboard.com/character/%s/)" % \
            (
                cls.eveName1.name,
                cls.eveName1.eve_id
            )

        cls.typeName = ItemType.objects.create(
            id=1,
            name="Item Type 1",
            published=True
        )
        cls.dateTime1Timestamp = 133772899408813831
        cls.dateTime1 = filetime_to_dt(
            cls.dateTime1Timestamp
        ).replace(tzinfo=datetime.timezone.utc)
        cls.dateTime1String = cls.dateTime1.strftime("%Y-%m-%d %H:%M")
        cls.corp1t = "[%s](https://zkillboard.com/corporation/%s/)" % (
            cls.corp1.corporation_name,
            cls.corp1.corporation_id
        )

        cls.region = Region.objects.create(
            id=1,
            name="Region 1"
        )
        cls.r1t = f"[Region 1](https://evemaps.dotlan.net/map/Region_1)"

        cls.constellation = Constellation.objects.create(
            id=1,
            name="Constellation 1",
            region=cls.region
        )
        cls.c1t = f"[Constellation 1](https://evemaps.dotlan.net/constellation/Constellation_1)"

        cls.system = SolarSystem.objects.create(
            id=1,
            name="System 1",
            security_status=0.0,
            x=0,
            y=0,
            z=0,
            constellation=cls.constellation
        )
        cls.s1t = f"[System 1](https://evemaps.dotlan.net/system/System_1)"

        cls.planet = Planet.objects.create(
            id=1,
            name="Planet 1",
            x=0,
            y=0,
            z=0,
            solar_system=cls.system
        )
        cls.p1t = f"[System 1](https://evemaps.dotlan.net/system/System_1) - Planet 1"

    def _build_notification(self, notification_type, notificaiton_text):

        note_class = Notification(character=self.ca1,
                    notification_id=123456789,
                    timestamp=timezone.now(),
                    notification_type=sanitize_notification_type(notification_type),
                    notification_text=str.encode(notificaiton_text))

        test_note = get_available_types()[notification_type](note_class)

        return json.loads(test_note._ping)
