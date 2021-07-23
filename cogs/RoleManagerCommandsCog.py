import asyncio
import discord
from discord.ext import commands
import re
from utils.database import db
from utils.menu import Menu
from utils.page import Page, EmbeddedPage

role_manager_message_example = "https://i.imgur.com/aWWPakN.png"
role_message_example = "https://i.imgur.com/a72g73D.png"
role_reaction_example = "https://i.imgur.com/SIfTfUU.png"


class RoleManagerCommandsCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def re_manage(self, ctx, manager_id: int):
        server = db['Servers'].find_one({'_id': ctx.guild.id})
        try:
            roles = server['role_managers'][str(manager_id)]['roles']
            channel_id = server['role_managers'][str(manager_id)]['channel']
        except KeyError:
            return

        channel = ctx.guild.get_channel(channel_id)
        message = await channel.fetch_message(manager_id)
        await message.clear_reactions()
        for react in roles.keys():
            await message.add_reaction(react)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def create_role_manager(self, ctx):

        # Init for getting manager message
        manager_message_page = EmbeddedPage (
            title="Enter the message that people will react to.",
            description="I suggest providing a list of the role and it's reaction!",
            image=role_manager_message_example
        )

        def manager_message_check(message):
            '''Check if:
                - Message from command invoker
                - Message in command invoked channel
            '''

            return (
            message.author == ctx.author and
            message.channel == ctx.channel
            )

        menu = Menu (
            bot=self.bot,
            pages=[manager_message_page],
            channel=ctx.channel,
            interactors=[ctx.author],
            input=manager_message_check,
            timeout=300,
            remove_message_after=True
        )

        # This is the message people are going to add reactions to.
        try:
            manager_message, _ = await menu.display()
        except TypeError:
            return

        menu.timeout = 60

        default_options = {
            "multi": {
                "yes": True,
                "no": False
            }
        }

        options_message_page = Page(
            title="Should one be able to get multiple of these roles?",
            description="Enter yes or no below!"
        )

        def options_message_check(message):
            '''Check if:
                - Message from command invoker
                - Message in command invoked channel
                - Message equal to "yes" or "no"
            '''

            return (
                message.author == ctx.author and
                message.channel == ctx.channel and
                message.content.lower() in ["yes", "no"]
            )

        menu.input = options_message_check
        menu.update(pages=[options_message_page])

        try:
            multi_message, _ = await menu.display(new=False)
        except TypeError:
            return
        else:
            multi = default_options["multi"][multi_message.content.lower()]

        role_manager = {
            'channel': ctx.channel.id,
            'multi': multi,
            'roles': {
            }
        }

        # Init for getting the roles
        role_message_page = EmbeddedPage (
            title="Enter the role you want to add.",
            description="Do this by mentioning the role with @[role-name]",
            footer="Click :x: to finish!",
            file=role_message_example
        )

        def role_message_check(message):
            '''Check if:
                - Message in command invoked channel
                - Message from command invoker
                - Message is a mention to a role
            '''
            return (
                message.channel == ctx.channel and
                message.author == ctx.author and
                re.match("^<@&[0-9]*>$", message.content)
            )

        # Init for getting the linked reactions
        role_reaction_page = EmbeddedPage (
            title="React the emoji that you want to link to your previous message!",
            image=role_reaction_example
        )

        def role_reaction_check(payload):
            '''Check if:
                - Reaction from command invoker
            '''
            return payload.user_id == ctx.author.id

        # Role - Reaction loop
        while len(role_manager['roles'].keys()) <= 50:
            # Role
            menu.show_general_buttons = True
            menu.reaction_input = None
            menu.input = role_message_check
            menu.update(pages=[role_message_page])

            try:
                role_message, _ = await menu.display(new=False)
            except TypeError:
                break
            else:
                role_id = re.sub("[<@&>]", '', role_message.content)

            # Reaction emoji
            menu.show_general_buttons = False
            menu.input = None
            menu.reaction_input = role_reaction_check
            menu.update(pages=[role_reaction_page])

            try:
                payload, _ = await menu.display(new=False)
            except TypeError:
                break

            try:
                await manager_message.add_reaction(payload.emoji)
            except discord.HTTPException:
                await ctx.send("Something went wrong... Maybe this emoji is invalid? :S")
            else:
                # Storing the link
                role_manager['roles'][str(payload.emoji)] = int(role_id)
        else:
            await ctx.send("You have reached the maximum of 50 entries! ",
            " Message has been actived, create a new manager to make more!")

        await menu.stop()
        await ctx.channel.purge(limit=len(role_manager['roles'].keys())+1)
        # Updating database information
        db['Servers'].update_one({'_id': ctx.guild.id},
        {'$set': {f'role_managers.{str(manager_message.id)}': role_manager}})

        end_message = await ctx.send("Everything is setup! You may delete anything unnecessary :)")
        await ctx.message.delete()
        await asyncio.sleep(5)
        try:
            await end_message.delete()
        except discord.NotFound:
            pass


def setup(bot):
    bot.add_cog(RoleManagerCommandsCog(bot))
