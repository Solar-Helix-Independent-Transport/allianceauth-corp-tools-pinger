import datetime
import logging

from corptools import models as ctm
from corptools.task_helpers.update_tasks import fetch_location_name
from eve_sde import models as sdem

from django.apps import apps

from allianceauth.eveonline.evelinks import (
    dotlan, eveimageserver, evewho, zkillboard,
)
from allianceauth.eveonline.models import EveCharacter

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
    if timers_enabled():
        return Timer(
            details=f"{structure} (Auto)",
            system=system,
            structure=structure_type,
            timer_type=timer_type,
            eve_time=date,
            eve_corp=corporation,
        )


def get_system_from_id(system_id):
    return sdem.SolarSystem.objects.get(id=system_id)


def get_system_name_from_id(system_id):
    return get_system_from_id(system_id).name


def get_system_url_from_id(system_id):
    system_name = get_system_from_id(system_id).name
    return f"[{system_name}]({dotlan.solar_system_url(system_name)})"


def get_region_url_from_system_id(system_id):
    region_name = get_system_from_id(system_id).constellation.region.name
    return f"[{region_name}]({dotlan.region_url(region_name)})"


def get_moon_from_id(moon_id):
    return sdem.Moon.objects.get(id=moon_id)


def get_moon_name_from_id(moon_id):
    return get_moon_from_id(moon_id).name


def get_planet_from_id(planet_id):
    return sdem.Planet.objects.get(id=planet_id)


def get_planet_name_from_id(planet_id):
    return get_planet_from_id(planet_id).name


def get_item_from_id(item_id):
    return sdem.ItemType.objects.get(id=item_id)


def get_item_name_from_id(item_id):
    return get_item_from_id(item_id).name


def footer_from_notification(notification):
    corp_id = notification.character.character.corporation_id
    corp_ticker = notification.character.character.corporation_ticker
    corp_name = notification.character.character.corporation_name
    return {
        "icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
        "text": f"{corp_name} ({corp_ticker})"
    }


def alliance_footer_from_notification(notification):
    alli_id = notification.character.character.alliance_id
    alli_ticker = notification.character.character.alliance_ticker
    alli_name = notification.character.character.alliance_name
    return {
        "icon_url": eveimageserver.alliance_logo_url(alli_id, 64),
        "text": f"{alli_name} ({alli_ticker})"
    }


def filter_from_notification(notification, system: sdem.SolarSystem = None):
    corp_id = notification.character.character.corporation_id
    alli_id = notification.character.character.alliance_id
    regn_id = None
    if system:
        regn_id = system.constellation.region.id
    return corp_id, alli_id, regn_id


def get_eve_name_by_id(eve_id):
    _en = ctm.EveName.objects.get_or_create_from_esi(eve_id)[0]
    return _en


def get_main_from_character_id(character_id):
    try:
        eve_main = EveCharacter.objects.get(
            character_id=character_id
        ).character_ownership.user.profile.main_character
        return (
            f"[{eve_main.character_name}]({evewho.character_url(eve_main.character_id)}) "
            f"[ [{eve_main.corporation_ticker}]({evewho.corporation_url(eve_main.corporation_id)}) ]"
        )
    except:
        return "Unknown"


def get_attacker_string(char_id, corp_id, alli_id=None):
    attacking_char = get_eve_name_by_id(char_id)
    attacking_corp = get_eve_name_by_id(corp_id)
    attacking_alli = None
    if alli_id:
        attacking_alli = get_eve_name_by_id(alli_id)
    return "".join([
        f"*[{attacking_char.name}]({zkillboard.character_url(attacking_char.eve_id)})*",
        f", [{attacking_corp.name}]({zkillboard.corporation_url(attacking_corp.eve_id)})",
        f", **[{attacking_alli.name}]({zkillboard.alliance_url(attacking_alli.eve_id)})**" if attacking_alli else ""
    ])


def get_timer_enum(timer_type):
    if timers_enabled():
        if timer_type == "ARMOR":
            return Timer.TimerType.ARMOR
        elif timer_type == "SHIELD":
            return Timer.TimerType.SHIELD
        elif timer_type == "HULL":
            return Timer.TimerType.HULL
    return None


def get_location_name_by_id(structure_id, character_id):
    try:
        structure_name = fetch_location_name(
            structure_id,
            "solar_system",
            character_id
        )
        if structure_name:
            return structure_name.location_name
        else:
            return "Unknown"
    except Exception as e:
        logger.error(f"PINGER: Error fetching structure name? {e}")
        return "Unknown"


def time_till_out(time_left, notification):
    _secondsRemaining = time_left / 10000000  # seconds
    _refTimeDelta = datetime.timedelta(seconds=_secondsRemaining)
    tile_till = format_timedelta(_refTimeDelta)
    ref_date_time = notification.timestamp + _refTimeDelta
    return tile_till, ref_date_time
