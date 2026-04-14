
import json

from corptools.task_helpers import sanitize_notification_type

from django.utils import timezone

from pinger.notifications.base import get_available_types
from pinger.tasks import Notification

from . import PingerTests


class TestWar(PingerTests):


    def test_war(self):
        notification_type = "WarDeclared"
        notificaiton_text = \
"""
againstID: 1
cost: 100000000
declaredByID: 1
delayHours: 123
hostileState: false
timeStarted: 133394547000000000
warHQ: <p>Test War HQ</p>
warHQ_IdType:
- 1042059347183
- 35833
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"War Declared"
        )
        self.assertEqual(
            note["description"],
            f"War against `Char 1` declared by `Char 1`\nWar HQ `Test War HQ`\nFighting can commence in 123 hours"
        )
