import asyncio
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from package_tools import _warn
import pymongo
from utils.constants import EPOCH, FMT
from utils.database import db


class ModeratorCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Member commands

    # Administrator commands
    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def move(self, ctx, message_id: int, channel: discord.TextChannel):
        message = await ctx.channel.fetch_message(int(message_id))
        if not message:
            return
        content = f"{message.content}"
        for atch in message.attachments:
            content += f"\n{atch.url}"
        await channel.send(f"Message by {message.author.mention}:\n{content}")
        await message.delete()
        await ctx.message.delete()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        '''Remove the last `amount` messages in channel'''

        await ctx.channel.purge(limit=amount+1)
        msg = await ctx.send(f"Deleted {amount} messages in channel {ctx.channel.mention}")
        await asyncio.sleep(2)
        await msg.delete()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(mute_members=True)
    async def mute(self, ctx, member: discord.Member, amount: int=0, time_instance: str='inf'):
        '''Mute a member for a `amount` `time_instance` amount of time'''

        time_instances_in_seconds = {
            'w': 604800,
            'd': 86400,
            'h': 3600,
            'm': 60,
            's': 1,
            'inf': 0
        }

        if time_instance not in time_instances_in_seconds.keys():
            await ctx.send('Invalid time format!')

        total_seconds = amount * time_instances_in_seconds[time_instance]

        if total_seconds == 0:
            dt_target_mute = datetime(2100, 1, 1)
        else:
            dt_target_mute = datetime.utcnow() + timedelta(seconds=total_seconds)

        user = db['Users'].find_one({'_id': member.id})
        try:
            dt_current_mute = user['Servers'][str(ctx.guild.id)]['muted_until']
        except KeyError:
            dt_current_mute = EPOCH

        if dt_current_mute > dt_target_mute:
            await ctx.send(f"{member} is already muted until {dt_current_mute.strftime(FMT)}")
            return

        db['Users'].update_one({'_id': member.id},
            {'$set': {f'servers.{ctx.guild.id}.muted_until': dt_target_mute}})

        server = db['Servers'].find_one({'_id': ctx.guild.id})
        try:
            muted_role_id = server['roles']['muted']
        except KeyError:
            ctx.send("This server does not have a muted role setup! Nothing happened...")
        else:
            muted_role = ctx.guild.get_role(muted_role_id)
            await member.add_roles(muted_role)
            await ctx.send(f"{member} has been muted until {dt_target_mute.strftime(FMT)} GMT+00:00!")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(mute_members=True)
    async def unmute(self, ctx, member: discord.Member):
        '''Remove a user's current mute'''
        db['Users'].update_one({'_id': member.id},
            {'$unset': {f'servers.{ctx.guild.id}.muted_until': ''}})

        server = db['Servers'].find_one({'_id': ctx.guild.id})
        try:
            muted_role_id = server['roles']['muted']
        except KeyError:
            pass
        else:
            muted_role = ctx.guild.get_role(muted_role_id)

        await member.remove_roles(muted_role)

        await ctx.send(f"{member.mention} was unmuted.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(mute_members=True)
    async def warn(self, ctx, member: discord.Member, *reason):
        '''Warn a user'''

        await _warn(member, ctx.guild, reason)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(mute_members=True)
    async def unwarn(self, ctx, member: discord.Member, amount: int=1):
        '''Remove `amount` warnings from user'''

        current_warnings_count = db['Users'].find_one(
        {'_id': member.id})['servers'][str(ctx.guild.id)]['warnings']

        if amount > current_warnings_count:
            amount = current_warnings_count

        db['Users'].update_one({'_id': member.id},
        {'$inc': {f'servers.{ctx.guild.id}.warnings': -amount}})

        await ctx.send(f"{member.name} now has {current_warnings_count-amount} of warnings left.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def ban_word(self, ctx, word: str):
        '''Add a word to the list of banned_words'''

        db['Servers'].update_one({'_id': ctx.guild.id},
            {'$addToSet': {'banned_words': word.strip().lower()}})
        msg = await ctx.send(f"Word ||{word}|| has been added to the ban list.")
        await asyncio.sleep(5)
        await msg.delete()
        await ctx.message.delete()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def show_banned_words(self, ctx):
        '''Show an array of all the banned words'''

        await ctx.send(db['Servers'].find_one({'_id': ctx.guild.id})["banned_words"])

def setup(bot):
    bot.add_cog(ModeratorCommandsCog(bot))
