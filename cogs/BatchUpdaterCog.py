import asyncio
from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
from utils.constants import DEFAULT_CHANNELS, DEFAULT_MANAGERS
from utils.database import db
from package_tools import add_user_to_database

DEFAULT_CHANNELS = ['spawn', 'eject', 'log', 'birthday']
DEFAULT_MANAGERS = ['role_managers', 'polls', 'events']
TIMEDELTA_DELETE_INFO = timedelta(days=14)


class BatchUpdaterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_user_information.start()
        self.check_important_roles.start()
        self.check_property_channels.start()
        self.check_important_channels.start()
        self.check_important_managers.start()
        self.user_information_removal.start()
        self.check_unmutes.start()

    def cog_unload(self):
        self.check_user_information.stop()
        self.check_important_roles.stop()
        self.check_property_channels.stop()
        self.check_important_channels.stop()
        self.check_important_managers.stop()
        self.user_information_removal.stop()
        self.check_unmutes.stop()

    @tasks.loop(minutes=5.0)
    async def check_user_information(self):
        '''Loop through all guilds and see if there are any users not in db'''
        async for guild in self.bot.fetch_guilds():
            async for member in guild.fetch_members():
                add_user_to_database(member)

    @tasks.loop(hours=1.0)
    async def check_important_roles(self):
        '''Check if all important saved roles are still in guild'''
        for server in db['Servers'].find():
            guild = await self.bot.fetch_guild(server['_id'])
            for role, role_id in server['roles'].items():
                if not guild.get_role(role_id):
                    db['Servers'].update_one({'_id': guild.id},
                        {'$unset': {f'roles.{role}': ''}})

    @tasks.loop(hours=1.0)
    async def check_property_channels(self):
        for server in db['Servers'].find():
            guild = await self.bot.fetch_guild(server['_id'])
            for channel_id in server['channels']['ignore_exp']:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except discord.NotFound:
                    db['Servers'].update_one({'_id': guild.id},
                        {'$pull': {'channels.ignore_exp': channel_id}})

    @tasks.loop(hours=1.0)
    async def check_important_channels(self):
        '''Check if all important saved channels are still in guild'''
        for server in db['Servers'].find():
            guild = await self.bot.fetch_guild(server['_id'])
            for channel in DEFAULT_CHANNELS:
                unset = False
                try:
                    channel_id = server['channels'][channel]
                except KeyError:
                    continue
                else:
                    try:
                        channel = await self.bot.fetch_channel(channel_id)
                    except discord.NotFound:
                        db['Servers'].update_one({'_id': guild.id},
                            {'$unset': {f'channels.{channel}': ''}})

    @tasks.loop(hours=1.0)
    async def check_important_managers(self):
        '''Check if all important saved messages are in still in guild'''
        for server in db['Servers'].find():
            guild = await self.bot.fetch_guild(server['_id'])
            for default_manager in DEFAULT_MANAGERS:
                for manager, info in server[default_manager].items():
                    channel = await self.bot.fetch_channel(info['channel'])
                    try:
                        message = await channel.fetch_message(manager)
                    except discord.NotFound:
                        db['Servers'].update_one({'_id': guild.id},
                            {'$unset': {f'{default_manager}.{manager}': ''}})


    @tasks.loop(hours=1.0)
    async def user_information_removal(self):
        '''After 2 weeks of absence remove user information from a server'''
        # Get time minus delay
        now_minus_delay = datetime.utcnow() - TIMEDELTA_DELETE_INFO
        # Get all (recently) connected servers
        for server in db['Servers'].find():
            # Remove server information from user if longer ago then set delay.
            db['Users'].update_many({f'servers.{server["_id"]}.leave_date': {'$lt': now_minus_delay}},
                {'$unset': {f'servers.{server["_id"]}': ''},})
        # Set a leave date if a user is no longer connected to any server
        db['Users'].update_many({'servers': {}},
            {'$set': {'leave_date': datetime.utcnow()}})
        # Delete any users from the database that are not connected to a server
        db['Users'].delete_many({'leave_date': {'$lt': now_minus_delay}})


    @tasks.loop(minutes=1.0)
    async def check_unmutes(self):
        '''
        Loop through users documents
            Loop through servers of users
                check if muted until
                    if muted until < datetime.utcnow():
                        check if leave_date
                        unmute
        ''' # TODO: Complete documentation
        users = db['Users'].find()
        for user in users:
            for guild_id, guild_info in user['servers'].items():
                try:
                    muted_until = guild_info['muted_until']
                except KeyError:
                    continue

                if not muted_until < datetime.utcnow():
                    continue

                server = db['Servers'].find_one({'_id': int(guild_id)})
                try:
                    role_id = server['roles']['muted']
                except KeyError:  # Doesn't exist
                    continue
                else:
                    guild = await self.bot.fetch_guild(int(guild_id))
                    role = guild.get_role(role_id)
                    try:
                        member = await guild.fetch_member(user['_id'])
                    except discord.NotFound:
                        continue
                    await member.remove_roles(role)


def setup(bot):
    bot.add_cog(BatchUpdaterCog(bot))
