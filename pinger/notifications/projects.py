
from corptools import models as ctm

from django.utils.html import strip_tags

from allianceauth.eveonline.evelinks import eveimageserver, evewho, zkillboard
from allianceauth.eveonline.models import EveCharacter

from pinger.notifications.helpers import (
    filter_from_notification, footer_from_notification, get_eve_name_by_id,
)

from .base import NotificationPing


class CorporationGoalCreated(NotificationPing):
    category = "corp-projects"  # Corporation Projects

    """
    CorporationGoalCreated

    corporation_id: 98707616
    creator_id: 2115640197
    goal_id: 245377162334488937895806423904722129957
    goal_name: Ice Ice Ice!
    """

    def build_ping(self):
        creator = get_eve_name_by_id(self._data['creator_id'])
        app_corp = get_eve_name_by_id(self._data['corporation_id'])
        footer = footer_from_notification(self._notification)

        title = "Corp Project Created"
        body = f"```{strip_tags(self._data['goal_name'])}```\n"

        fields = [
            {
                'name': 'Creator',
                'value': f"[{creator.name}]({evewho.character_url(self._data['creator_id'])})",
                'inline': True
            },
            {
                'name': 'Corporation',
                'value': app_corp.name,
                'inline': True
            }
        ]

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=16756480
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
        )
        self.force_at_ping = False


class CorporationGoalClosed(NotificationPing):
    category = "corp-projects"  # Corporation Projects

    """
    CorporationGoalClosed

    closer_id: 1752243149
    corporation_id: 98701936
    creator_id: 1708680704
    goal_id: 339451813142555916388672576952401560776
    goal_name: Corp project - Ship Food.
    """

    def build_ping(self):
        creator = get_eve_name_by_id(self._data['creator_id'])
        app_corp = get_eve_name_by_id(self._data['corporation_id'])
        footer = footer_from_notification(self._notification)

        if "closer_id" in self._data:
            closer = get_eve_name_by_id(self._data['closer_id'])
        else:
            closer = creator

        title = "Corp Project Closed"
        body = f"```{strip_tags(self._data['goal_name'])}```\nClosed by: {closer.name}"

        fields = [
            {
                'name': 'Creator',
                'value': f"[{creator.name}]({evewho.character_url(self._data['creator_id'])})",
                'inline': True
            },
            {
                'name': 'Corporation',
                'value': app_corp.name,
                'inline': True
            }
        ]

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=16756480
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
        )
        self.force_at_ping = False


class CorporationGoalCompleted(NotificationPing):
    category = "corp-projects"  # Corporation Projects

    """
    CorporationGoalCompleted

    corporation_id: 98707616
    creator_id: 2115640197
    goal_id: 245377162334488937895806423904722129957
    goal_name: Ice Ice Ice!
    """

    def build_ping(self):
        creator = get_eve_name_by_id(self._data['creator_id'])
        app_corp = get_eve_name_by_id(self._data['corporation_id'])
        footer = footer_from_notification(self._notification)

        title = "Corp Project Completed"
        body = f"```{strip_tags(self._data['goal_name'])}```\n"

        fields = [
            {
                'name': 'Creator',
                'value': f"[{creator.name}]({evewho.character_url(self._data['creator_id'])})",
                'inline': True
            },
            {
                'name': 'Corporation',
                'value': app_corp.name,
                'inline': True
            }
        ]

        self.package_ping(
            title,
            body,
            self._notification.timestamp,
            fields=fields,
            footer=footer,
            colour=16756480
        )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
        )
        self.force_at_ping = False


class CorporationGoalExpired(NotificationPing):
    category = "corp-projects"  # Corporation Projects

    """
    CorporationGoalExpired

    corporation_id: 98707616
    creator_id: 2115640197
    goal_id: 245377162334488937895806423904722129957
    goal_name: Ice Ice Ice!
    """

    def build_ping(self):
        creator = get_eve_name_by_id(self._data['creator_id'])
        app_corp = get_eve_name_by_id(self._data['corporation_id'])
        footer = footer_from_notification(self._notification)

        title = "Corp Project Expired"
        body = f"```{strip_tags(self._data['goal_name'])}```\n"


        fields = [
            {
                'name': 'Creator',
                'value': f"[{creator.name}]({evewho.character_url(self._data['creator_id'])})",
                'inline': True
            },
            {
                'name': 'Corporation',
                'value': app_corp.name,
                'inline': True
            }
        ]

        self.package_ping(
            title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=16756480
                          )

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
        )
        self.force_at_ping = False


class CorporationGoalLimitReached(NotificationPing):
    category = "corp-projects"  # Corporation Projects

    """
    CorporationGoalLimitReached

    corporation_id: 98707616
    creator_id: 2115640197
    goal_id: 245377162334488937895806423904722129957
    goal_name: Ice Ice Ice!
    """

    def build_ping(self):
        creator = get_eve_name_by_id(self._data['creator_id'])
        app_corp = get_eve_name_by_id(self._data['corporation_id'])
        footer = footer_from_notification(self._notification)

        title = "Corp Project Limit Reached"
        body = f"```{strip_tags(self._data['goal_name'])}```\n"

        fields = [
            {
                'name': 'Creator',
                'value': f"[{creator.name}]({evewho.character_url(self._data['creator_id'])})",
                'inline': True
            },
            {
                'name': 'Corporation',
                'value': app_corp.name,
                'inline': True
            }
        ]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=16756480)

        self._corp, self._alli, self._region = filter_from_notification(
            self._notification,
        )
        self.force_at_ping = False
