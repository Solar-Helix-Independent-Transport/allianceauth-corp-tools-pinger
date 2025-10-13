import datetime
import hashlib
import json
import logging
import time
from functools import wraps
from http.cookiejar import http2time

import requests
from bravado.exception import HTTPError
from celery import shared_task
from corptools.models import (
    CharacterAudit, CorpAsset, CorporationAudit, Structure,
)
from corptools.task_helpers import sanitize_notification_type
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max, Q, Sum
from django.utils import timezone

from allianceauth.eveonline.evelinks import eveimageserver
from allianceauth.services.tasks import QueueOnce
from esi.models import Token

from pinger.app_settings import CT_PINGER_VALID_STATES
from pinger.models import DiscordWebhook, FuelPingRecord, Ping, PingerConfig

from . import notifications
from .notifications.base import get_available_types
from .providers import cache_client, esi

TZ_STRING = "%Y-%m-%dT%H:%M:%SZ"

CACHE_TIME_SECONDS = 10 * 60

TASK_PRIO = 3

LOOK_BACK_HOURS = 6


logger = logging.getLogger(__name__)

alliances = []
corporations = []
min_time = 60
last_update = 0


def get_settings():
    pc = PingerConfig.objects.get(pk=1)
    alliances = pc.AllianceLimiter.all().values_list('alliance_id')
    corporations = pc.CorporationLimiter.all().values_list('corporation_id')
    min_time = pc.min_time_between_updates

    return alliances, corporations, min_time


def set_error_flag(timeout):
    tout = timezone.now() + datetime.timedelta(seconds=timeout)
    cache.set("esi_error_timeout", tout, timeout=timeout + 1)


def get_error_flag():
    return cache.get("esi_error_timeout", default=timezone.now())


def clear_error_flag():
    cache.delete("esi_error_timeout")


def esi_error_retry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        _ret = None

        if get_error_flag() >= timezone.now():
            logger.warning("Hit ESI error limit! will retry tasks!")
            args[0].retry(countdown=61)
        else:
            clear_error_flag()
        try:
            _ret = func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, (HTTPError)):
                code = e.status_code
                if code == 420:
                    logger.warning(f"Hit ESI error limit! Pausing Tasks! {e}")
                    set_error_flag(60)
                    args[0].retry(countdown=61)
            elif isinstance(e, (OSError)):
                logger.warning(f"Hit ESI error limit! Pausing Tasks! {e}")
            raise e
        return _ret
    return wrapper


def _get_head_id(char_id):
    _head = Notification.objects.filter(
        character__character__character_id=char_id,
    ).aggregate(
        Max('pk')
    )
    if _head.get("pk__max", 0) is None:
        return 0
    else:
        return _head.get("pk__max", 0)


def _build_char_cache_etag_id(char_id):
    return f"ct-pingger-char-etag-{char_id}"


def _get_last_cache_etag(char_id):
    return cache.get(_build_char_cache_etag_id(char_id), "")


def _set_last_cache_etag(char_id, etag):
    return cache.set(_build_char_cache_etag_id(char_id), etag)


def _build_char_cache_id(char_id):
    return f"ct-pingger-char-{char_id}"


def _get_last_cache_expire(char_id):
    return cache.get(_build_char_cache_id(char_id), 0)


def _set_last_cache_expire(char_id, expires):
    return cache.set(_build_char_cache_id(char_id), expires)


def _build_corp_cache_id(corp_id):
    return f"ct-pingger-corp-{corp_id}"


def _get_cache_data_for_corp(corp_id):
    cached_data = cache.get(_build_corp_cache_id(corp_id), False)
    if cached_data:
        cached_data = json.loads(cached_data)
        last_char = cached_data.get("last_char")
        char_array = cached_data.get("char_array")
        unixtime = time.mktime(timezone.now().timetuple())
        next_update = cached_data.get("next_update", 0)
        next_update = next_update - unixtime
        return (last_char, char_array, next_update)
    else:
        return (0, [], -661)


