
from allianceauth.eveonline.evelinks import zkillboard

from . import PingerTests


class TestStructures(PingerTests):

    def test_str_tower(self):
        notification_type = "TowerAlertMsg"
        notificaiton_text = \
"""
aggressorAllianceID: 3
aggressorCorpID: 2
aggressorID: 1
armorValue: 0.3566666666
hullValue: 0.75666666666
moonID: 1
shieldValue: 0.454444444
solarSystemID: 1
typeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            "Starbase Under Attack!"
        )
        self.assertEqual(
            note["description"],
            f"Structure under Attack!\n[ S: {45.444444444:.2f}% A: {35.666666666:.2f}% H: {75.666666666:.2f}% ]"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Moon", "value": self.moon.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "System", "value": self.s1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][2],
            {"name": "Region", "value": self.r1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][3],
            {"name": "Type", "value": self.typeName.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][4],
            {
                "name": "Attacker",
                "value": (
                    f"*[Char 1]({zkillboard.character_url(1)})*"
                    f", [Corp 2]({zkillboard.corporation_url(2)})"
                    f", **[Alli 3]({zkillboard.alliance_url(3)})**"
                ),
                "inline": False
            }
        )
