from datetime import datetime
import discord
from discord.ext import commands
from utils.constants import EXPRESSIONS
from utils.database import db


class CountingListenersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # Should message be handled?
        # Check if message not by a bot, in textchannel and only containing proper info
        if (
            message.author.bot or
            not isinstance(message.channel, discord.TextChannel) or
            any(char not in EXPRESSIONS and not char.isdigit() for char in message.content)
        ):
            return

        # Get server info and channel id for counting
        guild = message.guild
        server = db['Servers'].find_one({'_id': guild.id})
        try:
            count_channel_id = server['channels']['counting']
        except KeyError:
            return

        # If not in counting channel, return
        if message.channel.id != count_channel_id:
            return

        # Evaluate the expression
        try:
            evaluation = eval(message.content)
        except SyntaxError:
            return

        current = server['counting'].get('current', 1)
        last_counter = server['counting'].get('last_counter', None)

        if evaluation == current and message.author.id != last_counter:
            await message.add_reaction('👍')

            db['Servers'].update_one({'_id': guild.id},
                {'$inc': {'counting.current': 1},
                 '$set': {'counting.last_counter': message.author.id}})

        else:
            await message.add_reaction('👎')
            await message.channel.send(f"{message.author.name} fucked it up at {current}!")

            db['Servers'].update_one({'_id': guild.id},
                {'$set': {'counting.current': 1, 'counting.last_counter': 0}})


def setup(bot):
    bot.add_cog(CountingListenersCog(bot))