def _set_cache_data_for_corp(corp_id, last_char, char_array, next_update):
    data = {
        "latest_notification_id": 0,
        "latest_notification_character_id": 0,
        "last_char": last_char,
        "char_array": char_array,
        "next_update": time.mktime(timezone.now().timetuple()) + next_update
    }
    cache.set(_build_corp_cache_id(corp_id),
              json.dumps(data), CACHE_TIME_SECONDS + 60)


@shared_task
def bootstrap_notification_tasks():
    # build model for all known corps and fire off updates to get the ball rolling.
    # run at 10m intervals to keep sync, otherwise run at 10m/people in corp with roles intervals

    # get list of all active corp tasks from cache
    allis, corps, _ = get_settings()
    # get all new corps not in cache
    all_member_corps_in_audit = CharacterAudit.objects.filter(
        character__character_ownership__user__profile__state__name__in=CT_PINGER_VALID_STATES,
        characterroles__station_manager=True,
        active=True
    )

    # TODO add app.model setting to filter for who to ping for.
    filters = []
    if len(allis) > 0:
        filters.append(Q(character__alliance_id__in=allis))

    if len(corps) > 0:
        filters.append(Q(character__corporation_id__in=corps))

    if len(filters) > 0:
        query = filters.pop()
        for q in filters:
            query |= q
        all_member_corps_in_audit = all_member_corps_in_audit.filter(query)

    corps = list(set(all_member_corps_in_audit.values_list(
        "character__corporation_id", flat=True)))

    logger.warning(f"PINGER: Bootstrap found {len(corps)} to check.")
    # fire off tasks for each corp with active models
    for cid in corps:
        _, _, next_update = _get_cache_data_for_corp(cid)
        if next_update < -60:  # 1 min since last update should have fired.
            logger.warning(f"PINGER: {cid} Out of Sync, Starting back up!")
            corporation_notification_update.apply_async(
                args=[cid], priority=TASK_PRIO + 1
            )

    all_corps_in_audit = CorporationAudit.objects.all()
    for c in all_corps_in_audit:
        corporation_fuel_check.apply_async(
            args=[c.corporation.corporation_id], priority=TASK_PRIO + 1)
        corporation_gas_check.apply_async(
            args=[c.corporation.corporation_id], priority=TASK_PRIO + 1)


@shared_task()
def queue_corporation_notification_update(corporation_id, wait_time):
    corporation_notification_update.apply_async(
        args=[corporation_id], priority=(TASK_PRIO + 1), countdown=wait_time)


def fuel_ping_builder(structure, days, message):
    pingObj = FuelPingRecord.objects.filter(
        last_message=message, last_ping_lo_level__isnull=True, structure=structure, date_empty=structure.fuel_expires).exists()
    if not pingObj:
        # logger.info("new ping: %s %s"% (_structure,_pingText))

        n = FuelPingRecord(
            structure=structure,
            last_ping_time=days,
            last_message=message,
            date_empty=structure.fuel_expires)
        n.save()
        old = FuelPingRecord.objects.filter(
            last_ping_lo_level__isnull=True, structure=structure).exclude(pk=n.pk)
        if old.exists():
            # logger.debug("new ping %s" % str(structure.name))
            old.delete()
        n.ping_task_ob(message)
        return True
    else:
        # logger.info("already pinged: %s %s"% (_structure,_pingText))
        return False


