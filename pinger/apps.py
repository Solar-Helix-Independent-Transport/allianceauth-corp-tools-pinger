from django.apps import AppConfig
from . import __version__


class PingerConfig(AppConfig):
    name = 'pinger'
    label = 'pinger'

    verbose_name = f"Pinger v{__version__}"
