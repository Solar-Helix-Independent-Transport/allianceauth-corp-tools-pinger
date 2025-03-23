
from corptools import models as ctm

from django.utils.html import strip_tags

from allianceauth.eveonline.evelinks import eveimageserver, evewho, zkillboard
from allianceauth.eveonline.models import EveCharacter

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
        app_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])
        app_corp, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['corpID'])
        try:
            eve_main = EveCharacter.objects.get(
                character_id=self._data['charID']
            ).character_ownership.user.profile.main_character
            eve_main = f"[{eve_main.character_name}]({evewho.character_url(eve_main.character_id)}) [ [{eve_main.corporation_ticker}]({evewho.corporation_url(eve_main.corporation_id)}) ]"
        except:
            eve_main = "Unknown"

        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        corp_id = app_corp.eve_id
        corp_name = f"[{app_corp.name}]({zkillboard.corporation_url(corp_id)})"
        footer = {"icon_url": f"{eveimageserver.corporation_logo_url(corp_id, size=64)}",
                  "text": f"{app_corp.name}"
                  }

        fields = [{'name': 'Character', 'value': f"[{app_char}]({evewho.character_url(app_char.eve_id)})", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'Main Character', 'value': eve_main, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=3066993)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
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
        app_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])
        invoked_by, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['invokingCharID'])
        try:
            eve_main = EveCharacter.objects.get(
                character_id=self._data['charID']).character_ownership.user.profile.main_character
            eve_main = f"[{eve_main.character_name}]({evewho.character_url(eve_main.character_id)}) [ [{eve_main.corporation_ticker}]({evewho.corporation_url(eve_main.corporation_id)}) ]"
        except:
            eve_main = "Unknown"

        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Character', 'value': f"[{app_char}]({evewho.character_url(app_char.eve_id)})", 'inline': True},
                  {'name': 'Invoking Character',
                      'value': invoked_by.name, 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'Main Character', 'value': eve_main, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=3066993)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
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
        app_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])
        try:
            eve_main = EveCharacter.objects.get(
                character_id=self._data['charID']).character_ownership.user.profile.main_character
            eve_main = f"[{eve_main.character_name}]({evewho.character_url(eve_main.character_id)}) [ [{eve_main.corporation_ticker}]({evewho.corporation_url(eve_main.corporation_id)}) ]"
        except:
            eve_main = "Unknown"

        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Character', 'value': f"[{app_char}]({evewho.character_url(app_char.eve_id)})", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'Main Character', 'value': eve_main, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=1752220)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
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
        app_char, _ = ctm.EveName.objects.get_or_create_from_esi(
            self._data['charID'])
        try:
            eve_main = EveCharacter.objects.get(
                character_id=self._data['charID']).character_ownership.user.profile.main_character
            eve_main = f"[{eve_main.character_name}]({evewho.character_url(eve_main.character_id)}) [ [{eve_main.corporation_ticker}]({evewho.corporation_url(eve_main.corporation_id)}) ]"
        except:
            eve_main = "Unknown"
        body = f"```{strip_tags(self._data['applicationText'])}```\n"

        corp_id = self._notification.character.character.corporation_id
        corp_ticker = self._notification.character.character.corporation_ticker
        corp_name = "[%s](%s)" % \
            (self._notification.character.character.corporation_name,
             zkillboard.corporation_url(corp_id))
        footer = {"icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
                  "text": "%s (%s)" % (self._notification.character.character.corporation_name, corp_ticker)}

        fields = [{'name': 'Character', 'value': f"[{app_char}]({evewho.character_url(app_char.eve_id)})", 'inline': True},
                  {'name': 'Corporation', 'value': corp_name, 'inline': True},
                  {'name': 'Main Character', 'value': eve_main, 'inline': True}]

        self.package_ping(title,
                          body,
                          self._notification.timestamp,
                          fields=fields,
                          footer=footer,
                          colour=15158332)

        self._corp = self._notification.character.character.corporation_id
        self._alli = self._notification.character.character.alliance_id
        self.force_at_ping = False


"""
CharLeftCorpMsg

charID: 2112779955
corpID: 98577836
"""
