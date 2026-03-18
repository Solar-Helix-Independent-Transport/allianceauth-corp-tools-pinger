
from django.utils.html import strip_tags

from allianceauth.eveonline.evelinks import evewho

from pinger.notifications.helpers import (
    filter_from_notification, footer_from_notification, get_eve_name_by_id,
    get_main_from_character_id,
)

from .base import NotificationPing


class CorpAppAcceptMsg(NotificationPing):
    category = "hr-admin"  # Structure Alerts

    """
    CorpAppAcceptMsg

    applicationText: ''
    charID: 95954535
    corpID: 680022174
    """

    def build_ping(self):
        title = "Corp Application Accepted"
        app_char = get_eve_name_by_id(self._data['charID'])
        app_corp = get_eve_name_by_id(self._data['corpID'])
        eve_main = get_main_from_character_id(self._data['charID'])
        footer = footer_from_notification(self._notification)

        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        fields = [
            {
                'name': 'Character',
                'value': f"[{app_char.name}]({evewho.character_url(self._data['charID'])})",
                'inline': True
            },
            {
                'name': 'Corporation',
                'value': app_corp.name,
                'inline': True
            },
            {
                'name': 'Main Character',
                'value': eve_main,
                'inline': True
            }
        ]

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=3066993
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification
        )
        self.force_at_ping = False


class CorpAppInvitedMsg(NotificationPing):
    category = "hr-admin"  # Structure Alerts

    """
    CorpAppInvitedMsg

    applicationText: ''
    charID: 95954535
    corpID: 680022174
    invokingCharID: 95946886
    """

    def build_ping(self):
        title = "Corp Invite Sent"
        app_char = get_eve_name_by_id(self._data['charID'])
        app_corp = get_eve_name_by_id(self._data['corpID'])
        invoked_by = get_eve_name_by_id(self._data['invokingCharID'])
        eve_main = get_main_from_character_id(self._data['charID'])
        footer = footer_from_notification(self._notification)

        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        fields = [
            {
                'name': 'Character',
                'value': f"[{app_char.name}]({evewho.character_url(app_char.eve_id)})",
                'inline': True
            },
            {
                'name': 'Invoking Character',
                'value': invoked_by.name,
                'inline': True
             },
            {
                'name': 'Corporation',
                'value': app_corp.name,
                'inline': True
            },
            {
                'name': 'Main Character',
                'value': eve_main,
                'inline': True
            }
        ]

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=3066993
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification
        )
        self.force_at_ping = False


class CorpAppNewMsg(NotificationPing):
    category = "hr-admin"  # Structure Alerts

    """
    CorpAppNewMsg

    applicationText: ''
    charID: 95954535
    corpID: 680022174
    """

    def build_ping(self):
        title = "New Corp Application"
        app_char = get_eve_name_by_id(self._data['charID'])
        app_corp = get_eve_name_by_id(self._data['corpID'])
        eve_main = get_main_from_character_id(self._data['charID'])
        footer = footer_from_notification(self._notification)

        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        fields = [
            {
                'name': 'Character',
                'value': f"[{app_char.name}]({evewho.character_url(app_char.eve_id)})",
                'inline': True},
            {
                'name': 'Corporation',
                'value': app_corp.name,
                'inline': True
            },
            {
                'name': 'Main Character',
                'value': eve_main,
                'inline': True
            }
        ]

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=1752220
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification
        )
        self.force_at_ping = False


class CorpAppRejectMsg(NotificationPing):
    category = "hr-admin"  # Structure Alerts

    """
    CorpAppRejectMsg

    applicationText: ''
    charID: 95954535
    corpID: 680022174
    """

    def build_ping(self):
        title = "Corp Application Rejected"
        app_char = get_eve_name_by_id(self._data['charID'])
        app_corp = get_eve_name_by_id(self._data['corpID'])
        eve_main = get_main_from_character_id(self._data['charID'])
        footer = footer_from_notification(self._notification)

        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        fields = [
            {
                'name': 'Character',
                'value': f"[{app_char.name}]({evewho.character_url(app_char.eve_id)})",
                'inline': True
            },
            {
                'name': 'Corporation',
                'value': app_corp.name,
                'inline': True
            },
            {
                'name': 'Main Character',
                'value': eve_main,
                'inline': True
            }
        ]

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=15158332
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification
        )
        self.force_at_ping = False


"""
CharLeftCorpMsg

charID: 2112779955
corpID: 98577836
"""
