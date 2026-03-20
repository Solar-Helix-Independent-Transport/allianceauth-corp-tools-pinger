
from allianceauth.eveonline.evelinks import zkillboard

from . import PingerTests


class TestStructures(PingerTests):

    def test_str_ref_shld(self):
        notification_type = "StructureLostShields"
        notificaiton_text = \
"""
solarsystemID: 1
structureID: &id001 12345678
structureShowInfoData:
- showinfo
- 35835
- *id001
structureTypeID: 1
timeLeft: 958011150532
timestamp: 132792333490000000
vulnerableTime: 9000000000
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            self.eveLoc1.location_name
        )
        self.assertEqual(
            note["description"],
            f"Structure has lost its Shields"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "System", "value": self.s1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Type", "value": self.typeName.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][2],
            {"name": "Owner", "value": self.corp1.corporation_name, "inline": False}
        )
        self.assertEqual(
            note["fields"][3],
            {"name": "Time Till Out", "value": "1 Days, 2 Hours, 36 Min", "inline": False}
        )


    def test_str_ref_armr(self):
        notification_type = "StructureLostArmor"
        notificaiton_text = \
"""
solarsystemID: 1
structureID: &id001 12345678
structureShowInfoData:
- showinfo
- 35835
- *id001
structureTypeID: 1
timeLeft: 958011150532
timestamp: 132792333490000000
vulnerableTime: 9000000000
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            self.eveLoc1.location_name
        )
        self.assertEqual(
            note["description"],
            f"Structure has lost its Armor"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "System", "value": self.s1t, "inline": True}
        )
        self.assertEqual(
            note["fields"][1],
            {"name": "Type", "value": self.typeName.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][2],
            {"name": "Owner", "value": self.corp1.corporation_name, "inline": False}
        )
        self.assertEqual(
            note["fields"][3],
            {"name": "Time Till Out", "value": "1 Days, 2 Hours, 36 Min", "inline": False}
        )

    def test_str_attack(self):
        notification_type = "StructureUnderAttack"
        notificaiton_text = \
"""
allianceID: 3
allianceLinkData:
- showinfo
- 30
- 500010
allianceName: Guristas Pirates
armorPercentage: 100.0
charID: 1
corpLinkData:
- showinfo
- 2
- 1000127
corpName: Guristas
hullPercentage: 100.0
shieldPercentage: 94.88716147275748
solarsystemID: 1
structureID: &id001 12345678
structureShowInfoData:
- showinfo
- 35835
- *id001
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            self.eveLoc1.location_name
        )
        self.assertEqual(
            note["description"],
            f"Structure under Attack!\n[ S: {94.887:.2f}% A: {100:.2f}% H: {100:.2f}% ]"
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
            note["fields"][2],
            {"name": "Type", "value": self.typeName.name, "inline": True}
        )
        self.assertEqual(
            note["fields"][3],
            {
                "name": "Attacker",
                "value": (
                    f"*[Char 1]({zkillboard.character_url(1)})*"
                    f", [Guristas]({zkillboard.corporation_url(1000127)})"
                    f", **[Guristas Pirates]({zkillboard.alliance_url(3)})**"
                ),
                "inline": False
            }
        )

    def test_str_txfr(self):
        notification_type = "OwnershipTransferred"
        notificaiton_text = \
"""
charID: 1
newOwnerCorpID: 2
oldOwnerCorpID: 3
solarSystemID: 1
structureID: 12345678
structureName: D4KU-5 - ducktales
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            "Structure Transferred"
        )
        self.assertEqual(
            note["description"],
            f"Structure Transferred from {self.eveName3.name} to {self.eveName2.name}"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Structure", "value": "D4KU-5 - ducktales", "inline": True}
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
            {"name": "Originator", "value": self.eveName1.name, "inline": True}
        )


    def test_str_ankr(self):
        notification_type = "StructureAnchoring"
        notificaiton_text = \
"""
ownerCorpLinkData:
- showinfo
- 2
- 680022174
ownerCorpName: WOOO.
solarsystemID: 1
structureID: &id001 12345678
structureShowInfoData:
- showinfo
- 35825
- *id001
structureTypeID: 1
timeLeft: 8999632416
vulnerableTime: 9000000000
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            self.eveLoc1.location_name
        )
        self.assertEqual(
            note["description"],
            "Structure Anchoring!"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Corporation", "value": self.corp1.corporation_name, "inline": True}
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

    def test_str_unankr(self):
        notification_type = "StructureUnanchoring"
        notificaiton_text = \
"""
ownerCorpLinkData:
- showinfo
- 2
- 680022174
ownerCorpName: wooo.
solarsystemID: 1
structureID: &id001 12345678
structureShowInfoData:
- showinfo
- 37534
- *id001
structureTypeID: 1
timeLeft: 958011150532
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            self.eveLoc1.location_name
        )
        self.assertEqual(
            note["description"],
            "Structure Unanchoring!"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Corporation", "value": self.corp1.corporation_name, "inline": True}
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
            {"name": "Time Till Out", "value": "1 Days, 2 Hours, 36 Min", "inline": False}
        )


    def test_str_low_pow(self):
        notification_type = "StructureWentLowPower"
        notificaiton_text = \
"""
solarsystemID: 1
structureID: &id001 12345678
structureShowInfoData:
- showinfo
- 35832
- *id001
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            self.eveLoc1.location_name
        )
        self.assertEqual(
            note["description"],
            "Structure Went Low Power!"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Corporation", "value": self.corp1.corporation_name, "inline": True}
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

    def test_str_high_pow(self):
        notification_type = "StructureWentHighPower"
        notificaiton_text = \
"""
solarsystemID: 1
structureID: &id001 12345678
structureShowInfoData:
- showinfo
- 35832
- *id001
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            self.eveLoc1.location_name
        )
        self.assertEqual(
            note["description"],
            "Structure Went High Power!"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Corporation", "value": self.corp1.corporation_name, "inline": True}
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


    def test_str_dest(self):
        notification_type = "StructureDestroyed"
        notificaiton_text = \
"""
isAbandoned: false
ownerCorpLinkData:
- showinfo
- 2
- 1
ownerCorpName: wooo.
solarsystemID: 1
structureID: &id001 12345678
structureShowInfoData:
- showinfo
- 35825
- *id001
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            self.eveLoc1.location_name
        )
        self.assertEqual(
            note["description"],
            "Structure Destroyed!"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Corporation", "value": self.corp1.corporation_name, "inline": True}
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
            {"name": "Abandoned", "value": "No", "inline": True}
        )

    def test_str_no_react(self):
        notification_type = "StructureNoReagentsAlert"
        notificaiton_text = \
"""
solarsystemID: 1
structureID: &id001 12345678
structureShowInfoData:
- showinfo
- 1
- *id001
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            self.eveLoc1.location_name
        )
        self.assertEqual(
            note["description"],
            "Structure Out of Reagents!"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Corporation", "value": self.corp1.corporation_name, "inline": True}
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

    def test_str_lo_react(self):
        notification_type = "StructureLowReagentsAlert"
        notificaiton_text = \
"""
solarsystemID: 1
structureID: &id001 12345678
structureShowInfoData:
- showinfo
- 1
- *id001
structureTypeID: 1
"""

        note = self._build_notification(notification_type, notificaiton_text)

        self.assertIsNotNone(note)

        self.assertEqual(
            note["title"],
            self.eveLoc1.location_name
        )
        self.assertEqual(
            note["description"],
            "Structure is Low on Reagents!"
        )
        self.assertEqual(
            note["fields"][0],
            {"name": "Corporation", "value": self.corp1.corporation_name, "inline": True}
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
