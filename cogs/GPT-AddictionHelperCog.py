import asyncio
import discord
from discord.ext import commands
import openai
from utils.constants import OPENAI_API_KEY
from utils.menu import Menu
from utils.page import Page

openai.api_key = OPENAI_API_KEY


class AddictionHelperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.prompt = """
A conversation between a human with an alcohol addiction and an AI attempting to help said human:

AI: What addiction are you struggling with?
"""

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def adhelp(self, ctx):
        if not ctx.channel.nsfw:
            await ctx.send("This command can only be used in NSFW channels!")
            return

        def check(message):
            return (
                message.author == ctx.author and
                message.channel == ctx.channel
            )
        prompt = self.prompt
        await ctx.send("What addiction are you struggling with? (send 'end' to end conversation)")
        for _ in range(10):
            try:
                inp = await self.bot.wait_for('message', timeout=60, check=check)
            except asyncio.TimeoutError:
                await ctx.send("Timed out!")
                return
            if inp.content == "end":
                return
            prompt += "Human: " + inp.content + "\n"

            response = openai.Completion.create(
                engine="davinci",
                prompt=prompt,
                temperature=0.7,
                max_tokens=350,
                top_p=1.0,
                frequency_penalty=0.5,
                presence_penalty=0.25,
                stop=["\n"]
            )

            output = response['choices'][0]['text']
            prompt += output + "\n"
            await ctx.send(output.strip('AI:'))


def setup(bot):
    bot.add_cog(AddictionHelperCog(bot))
