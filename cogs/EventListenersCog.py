from datetime import datetime
import discord
from discord.ext import commands
import math
from utils.constants import EVENT_COLOUR, EVENT_DISCORD_EMOTES, EVENT_EMOTES, TOTAL_BARS
from utils.database import db


class EventListenersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_event(self, payload):

        server = db['Servers'].find_one({'_id': payload.guild_id})
        try:
            event = server['events'][str(payload.message_id)]
        except KeyError:
            return

        user = self.bot.get_user(payload.user_id)
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        embed = discord.Embed(
            title=event['title'],
            description=event['description'],
            colour=EVENT_COLOUR
        )
        dt_string = event['datetime'].strftime("On %a %d %B %Y @ %H:%M GMT%z")
        embed.set_footer(text=dt_string)

        if str(payload.emoji) not in EVENT_EMOTES.keys():
            await message.remove_reaction(payload.emoji)
        total_reactions = sum([(reaction.count-1) for reaction in message.reactions])
        for ind, reaction in enumerate(message.reactions):
            if total_reactions == 0:
                fraction = 0
            else:
                fraction = (reaction.count-1)/total_reactions

            name = f"{EVENT_DISCORD_EMOTES[ind]} {EVENT_EMOTES[str(reaction.emoji)]}"
            bars = '█'*math.ceil(fraction*TOTAL_BARS)
            empty = ' '*math.ceil((1-fraction)*TOTAL_BARS)
            percentage = round(fraction*100, 2)
            total = reaction.count - 1
            # Add embedded field depending on the fraction
            embed.add_field(
                name=name,
                value=f"`{bars}{empty}`| {percentage}% ({total})"
            )

        await message.edit(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id:
            return

        await self.update_event(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id:
            return

        await self.update_event(payload)


def setup(bot):
    bot.add_cog(EventListenersCog(bot))
