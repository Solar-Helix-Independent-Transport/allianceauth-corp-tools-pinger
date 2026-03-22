
import json

from corptools.task_helpers import sanitize_notification_type

from django.utils import timezone

from pinger.notifications.base import get_available_types
from pinger.tasks import Notification

from . import PingerTests


class TestSov(PingerTests):

    def _build_notification(self, notification_type, notificaiton_text):

        note_class = Notification(character=self.ca3,
                    notification_id=123456789,
                    timestamp=timezone.now(),
                    notification_type=sanitize_notification_type(notification_type),
                    notification_text=str.encode(notificaiton_text))

        test_note = get_available_types()[notification_type](note_class)

        return json.loads(test_note._ping)

    def test_sov_ref(self):
        notification_type = "SovStructureReinforced"
        notificaiton_text = \
"""
campaignEventType: 2
decloakTime: 133772899408813831
solarSystemID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Entosis notification"
        )
        self.assertEqual(
            note["description"],
            f"IHub Reinforced in {self.s1t}"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "System", "value": self.s1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Region", "value": self.r1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][3],
            {"name": "Date Out", "value": self.dateTime1String, "inline": False}
        )

    def test_sov_attack(self):
        notification_type = "EntosisCaptureStarted"
        notificaiton_text = \
"""
solarSystemID: 1
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Entosis Notification"
        )
        self.assertEqual(
            note["description"],
            f"Entosis has started in {self.s1t} on {self.typeName.name}"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "System", "value": self.s1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Region", "value": self.r1t, "inline": True}
        )
