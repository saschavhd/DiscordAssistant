import discord
from discord.ext import commands
from utils.constants import NUMBER_EMOTES_DISCORD, NUMBER_EMOTES_UNICODE, TOTAL_BARS
from utils.database import db


class PollCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def poll(self, ctx):
        def message_check(message):
            '''Generic checker function'''
            return (
            message.author == ctx.author and
            message.channel == ctx.channel
            )

        # Get poll question/title
        msg = await ctx.send("Enter your poll question")
        while True:
            try:
                poll = await self.bot.wait_for("message", timeout=60, check=message_check)
            except asyncio.TimeoutError:
                await ctx.send("Timed out! Please start over.")
                return
            else:
                break

        # Get poll entries
        queries = []
        count = 1
        while count < 10:
            await msg.edit(content=f"Enter response query ({count}) - 'done' to finish.")
            while True:
                try:
                    query = await self.bot.wait_for("message", timeout=60, check=message_check)
                except asyncio.TimeoutError:
                    await ctx.send("Timed out! Please start over.")
                    return
                else:
                    queries.append(query.content)
                    count += 1
                    break
            if query.content.lower() == "done":
                queries.pop()
                break
        else:
            await ctx.send("Maximum poll queries reached!")

        # Setup embed for poll message
        embed = discord.Embed(title=f":bar_chart: {poll.content}")

        for ind, query in enumerate(queries):
            embed.add_field(
            name=f"{NUMBER_EMOTES_DISCORD[ind+1]} {query}",
            value=f"`{' '*TOTAL_BARS}`| 0% (0)",
            inline=False
            )

        # Remove operation messages
        await ctx.channel.purge(limit=4+len(queries))

        # Send poll message & add oppropriate reactions
        poll_message = await ctx.send(embed=embed)

        for i in range(len(queries)):
            await poll_message.add_reaction(NUMBER_EMOTES_UNICODE[i])

        # Save data in database
        db['Servers'].update_one({'_id': ctx.guild.id},
            {'$set': {
                f'polls.{poll_message.id}.channel': ctx.channel.id,
                f'polls.{poll_message.id}.title': poll.content,
                f'polls.{poll_message.id}.queries': queries
                }
            }
        )


def setup(bot):
    bot.add_cog(PollCommandsCog(bot))
