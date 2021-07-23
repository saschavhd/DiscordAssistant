import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from utils.constants import FMT, FMT_DATE, FMT_TIME, TIMEZONE_CATEGORIES
from utils.database import db
from utils.menu import Menu
from utils.page import Page, EmbeddedPage
import pytz
import re

FMT = '%y-%m-%d %H:%M:%S'
FMT_DATE = '%y-%m-%d'
FMT_DATE_NO_YEAR = "%m-d"
FMT_TIME = '%H:%M'


class BirthdayCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def birthday(self, ctx):
        user = db['Users'].find_one({'_id': ctx.author.id})
        try:
            birth_date = user['birthday']
            timezone = user['timezone']
        except KeyError:
            prefix = db['Servers'].find_one({'_id': ctx.guild.id})['prefix']
            await ctx.send(f"You have not setup a birthday yet! Command: {prefix}set_birthday")
            return
        else:
            birthday = birth_date.replace(year=datetime.utcnow().year)
            birthday = birthday.astimezone(pytz.timezone(timezone))
            birthday = birthday.strftime("%a %d %B")

        await ctx.send(f"Your birthday this year: {birthday}")


    @commands.command()
    async def set_birthday(self, ctx):
        '''Setup the birthday of a member'''

        # Setup DM channel with user.
        dm_channel = await ctx.author.create_dm()

        def timezone_check(message):
            '''Check if:
                - Message by command invoker
                - Message in command invoked channel
                - Message is an integer choice between 1 and 10.
            '''

            return (
                message.author == ctx.author and
                message.channel == dm_channel and
                message.content.isdigit() and
                int(message.content) in range(1, 10)
            )

        timezone_catagory_page = EmbeddedPage (
            content = TIMEZONE_CATEGORIES,
            title = "Choose a location!",
            description = "Type your response in the chat below!"
        )

        # Menu creation
        menu = Menu(
            bot=self.bot,
            pages=[timezone_catagory_page],
            interactors=[ctx.author],
            channel=dm_channel,
            enumerate_with_emoji=True,
            input=timezone_check,
            remove_message_after=True,
            all_embedded = True
        )

        # Continent selection handling (user input)
        input_tuple = await menu.display()
        try:
            selection, _ = input_tuple
        except TypeError:
            return
        else:
            continent = TIMEZONE_CATEGORIES[int(selection.content)-1]

        # Generating new information
        timezones = [tz for tz in pytz.all_timezones if tz.startswith(continent)]
        selected_continent_timezones = sorted([
            f"{tz}  ({datetime.now(pytz.timezone(tz)).strftime(FMT_TIME)})" for tz in timezones
        ])

        # Updating menu information & properties
        menu.options['title'] = "Choose your timezone!"
        menu.options['description'] = "Type your response in the chat below!"

        per_page = 8
        pages=[
            selected_continent_timezones[i:i+per_page]
            for i in range(0, len(timezones), per_page)
        ]

        # Setting up pages
        menu.update(pages=pages)

        # Timezone selection handling (user input)
        input_tuple = await menu.display(new=False)
        try:
            selection, page = input_tuple
        except TypeError:
            return
        else:
            sel_index = int(selection.content) - 1
            timezone = re.sub('\([0-9]{2}:[0-9]{2}\)$', '', page.content[sel_index]).rstrip()

        menu.options['title'] = f"You have chosen {timezone} as your timezone."
        menu.options['description'] = ' '.join(("Please enter your birthday (YYYY/MM/DD) now!",
        "If you don't want to you need not provide your year of birth."))

        def birthday_check(message):
            '''Generic checker function'''

            return (
                not message.author.bot and
                message.author == ctx.author and
                message.channel == dm_channel and
                re.match("([0-9]{4}/|)[0-9]{1,2}/[0-9]{1,2}", message.content)
            )

        # Updating menu pages & properties
        menu.input = birthday_check

        while True:
            menu.update(
                pages=["Once it's your birthday you'll get a notification and a role in this server for the duration!"]
            )

            # Birthday input handling
            try:
                input, _ = await menu.display(new=False, reset_position=True)
            except TypeError:
                return
            else:
                birthday_string = input.content

            # Prepare datetime object creation
            birthday_seq = [int(date_part) for date_part in birthday_string.split('/')]
            if len(birthday_seq) == 2:
                year, date, month = 1970, birthday_seq[1], birthday_seq[2]
            else:
                year, date, month = birthday_seq

            # Make datetime object and check if valid
            try:
                birthday = datetime(year, date, month)
            except ValueError:
                menu.options['title'] = "Woah that's not a valid birthday! Try again."
                continue
            else:
                if birthday > datetime.utcnow():
                    menu.options['title'] = "Living in the future hu? ;)"
                    continue
                else:
                    break

        await menu.stop()
        # Update database information
        db['Users'].update_one({'_id': ctx.author.id},
            {'$set': {
                'birthday': birthday,
                'timezone': timezone,
                'has_birthday_role': False
                }
            }
        )

        await dm_channel.send(f"Your birthday has been updated to {birthday.strftime(FMT_DATE)}!")


def setup(bot):
    bot.add_cog(BirthdayCommandsCog(bot))
