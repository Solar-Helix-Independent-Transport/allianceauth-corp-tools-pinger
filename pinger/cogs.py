# Cog Stuff
import logging
from typing import Optional

from aadiscordbot import app_settings
from aadiscordbot.cogs.utils.decorators import sender_has_perm
from aadiscordbot.tasks import send_channel_message_by_discord_id
# AA Contexts
from corptools.models import (
    CharacterAudit, EveLocation, MapSystem, MapSystemMoon,
)
from discord import AutocompleteContext, ButtonStyle, Embed, option, ui
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

from django.conf import settings
from django.db.models.query_utils import Q
from django.utils import timezone

from allianceauth.eveonline.evelinks import dotlan
from allianceauth.eveonline.models import EveCharacter
from allianceauth.services.modules.discord.models import DiscordUser

from pinger.app_settings import CT_PINGER_VALID_STATES
from pinger.models import MutedStructure, PingerConfig
from pinger.tasks import _get_cache_data_for_corp, get_settings

from .providers import cache_client

logger = logging.getLogger(__name__)

BLUE = 0x3498db
MAGENTA = 0xe91e63
GREYPLE = 0x99aab5
RED = 0x992d22


class AttackView(ui.View):
    embed_text = None
    created = None

    def __init__(self,
                 *items: ui.Item,
                 found_by_uid: int = 0,
                 found_by: str = "",
                 system: str = "",
                 timeout: Optional[float] = 60 * 60 * 24,  # 24h from last click
                 embed: Optional[Embed] = None,
                 bot=None
                 ):
        if embed:
            if isinstance(embed, dict):
                self.embed_text = Embed.from_dict(embed)
            elif isinstance(embed, Embed):
                self.embed_text = embed
        self.bot = bot
        self.created = timezone.now()
        super().__init__(*items, timeout=timeout)
        logger.debug(self.id)

    @ui.button(label="FC Claim", style=ButtonStyle.blurple)
    async def claim(self, button: ui.Button, interaction):
        logger.debug(self.id)
        view = self
        view.children[0].disabled = True
        message = f"{interaction.user.nick if interaction.user.nick else interaction.user.name}"
        embed = interaction.message.embeds[0]
        embed.color = MAGENTA
        embed.add_field(name="Claimed By", value=message, inline=False)

        await interaction.response.edit_message(embed=embed, view=view)

    @ui.button(label="Safe", style=ButtonStyle.success)
    async def run(self, button: ui.Button, interaction):
        logger.debug(self.id)
        message = f"{interaction.user.nick if interaction.user.nick else interaction.user.name}"
        embed = interaction.message.embeds[0]
        embed.color = GREYPLE
        embed.add_field(name="Declared Safe by", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self) -> None:
        print(vars(self))
        await super().on_timeout()


