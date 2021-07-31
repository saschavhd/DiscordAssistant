from datetime import datetime
import discord
import os

DISCORD_API_KEY = os.getenv('apikey_discordassistant')
MONGODB_API_KEY = os.getenv('apikey_mongodb_discordassistant')
OPENAI_API_KEY = os.getenv('apikey_openai')

DEFAULT_CHANNELS = ['spawn', 'eject', 'log', 'birthday', 'counting']
DEFAULT_EXP_INCREASE = 100
DEFAULT_PREFIX = '.'
DEFAULT_ROLES = ['muted', 'birthday']
DEFAULT_MANAGERS = ['role_managers', 'polls', 'events']

EPOCH = datetime(1970, 1, 1)
EVENT_COLOUR = discord.Colour.purple()
EVENT_DISCORD_EMOTES = [':white_check_mark:', ':question:', ':x:']
EVENT_EMOTES = {
    '✅': "Attending",
    '❌': "Not attending",
    '❓': "Unsure"
}
EXPRESSIONS = ["*", "/", "+", "-", "%", "(", ")", " ", "."]

FMT = '%y-%m-%d %H:%M:%S'
FMT_DATE = '%y-%m-%d'
FMT_DATE_NO_YEAR = "%m-%d"
FMT_TIME = '%H:%M'

"""
LEVELS = {
    1: 0,
    2: 1000,
    3: 3000,
    4: 6000,
    5: 10000,
    6: 15000,
    7: 21000,
    8: 28000,
    9: 36000,
    10: 45000,
    11: 55000,
    12: 66000,
    13: 78000,
    14: 91000,
    15: 105000,
    16: 120000,
    17: 136000,
    18: 153000,
    19: 171000,
    20: 190000
}
"""

NUMBER_EMOTES_DISCORD = [
    ":zero:",
    ":one:",
    ":two:",
    ":three:",
    ":four:",
    ":five:",
    ":six:",
    ":seven:",
    ":eight:",
    ":nine:"
]
NUMBER_EMOTES_UNICODE = [
    "\u0031\uFE0F\u20E3",
    "\u0032\uFE0F\u20E3",
    "\u0033\uFE0F\u20E3",
    "\u0034\uFE0F\u20E3",
    "\u0035\uFE0F\u20E3",
    "\u0036\uFE0F\u20E3",
    "\u0037\uFE0F\u20E3",
    "\u0038\uFE0F\u20E3",
    "\u0039\uFE0F\u20E3"
]

MAX_LEVEL = 100

TIMEZONE_CATEGORIES = [
    "Africa",
    "America",
    "Asia",
    "Atlantic",
    "Australia",
    "Europe",
    "Pacific",
    "US",
    "Etc/GMT"
]

TOTAL_BARS = 20

CHAT_FORMATTERS: {
    'cursive': '*{}*',
    'bold': '**{}**',
    'curisve_bold': '***{}***',
    'spoiler': '||{}||',
    'engraved_relief': '`{}`'
}
