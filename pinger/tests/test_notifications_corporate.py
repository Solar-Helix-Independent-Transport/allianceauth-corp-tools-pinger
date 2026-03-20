
from . import PingerTests


def check_notes(test, note):
    test.assertIsNotNone(note)

    test.assertEqual(
        note["description"],
        f"```This is a TEST!```\n"
    )
    test.assertEqual(
        note["fields"][0],
        {"name": "Character", "value": test.eveName1linkewho, "inline": True}
    )
    test.assertEqual(
        note["fields"][1],
        {"name": "Corporation", "value": test.eveName2.name, "inline": True}
    )
    test.assertEqual(
        note["fields"][2],
        {"name": "Main Character", "value": test.ca1text, "inline": True}
    )

class TestCorporation(PingerTests):

    def test_corp_new_app(self):
        notification_type = "CorpAppNewMsg"
        notificaiton_text = \
"""
applicationText: 'This is a TEST!'
charID: 1
corpID: 2
"""

        note = self._build_notification(notification_type, notificaiton_text)

        check_notes(self, note)

        self.assertEqual(
            note["title"],
            f"New Corp Application"
        )

    def test_corp_acc_app(self):
        notification_type = "CorpAppAcceptMsg"
        notificaiton_text = \
"""
applicationText: 'This is a TEST!'
charID: 1
corpID: 2
"""

        note = self._build_notification(notification_type, notificaiton_text)

        check_notes(self, note)

        self.assertEqual(
            note["title"],
            f"Corp Application Accepted"
        )

    def test_corp_inv_app(self):
        notification_type = "CorpAppInvitedMsg"
        notificaiton_text = \
"""
applicationText: 'This is a TEST!'
charID: 1
corpID: 2
invokingCharID: 3
"""

        note = self._build_notification(notification_type, notificaiton_text)

        check_notes(self, note)

        self.assertEqual(
            note["title"],
            f"Corp Invite Sent"
        )

    def test_corp_new_app(self):
        notification_type = "CorpAppNewMsg"
        notificaiton_text = \
"""
applicationText: 'This is a TEST!'
charID: 1
corpID: 2
"""

        note = self._build_notification(notification_type, notificaiton_text)

        check_notes(self, note)

        self.assertEqual(
            note["title"],
            f"New Corp Application"
        )

    def test_corp_rej_app(self):
        notification_type = "CorpAppRejectMsg"
        notificaiton_text = \
"""
applicationText: 'This is a TEST!'
charID: 1
corpID: 2
"""

        note = self._build_notification(notification_type, notificaiton_text)

        check_notes(self, note)

        self.assertEqual(
            note["title"],
            f"Corp Application Rejected"
        )