@shared_task(bind=True, base=QueueOnce, max_retries=None)
def corporation_fuel_check(self, corporation_id):
    logger.info(
        f"PINGER: FUEL Sending Starting Fuel Checks for {corporation_id}")
    fuel_structures = Structure.objects.filter(
        corporation__corporation__corporation_id=corporation_id)

    for struct in fuel_structures:
        daysLeft = 0
        if not struct.fuel_expires:
            continue  # use the eve notifications

        daysLeft = (struct.fuel_expires - datetime.datetime.now(timezone.utc)).days

        if daysLeft < 15:
            if 0 <= daysLeft < 2:
                fuel_ping_builder(struct, daysLeft, "Critical Fuel! :ambulance:")
            elif 2 <= daysLeft < 3:
                fuel_ping_builder(struct, daysLeft, "Critical Fuel! :ambulance: :eyes:")
            elif 3 <= daysLeft < 8:
                fuel_ping_builder(struct, daysLeft, "Low Fuel")
            elif 8 <= daysLeft:
                fuel_ping_builder(struct, daysLeft, "Low Fuel")
        else:
            old = FuelPingRecord.objects.filter(
                last_ping_lo_level__isnull=True, structure=struct)
            if old.exists():
                old.delete()


def get_lo_key(corp_id):
    return f"LO_LEVEL_HASH_KEY_{corp_id}"


def get_lo_ping_state(corp_id):
    return cache.get(get_lo_key(corp_id), "")


def set_lo_ping_state(corp_id, hash):
    return cache.set(get_lo_key(corp_id), hash, timeout=60 * 60 * 24 * 7)


def sort_structure_list(struct_list):
    return [x.name for x in sorted(struct_list, key=lambda x: x.name)]


@shared_task(bind=True, base=QueueOnce, max_retries=None)
def corporation_lo_check(self, corporation_id):
    logger.info(f"PINGER: Starting LO Checks {corporation_id}")
    fuel_structures = Structure.objects.filter(
        type_name_id=35841,
        corporation__corporation__corporation_id=corporation_id
    ).order_by("name")

    low = []
    crit = []
    unknown = []
    corp = None
    for struct in fuel_structures:
        if corp is None:
            corp = struct.corporation.corporation

        th_low = 1500000
        th_crit = 25000

        try:
            th_low = struct.lo_th.low
            th_crit = struct.lo_th.critical
        except ObjectDoesNotExist:
            pass

        loLeft = struct.ozone_level
        if loLeft is False:
            unknown.append(struct)
            continue

        if loLeft < th_low:
            if 1 <= loLeft < th_crit:
                crit.append(struct)
                continue
            elif th_crit <= loLeft:
                low.append(struct)
                continue
        else:
            pass

    if len(crit) or len(low) or len(unknown):
        # build it!
        sorted_arrays = (
            sort_structure_list(crit),
            sort_structure_list(low),
            sort_structure_list(unknown)
        )

        sorted_hash = hashlib.md5(json.dumps(
            sorted_arrays).encode()).hexdigest()

        if get_lo_ping_state(corporation_id) == sorted_hash:
            set_lo_ping_state(corporation_id, sorted_hash)
            logger.info(
                f"LO HASH Match for {get_gas_ping_state(corporation_id)} - "
                f"{json.dumps(sorted_arrays, indent=2)}"
            )

            return
        else:
            # send pings
            embed = {
                'color': 15158332,
                'title': "Liquid Ozone State",
                'description': ""
            }

            footer = {
                "icon_url": eveimageserver.corporation_logo_url(corporation_id, 64),
                "text": f"{corp.corporation_name} ({corp.corporation_ticker})"
            }

            embed["footer"] = footer

            gap = "               "
            desc = []
            if len(crit):
                desc.append("\n**Critical Ozone Levels:**")
                crit_block = [
                    f"{s.ozone_level:,}{gap[len(f'{s.ozone_level:,}'):15]}{s.name}" for s in crit
                ]
                crit_block = "\n".join(crit_block)
                desc.append(f'```Liquid Ozone   Structure\n{crit_block}```')
            if len(low):
                desc.append("\n**Low Ozone Levels:**")
                low_block = [
                    f"{s.ozone_level:,}{gap[len(f'{s.ozone_level:,}'):15]}{s.name}" for s in low
                ]
                low_block = "\n".join(low_block)
                desc.append(f'```Liquid Ozone   Structure\n{low_block}```')
            if len(unknown):
                desc.append("\n**Unknown Ozone Levels:**")
                unknown_block = [f" -             {s.name}" for s in low]
                unknown_block = "\n".join[unknown_block]
                desc.append(f'```~~Liquid Ozone~~   Structure\n{low_block}```')

            embed["description"] = "\n".join(desc)

            set_lo_ping_state(corporation_id, sorted_hash)

            webhooks = DiscordWebhook.objects.filter(
                lo_pings=True
            ).prefetch_related(
                "alliance_filter",
                "corporation_filter",
                "region_filter"
            )

            logger.info(f"PINGER: FUEL Webhooks {webhooks.count()}")

            for hook in webhooks:
                corporations = hook.corporation_filter.all(
                ).values_list("corporation_id", flat=True)

                corp_filter = corporation_id

                if corp_filter is not None and len(corporations) > 0:
                    if corp_filter not in corporations:
                        logger.info(
                            f"PINGER: FUEL  Skipped {self.structure.name} Corp {corp_filter} not in {corporations}"
                        )
                        continue

                alert = False
                p = Ping.objects.create(
                    notification_id=-1,
                    hook=hook,
                    body=json.dumps(embed),
                    time=timezone.now(),
                    alerting=alert
                )
                p.send_ping()

                return embed


