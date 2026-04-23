import datetime
import json
import logging

import yaml

from ..models import Notification

logger = logging.getLogger(__name__)


def get_available_types():
    classes = NotificationPing.__subclasses__()

    output = {}

    for c in classes:
        output[c.__name__] = c

    return output


class NotificationPing:
    # Settings
    force_at_ping = False
    category = "None"
    timer = False

    # Data
    _notification : Notification
    _data = {}
    _ping = ""

    _corp = None
    _alli = None
    _region = None

    def __init__(self, notification: Notification):
        self._notification = notification
        self._data = self.parse_notification()
        self.build_ping()

    def parse_notification(self):
        return yaml.load(
            self._notification.notification_text,
            Loader=yaml.UnsafeLoader
        )

    def build_ping(self):
        raise NotImplementedError(
            "Create the Notification Map class to process this ping!")

    def package_ping(
            self,
            title,
            body,
            timestamp: datetime.datetime,
            fields=None,
            footer=None,
            img_url=None,
            colour=16756480):
        custom_data = {
            'color': colour,
            'title': title,
            'description': body,
            'timestamp': timestamp.replace(tzinfo=None).isoformat(),
        }

        if fields:
            custom_data['fields'] = fields

        if img_url:
            custom_data['image'] = {'url': img_url}

        if footer:
            custom_data['footer'] = footer

        self._ping = json.dumps(custom_data)

    def get_filters(self):
        return (self._corp, self._alli, self._region)
