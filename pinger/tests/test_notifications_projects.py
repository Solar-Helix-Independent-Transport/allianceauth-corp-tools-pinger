
from allianceauth.eveonline.evelinks import evewho, zkillboard

from . import PingerTests


class TestProjects(PingerTests):

    def test_corp_goal_created(self):
        notification_type = "CorporationGoalCreated"
        notificaiton_text = \
"""
corporation_id: 2
creator_id: 1
goal_id: 245377162334488937895806423904722129957
goal_name: Ice Ice Ice!
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Corp Project Created"
        )
        self.assertEqual(
            note["description"],
            f"```Ice Ice Ice!```\n"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Creator", "value": f"[Char 1]({evewho.character_url(1)})", "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Corporation", "value": self.eveName2.name, "inline": True}
        )

    def test_corp_goal_closed(self):
        notification_type = "CorporationGoalClosed"
        notificaiton_text = \
"""
closer_id: 3
corporation_id: 2
creator_id: 1
goal_id: 339451813142555916388672576952401560776
goal_name: Ice Ice Ice!
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Corp Project Closed"
        )
        self.assertEqual(
            note["description"],
            f"```Ice Ice Ice!```\nClosed by: Alli 3"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Creator", "value": f"[Char 1]({evewho.character_url(1)})", "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Corporation", "value": self.eveName2.name, "inline": True}
        )

    def test_corp_goal_completed(self):
        notification_type = "CorporationGoalCompleted"
        notificaiton_text = \
"""
corporation_id: 2
creator_id: 1
goal_id: 245377162334488937895806423904722129957
goal_name: Ice Ice Ice!
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Corp Project Completed"
        )
        self.assertEqual(
            note["description"],
            f"```Ice Ice Ice!```\n"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Creator", "value": f"[Char 1]({evewho.character_url(1)})", "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Corporation", "value": self.eveName2.name, "inline": True}
        )

    def test_corp_goal_expired(self):
        notification_type = "CorporationGoalExpired"
        notificaiton_text = \
"""
corporation_id: 2
creator_id: 1
goal_id: 245377162334488937895806423904722129957
goal_name: Ice Ice Ice!
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Corp Project Expired"
        )
        self.assertEqual(
            note["description"],
            f"```Ice Ice Ice!```\n"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Creator", "value": f"[Char 1]({evewho.character_url(1)})", "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Corporation", "value": self.eveName2.name, "inline": True}
        )

    def test_corp_goal_limit_reached(self):
        notification_type = "CorporationGoalLimitReached"
        notificaiton_text = \
"""
corporation_id: 2
creator_id: 1
goal_id: 245377162334488937895806423904722129957
goal_name: Ice Ice Ice!
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Corp Project Limit Reached"
        )
        self.assertEqual(
            note["description"],
            f"```Ice Ice Ice!```\n"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Creator", "value": f"[Char 1]({evewho.character_url(1)})", "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Corporation", "value": self.eveName2.name, "inline": True}
        )
