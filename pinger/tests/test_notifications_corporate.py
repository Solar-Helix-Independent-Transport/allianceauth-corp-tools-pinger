
from . import PingerTests


def check_notes(test, note, test_description=True):
    test.assertIsNotNone(note)

    if test_description:
        test.assertEqual(
            note["description"],
            "```This is a TEST!```\n"
        )
    test.assertEqual(
        note["fields"][0],
        {"name": "Character", "value": test.eveName1linkewho, "inline": True}
    )
    test.assertEqual(
        note["fields"][1],
        {"name": "Corporation", "value": test.eveName2CorporationLinkZkillboard, "inline": True}
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
            "New Corp Application"
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
            "Corp Application Accepted"
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
            "Corp Invite Sent"
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
            "Corp Application Rejected"
        )

    def test_corp_withd_app(self):
        notification_type = "CharAppWithdrawMsg"
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
            "Corp Application Withdrawn"
        )

    def test_corp_accepted_app(self):
        notification_type = "CharAppAcceptMsg"
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
            "Member Joined Corp"
        )

    def test_corp_member_left(self):
        notification_type = "CharLeftCorpMsg"
        notificaiton_text = \
"""
charID: 1
corpID: 2
"""

        note = self._build_notification(notification_type, notificaiton_text)

        check_notes(self, note, False)

        self.assertEqual(
            note["title"],
            "Character Left Corporation"
        )
