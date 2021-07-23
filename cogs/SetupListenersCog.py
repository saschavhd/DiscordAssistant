import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from package_tools import add_user_to_database, _leave, _setup
import pymongo
from utils.constants import DEFAULT_CHANNELS, DEFAULT_ROLES, FMT, FMT_DATE
from utils.database import db, DEFAULT_SERVER, DEFAULT_USER


class SetupListenersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        '''Bot joins guild handler'''

        await _setup(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        '''Bot removed from guild handler'''

        await _leave(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        '''Member joins guild of bot handler'''

        add_user_to_database(member)
        server = db['Servers'].find_one({'_id': member.guild.id})
        try:
            spawn_channel_id = server['channels']['spawn']
        except KeyError:
            pass
        else:
            spawn_channel = member.guild.get_channel(spawn_channel_id)
            welcome_message = f"Hello {member.mention}, welcome to {member.guild.name}!"
            await spawn_channel.send(welcome_message)

        try:
            start_role_id = server['roles']['0']
        except KeyError:
            return
        else:
            start_role = member.guild.get_role(start_role_id)
            await member.add_roles(start_role)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        '''Member leaves guild of bot handler'''

        guild = member.guild
        # Set member leave date
        try:
            db['Users'].update_one({'_id': member.id},
            {'$set': {f'servers.{guild.id}.leave_date': datetime.utcnow()}})
        except KeyError:
            print(f"[{datetime.utcnow().strftime(FMT)}]\t ",
            f"Member {member.id} was removed from {guild.name}:{guild.id} ",
            "but server information for user was never stored.")
        except AttributeError:
            print(f"[{datetime.utcnow().strftime(FMT)}]\t ",
            f"Member {member.id} was removed from {guild.name}:{guild.id} ",
            "but user information was never stored.")

        # Get eject channel
        server = db['Servers'].find_one({'_id': guild.id})
        try:
            eject_channel_id = server['channels']['eject']
        except KeyError:
            return
        else:
            eject_channel = guild.get_channel(eject_channel_id)

        eject_message = f"{member} was ejected :("

        await eject_channel.send(eject_message)


def setup(bot):
    bot.add_cog(SetupListenersCog(bot))
