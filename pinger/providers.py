from esi.openapi_clients import ESIClientProvider

from pinger import __title__, __version__

try:
    from django_redis import get_redis_connection
    _client = get_redis_connection("default")
except (NotImplementedError, ModuleNotFoundError):
    from django.core.cache import caches
    default_cache = caches['default']
    _client = default_cache.get_master_client()

cache_client = _client

esi_openapi = ESIClientProvider(
    compatibility_date="2026-05-19",
    ua_appname=__title__,
    ua_url="https://github.com/Solar-Helix-Independent-Transport/allianceauth-corp-tools-pinger",
    ua_version=__version__,
    operations=["GetCharactersCharacterIdNotifications"],
)