def get_gas_key(corp_id):
    return f"GAS_LEVEL_HASH_KEY_{corp_id}"


def get_gas_ping_state(corp_id):
    return cache.get(get_gas_key(corp_id), "")


def set_gas_ping_state(corp_id, hash):
    return cache.set(get_gas_key(corp_id), hash, timeout=60 * 60 * 24 * 7)


@shared_task(bind=True, base=QueueOnce, max_retries=None)
def corporation_gas_check(self, corporation_id):
    logger.info(f"PINGER: Starting Gas Checks {corporation_id}")

    fuel_structures = Structure.objects.filter(
        type_name_id=81826,
        corporation__corporation__corporation_id=corporation_id
    ).order_by("name")

    low = []
    crit = []
    unknown = []
    levels = {}
    corp = None
    for struct in fuel_structures:
        if corp is None:
            corp = struct.corporation.corporation

        th_low = 18480
        th_crit = 7920

        # try:
        #     th_low = struct.gas_th.low
        #     th_crit = struct.gas_th.critical
        # except ObjectDoesNotExist:
        #     pass

        loLeft = CorpAsset.objects.filter(
            location_id=struct.structure_id,
            type_id=81143
        ).aggregate(
            total=Sum("quantity")
        )["total"]

        if loLeft is None:
            unknown.append(struct)
            continue

        if loLeft < th_low:
            if 1 <= loLeft < th_crit:
                crit.append(struct)
                levels[struct.structure_id] = loLeft
                continue
            elif th_crit <= loLeft:
                low.append(struct)
                levels[struct.structure_id] = loLeft
                continue
        else:
            pass

    if len(crit) or len(low) or len(unknown):
        # build it!
        sorted_arrays = (
            sort_structure_list(crit),
            sort_structure_list(low),
            sort_structure_list(unknown)
        )

        sorted_hash = hashlib.md5(
            json.dumps(
                sorted_arrays
            ).encode()
        ).hexdigest()

        if get_gas_ping_state(corporation_id) == sorted_hash:
            set_gas_ping_state(corporation_id, sorted_hash)
            logger.info(
                f"GAS HASH Match for {get_gas_ping_state(corporation_id)} - "
                f"{json.dumps(sorted_arrays, indent=2)}"
            )
            return
        else:
            # send pings
            embed = {
                'color': 15158332,
                'title': "Magmatic Gas State",
                'description': ""
            }

            footer = {
                "icon_url": eveimageserver.corporation_logo_url(corporation_id, 64),
                "text": f"{corp.corporation_name} ({corp.corporation_ticker})"
            }

            embed["footer"] = footer

            gap = "               "
            desc = []
            if len(crit):
                desc.append("\n**Critical Gas Levels:**")
                crit_block = [
                    f"{levels[s.structure_id]:,}{gap[len(f'{levels[s.structure_id]:,}'):15]}{s.name}" for s in crit
                ]
                crit_block = "\n".join(crit_block)
                desc.append(f'```Magmatic Gas   Structure\n{crit_block}```')
            if len(low):
                desc.append("\n**Low Gas Levels:**")
                low_block = [
                    f"{levels[s.structure_id]:,}{gap[len(f'{levels[s.structure_id]:,}'):15]}{s.name}" for s in low
                ]
                low_block = "\n".join(low_block)
                desc.append(f'```Magmatic Gas   Structure\n{low_block}```')
            if len(unknown):
                desc.append("\n**Unknown Gas Levels:**")
                unknown_block = [f" -             {s.name}" for s in unknown]
                unknown_block = "\n".join(unknown_block)
                desc.append(
                    f'```~~Magmatic Gas~~   Structure\n{unknown_block}```')

            embed["description"] = "\n".join(desc)

            set_gas_ping_state(corporation_id, sorted_hash)

            webhooks = DiscordWebhook.objects.filter(
                gas_pings=True
            ).prefetch_related(
                "alliance_filter",
                "corporation_filter",
                "region_filter"
            )
            logger.info(f"PINGER: FUEL Webhooks {webhooks.count()}")

            for hook in webhooks:
                corporations = hook.corporation_filter.all(
                ).values_list("corporation_id", flat=True)

                corp_filter = corporation_id

                if corp_filter is not None and len(corporations) > 0:
                    if corp_filter not in corporations:
                        logger.info(
                            f"PINGER: FUEL  Skipped Corp_ID:{corp_filter} not in {corporations}"
                        )
                        continue

                alert = False
                p = Ping.objects.create(
                    notification_id=-2,
                    hook=hook,
                    body=json.dumps(embed),
                    time=timezone.now(),
                    alerting=alert
                )
                p.send_ping()

                return embed


