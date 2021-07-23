import asyncio
import discord
from discord.ext import commands
from package_tools import _leave, _purge, _setup
import pymongo
import re
from utils.constants import DEFAULT_CHANNELS, NUMBER_EMOTES_DISCORD, NUMBER_EMOTES_UNICODE
from utils.database import db
from utils.menu import Menu
from utils.page import Page, EmbeddedPage


class SetupCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Administrator commands
    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def force_setup(self, ctx):
        await _setup(ctx.guild)

    # @commands.command()
    # @commands.guild_only()
    # @commands.has_permissions(administrator=True)
    # async def force_purge(self, ctx):
    #     await _purge(ctx.guild)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def leave(self, ctx):
        '''Makes bot leave server and deletes all saved information!!!'''
        await _leave(ctx.guild)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx, prefix: str):
        '''Set the command prefix'''

        if len(prefix) > 5:
            await ctx.send("The prefix may not be longer than 5 characters.")
            return

        db['Servers'].update_one({'_id': ctx.guild.id}, {'$set': {'prefix': prefix}})
        await ctx.send(f"Your prefix has been changed to {prefix}")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx):
        '''Open the menu for channel assignment'''

        channel_type_page = EmbeddedPage(
            title="Select down below what channel type you would like to set up!",
            content=DEFAULT_CHANNELS,
            enumerate_with_emoji=True
        )

        selectors = [NUMBER_EMOTES_UNICODE[i] for i in range(len(DEFAULT_CHANNELS))]
        menu = Menu (
            bot=self.bot,
            channel=ctx.channel,
            interactors=[ctx.author],
            pages=[channel_type_page],
            selectors=selectors,
            remove_message_after=True
        )

        input_tuple = await menu.display()
        if not input_tuple:
            return
        input, _ = input_tuple
        selection = NUMBER_EMOTES_UNICODE.index(str(input.emoji))
        channel_type = DEFAULT_CHANNELS[selection]

        menu.selectors = None
        def channel_message_check(message):
            '''Check if:
                - Message by command invoker
                - Message in command invoked channel
                - Message content is a channel
            '''

            return (
                message.author == ctx.author and
                message.channel == ctx.channel and
                re.match('<#[0-9]*>', message.content)
            )
        menu.input = channel_message_check

        channel_page = EmbeddedPage(
            title="Enter the channel you want to link below!",
            description="Do this by mentioning the channel as follows #[channel-name]"
        )
        menu.update(pages=[channel_page])

        input_tuple = await menu.display(new=False)
        if not input_tuple:
            return
        input, _ = input_tuple
        channel_id = int(re.sub('[<#>]', '', input.content))

        db['Servers'].update_one({'_id': ctx.guild.id},
            {'$set': {f'channels.{channel_type}': channel_id}})
        await menu.stop()
        await ctx.send(f"<#{channel_id}> has been setup as the {channel_type} channel!")



def setup(bot):
    bot.add_cog(SetupCommandsCog(bot))
