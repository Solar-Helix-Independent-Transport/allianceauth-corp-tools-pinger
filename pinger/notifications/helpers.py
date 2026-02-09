import datetime
import logging

from django.apps import apps

logger = logging.getLogger(__name__)


def timers_enabled():
    return apps.is_installed("allianceauth.timerboard")


if timers_enabled():
    from allianceauth.timerboard.models import Timer


def filetime_to_dt(ft):
    us = (ft - 116444736000000000) // 10
    return datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=us)


def convert_timedelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 60)
    return hours, minutes, seconds


def format_timedelta(td):
    hours, minutes, seconds = convert_timedelta(td)
    return ("%d Days, %d Hours, %d Min" % (td.days, round(hours), round(minutes)))


def time_till_to_td(ms):
    _secondsRemaining = ms / 10000000  # seconds
    return datetime.timedelta(seconds=_secondsRemaining)


def time_till_to_string(ms):
    _refTimeDelta = time_till_to_td(ms)
    return format_timedelta(_refTimeDelta)


def time_till_to_dt(ms, timestamp):
    _refTimeDelta = time_till_to_td(ms)
    return timestamp + _refTimeDelta


def create_timer(structure, structure_type, system, timer_type, date, corporation):
    # Pre process??? add anything new???
    return Timer(
        details=f"{structure} (Auto)",
        system=system,
        structure=structure_type,
        timer_type=timer_type,
        eve_time=date,
        eve_corp=corporation,
    )