@shared_task(bind=True, base=QueueOnce, max_retries=None)
@esi_error_retry
def corporation_notification_update(self, corporation_id):
    # get oldest token and update notifications chained with a notification check
    data = _get_cache_data_for_corp(corporation_id)
    CUTTOFF = timezone.now() - datetime.timedelta(hours=LOOK_BACK_HOURS)

    if data:
        last_character = data[0]

        logger.info(
            f"PINGER: {corporation_id} Last Update was with {last_character}")

        all_chars_in_corp = set(CharacterAudit.objects.filter(characterroles__station_manager=True,
                                                              character__corporation_id=corporation_id,
                                                              active=True).values_list("character__character_id", flat=True))

        all_hr_chars = list(set(CharacterAudit.objects.filter(characterroles__personnel_manager=True,
                                                              character__corporation_id=corporation_id,
                                                              active=True).values_list("character__character_id", flat=True)))

        # todo make this nicer...
        if len(all_hr_chars) > 0:
            hr_presented = False
            for i in all_hr_chars:
                if i in all_chars_in_corp:
                    hr_presented = True
                    logger.info(
                        f"PINGER: HR {corporation_id} We have HR covered")
                    break

            if not hr_presented:
                logger.info(
                    f"PINGER: HR {corporation_id} Adding a HR character")

                all_chars_in_corp.add(all_hr_chars[0])

        all_chars_in_corp = list(all_chars_in_corp)
        all_chars_in_corp.sort()
        logger.info(
            f"PINGER: {corporation_id} We have these Characters {all_chars_in_corp}")

        if last_character in all_chars_in_corp:
            idx = all_chars_in_corp.index(last_character) + 1
        else:
            idx = 0

        if idx == len(all_chars_in_corp):
            idx = 0

        character_id = all_chars_in_corp[idx]
        logger.info(f"PINGER: {corporation_id} Updating with {character_id}")

        # if the char bugs out we will retry. so use next toon.
        # TODO Blacklist bad chars
        req_scopes = ['esi-characters.read_notifications.v1']

        token = Token.get_token(character_id, req_scopes)

        if not token:
            _set_cache_data_for_corp(
                corporation_id,
                character_id,
                all_chars_in_corp,
                30
            )
            logger.error(f"PINGER: {corporation_id} - {character_id} has no tokens, retrying in 30s with next char.")
            self.retry(countdown=30)

        try:
            access_token = token.valid_access_token()
        except InvalidGrantError:
            logger.error(
                f"Invalid Grant on {token}, Deleting {token.character_name}'s token")
            self.retry(countdown=10)

        last_expire = _get_last_cache_expire(character_id)
        _set_cache_data_for_corp(
            corporation_id, character_id, all_chars_in_corp, 10)

        types = get_available_types()
        # update notifications for this character inline.

        notifs = esi.client.Character.get_characters_character_id_notifications(
            character_id=character_id,
            token=access_token
        )

        # CCPLEASE Why do you make me do this....
        # I hate this... i am unsure of the possible dangers of allowing invalid data through...
        # maybe we can make this an option later on or add some kind of admin ping on bad data...
        # TODO yell in the direction of CCP and find a nicer way to manage this.
        # notifs.operation.swagger_spec.config["validate_responses"] = False
        notifs.request_config.also_return_response = True
        _notifs = []

        try:
            _notifs, response = notifs.results()
        except Exception as e:
            raise e
        finally:
            # As this is a spec level change i think it needs to be reverted
            # if it is not all requests stop being validated this is bad...
            # but for now lets not... see what happens...
            # notifs.operation.swagger_spec.config["validate_responses"] = False
            pass

        now = time.mktime(timezone.now().timetuple())
        next_expire = http2time(response.headers.get('Expires'))

        secs_till_expire = next_expire - now
        if next_expire == last_expire:
            logger.info("PINGER: CACHE: Same Cache as last update.")
        if secs_till_expire < 30:
            logger.warning(
                f"PINGER: CACHE: Almost expired cache {token.character_name}, retrying with this character in {secs_till_expire + 1} seconds")
            _set_cache_data_for_corp(
                corporation_id, last_character, all_chars_in_corp, 0)
            self.retry(countdown=secs_till_expire + 1)
        elif secs_till_expire < 570:
            logger.warning(
                f"PINGER: CACHE: Mid cache cycle {token.character_name}, retrying with next character")
            self.retry(countdown=1)

        _set_last_cache_expire(character_id, next_expire)

        pingable_notifs = []
        pinged_already = set(
            list(Ping.objects.values_list("notification_id", flat=True)))

        for n in _notifs:
            if n.get('timestamp') > CUTTOFF:
                _t = sanitize_notification_type(n.get('type'))
                if _t.startswith("unknown"):
                    logger.warning(
                        f"PINGER: {corporation_id} Got Notification "
                        f"{n.get('notification_id')} {n.get('type')} "
                        f"{n.get('timestamp')}\n\n{n.get('text')}"
                    )
                if _t in types.keys():
                    if n.get('notification_id') not in pinged_already:
                        n['time'] = datetime.datetime.timestamp(
                            n.get('timestamp'))
                        pingable_notifs.append(n)

        logger.info(
            f"PINGER: {corporation_id} Pings to process: {len(pingable_notifs)}")

        # did we get any?
        try:
            process_notifications.apply_async(
                priority=TASK_PRIO,
                args=[character_id, pingable_notifs],
                once={'graceful': False}
            )
        except Exception as e:
            logger.warning(f"PINGER: {corporation_id} Already Queued process_notifications - {e}")

        _, _, min_delay = get_settings()

        delay = max(CACHE_TIME_SECONDS / len(all_chars_in_corp), min_delay)

        # leverage cache
        _set_cache_data_for_corp(
            corporation_id, character_id, all_chars_in_corp, delay)
        # schedule the next corp token depending on the amount available ( 10 min / characters we have ) for each corp
        logger.info(
            f"PINGER: {corporation_id} We have {len(all_chars_in_corp)} Characters, will update every {delay} seconds.")
        # cant requeue ourself in a queueonce enviro
        queue_corporation_notification_update.apply_async(
            args=[corporation_id, delay], priority=(TASK_PRIO + 1), countdown=1)


