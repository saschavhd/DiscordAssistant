from datetime import date, datetime
import discord
from discord.ext import commands, tasks
from package_tools import get_shared_guilds
import pytz
from utils.constants import FMT_DATE_NO_YEAR
from utils.database import db


class BirthdayTasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_birthdays.start()

    def cog_unload(self):
        self.check_birthdays.stop()

    @tasks.loop(minutes=5.0)
    async def check_birthdays(self):
        '''Batch updater for birthdays'''

        # Iterate over all users in database
        for user in db['Users'].find():
            # Check if user ever entered a birthday
            try:
                birthday = user['birthday']
                timezone = user['timezone']
            except KeyError:
                continue

            # Check whether it's their birthday
            if (
                datetime.now(pytz.timezone(timezone)).strftime(FMT_DATE_NO_YEAR)
                ==
                birthday.astimezone(pytz.timezone(timezone)).strftime(FMT_DATE_NO_YEAR)
            ):
                update_role = True
            else:
                update_role = False

            guilds = await get_shared_guilds(self.bot, user['_id'])
            for guild in guilds:
                server = db['Servers'].find_one({'_id': guild.id})
                try:
                    role_id = server['roles']['birthday']
                except KeyError:
                    continue
                else:
                    role = guild.get_role(role_id)
                    member = guild.get_member(user['_id'])

                    if update_role:
                        await member.add_roles(role)
                    else:
                        await member.remove_roles(role)

            db['Users'].update_one({'_id': user['_id']},
                {'$set': {'has_birthday_role': update_role}})

            # TODO: ADD BIRTHDAY MESSAGE


def setup(bot):
    bot.add_cog(BirthdayTasksCog(bot))
