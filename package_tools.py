import asyncio
import collections
import discord
from discord.ext import commands
from datetime import datetime
import emoji
import math
import pymongo
import re
from typing import Union
from utils.database import db, DEFAULT_SERVER, DEFAULT_USER
from utils.constants import DEFAULT_CHANNELS, DEFAULT_ROLES, FMT, MAX_LEVEL, NUMBER_EMOTES_DISCORD, TOTAL_BARS



def level_to_exp(level: int) -> int:
    return 1000 * sum(range(level+1))


def exp_to_level(exp: int) -> int:
    total = 0
    for i in range(MAX_LEVEL):
        total += i
        if total * 1000 > exp:
            return i - 1
    return MAX_LEVEL


def get_emoji_number(number: int) -> str:
    '''
    Turns postive integer into discord emoji

    Parameters:
    -----------
        number: :class:`int`
            Integer to convert to emoji string

    Returns:
    --------
        emoji_number: :class:`str`
            (Combined) string version of the integer
    '''

    if number < 0:
        raise NotImplementedError("Method _get_emoji_number does not yet ",
        "convert negative integers.")

    emoji_number = ''
    for char in str(number):
        emoji_number += f"{NUMBER_EMOTES_DISCORD[int(char)]}"
    return emoji_number


def add_user_to_database(member: discord.Member):
    '''
    Setup configuration settings for new member,
    bundle and store data in database.

    Paramaters:
    -----------
        member: discord.Member
            Member to add.
    '''

    if member.bot:
        return

    guild = member.guild
    user = db['Users'].find_one({'_id': member.id})
    if not user:
        user = DEFAULT_USER
        user['_id'] = member.id

    try:
        server = user['servers'][str(guild.id)]
    except KeyError:
        server = {
            'join_date': datetime.utcnow(),
            'experience': 0
        }
    else:
        try:
            del server['leave_date']
        except KeyError:
            pass
    finally:
        db['Users'].update_one({'_id': member.id},
            {'$set': {f'servers.{guild.id}': server}}, upsert=True)


async def get_shared_guilds(bot: commands.Bot, user_id: int) -> list:
    '''
    Return a list of guilds shared between current bot and user

    Parameters:
    -----------
        bot: :class:`commands.Bot`
            Passthrough of Bot object.
        user: :class:`discord.User`
            User of which you want the communal guilds.

    Returns:
    --------
        shared_guilds: :class:`list`
            List of the shared guilds
    '''

    shared_guilds = []
    for guild in bot.guilds:
        if guild.get_member(user_id):
            shared_guilds.append(guild)

    return shared_guilds


async def _warn(member: discord.Member, guild: discord.Guild, *reason: tuple):
    '''
    Give a user a warning and update their warn count in database.
    If guild log channel is set up, log the warning there.

    Parameters:
    -----------
        member: :class:`discord.Member`
            Member the warning will be applied to.
        guild: :class:`discord.Guild`
            Guild the member will receive their warning in.
        reason: :class:`tuple`
            The reason for the warning, this could be set manually by an
            executer or passed through by an automated function
    '''

    # Handle any input for reason
    if not isinstance(reason[0], str):
        reason = ' '.join(list(reason[0]))
    else:
        reason = reason[0]

    if not reason:
        reason = "No reason given."

    # Increment total warnings count for user in guild
    db['Users'].update_one({'_id': member.id},
        {'$inc': {f'servers.{guild.id}.warnings': 1}})

    # Get current amount of warnings
    current_warnings_count = db['Users'].find_one(
        {'_id': member.id})['servers'][str(guild.id)]['warnings']

    # Get log channel
    server = db['Servers'].find_one({'_id': guild.id})
    try:
        log_channel_id = server['channels']['log']
    except KeyError:
        return
    else:
        log_channel = guild.get_channel(log_channel_id)

    # Setting up log message embed
    embed = discord.Embed(
        title=f"Member {member.name}:{member.id} was warned!",
        description=f"This was their warning number {current_warnings_count}.",
        colour=discord.Colour.orange()
    )
    embed.add_field(name="Reason: ", value=reason, inline=False)

    await log_channel.send(embed=embed)


async def _setup(guild):
    '''Setting up a guild'''

    # Check if bot already knows server
    server = db['Servers'].find_one({'_id': guild.id})
    if not server:
        server = DEFAULT_SERVER
        server['_id'] = guild.id
    # Server properties setup
    # Channels
    for channel_name in DEFAULT_CHANNELS:
        if channel_name in server['channels'].keys():
            continue

        channel = await guild.create_text_channel(channel_name)
        server['channels'][channel_name] = channel.id

    # Roles
    # Muted role
    try:
        muted_role_id = server['roles']['muted']
    except KeyError:
        muted_role_id = 0

    if not guild.get_role(muted_role_id):
        muted_role = await guild.create_role(name="muted", colour=discord.Colour.red())
        server['roles']['muted'] = muted_role.id
        try:
            await muted_role.edit(position=guild.default_role.position+1)
        except discord.Forbidden:
            pass

        for text_channel in guild.text_channels:
            perms = text_channel.overwrites_for(muted_role)
            perms.send_messages = False
            perms.add_reactions = False
            await text_channel.set_permissions(muted_role, overwrite=perms)

        for voice_channel in guild.voice_channels:
            perms = voice_channel.overwrites_for(muted_role)
            perms.speak = False
            await voice_channel.set_permissions(muted_role, overwrite=perms)

    try:
        birthday_role_id = server['roles']['birthday']
    except KeyError:
        birthday_role_id = 0
    # Birthday role
    if not guild.get_role(birthday_role_id):
        birthday_role = await guild.create_role(name="It's my birthday!", colour=discord.Colour.gold())
        server['roles']['birthday'] = birthday_role.id
        try:
            await birthday_role.edit(position=guild.default_role.position+1)
        except discord.Forbidden:
            pass

    # Adding information to database
    db['Servers'].replace_one({'_id': guild.id}, server, upsert=True)


async def _leave(guild):
        '''Makes bot leave guild and delete it's features'''

        db['Servers'].delete_one({'_id': guild.id})

        db['Users'].update_many({'servers': str(guild.id)},
            {'$unset':
                {f'servers.{guild.id}'}
            }
        )

        await guild.leave()


async def _purge(guild):
    '''Purging all channels and roles from guild'''

    try:
        for channel in guild.text_channels + guild.voice_channels:
            await channel.delete()
    except discord.Forbidden:
        print(f"[{datetime.utcnow().strftime(FMT)}]\t",
              "Purge with insufficient permissions was attempted on guild:",
              f"{guild.name} - {guild.id}")

    try:
        for role in guild.roles[1:]:
            await role.delete()
    except discord.Forbidden:
        print(f"[{datetime.utcnow().strftime(FMT)}]\t",
              "Purge with incomplete permissions was attempted on guild:",
              f"{guild.name} - {guild.id}. (Damage was done)")

    else:
        print(f"[{datetime.utcnow().strftime(FMT)}\t]",
              f"Purge successfull on guild: {guild.name} - {guild.id}")
