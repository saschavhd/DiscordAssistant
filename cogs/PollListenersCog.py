import discord
from discord.ext import commands
import math
from utils.constants import NUMBER_EMOTES_DISCORD, TOTAL_BARS
from utils.database import db


class PollListenersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_poll(self, payload):
        '''
        Update poll message based on reactions
        Invoked on on_raw_reaction_add or on_raw_reaction_remove
        '''

        # Get query data from database
        server = db['Servers'].find_one({'_id': payload.guild_id})
        try:
            info = server['polls'][str(payload.message_id)]
        except KeyError:
            return  # Message not a poll

        # Retrieve necessary information from Discord Api
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        embed = discord.Embed(title=f":bar_chart: {info['title']}")
        # Get fraction of reactions for every query
        total_reactions = sum([(reaction.count-1) for reaction in message.reactions])
        for ind, reaction in enumerate(message.reactions):
            if total_reactions == 0:
                fraction = 0
            else:
                fraction = (reaction.count-1)/total_reactions


            emote = NUMBER_EMOTES_DISCORD[ind+1]
            query = info['queries'][ind]
            bars = '█'*math.ceil(fraction*TOTAL_BARS)
            empty = ' '*(math.ceil((1-fraction)*TOTAL_BARS))
            percentage = round(fraction*100, 2)
            total = reaction.count - 1

            # Add embedded field depending on the fraction
            embed.add_field(
                name=f"{emote} {query}",
                value=f"`{bars}{empty}`| {percentage}% ({total})",
                inline=False
            )

        await message.edit(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        '''Poll update function on added reaction'''

        if payload.guild_id:
            await self.update_poll(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        '''Poll update function on removed reaction'''

        if payload.guild_id:
            await self.update_poll(payload)

    # @commands.Cog.listener()
    # async def on_raw_message_delete(self, payload):  # Put into batch updater?
    #     '''Poll message deletion handler'''
    #
    #     if (
    #     not payload.guild_id or
    #     not str(payload.message_id) in db['Servers'].find_one({'_id': payload.guild_id})['polls'].keys()
    #     ):
    #         return
    #
    #     db['Servers'].update({'_id': payload.guild_id},
    #     {'$unset': {f'polls.{payload.message_id}': ""}}
    #     )

def setup(bot):
    bot.add_cog(PollListenersCog(bot))
