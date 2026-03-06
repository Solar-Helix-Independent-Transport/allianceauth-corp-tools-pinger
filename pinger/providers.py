from corptools.providers import esi_openapi

from esi.clients import EsiClientProvider, esi_client_factory

try:
    from django_redis import get_redis_connection
    _client = get_redis_connection("default")
except (NotImplementedError, ModuleNotFoundError):
    from django.core.cache import caches
    default_cache = caches['default']
    _client = default_cache.get_master_client()

cache_client = _client


class LocalClient(EsiClientProvider):
    @property
    def client(self):
        if self._client is None:
            self._client = esi_client_factory(
                datasource=self._datasource,
                spec_file=self._spec_file,
                version=self._version,
                app_info_text=self._app_text,
                **self._kwargs,
            )
            # CCP fix...
            self._client.Character.get_characters_character_id_notifications.operation.swagger_spec.config[
                'validate_responses'] = False
        return self._client


esi = LocalClient()