class Pinger(commands.Cog):
    """
    All about pinger!
    """

    def __init__(self, bot):
        self.bot = bot

    pinger_commands = SlashCommandGroup(
        "pinger", "Infra Pinger Commands", guild_ids=[int(settings.DISCORD_GUILD_ID)])

    async def search_systems(ctx: AutocompleteContext):
        """Returns a list of systems that have the characters entered so far."""
        return list(MapSystem.objects.filter(name__icontains=f"{ctx.value}")[:10].values_list("name", flat=True))

    @commands.slash_command(name='attack', guild_ids=[int(settings.DISCORD_GUILD_ID)])
    @option("system", description="What System has been attacked?", autocomplete=search_systems)
    @option("message", description="Anything else to add? Narrow it down a bit for the FC's")
    async def sov_hacked(
        self,
        ctx,
        system: str,
        message: str
    ):
        """
            Notify that something is being attacked/stolen from! ( Skyhook, etc )
        """
        await ctx.defer(ephemeral=True)

        user = ctx.author

        # no dupes!
        exist = await self.bot.redis.get(f"pinger-claimbot-{system}")
        if exist:
            return await ctx.respond(f"Activity in `{system}` has already been pinged in the last 5 Minutes! Ping manually if required.", ephemeral=True)
        else:
            await self.bot.redis.set(f"pinger-claimbot-{system}", user.name, ex=60 * 5)

        config = PingerConfig.objects.get(id=1)

        output_channel = config.attack_command_output_id if config.attack_command_output_id else ctx.channel.id

        e = Embed(title="Attack Reported!", color=RED)

        msg = [f"System: [{system}]({dotlan.solar_system_url(system)})"]

        if message:
            msg.append(f"{message}")

        extra_message = "\n".join(msg)

        e.description = extra_message

        e.add_field(
            name="Reported By",
            value=f"{user.nick if user.nick else user.name} <@{user.id}>",
            inline=False
        )

        view_str = "pinger.cogs.AttackView"

        send_channel_message_by_discord_id.delay(
            output_channel,
            "@everyone",
            embed=e.to_dict(),
            view_class=view_str,
            view_kwargs={"found_by": f"{ctx.author.nick if ctx.author.nick else ctx.author.name}",
                         "found_by_uid": ctx.author.id,
                         "system": system}
        )

        return await ctx.respond("sent message!", ephemeral=True)

    def mute_str(self, input_name):
        locs = EveLocation.objects.filter(location_name=input_name.strip())
        moon = MapSystemMoon.objects.filter(name=input_name.strip())
        if locs.count() > 0:
            for loc in locs:
                muted, _ = MutedStructure.objects.update_or_create(
                    structure_id=loc.location_id)
            return True
        elif moon.count() > 0:
            for loc in moon:
                muted, _ = MutedStructure.objects.update_or_create(
                    structure_id=loc.moon_id)
            return True
        else:
            return False

    def unmute_str(self, input_name):
        locs = EveLocation.objects.filter(location_name=input_name.strip())
        moon = MapSystemMoon.objects.filter(name=input_name.strip())
        if locs.count() > 0:
            for loc in locs:
                MutedStructure.objects.filter(
                    structure_id=loc.location_id).delete()
            return True
        elif moon.count() > 0:
            for loc in moon:
                MutedStructure.objects.filter(
                    structure_id=loc.moon_id).delete()
            return True
        else:
            return False

    def sender_has_structure_perm(self, ctx):
        id = ctx.author.id
        try:
            has_perm = DiscordUser.objects.get(
                uid=id).user.has_perm("corptools.corp_hr")
            if has_perm:
                return True
            else:
                return False
        except Exception:
            return False

    def get_mute_channels(self):
        conf = PingerConfig.objects.get(pk=1)
        ch_str = conf.discord_mute_channels
        out = []
        for i in ch_str.split(","):
            try:
                out.append(int(i))
            except ValueError:
                pass
        return out

    @commands.command(pass_context=True, aliases=['fuckoff', 'pissoff', 'goaway', 'shutup'])
    @sender_has_perm('corptools.corp_hr')
    async def mute(self, ctx):
        """
        Mute a structure for 48h cause its being annoying.
        """
        if ctx.message.channel.id not in self.get_mute_channels():
            return await ctx.message.reply("Please use this in a correct channel.")

        cmds = ctx.message.content.split(" ")[1:]
        input_name = " ".join(cmds)
        if self.mute_str(input_name):
            await ctx.message.reply(f"`{input_name}` Muted for 48hours")
        else:
            await ctx.message.reply(f"`{input_name}` Could not find structure")

    async def get_recent(self, ctx: AutocompleteContext):
        """Returns a list of colors that begin with the characters entered so far."""
        recent = cache_client.zrange("ctpingermute", 0, 4, "REV")
        output = []
        for i in recent:
            output.append(i.decode('utf-8'))
        return output

    @pinger_commands.command(name='mute', guild_ids=[int(settings.DISCORD_GUILD_ID)])
    async def mute_slash(self, ctx, structure: Option(str, autocomplete=get_recent)):
        """
        Mute a structure for 48h....
        """

        if ctx.channel_id not in self.get_mute_channels():
            return await ctx.respond("Please use this in a correct channel.", ephemeral=True)

        if not self.sender_has_structure_perm(ctx):
            return await ctx.respond("You do not have permision to use this command.", ephemeral=True)

        if self.mute_str(structure):
            await ctx.respond(f"`{structure}` Muted for 48hours")
        else:
            await ctx.respond(f"`{structure}` Could not find structure")

    @pinger_commands.command(name='unmute', guild_ids=[int(settings.DISCORD_GUILD_ID)])
    async def unmute_slash(self, ctx, structure: Option(str, autocomplete=get_recent)):
        """
        Mute a structure for 48h....
        """

        if ctx.channel_id not in self.get_mute_channels():
            return await ctx.respond("Please use this in a correct channel.", ephemeral=True)

        if not self.sender_has_structure_perm(ctx):
            return await ctx.respond("You do not have permision to use this command.", ephemeral=True)

        if self.unmute_str(structure):
            await ctx.respond(f"`{structure}` Un-Muted")
        else:
            await ctx.respond(f"`{structure}` Could not find structure")

    @commands.command(pass_context=True, hidden=True)
    async def pingerstats(self, ctx):
        # https://media1.tenor.com/images/1796f0fa0b4b07e51687fad26a2ce735/tenor.gif
        if ctx.message.author.id not in app_settings.get_admins():
            return await ctx.message.add_reaction(chr(0x1F44E))

        if ctx.message.channel.id not in settings.ADMIN_DISCORD_BOT_CHANNELS:
            return await ctx.message.add_reaction(chr(0x1F44E))

        allis, corps, _ = get_settings()

        # get all new corps not in cache
        all_member_corps_in_audit = CharacterAudit.objects.filter(character__character_ownership__user__profile__state__name__in=CT_PINGER_VALID_STATES,
                                                                  characterroles__station_manager=True,
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
                    if last_update < -60:
                        done[c[1]
                             ] = f"{c[1]} Total Characters : {len(chars)}, Last Character: {last_char_model.character_name} ({last_char}), Next Update: {last_update} Seconds"
                else:
                    done[c[1]] = f"{c[1]} Not Updated Yet"

        await ctx.message.reply(f"Found {len(seen_cid)} Valid Corps! {len(done)} have sync issues.")
        sorted_keys = list(done.keys())
        sorted_keys.sort()

        n = 10
        chunks = [list(sorted_keys[i * n:(i + 1) * n])
                  for i in range((len(sorted_keys) + n - 1) // n)]

        for c in chunks:
            output = ""
            for i in c:
                output += done[i] + "\n"
            await ctx.send(output)


def setup(bot):
    bot.add_cog(Pinger(bot))
