import asyncio
import discord
from discord.ext import commands
import math
from package_tools import exp_to_level, get_emoji_number, level_to_exp
import re
from utils.constants import NUMBER_EMOTES_UNICODE, TOTAL_BARS
from utils.database import db
from utils.menu import Menu
from utils.page import Page, EmbeddedPage


class LevelCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def rank(self, ctx):
        user = db['Users'].find_one({'_id': ctx.author.id})
        try:
            user_exp = user['servers'][str(ctx.guild.id)]['experience']
        except (KeyError, TypeError):
            await ctx.send("No record found!")
            return

        users = list(db['Users'].find({f'servers.{ctx.guild.id}': {'$exists': True}}))
        users_exp = []
        for user in users:
            try:
                users_exp.append(user['servers'][str(ctx.guild.id)]['experience'])
            except KeyError:
                continue
        users_exp.sort(reverse=True)

        rank = users_exp.index(user_exp) + 1
        await ctx.send(f"You are ranked #{rank} in this server!")

    @commands.command()
    @commands.guild_only()
    async def top(self, ctx):
        top = db['Users'].find({f'servers.{ctx.guild.id}.experience': {'$exists': True}})
        top = list(top)
        top = sorted(top, key=lambda x: x['servers'][str(ctx.guild.id)]['experience'], reverse=True)
        top = top[:80]
        ranking = []
        for itr, user in enumerate(top):
            member = ctx.guild.get_member(user['_id'])
            if not member:
                continue
            user_server = user['servers'][str(ctx.guild.id)]
            exp = user_server['experience']
            ranking.append(f"{get_emoji_number(itr+1)} {member.name} - Level: {exp_to_level(exp)} | {exp}")

        per_page = 8
        pages = [ranking[i:i+per_page] for i in range(0, len(ranking), per_page)]

        menu = Menu (
            bot=self.bot,
            channel=ctx.channel,
            interactors=[ctx.author],
            pages=pages,
            title="Level ranking for this server.",
            remove_message_after=True,
            all_embedded=True
        )

        await menu.display()

    @commands.command()
    @commands.guild_only()
    async def level(self, ctx, member: discord.Member=None):
        if not member:
            member = ctx.author
        user = db['Users'].find_one({'_id': member.id})
        try:
            exp = user['servers'][str(ctx.guild.id)]['experience']
        except (KeyError, TypeError):
            await ctx.send("Something went wrong, please try again later!")
            return

        current_level = exp_to_level(exp)
        exp_req_current_level = level_to_exp(current_level)
        exp_gained_current_level = exp - exp_req_current_level
        exp_req_next_level = level_to_exp(current_level+1)
        exp_req_level_up = exp_req_next_level - exp_req_current_level

        fraction = exp_gained_current_level/exp_req_next_level

        bars = '█' * math.ceil(fraction*TOTAL_BARS)
        empty = ' ' * math.ceil((1-fraction)*TOTAL_BARS)
        percentage = round(fraction*100, 1)

        embed = discord.Embed(
            title=f"{member.name} is level {current_level}!",
            description=f"{member.name} has gained a total of {exp} experience points!"
        )
        embed.add_field(
            name=f"{exp_gained_current_level}/{exp_req_level_up} - {percentage}%",
            value=f"`{bars}{empty}`|",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setup_level(self, ctx):

        # Initialing menu
        menu = Menu (
            bot=self.bot,
            interactors=[ctx.author],
            channel=ctx.channel,
            pages=['_'],
            remove_message_after=True
        )

        # Main menu page
        main_menu_options = [
            "Main level properties menu",
            "Level roles",
            "Disable channels"
        ]
        selectors = [NUMBER_EMOTES_UNICODE[i] for i in range(len(main_menu_options))]
        main_menu = EmbeddedPage (
            title="Change the leveling properties for your server!",
            footer="Click the reaction for your choice",
            content=main_menu_options,
            enumerate_with_emoji=True,
            using_fields=True
        )
        menu.selectors = selectors
        menu.update(pages=[main_menu])

        input_tuple = await menu.display()
        try:
            selection, _ = input_tuple
        except TypeError:
            return

        selection = NUMBER_EMOTES_UNICODE.index(str(selection.emoji)) + 1

        await menu.stop()
        submenus = {
            1: self.setup_level,
            2: self.setup_level_roles,
            3: self.setup_exp_channels
        }
        await submenus[selection](ctx)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setup_level_roles(self, ctx):
        menu = Menu (
            bot=self.bot,
            interactors=[ctx.author],
            channel=ctx.channel,
            pages=['_'],
            remove_message_after=True
        )

        level_roles = db['Servers'].find_one({'_id': ctx.guild.id})['roles']

        prefix, roles = [], []
        if level_roles:
            for level_str, role_id in level_roles.items():
                try:
                    level = int(level_str)
                except ValueError:
                    continue
                else:
                    prefix.append(get_emoji_number(level))
                    roles.append(f"<@&{int(role_id)}>")
        else:
            prefix = None
            roles = ["There are no level roles setup for this server."]

        level_roles_page = Page (
            title="Enter the number of the level (max: 100) you want to change.",
            content=roles,
            prefix=prefix
        )

        def level_check(message):
            '''Check if:
                - Message from command invoker
                - Message in command invoked channel
                - Message content is a positive integer
                - Above integer is between 0 and 100
            '''
            return (
                message.author == ctx.author and
                message.channel == ctx.channel and
                message.content.isdigit() and
                0 <= int(message.content) <= 100
            )

        menu.input = level_check
        menu.selectors = None
        menu.update(pages=[level_roles_page])

        input_tuple = await menu.display()
        try:
            input, _ = input_tuple
        except TypeError:
            return

        level = int(input.content)

        # Get role linked to level
        role_input_page = EmbeddedPage (
            title="Enter the role you want to link to this level below!",
            footer="Do this by mentioning the role as follows @[role-name]"
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
                re.match("<@&[0-9]*>", message.content)
            )

        menu.input = role_message_check
        menu.update(pages=[role_input_page])

        input_tuple = await menu.display(new=False)
        try:
            input, _ = input_tuple
        except TypeError:
            return

        role = input.content
        role_id = int(re.sub("[<@&>]", '', role))

        db['Servers'].update_one({'_id': ctx.guild.id},
            {'$set': {f'roles.{str(level)}': role_id}}
        )
        await menu.stop()
        await ctx.send(f"Role {role} will now be obtained upon reaching level {level}.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setup_exp_channels(self, ctx):
        menu = Menu (
            bot = self.bot,
            interactors = [ctx.author],
            channel = ctx.channel,
            pages=['_'],
            remove_message_after=True
        )

        def channel_message_check(message):
            '''Check if:
                - Message by command invoker
                - Message in command invoked channel
                - Message contains a channel
            '''
            return (
                message.author == ctx.author and
                message.channel == ctx.channel and
                re.match('<#[0-9]*>', message.content)
            )


        server = db['Servers'].find_one({'_id': ctx.guild.id})
        ignore_exp_channels = [f"<#{channel_id}>" for channel_id in server['channels']['ignore_exp']]

        exp_channel_page = Page (
            title="Channels that will not gain experience",
            description="Mention a channel below to toggle experience gain there.",
            footer="Do this using #[channel-name]!",
            content=ignore_exp_channels
        )

        menu.input = channel_message_check
        menu.update(pages=[exp_channel_page])

        input_tuple = await menu.display()
        if not input_tuple:
            return
        input, _ = input_tuple
        channel_id = int(re.sub('[<#>]', '', input.content))

        if channel_id in server['channels']['ignore_exp']:
            db['Servers'].update_one({'_id': ctx.guild.id},
                {'$pull': {'channels.ignore_exp': channel_id}})
        else:
            db['Servers'].update_one({'_id': ctx.guild.id},
                {'$addToSet': {'channels.ignore_exp': channel_id}})

        await menu.stop()
        await ctx.send(f"Experience gain has been toggled in channel <#{channel_id}>!")


def setup(bot):
    bot.add_cog(LevelCommandsCog(bot))
