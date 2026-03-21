
from allianceauth.eveonline.evelinks import zkillboard

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

    def test_hook_dep(self):
        notification_type = "SkyhookDeployed"
        notificaiton_text = \
"""
itemID: &id002 1046336471456
ownerCorpLinkData:
- showinfo
- 2
- 98609787
ownerCorpName: Initiative Trust
planetID: &id001 1
planetShowInfoData:
- showinfo
- 13
- *id001
skyhookShowInfoData:
- showinfo
- 81080
- *id002
solarsystemID: 1
timeLeft: 958011150532
typeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Skyhook Deployed"
        )
        self.assertEqual(
            note["description"],
            f"{self.s1t} - {self.r1t} - {self.planet.name} Deployed"
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
            {"name": "Time Till Out", "value": "1 Days, 2 Hours, 36 Min", "inline": False}
        )

    def test_hook_online(self):
        notification_type = "SkyhookOnline"
        notificaiton_text = \
"""
itemID: &id002 1046336471456
planetID: &id001 1
planetShowInfoData:
- showinfo
- 13
- *id001
skyhookShowInfoData:
- showinfo
- 81080
- *id002
solarsystemID: 1
typeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Skyhook Online"
        )
        self.assertEqual(
            note["description"],
            f"{self.s1t} - {self.r1t} - {self.planet.name} Online"
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


    def test_ref_shld(self):
        notification_type = "SkyhookLostShields"
        notificaiton_text = \
"""
itemID: &id001 1046042982766
planetID: 1
planetShowInfoData:
- showinfo
- 2017
- 40288591
skyhookShowInfoData:
- showinfo
- 81080
- *id001
solarsystemID: 1
timeLeft: 958011150532               # figure out what this is
timestamp: 132052212600000000         # figure out what this is
typeID: 1
vulnerableTime: 9000000000            # figure out what this is
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Skyhook Reinforced"
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
            {"name": "Owner", "value": self.ca1.character.corporation_name, "inline": False}
        )
        self.assertEqual(
            note["fields"][5],
            {"name": "Date Out", "value": "2019-06-17 05:01", "inline": False}
        )


    def test_ref_hull(self):
        notification_type = "OrbitalReinforced"
        notificaiton_text = \
"""
aggressorAllianceID: null
aggressorCorpID: 1
aggressorID: 1
planetID: 1
planetTypeID: 2016
reinforceExitTime: 132052212600000000
solarSystemID: 1
typeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            f"Skyhook Reinforced"
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
            {"name": "Owner", "value": self.ca1.character.corporation_name, "inline": False}
        )
        self.assertEqual(
            note["fields"][5],
            {"name": "Date Out", "value": "2019-06-17 05:01", "inline": False}
        )

    def test_orb_attack(self):
        notification_type = "OrbitalAttacked"
        notificaiton_text = \
"""
aggressorAllianceID: 3
aggressorCorpID: 2
aggressorID: 1
planetID: 1
planetTypeID: 1
shieldLevel: 0.45555555555
solarSystemID: 1
typeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            "Poco Under Attack"
        )
        self.assertEqual(
            note["description"],
            f"{self.typeName.name} under Attack!\nShield Level: {45.555555555:.2f}%"
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

    def test_hook_attack(self):
        notification_type = "SkyhookUnderAttack"
        notificaiton_text = \
"""
allianceID: 3
allianceLinkData:
- showinfo
- 16159
- 1900696668
allianceName: The Initiative.
armorPercentage: 85.444444
charID: 1
corpLinkData:
- showinfo
- 5
- 2
corpName: Tactically Challenged
hullPercentage: 75.666666
isActive: true
itemID: &id001 1
planetID: 1
planetShowInfoData:
- showinfo
- 2015
- 40290676
shieldPercentage: 94.555555555555
skyhookShowInfoData:
- showinfo
- 81080
- *id001
solarsystemID: 1
typeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            "Skyhook Under Attack"
        )
        self.assertEqual(
            note["description"],
            f"{self.typeName.name} - {self.p1t} under Attack!\nS: {94.555555555:.2f}%, A: {85.444444444:.2f}%, H: {75.66666666:.2f}%"
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
