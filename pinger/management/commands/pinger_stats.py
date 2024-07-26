from corptools.models import CharacterAudit

from django.core.management.base import BaseCommand
from django.db.models.query_utils import Q

from allianceauth.eveonline.models import EveCharacter

from pinger.app_settings import CT_PINGER_VALID_STATES
from pinger.tasks import _get_cache_data_for_corp, get_settings


class Command(BaseCommand):
    help = 'Spit out stats for pinger'

    def handle(self, *args, **options):
        self.stdout.write("Reading Settings!")

        allis, corps, _ = get_settings()
        self.stdout.write("Looking for Valid Corps:")

        # get all new corps not in cache
        all_member_corps_in_audit = CharacterAudit.objects.filter((Q(characterroles__station_manager=True) | Q(characterroles__personnel_manager=True)),
                                                                  character__character_ownership__user__profile__state__name__in=CT_PINGER_VALID_STATES,
                                                                  active=True)

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

        corps = all_member_corps_in_audit.values_list(
            "character__corporation_id", "character__corporation_name")

        done = {}
        seen_cid = set()
        for c in corps:
            if c[0] not in seen_cid:
                seen_cid.add(c[0])
                last_char, chars, last_update = _get_cache_data_for_corp(c[0])
                if last_char:
                    last_char_model = EveCharacter.objects.get(
                        character_id=last_char)
                    done[c[1]
                         ] = f"{c[1]} Total Characters : {len(chars)}, Last Character: {last_char_model.character_name} ({last_char}), Next Update: {last_update} Seconds"
                else:
                    done[c[1]] = f"{c[1]} Not Updated Yet"

        self.stdout.write(f"Found {len(done)} Valid Corps!")
        sorted_keys = list(done.keys())
        sorted_keys.sort()
        for id in sorted_keys:
            self.stdout.write(done[id])
