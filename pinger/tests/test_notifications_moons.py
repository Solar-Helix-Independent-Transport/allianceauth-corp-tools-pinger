
from allianceauth.eveonline.evelinks import zkillboard

from . import PingerTests


class TestStructures(PingerTests):

    def test_moon_fin(self):
        notification_type = "MoonminingExtractionFinished"
        notificaiton_text = \
"""
autoTime: 132052212600000000
moonID: 1
oreVolumeByType:
    1: 1000000.0
    2: 2000000.0
solarSystemID: 1
structureID: 12345678
structureLink: <a href="showinfo:35835//1029754067191">NY6-FH - ISF Three</a>
structureName: Test STR
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            "Moon Extraction Complete!"
        )
        self.assertEqual(
            note["description"],
            f"Ready to Fracture!"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Structure", "value": "Test STR", "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "System", "value": self.s1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][2],
            {"name": "Moon", "value": self.moon.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][3],
            {"name": "Type", "value": self.typeName.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][4],
            {"name": "Auto Fire", "value": "2019-06-17 05:01", "inline": False}
        )
        self.assertEqual(
            note["fields"][5],
            {"name": "Ore", "value": f"**Item Type 1**: {33.3333:2.1f}%\n**Item Type 2**: {66.6666:2.1f}%"}
        )

    def test_moon_frack(self):
        notification_type = "MoonminingAutomaticFracture"
        notificaiton_text = \
"""
moonID: 1
oreVolumeByType:
    1: 1000000.0
    2: 2000000.0
solarSystemID: 1
structureID: 12345678
structureLink: <a href="showinfo:35835//1029754067191">NY6-FH - ISF Three</a>
structureName: Test STR
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            "Moon Auto-Fractured!"
        )
        self.assertEqual(
            note["description"],
            f"Ready to Mine!"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Structure", "value": "Test STR", "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "System", "value": self.s1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][2],
            {"name": "Moon", "value": self.moon.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][3],
            {"name": "Type", "value": self.typeName.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][4],
            {"name": "Ore", "value": f"**Item Type 1**: {33.3333:2.1f}%\n**Item Type 2**: {66.6666:2.1f}%"}
        )

    def test_moon_fire(self):
        notification_type = "MoonminingLaserFired"
        notificaiton_text = \
"""
firedBy: 1
firedByLink: <a href="showinfo:1380//824787891">Character 1</a>
moonID: 1
oreVolumeByType:
    1: 1000000.0
    2: 2000000.0
solarSystemID: 1
structureID: 12345678
structureLink: <a href="showinfo:35835//1029754067191">NY6-FH - ISF Three</a>
structureName: Test STR
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            "Moon Laser Fired!"
        )
        self.assertEqual(
            note["description"],
            "Fired By [Character 1](https://zkillboard.com/character/1/)"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Structure", "value": "Test STR", "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "System", "value": self.s1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][2],
            {"name": "Moon", "value": self.moon.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][3],
            {"name": "Type", "value": self.typeName.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][4],
            {"name": "Ore", "value": f"**Item Type 1**: {33.3333:2.1f}%\n**Item Type 2**: {66.6666:2.1f}%"}
        )

    def test_moon_start(self):
        notification_type = "MoonminingExtractionStarted"
        notificaiton_text = \
"""
autoTime: 132052212600000000
firedBy: 1
firedByLink: <a href="showinfo:1380//824787891">Character 1</a>
moonID: 1
oreVolumeByType:
    1: 1000000.0
    2: 2000000.0
readyTime: 132052212600000000
solarSystemID: 1
startedBy: 1
startedByLink: <a href="showinfo:1380//824787891">Character 1</a>
structureID: 12345678
structureLink: <a href="showinfo:35835//1029754067191">NY6-FH - ISF Three</a>
structureName: Test STR
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            "Moon Extraction Started!"
        )
        self.assertEqual(
            note["description"],
            "Fired By [Character 1](https://zkillboard.com/character/1/)"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Structure", "value": "Test STR", "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "System", "value": self.s1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][2],
            {"name": "Moon", "value": self.moon.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][3],
            {"name": "Type", "value": self.typeName.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][4],
            {"name": "Ready Time", "value": "2019-06-17 05:01", "inline": False}
        )
        self.assertEqual(
            note["fields"][5],
            {"name": "Auto Fire", "value": "2019-06-17 05:01", "inline": False}
        )
        self.assertEqual(
            note["fields"][6],
            {"name": "Ore", "value": f"**Item Type 1**: {33.3333:2.1f}%\n**Item Type 2**: {66.6666:2.1f}%"}
        )
