import asyncio
import discord
from discord.ext import commands
from datetime import datetime
import pymongo
from utils.constants import DEFAULT_PREFIX, DISCORD_API_KEY, FMT, OPENAI_API_KEY
from utils.database import db


GPT_ENABLED = True # CHANGE THIS IF YOU DO NOT HAVE A GPT-3 Beta key
intents = discord.Intents.all()


def prefix(bot, message):
    try:
        return db['Servers'].find_one({'_id': message.guild.id})['prefix']
    except (AttributeError, TypeError):
        return DEFAULT_PREFIX


bot = commands.Bot(command_prefix=prefix, intents=intents)

extensions = [
    "cogs.BirthdayCommandsCog",
    "cogs.CountingListenersCog",
    "cogs.EventCommandsCog",
    "cogs.EventListenersCog",
    "cogs.LevelCommandsCog",
    "cogs.LevelListenersCog",
    "cogs.MarriageCommandsCog",
    "cogs.ModeratorCommandsCog",
    "cogs.ModeratorListenersCog",
    "cogs.PollCommandsCog",
    "cogs.PollListenersCog",
    "cogs.RoleManagerCommandsCog",
    "cogs.RoleManagerListenersCog",
    "cogs.SetupCommandsCog",
    "cogs.SetupListenersCog",
]

task_cogs = [
    "cogs.BatchUpdaterCog",
    "cogs.BirthdayTasksCog",
    "cogs.UpdateListenersCog"
]

gpt_cogs = [
    "cogs.GPT-AddictionHelperCog",
    "cogs.GPT-JokeCog",
    "cogs.GPT-StoryCog"
]

@bot.event
async def on_ready():
    print(f"[{datetime.utcnow().strftime(FMT)}]\t Discord Assistant ready!")
    await load()


async def load():
    try:
        for ext in extensions:
            bot.load_extension(ext)

        if OPENAI_API_KEY:
            for ext in gpt_cogs:
                bot.load_extension(ext)

        await asyncio.sleep(3)

        for ext in task_cogs:
            bot.load_extension(ext)

    except commands.errors.ExtensionAlreadyLoaded:
        print(f"[{datetime.utcnow().strftime(FMT)}]\t Bot reloading...")
        return


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on a {round(error.retry_after, 1)} cooldown")

    if isinstance(error, commands.BadArgument):
        await ctx.send("Invalid format! Please try again.")

    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Invalid format! Please try again.")
    raise error


bot.run(DISCORD_API_KEY)
