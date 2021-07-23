import discord
from discord.ext import commands
from utils.constants import DEFAULT_MANAGERS
from utils.database import db


class UpdateListenersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        '''Polls/Role Managers/Events''' # TODO: write proper documentation

        guild_id = payload.guild_id
        if not guild_id:
            return
        message_id = payload.message_id
        server = db['Servers'].find_one({'_id': int(guild_id)})
        deleted_message_type = None
        for manager in DEFAULT_MANAGERS:
            if str(message_id) in server[manager].keys():
                deleted_message_type = manager
                db['Servers'].update_one({'_id': guild_id},
                    {'$unset': {f'{manager}.{message_id}': ''}})


        if not deleted_message_type:
            return

        try:
            log_channel_id = server['channels']['log']
        except KeyError:
            return
        else:
            guild = self.bot.get_guild(guild_id)
            log_channel = guild.get_channel(log_channel_id)

        embed = discord.Embed(
            title=f"Important message in category *{deleted_message_type}* was deleted!",
            description=f"Message with id {message_id} in channel <#{payload.channel_id}>",
            colour=discord.Colour.red()
        )

        await log_channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_channel_delete(self, deleted_channel):
        '''CHANNEL DELETE HANDLER''' # TODO:  write proper documentation

        guild = deleted_channel.guild

        server = db['Servers'].find_one({'_id': guild.id})
        for name, id in server['channels'].items():
            if deleted_channel.id == id:
                db['Servers'].update_one({'_id': guild.id},
                    {'$unset': {f'channels.{name}': ''}})
                break
        else:
            return

        try:
            log_channel_id = server['channels']['log']
        except KeyError:
            return
        else:
            log_channel = guild.get_channel(log_channel_id)

        embed = discord.Embed(
            title=f"Important channel *{deleted_channel.name}* was deleted!",
            description=f"Channel with id {deleted_channel.id}.",
            colour=discord.Colour.red()
        )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    @commands.bot_has_permissions(manage_roles=True)
    async def on_guild_role_delete(self, deleted_role):
        '''
        On deletion of a role check if it's in server.roles.general or
        server.level_props.roles, if it is, remove it from there and
        send a log update of this happening.
        '''
        guild = deleted_role.guild
        server = db['Servers'].find_one({'_id': guild.id})

        log = False
        for role, role_id in server['roles'].items():
            if role_id == deleted_role.id:
                log = (role, role_id)
                db['Servers'].update_one({'_id': guild.id}, {
                    '$unset': {f'roles.{role}': ''}
                })

        if not log:
            return

        try:
            log_channel_id = server['channels']['log']
        except KeyError:
            return
        else:
            log_channel = guild.get_channel(log_channel_id)

        embed = discord.Embed(
            title="An important role was deleted!",
            description=f"Role for '{log[0]}' with id:{log[-1]} was deleted.",
            colour=discord.Colour.red()
        )
        embed.set_footer(text="This could hamper working of certain features!")

        await log_channel.send(embed=embed)


def setup(bot):
    bot.add_cog(UpdateListenersCog(bot))
