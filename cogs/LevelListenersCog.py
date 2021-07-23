from datetime import datetime
import discord
from discord.ext import commands
from package_tools import exp_to_level
from utils.constants import DEFAULT_EXP_INCREASE, EPOCH
from utils.database import db


class LevelListenerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):

        # Check if message by bot or message a DM.
        if (
            message.author.bot or
            isinstance(message.channel, discord.DMChannel) or
            message.channel.id in db['Servers'].find_one(
                {'_id': message.guild.id})['channels']['ignore_exp']
        ):
            return

        # Look for total current experience and last experience gain in db.
        try:
            user_server_info = db['Users'].find_one(
                {'_id': message.author.id})['servers'][str(message.guild.id)]
            experience = user_server_info['experience']
            last_experience_gain = user_server_info['last_experience_gain']
        except KeyError:
            experience = 0
            last_experience_gain = EPOCH
        else:
            # If last gain was less than 60 seconds ago then abort.
            if (datetime.utcnow() - last_experience_gain).total_seconds() < 60:
                return

        # Check if user leveled up
        old_level = exp_to_level(experience)
        current_level = exp_to_level(experience + DEFAULT_EXP_INCREASE)
        if current_level > old_level:
            await message.channel.send(f"{message.author.name} leveled up to {current_level}! Congratulations :partying_face:")

            server_roles = db['Servers'].find_one({'_id': message.guild.id})['roles']
            try:
                new_level_role_id = server_roles[str(current_level)]
            except KeyError:
                pass
            else:
                # Remove old roles and add new one
                member_role_ids = [role.id for role in message.author.roles]
                for role_name, role_id in server_roles.items():
                    if (role_id in member_role_ids and
                        role_name.isdigit() and
                        int(role_name) < current_level):
                        old_role = message.guild.get_role(role_id)
                        await message.author.remove_roles(old_role)
                        break
                new_role = message.guild.get_role(new_level_role_id)
                await message.author.add_roles(new_role)

        # Update databse information
        db['Users'].update_one({'_id': message.author.id},
            {'$inc': {f'servers.{message.guild.id}.experience': DEFAULT_EXP_INCREASE},
             '$set': {f'servers.{message.guild.id}.last_experience_gain': datetime.utcnow()}}
        )


def setup(bot):
    bot.add_cog(LevelListenerCog(bot))
