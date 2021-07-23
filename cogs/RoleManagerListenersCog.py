import asyncio
import discord
from discord.ext import commands
from utils.database import db


class RoleManagerListenersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id:
            return

        server = db['Servers'].find_one({'_id': payload.guild_id})
        try:
            manager = server['role_managers'][str(payload.message_id)]
        except KeyError:
            return

        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        member = guild.get_member(payload.user_id)
        message = await channel.fetch_message(payload.message_id)

        try:
            role_id = manager['roles'][str(payload.emoji)]
        except KeyError:
            await message.remove_reaction(payload.emoji, member)
            return

        if member.bot: return

        member_role_ids = [role.id for role in member.roles]
        if not manager['multi']:
            if any(id in member_role_ids for id in manager['roles'].values()):
                await message.remove_reaction(payload.emoji, member)
                return

        role = guild.get_role(role_id)

        await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id:
            return

        server = db['Servers'].find_one({'_id': payload.guild_id})
        try:  # Check if message a role manager
            manager = server['role_managers'][str(payload.message_id)]
        except KeyError:
            return

        try:  # Check if reaction has corresponding role stored.
            role_id = manager['roles'][str(payload.emoji)]
        except KeyError:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)

        if member.bot: return

        role = guild.get_role(role_id)

        await member.remove_roles(role)

def setup(bot):
    bot.add_cog(RoleManagerListenersCog(bot))
