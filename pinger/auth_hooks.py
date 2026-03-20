from allianceauth import hooks
from allianceauth.services.hooks import UrlHook

"""from . import urls

@hooks.register('url_hook')
def register_url():
    return UrlHook(urls, 'srpmod', r'^srpmod/')
"""


@hooks.register('discord_cogs_hook')
def register_cogs():
    return ["pinger.cogs"]
