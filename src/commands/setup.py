from resources.structures.Bloxlink import Bloxlink # pylint: disable=import-error, no-name-in-module
from resources.constants import ARROW, BROWN_COLOR, NICKNAME_TEMPLATES # pylint: disable=import-error, no-name-in-module
from resources.exceptions import Error, RobloxNotFound, CancelCommand # pylint: disable=import-error, no-name-in-module
import discord
import re

NICKNAME_DEFAULT = "{smart-name}"
VERIFIED_DEFAULT = "Verified"

get_group = Bloxlink.get_module("roblox", attrs=["get_group"])
post_event = Bloxlink.get_module("utils", attrs=["post_event"])
set_guild_value, get_guild_value = Bloxlink.get_module("cache", attrs=["set_guild_value", "get_guild_value"])

roblox_group_regex = re.compile(r"roblox.com/groups/(\d+)/")


@Bloxlink.command
class SetupCommand(Bloxlink.Module):
    """set-up your server with Bloxlink"""

    def __init__(self):
        self.permissions = Bloxlink.Permissions().build("BLOXLINK_MANAGER")
        self.category = "Administration"
        self.aliases = ["set-up"]
        self.slash_enabled = True
        self.slash_defer = True

    @staticmethod
    async def validate_group(message, content, prompt, guild):
        if content.lower() in ("skip", "next"):
            return "skip"

        regex_search = roblox_group_regex.search(content)

        if regex_search:
            group_id = regex_search.group(1)
        else:
            group_id = content

        try:
            group = await get_group(group_id, full_group=True)
        except RobloxNotFound:
            return None, "No group was found with this ID. Please try again."

        return group

    async def __main__(self, CommandArgs):
        guild = CommandArgs.guild
        author = CommandArgs.author
        response = CommandArgs.response

        group_ids = await get_guild_value(guild, "groupIDs") or {}

        settings_buffer = []
        insertion = {}
        parsed_args_1 = {}
        nickname = None

        response.delete(await response.info("See this video for a set-up walkthrough: <https://blox.link/tutorial/setup/>", dm=False, no_dm_post=True))

        parsed_args_1 = await CommandArgs.prompt([
            {
                "prompt": "**Thank you for choosing Bloxlink!** In a few simple prompts, **we'll configure Bloxlink for your server.**\n\n"
                          "**Pre-configuration:**\nBefore continuing, please ensure that Bloxlink has all the proper permissions, "
                          "such as the ability to `manage roles, nicknames, channels`, etc. If you do not set these "
                          "permissions, you may encounter issues with using certain commands.",
                "name": "_",
                "footer": "Say **next** to continue.",
                "type": "choice",
                "choices": ["next"],
                "components": [discord.ui.Button(label="Next", style=discord.ButtonStyle.primary)],
                "embed_title": "Setup Prompt"
            },
            {
                "prompt": "Should your members be given a nickname? Please create a nickname using these templates. You may "
                          f"combine templates. The templates MUST match exactly.\n\n**Templates:** ```{NICKNAME_TEMPLATES}```",
                "name": "nickname",
                "embed_title": "Setup Prompt",
                "footer": "Say **disable** to not have a nickname.\nSay **skip** to leave this as the default (`{smart-name}`).",
                "formatting": False,
                "exceptions": ("disable", "skip")
            },
            {
                "prompt": "Would you like to change the **Verified role** (the role people are given if they're linked to Bloxlink) name to something else?\n"
                          "Default: `Verified`",
                "name": "verified_role",
                "footer": "Say **disable** to disable the Verified role.\nSay **skip** to leave as-is.",
                "embed_title": "Setup Prompt",
                "max": 50
            },
            {
                "prompt": "Would you like to link a **Roblox group** to this Discord server? Please provide the **Group URL, or Group ID**.",
                "name": "group",
                "footer": "Say **skip** to leave as-is.",
                "embed_title": "Setup Prompt",
                "validation": self.validate_group
            }
        ], dm=False, no_dm_post=False)

        for k, v in parsed_args_1.items():
            if k != "_":
                settings_buffer.append(f"**{k}** {ARROW} {v}")

        group = parsed_args_1["group"]
        verified = parsed_args_1["verified_role"]
        nickname = parsed_args_1["nickname"] if parsed_args_1["nickname"] != "disable" else "{disable-nicknaming}"
        verified_lower = verified.lower()

        if group not in ("next", "skip"):
            group_ids[group.group_id] = {"nickname": None, "groupName": group.name}

            merge_replace = (await CommandArgs.prompt([
                {
                    "prompt": "Would you like to automatically transfer your Roblox group ranks to Discord roles?\nValid choices:\n"
                              "`merge` — This will **NOT** remove any roles. Your group Rolesets will be **merged** with your current roles.\n"
                              "`replace` — **This will REMOVE and REPLACE your CURRENT ROLES** with your Roblox group Rolesets. You'll "
                              "need to configure permissions and colors yourself.\n"
                              "`skip` — nothing will be changed.",
                    "name": "merge_replace",
                    "type": "choice",
                    "components": [discord.ui.Select(max_values=1, options=[
                            discord.SelectOption(label="Merge", description="No roles will be removed, only added."),
                            discord.SelectOption(label="Replace", description="This will remove your existing roles."),
                            discord.SelectOption(label="Skip", description="Your roles will be un-touched.")
                        ])],
                    "choices": ["merge", "replace", "skip", "next"],
                    "embed_title": "Setup Prompt"

                }
            ], dm=False, no_dm_post=True))["merge_replace"][0]

            if merge_replace  == "next":
                merge_replace = "skip"

            group_ids[group.group_id] = {"nickname": None, "groupName": group.name}

            settings_buffer.append(f"**merge_replace** {ARROW} {merge_replace}")


        parsed_args_4 = await CommandArgs.prompt([
            {
                "prompt": "You have reached the end of the setup. Here are your current settings:\n"
                           + "\n".join(settings_buffer),
                "name": "setup_complete",
                "type": "choice",
                "footer": "Please say **done** to complete the setup.",
                "choices": ["done"],
                "embed_title": "Setup Prompt Confirmation",
                "embed_color": BROWN_COLOR,
                "components": [discord.ui.Button(label="Done", style=discord.ButtonStyle.primary)],
                "formatting": False
            }
        ], dm=False, no_dm_post=True, last=True)

        if group and group != "skip":
            if merge_replace not in ("skip", "next"):
                if merge_replace == "replace":
                    for role in list(guild.roles):
                        try:
                            if not (role in guild.me.roles or role.is_default()):
                                try:
                                    await role.delete(reason=f"{author} chose to replace roles through /setup")
                                except discord.errors.Forbidden:
                                    pass
                                except discord.errors.HTTPException:
                                    pass

                        except AttributeError: # guild.me is None -- bot kicked out
                            raise CancelCommand

                for _, roleset_data in group.rolesets.items():
                    if not discord.utils.find(lambda r: r.name == roleset_data[0], guild.roles):
                        try:
                            await guild.create_role(name=roleset_data[0], reason="Creating role from /setup")
                        except discord.errors.Forbidden:
                            raise Error("Please ensure I have the `Manage Roles` permission; setup aborted.")

        if verified:
            if verified_lower == "disable":
                insertion["verifiedRoleEnabled"] = False
            elif verified_lower not in ("next", "skip"):
                insertion["verifiedRoleName"] = verified
                insertion["verifiedRoleEnabled"] = True

        if group_ids:
            insertion["groupIDs"] = group_ids

        if nickname != "skip":
            insertion["nicknameTemplate"] = nickname


        await set_guild_value(guild, **insertion)

        await post_event(guild, "configuration", f"{author.mention} ({author.id}) has **set-up** the server.", BROWN_COLOR)

        await response.success("Your server is now **configured** with Bloxlink!", dm=False, no_dm_post=True)
