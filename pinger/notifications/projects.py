
from allianceauth.eveonline.evelinks import eveimageserver, evewho, zkillboard
from allianceauth.eveonline.models import EveCharacter
from corptools import models as ctm
from django.utils.html import strip_tags

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
        creator, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['creator_id'])
        app_corp, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['corporation_id'])

        title = "Corp Project Created"
        body = f"```{strip_tags(self._data['goal_name'])}```\n"

        corp_id = app_corp.eve_id
        corp_name = f"[{app_corp.name}]({zkillboard.corporation_url(corp_id)})"
        footer = {"icon_url": f"{eveimageserver.corporation_logo_url(corp_id, size=64)}",
                  "text": f"{app_corp.name}"
                  }

        fields = [{'name': 'Creator', 'value': f"[{creator}](https://evewho.com/character/{creator.eve_id}/)", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=16756480)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
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
        creator, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['creator_id'])
        if "closer_id" in self._data:
            closer, _ = ctm.EveName.objects.get_or_create_from_esi(
                self._data['closer_id'])
        else:
            closer = creator
        app_corp, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['corporation_id'])

        title = "Corp Project Closed"
        body = f"```{strip_tags(self._data['goal_name'])} Closed by {closer}```\n"

        corp_id = app_corp.eve_id
        corp_name = f"[{app_corp.name}]({zkillboard.corporation_url(corp_id)})"
        footer = {"icon_url": f"{eveimageserver.corporation_logo_url(corp_id, size=64)}",
                  "text": f"{app_corp.name}"
                  }

        fields = [{'name': 'Creator', 'value': f"[{creator}](https://evewho.com/character/{creator.eve_id}/)", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=16756480)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
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
        creator, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['creator_id'])
        app_corp, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['corporation_id'])

        title = "Corp Project Completed"
        body = f"```{strip_tags(self._data['goal_name'])}```\n"

        corp_id = app_corp.eve_id
        corp_name = f"[{app_corp.name}]({zkillboard.corporation_url(corp_id)})"
        footer = {"icon_url": f"{eveimageserver.corporation_logo_url(corp_id, size=64)}",
                  "text": f"{app_corp.name}"
                  }

        fields = [{'name': 'Creator', 'value': f"[{creator}](https://evewho.com/character/{creator.eve_id}/)", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=16756480)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
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
        creator, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['creator_id'])
        app_corp, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['corporation_id'])

        title = "Corp Project Expired"
        body = f"```{strip_tags(self._data['goal_name'])}```\n"

        corp_id = app_corp.eve_id
        corp_name = f"[{app_corp.name}]({zkillboard.corporation_url(corp_id)})"
        footer = {"icon_url": f"{eveimageserver.corporation_logo_url(corp_id, size=64)}",
                  "text": f"{app_corp.name}"
                  }

        fields = [{'name': 'Creator', 'value': f"[{creator}](https://evewho.com/character/{creator.eve_id}/)", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=16756480)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
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
        creator, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['creator_id'])
        app_corp, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['corporation_id'])

        title = "Corp Project Limit Reached"
        body = f"```{strip_tags(self._data['goal_name'])}```\n"

        corp_id = app_corp.eve_id
        corp_name = f"[{app_corp.name}]({zkillboard.corporation_url(corp_id)})"
        footer = {"icon_url": f"{eveimageserver.corporation_logo_url(corp_id, size=64)}",
                  "text": f"{app_corp.name}"
                  }

        fields = [{'name': 'Creator', 'value': f"[{creator}](https://evewho.com/character/{creator.eve_id}/)", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=16756480)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self.force_at_ping = False
