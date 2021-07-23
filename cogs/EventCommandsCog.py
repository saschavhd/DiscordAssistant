from datetime import datetime, date, time
import discord
from discord.ext import commands
import pytz
from utils.constants import EVENT_COLOUR, EVENT_EMOTES, FMT_TIME, NUMBER_EMOTES_UNICODE, TIMEZONE_CATEGORIES, TOTAL_BARS
from utils.database import db
from utils.menu import Menu
from utils.page import EmbeddedPage


class EventCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def event(self, ctx):

        # TITLE PAGE
        def title_description_check(message):
            '''Check if
                - Message by command invoker
                - Message in command invoked channel
            '''

            return (
                message.author == ctx.author and
                message.channel == ctx.channel
            )

        title_page = EmbeddedPage (
            title="Enter the title for your event now!",
            description="Type your response in the chat below!",
            footer="Step 1/6"
        )

        # MENU INIT
        menu = Menu(
            bot=self.bot,
            pages=[title_page],
            interactors=[ctx.author],
            channel=ctx.channel,
            enumerate_with_emoji=True,
            input=title_description_check,
            remove_message_after=True,
            all_embedded=True
        )
        event = {}

        # TITLE INPUT
        input_tuple = await menu.display()
        try:
            title_message, _ = input_tuple
        except TypeError:
            return
        else:
            event['title'] = title_message.content


        # DESCRIPTION PAGE
        description_page = EmbeddedPage (
            title="Enter a description for your event.",
            description="Type your response in the chat below!",
            footer="Step 2/6"
        )

        menu.timeout = 240
        menu.update(pages=[description_page])
        input_tuple = await menu.display(new=False)
        try:
            description_message, _ = input_tuple
        except TypeError:
            return
        else:
            event['description'] = description_message.content


        # TIMEZONE CATEGORY PAGE
        def timezone_check(message):
            '''Check if:
                - Message by command invoker
                - Message in command invoked channel
                - Message is an integer choice between 1 and 10
            '''

            return (
                message.author == ctx.author and
                message.channel == ctx.channel and
                message.content.isdigit() and
                int(message.content) in range(1, 10)
            )

        timezone_catagory_page = EmbeddedPage (
            content = TIMEZONE_CATEGORIES,
            title = "Choose a location!",
            description = "Type your response in the chat below!",
            footer="Step 3/6"
        )
        menu.timeout = 60
        menu.input = timezone_check
        menu.update(pages=[timezone_catagory_page])

        # TIMEZONE CATEGORY INPUT
        input_tuple = await menu.display(new=False)
        try:
            continent_selection, _ = input_tuple
        except TypeError:
            return
        else:
            continent = TIMEZONE_CATEGORIES[int(continent_selection.content)-1]

        # TIMEZONE PAGE
        # Formatting timezone information correct based on chosen category
        timezones = [tz for tz in pytz.all_timezones if tz.startswith(continent)]
        selected_continent_timezones = sorted([
            f"{tz}  ({datetime.now(pytz.timezone(tz)).strftime(FMT_TIME)})" for tz in timezones
        ])

        menu.options['title'] = "Choose your timezone!"
        menu.options['description'] = "Type your response in the chat below!"
        menu.options['footer'] = "Step 4/6"

        per_page = 8
        menu.update(
            pages=[selected_continent_timezones[i:i+per_page]
            for i in range(0, len(timezones)+per_page, per_page)]
        )

        # TIMEZONE INPUT
        input_tuple = await menu.display(new=False)
        try:
            timezone_selection, page = input_tuple
        except TypeError:
            return
        else:
            timezone = timezones[per_page*int(timezone_selection.content)]


        # DATE PAGE
        def date_check(message):
            '''Check if:
                - Message by command invoker
                - Message in command invoked channel
                - Message contains a valid date
            '''

            if not (
                message.author == ctx.author and
                message.channel == ctx.channel
            ):
                return False

            try:
                year, month, day = [int(date_part) for date_part in message.content.split('/')]
                event_date = date(year, month, day)
            except ValueError:
                return False

            return True
            
        date_page = EmbeddedPage(
            title="Enter what day you'd like the event to happen.",
            description="Type your response in the chat below!",
            content="Date should be formatted as follows: YEAR/MONTH/DAY",
            footer="Step 5/6"
        )

        menu.input = date_check
        menu.update(pages=[date_page])
        # DATE INPUT
        input_tuple = await menu.display(new=False)
        try:
            date_message, _ = input_tuple
        except TypeError:
            return
        else:
            year, month, day = [int(date_part) for date_part in date_message.content.split('/')]
            event_date = date(year, month, day)


        # TIME PAGE
        def time_check(message):
            '''Check if:
                - Message by command invoker
                - Message in command invoked channel
                - Message contains a valid date
            '''
            if not (
                message.author == ctx.author and
                message.channel == ctx.channel
            ):
                return False

            try:
                hour, minute = [int(time_part) for time_part in message.content.split(':')]
                event_time = time(hour, minute)
            except (TypeError, ValueError):
                return False

            return True

        time_page = EmbeddedPage (
            title="Enter what time you'd like the event to happen.",
            description="Type your response in the chat below!",
            content="Time should be formatted as follows: HOUR:MINUTE",
            footer="Step 6/6"
        )

        menu.input = time_check
        menu.update(pages=[time_page])

        # TIME INPUT
        input_tuple = await menu.display(new=False)
        try:
            time_message, _ = input_tuple
        except TypeError:
            return
        else:
            hour, minute = [int(time_part) for time_part in time_message.content.split(':')]
            event_time = time(hour, minute)

        # Combining input dat and time
        event['datetime'] = datetime.combine(event_date, event_time)
        event['datetime'] = event['datetime'].astimezone(pytz.timezone(timezone))

        # Creating embed for event-message
        embed = discord.Embed(
            title=event['title'],
            description=event['description'],
            colour=EVENT_COLOUR
        )
        dt_string = event['datetime'].strftime("On %a %d %B %Y @ %H:%M GMT %z")
        embed.set_footer(text=dt_string)

        field_val = f"`{' ' * TOTAL_BARS}` | 0% (0)"
        # Adding event attending fields
        embed.add_field(name=":white_check_mark: Attending", value=field_val)
        embed.add_field(name=":x: Not attending", value=field_val)
        embed.add_field(name=":question: Unsure", value=field_val)

        # Sending message and adding reactions to it.
        event_message = await ctx.send(embed=embed)
        for emoji in EVENT_EMOTES:
            await event_message.add_reaction(emoji)

        # TODO: IMPLEMENT EVENT ROLE

        # attending_role = await ctx.guild.create_role(name=event['title'],
        #                                              colour=EVENT_COLOUR)
        # event['role'] = attending_role.id
        event['channel'] = ctx.channel.id
        db['Servers'].update_one({'_id': ctx.guild.id},
            {'$set': {f'events.{event_message.id}': event}}
        )


def setup(bot):
    bot.add_cog(EventCommandsCog(bot))