class Notification:
    # Settings
    character = None
    notification_id = None
    timestamp = None
    notification_type = None
    notification_text = None

    def __init__(self, character, notification_id, timestamp, notification_type, notification_text):
        self.character = character
        self.notification_id = notification_id
        self.timestamp = timestamp
        self.notification_type = notification_type
        self.notification_text = notification_text


@shared_task(bind=True, base=QueueOnce)
def process_notifications(self, cid, notifs):
    char = CharacterAudit.objects.get(character__character_id=cid)
    logger.info(f"PINGER: {char.character.corporation_id} {cid} process_notifications: {notifs}")
    new_notifs = []
    CUTTOFF = timezone.now() - datetime.timedelta(hours=LOOK_BACK_HOURS)

    for note in notifs:
        if not isinstance(note['timestamp'], datetime.datetime):
            note['timestamp'] = datetime.datetime.fromtimestamp(
                note.get('time'), tz=datetime.timezone.utc)
        if note.get('timestamp') > CUTTOFF:
            if note.get('type').startswith("unknown"):
                logger.info(
                    f"PINGER: {char.character.corporation_id} {cid} Got Notification {note.get('notification_id')} {note.get('type')} {note.get('timestamp')}\n\n{note.get('text')}")
            logger.info(f"PINGER: {char.character.corporation_id} {cid} Found: {note}")
            n = Notification(character=char,
                             notification_id=note.get(
                                 'notification_id'),
                             timestamp=note.get('timestamp'),
                             notification_type=sanitize_notification_type(
                                 note.get('type')),
                             notification_text=note.get('text'))
            new_notifs.append(n)

    pings = {}
    # grab all notifications within scope.
    types = get_available_types()
    pinged_already = set(list(Ping.objects.filter(
        time__gte=(CUTTOFF - datetime.timedelta(days=1))).values_list("notification_id", flat=True)))
    # parse them into the parsers
    for n in new_notifs:
        if n.notification_id not in pinged_already:
            logger.info(f"PINGER: {char.character.corporation_id} {cid} Processing: {note}")
            pinged_already.add(n.notification_id)
            try:
                _t = n.notification_type.replace(
                    " ", "").replace("(", "").replace(")", "")
                note = types[_t](n)
                if _t not in pings:
                    pings[_t] = []
                pings[_t].append(note)
            except notifications.MutedException:
                logger.warning(f"PINGER: {char.character.corporation_id} MUTED: {note}")
                pass

    logger.info(f"PINGER: {char.character.corporation_id} {cid} Sending {len(pings.keys())} pings")
    # send them to webhooks as needed
    for k, l in pings.items():
        webhooks = DiscordWebhook.objects.filter(ping_types__class_tag=k)\
            .prefetch_related("alliance_filter", "corporation_filter", "region_filter")

        for hook in webhooks:
            regions = hook.region_filter.all().values_list("region_id", flat=True)
            alliances = hook.alliance_filter.all().values_list("alliance_id", flat=True)
            corporations = hook.corporation_filter.all(
            ).values_list("corporation_id", flat=True)

            for p in l:
                corp_filter, alli_filter, region_filter = p.get_filters()

                if corp_filter is not None and len(corporations) > 0:
                    if corp_filter not in corporations:
                        logging.info(f"PINGER: {char.character.corporation_id} {cid} ignroing Ping {p} corp filter")
                        continue

                if alli_filter is not None and len(alliances) > 0:
                    if alli_filter not in alliances:
                        logging.info(f"PINGER: {char.character.corporation_id} {cid} ignroing Ping {p} alli filter")
                        continue

                if region_filter is not None and len(regions) > 0:
                    if region_filter not in regions:
                        logging.info(
                            f"PINGER: {char.character.corporation_id} {cid} ignroing Ping {p} region filter")
                        continue

                ping_ob = Ping.objects.create(
                    notification_id=p._notification.notification_id,
                    time=p._notification.timestamp,
                    body=p._ping,
                    hook=hook,
                    alerting=p.force_at_ping
                )
                logging.info(f"PINGER: {char.character.corporation_id} {cid} Sending Ping {ping_ob}")
                ping_ob.send_ping()
                try:
                    if p.timer:
                        p.timer.save()
                except Exception:
                    logger.exception(f"PINGER: {char.character.corporation_id} {cid} Faiiled to add Timer... {ping_ob}")


