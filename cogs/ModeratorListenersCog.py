from datetime import datetime
import discord
from discord.ext import commands
import emoji
from package_tools import _warn
import re
from utils.constants import FMT
from utils.database import db


class ModeratorListenersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        '''Illegal message handler'''

        # Check if:
        #   - Message in guild TextChannel
        #   - Message not by bot
        #   - Message is command to ban word
        if (
            not isinstance(message.channel, discord.TextChannel) or
            message.author.bot or
            re.match('^.ban_word .*', message.content)
        ):
            return

        # Retrieve list of banned words from database
        banned_words = db['Servers'].find_one({'_id': message.guild.id})['banned_words']

        # Search for word in text
        for word in banned_words:
            if re.search(word, message.content.replace(" ", ""), re.IGNORECASE):
                reason = f"Use of banned word(s): ||{word}||"
                await _warn(message.author, message.guild, reason)
                await message.delete()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        '''Logging of message deletes'''

        # Check if message in a guild
        if not payload.guild_id: return

        # Retrieve log channel id and get channel object
        server = db['Servers'].find_one({'_id': payload.guild_id})
        try:
            log_channel_id = server['channels']['log']
        except KeyError:
            return
        else:
            log_channel = self.bot.get_channel(log_channel_id)

        if not payload.cached_message:
            embed = discord.Embed(
                title="A message was deleted!",
                description=f"Message with id {payload.message_id} in channel <#{payload.channel_id}>.",
                colour=discord.Colour.red()
            )
            await log_channel.send(embed=embed)
            return

        if (
            payload.cached_message.author.bot or
            re.match('^(Deleted [0-9]+).*', payload.cached_message.content)
        ):
            return
        message = payload.cached_message

        # Setting up log message embed
        embed = discord.Embed(
            title=f"Message by {message.author}:{message.author.id} was deleted!",
            description=f"Message {message.id} from channel: <#{payload.channel_id}>",
            colour=discord.Colour.dark_red()
        )

        # Differentiating message content and adding embed fields accordingly
        if message.attachments and message.content:
            embed.add_field(name="**Content: **", value=f"{message.content}", inline=False)
            embed.add_field(name="**Attachment: **", value=f"[View]({message.attachments[0].url})", inline=False)
        elif message.attachments:
            embed.add_field(name="**Attachment: **", value=f"[View]({message.attachments[0].url})", inline=False)
        elif message.content:
            embed.add_field(name="**Content: **", value=f"{message.content}", inline=False)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        '''Logging of message edits'''

        # Check if guild id is present in payload data
        # If not -> message was not sent in a guild
        try:
            guild_id = int(payload.data['guild_id'])
        except KeyError:
            return

        server = db['Servers'].find_one({'_id': guild_id})
        try:
            log_channel_id = server['channels']['log']
        except KeyError:
            return
        else:
            log_channel = self.bot.get_channel(log_channel_id)


        # Get necessary information from Discord Api
        guild = self.bot.get_guild(guild_id)
        channel_id = int(payload.data['channel_id'])
        channel = guild.get_channel(channel_id)

        # Get log channel
        message_after = await channel.fetch_message(payload.message_id)
        if message_after.author.bot:
            return

        if not payload.cached_message:
            embed = discord.Embed(
                title="A message was edited!",
                description=f"Message {message_after.id} in channel <#{channel_id}>.",
                colour=discord.Colour.orange()
            )
            embed.add_field(name="Content", value=message_after.content)
            await log_channel.send(embed=embed)
            return

        message_before = payload.cached_message
        if message_before == message_after:
            return

        # Setting up log message embed
        embed = discord.Embed(
            title=f"Message by {message_before.author.name}:{message_before.author.id} was edited!",
            description=f"Message {message_before.id} has in channel: {message_before.channel.mention}",
            colour=discord.Colour.orange()
        )

        # Differentiating message types and adding embed fields accordingly
        if message_before.attachments:
            embed.add_field(
                name="**Involved attachment: **",
                value=f"[view]({message_before.attachments[0].url})",
                inline=False
            )
        elif message_after.attachments:
            embed.add_field(
                name="**Involved attachment: **",
                value=f"[view]({message_after.attachments[0].url})",
                inline=False
            )

        # Making sure embed field values are never empty
        if not message_before.content:
            message_before.content = "*NO CONTENT*"
        if not message_after.content:
            message_after.content = "*NO CONTENT*"

        embed.add_field(name="**Before: **", value=f"{message_before.content}", inline=False)
        embed.add_field(name="**After: **", value=f"{message_after.content}", inline=False)

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        '''Logging of bulk message deletes'''

        # Init information about guild and action performer
        guild_id = messages[-1].guild.id
        deleter, channel = messages[-1].author, messages[-1].channel

        # Get log channel from database
        server = db['Servers'].find_one({'_id': guild_id})
        try:
            log_channel_id = server['channels']['log']
        except KeyError:
            return
        else:
            log_channel = self.bot.get_channel(log_channel_id)

        # Reformat and write messages to text file
        with open(f"bulk_delete_logs/{guild_id}.txt", 'w') as f:
            print(
                f"Bulk delete by {deleter.name}:{deleter.id} at",
                f"{datetime.utcnow().strftime(FMT)}",
                end="\n\n", file=f
            )
            for message in messages:
                # Filter emoji's
                message.content = emoji.demojize(message.content)

                # Remove 'Zero Width Space' unicodes
                message.content = re.sub('U200B', 'ZWS', message.content)

                # Add attachment url if necessary
                if not message.content and message.attachments:
                    message.content = f"Attachment[{message.attachments[0].url}]"
                elif message.content and message.attachments:
                    message.content += f" | Attachment[{message.attachments[0].url}]"

                try:
                    print(
                        f"[{message.created_at.strftime(FMT)}]",
                        f"| By: {message.author}:{message.author.id}",
                        f"| In: {channel.id} | Containing: {message.content}",
                        end="\n\n", file=f
                    )
                except UnicodeEncodeError:
                    pass

        # Setting up log message embed
        embed = discord.Embed(
            title=f"Bulk delete by {deleter.name}:{deleter.id}!",
            description=f"Purge action performed in channel: {channel.mention}",
            colour=discord.Colour.purple()
        )
        embed.add_field(name="Content: ", value="See attached txt file!")
        await log_channel.send(embed=embed)

        # Sending log file
        with open(f"bulk_delete_logs/{guild_id}.txt", 'rb') as f:
            file_name = f"[{datetime.utcnow().strftime(FMT)}]_bulk_delete.txt"
            await log_channel.send(file=discord.File(f, file_name))

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        '''Logging of kicks and bans'''

        # Get last audit log entry and check if seconds gone by since entry
        # is lower than 2.5
        # This could perform poorly when either guild or bot are
        # under heavy loads.
        async for entry in member.guild.audit_logs(limit=1):
            act = entry
            if (datetime.utcnow()-entry.created_at).total_seconds() > 2.5:
                return

        # Get performed action (kick or ban)
        if str(act.action) == "AuditLogAction.kick":
            action = "kicked"
        elif str(act.action) == "AuditLogAction.ban":
            action = "banned"
        else:
            return

        # Get log channel from database
        server = db['Servers'].find_one({'_id': member.guild.id})
        try:
            log_channel_id = server['channels']['log']
        except KeyError:
            return
        else:
            log_channel = self.bot.get_channel(log_channel_id)

        # Setting up log message embed
        embed = discord.Embed(
            title=f"Member {member.name}:{member.id} was {action}!",
            description=f"Punishment performed by: {act.user.name}:{act.user.id}",
            colour=discord.Colour.gold()
        )

        # Check reason and add it as embed field
        if not act.reason:
            act.reason = 'No reason given.'
        embed.add_field(name="Reason: ", value=act.reason)

        await log_channel.send(embed=embed)


def setup(bot):
    bot.add_cog(ModeratorListenersCog(bot))
