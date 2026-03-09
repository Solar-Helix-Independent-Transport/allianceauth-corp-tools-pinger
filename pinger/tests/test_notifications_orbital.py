
from . import PingerTests


class TestOrbitals(PingerTests):

    def test_den_ref(self):
        notification_type = "MercenaryDenReinforced"
        notificaiton_text = \
"""
aggressorAllianceName: Unknown
aggressorCharacterID: 1
aggressorCorporationName: <a href=\"showinfo:2//1715234301\">Isk sellers</a>
itemID: &id001 1
mercenaryDenShowInfoData:
- showinfo
- 1
- *id001
planetID: 1
planetShowInfoData:
- showinfo
- 11
- 1
solarsystemID: 1
timestampEntered: 133771953678813831
timestampExited: 133772899408813831
typeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Merc Den Reinforced"
        )
        self.assertEqual(
            note["description"],
            f"{self.typeName.name} has lost its Shields"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "System/Planet", "value": self.p1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Region", "value": self.r1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][2],
            {"name": "Type", "value": self.typeName.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][3],
            {"name": "Owner", "value": self.corp1.corporation_name, "inline": False}
        )
        self.assertEqual(
            note["fields"][5],
            {"name": "Date Out", "value": self.dateTime1String, "inline": False}
        )

    def test_den_attack(self):
        notification_type = "MercenaryDenAttacked"
        notificaiton_text = \
"""
aggressorAllianceName: Unknown
aggressorCharacterID: 1
aggressorCorporationName: <a href=\"showinfo:2//1715234301\">Isk sellers</a>
armorPercentage: 50.500001
hullPercentage: 99.500001
itemID: &id001 1047336167535
mercenaryDenShowInfoData:
- showinfo
- 1
- *id001
planetID: 1
planetShowInfoData:
- showinfo
- 11
- 1
shieldPercentage: 25.500001
solarsystemID: 1
typeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Merc Den Under Attack"
        )
        self.assertEqual(
            note["description"],
            f"{self.typeName.name} under Attack!\n[ S: 25.50% A: 50.50% H: 99.50% ]"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "System/Planet", "value": self.p1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Region", "value": self.r1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][2],
            {"name": "Type", "value": self.typeName.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][3],
            {"name": "Owner", "value": self.corp1.corporation_name, "inline": False}
        )
        self.assertEqual(
            note["fields"][4],
            {"name": "Attacker", "value": self.eveName1link , "inline": False}
        )