def _build_wh_cache_key(wh_id):
    return f"ct-pingger-wh-{wh_id}"


def _get_wh_cooloff(wh_id):
    return cache.get(_build_wh_cache_key(wh_id), False)


def _set_wh_cooloff(wh_id, cooloff):
    ready_time = timezone.now() + datetime.timedelta(seconds=cooloff)
    unixtime = time.mktime(ready_time.timetuple())
    cache.set(_build_wh_cache_key(wh_id), unixtime, cooloff + .5)


def _get_cooloff_time(wh_id):
    cached = _get_wh_cooloff(wh_id)
    if cached:
        unixtime = time.mktime(timezone.now().timetuple())
        return (cached - unixtime) + 0.15
    else:
        return 0


@shared_task(bind=True, max_retries=None)
def send_ping(self, ping_id):
    ping_ob = Ping.objects.get(id=ping_id)
    CUTTOFF = timezone.now() - datetime.timedelta(hours=LOOK_BACK_HOURS)

    if ping_ob.notification_id > 0:
        saved = cache_client.sadd(
            "ct-pinger-ping-lock-set", f"{ping_id}{ping_ob.notification_id}")
        if saved == 0:
            logger.info(
                f"PINGER: DUPLICATE skipping {ping_ob.notification_id}")
            ping_ob.ping_sent = True
            ping_ob.save()
            return

    wh_sleep = _get_cooloff_time(ping_ob.hook.id)
    if wh_sleep > 0:
        logger.warning(
            f"Webhook rate limited: trying again in {wh_sleep} seconds...")
        self.retry(countdown=wh_sleep)

    if ping_ob.ping_sent is True:
        return "Already done!"

    if ping_ob.time < CUTTOFF:
        return "TOO OLD!"

    alertText = ""
    if ping_ob.alerting and not ping_ob.hook.no_at_pings:
        alertText = '"content": "@here", '

    payload = f'{{{alertText}"embeds": [{ping_ob.body}]}}'

    logger.debug(payload)
    url = ping_ob.hook.discord_webhook
    custom_headers = {'Content-Type': 'application/json'}

    response = requests.post(url,
                             headers=custom_headers,
                             data=payload,
                             params={'wait': True})

    if response.status_code in [200, 204]:
        logger.debug(f"{ping_ob.notification_id} Ping Sent!")
        ping_ob.ping_sent = True
        ping_ob.save()
    elif response.status_code == 429:
        if ping_ob.notification_id > 0:
            saved = cache_client.srem(
                "ct-pinger-ping-lock-set", f"{ping_id}{ping_ob.notification_id}")
        errors = json.loads(response.content.decode('utf-8'))
        wh_sleep = (int(errors['retry_after']) / 1000) + 0.15
        logger.warning(
            f"Webhook rate limited: trying again in {wh_sleep} seconds...")
        _set_wh_cooloff(ping_ob.hook.id, wh_sleep)
        self.retry(countdown=wh_sleep)
    else:
        if ping_ob.notification_id > 0:
            saved = cache_client.srem(
                "ct-pinger-ping-lock-set", f"{ping_id}{ping_ob.notification_id}")
        logger.error(
            f"{ping_ob.notification_id} failed ({response.status_code}) to: {url}")
        response.raise_for_status()
    # TODO 404/403/500 etc etc etc etc
