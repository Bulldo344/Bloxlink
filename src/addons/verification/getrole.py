from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error, no-name-in-module
import discord
from resources.exceptions import (Message, UserNotVerified, Error, RobloxNotFound, BloxlinkBypass, # pylint: disable=import-error, no-name-in-module
                                 Blacklisted, PermissionError, CancelCommand) # pylint: disable=import-error, no-name-in-module
from resources.constants import GREEN_COLOR # pylint: disable=import-error, no-name-in-module

get_user, get_nickname, get_roblox_id, parse_accounts, format_update_embed, guild_obligations = Bloxlink.get_module("roblox", attrs=["get_user", "get_nickname", "get_roblox_id", "parse_accounts", "format_update_embed", "guild_obligations"])
post_event = Bloxlink.get_module("utils", attrs=["post_event"])
set_guild_value = Bloxlink.get_module("cache", attrs=["set_guild_value"])
get_verify_link = Bloxlink.get_module("robloxnew.verifym", attrs=["get_verify_link"], name_override="verifym")



class GetRoleCommand(Bloxlink.Module):
    """link your Roblox account to your Discord account and get your server roles"""

    def __init__(self):
        self.examples = ["add", "unlink", "view", "blox_link"]
        self.category = "Account"
        self.cooldown = 5
        self.dm_allowed = True
        self.slash_enabled = True
        self.slash_defer = True

    @staticmethod
    async def validate_username(message, content):
        try:
            roblox_id, username = await get_roblox_id(content)
        except RobloxNotFound:
            return None, "There was no Roblox account found with that username. Please try again."

        return username

    @Bloxlink.flags
    async def __main__(self, CommandArgs):
        guild = CommandArgs.guild
        author = CommandArgs.author
        response = CommandArgs.response

        try:
            if not guild:
                await response.info("You must run this in a server to get your roles.")
                raise UserNotVerified

            if CommandArgs.command_name in ("getrole", "getroles"):
                CommandArgs.string_args = []

            old_nickname = author.display_name

            added, removed, nickname, errors, warnings, roblox_user = await guild_obligations(
                CommandArgs.author,
                join                 = True,
                guild                = guild,
                roles                = True,
                nickname             = True,
                cache                = False,
                response             = response,
                dm                   = False,
                exceptions           = ("BloxlinkBypass", "Blacklisted", "UserNotVerified", "PermissionError", "RobloxDown", "RobloxAPIError")
            )

        except BloxlinkBypass:
            raise Message("Since you have the `Bloxlink Bypass` role, I was unable to update your roles/nickname.", type="info")

        except Blacklisted as b:
            await response.send(b.message, hidden=True)

            raise CancelCommand()

        except UserNotVerified:
            verify_link = await get_verify_link(guild)

            view = discord.ui.View()
            view.add_item(item=discord.ui.Button(style=discord.ButtonStyle.link, label="Verify with Bloxlink", url=verify_link, emoji="🔗"))
            view.add_item(item=discord.ui.Button(style=discord.ButtonStyle.link, label="Stuck? See a Tutorial", emoji="❔",
                                                 url="https://www.youtube.com/watch?v=mSbD91Zug5k&list=PLz7SOP-guESE1V6ywCCLc1IQWiLURSvBE&index=1"))

            await CommandArgs.response.send("To verify with Bloxlink, click the link below.", mention_author=True, view=view)


        except PermissionError as e:
            raise Error(e.message)

        else:
            welcome_message, card, embed = await format_update_embed(
                roblox_user,
                author,
                guild=guild,
                added=added, removed=removed, errors=errors, warnings=warnings, nickname=nickname if old_nickname != nickname else None,
            )

            message = await response.send(welcome_message, files=[card.front_card_file] if card else None, view=card.view if card else None, embed=embed, mention_author=True)

            if card:
                card.response = response
                card.message = message
                card.view.message = message

            await post_event(guild, "verification", f"{author.mention} ({author.id}) has **verified** as `{roblox_user.username}`.", GREEN_COLOR)
