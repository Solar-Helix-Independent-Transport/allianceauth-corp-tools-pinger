import logging
from typing import TYPE_CHECKING

from requests.exceptions import HTTPError

from django.apps import apps

from allianceauth.eveonline.evelinks import dotlan, eveimageserver

if TYPE_CHECKING:
    from django.contrib.auth.models import Group

    from pinger.models import Structure

logger = logging.getLogger(__name__)


def _discord_service_installed() -> bool:
    return apps.is_installed("allianceauth.services.modules.discord")


def role_id_for_group(group: "Group"):
    """The discord role id matching `group` by name, or None if it cannot be resolved."""
    if not _discord_service_installed():
        return None

    from allianceauth.services.modules.discord.models import DiscordUser

    try:
        role = DiscordUser.objects.group_to_role(group)
    except HTTPError:
        logger.warning(
            f"PINGER: FUEL failed to fetch the discord role for {group}", exc_info=True
        )
        return None

    if not role:
        logger.warning(f"PINGER: FUEL no discord role matches the group {group}")
        return None

    return role.get("id")


def build_fuel_embed(
    structure: "Structure", message: str, color: int, days_left: int
) -> dict:
    _title = f"{structure.name}"

    system = structure.system_name
    if system is not None:
        _system_name = f"[{system.name}]({dotlan.solar_system_url(system.name)})"
    else:
        _system_name = f"{structure.system_id}"

    _url = eveimageserver.type_icon_url(structure.type_id, 64)

    _services = ",".join(
        structure.structureservice_set.filter(state="online").values_list(
            "name", flat=True
        )
    )
    if len(_services) == 0:
        _services = "None"

    corp_ticker = structure.corporation.corporation.corporation_ticker
    corp_name = structure.corporation.corporation.corporation_name
    corp_id = structure.corporation.corporation.corporation_id
    footer = {
        "icon_url": eveimageserver.corporation_logo_url(corp_id, 64),
        "text": f"{corp_name} ({corp_ticker})",
    }

    custom_data = {
        "color": color,
        "title": _title,
        "footer": footer,
        "fields": [
            {"name": "System", "value": _system_name, "inline": False},
        ],
    }

    if message:
        custom_data["description"] = message

    if structure.fuel_expires:
        custom_data["fields"].append(
            {
                "name": "Fuel Expires",
                "value": structure.fuel_expires.strftime("%Y-%m-%d %H:%M"),
                "inline": True,
            }
        )
        custom_data["fields"].append(
            {"name": "Days Remaining", "value": str(days_left), "inline": True}
        )
        custom_data["fields"].append(
            {"name": "Online Services", "value": _services, "inline": False}
        )

    custom_data["image"] = {"url": _url}

    return custom_data
