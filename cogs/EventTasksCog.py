import discord
from discord.ext import commands
from utils.database import db


class EventTasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # TODO: IMPLEMENT EVENT ROLE


def setup(bot):
    bot.add_cog(EventTasksCog(bot))
